#!/usr/bin/env python3
"""
Segmentation Pipe: Executes the second phase of the PDF processing pipeline.
Iterates over 'safe' books (those with valid metadata), uses AI to generate 
pdftk commands via `get_gemini_response` with strategic model rotation, 
and splits the PDFs into chapter-level files.
"""

import os
import json
import subprocess
import logging
import pypdf
from datetime import datetime

# Importaciones del proyecto
from get_gemini_response import get_gemini_response
from prompt_generator import generate_segmentation_prompt

# --- Configuración de Rutas ---
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
CLASSIFICATIONS_FILE = os.path.join(PROJECT_ROOT, "book_classifications.jsonl")
OUTPUT_DIR_BASE = os.path.join(PROJECT_ROOT, "segmented_output", "BOOKS")
SEGMENTATION_LOG_FILE = os.path.join(PROJECT_ROOT, "logs", "segmentation_log.jsonl")

# --- Configuración de Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

os.makedirs(os.path.dirname(SEGMENTATION_LOG_FILE), exist_ok=True)


def segment_single_book(pdf_path: str, output_base_dir: str, classification_data: dict) -> dict:
    """
    Orquesta la segmentación de un único libro: extrae marcadores, genera prompt con IA,
    parsea comandos y ejecuta pdftk para crear los archivos segmentados.
    """
    logging.info(f"--- Iniciando Segmentación para: {os.path.basename(pdf_path)} ---")
    
    # 1. Preparación de Directorios de Salida
    book_folder_name = os.path.splitext(os.path.basename(pdf_path))[0]
    dest_folder = os.path.join(output_base_dir, book_folder_name)
    
    try:
        os.makedirs(dest_folder, exist_ok=True)
        logging.info(f"Directorio de salida creado/verificado: {dest_folder}")
    except OSError as e:
        logging.error(f"Error creando directorio {dest_folder}: {e}")
        return {"status": "failed", "reason": f"Directory creation failed: {e}"}

    try:
        # 2. Extracción de Bookmarks (ToC) del PDF
        reader = pypdf.PdfReader(pdf_path)
        
        # Función auxiliar recursiva robusta
        def extract_bookmarks(outline, level=0):
            items = []
            
            if not hasattr(outline, '__iter__'):
                return items

            for item in outline:
                try:
                    page_num = reader.get_destination_page_number(item) + 1
                except Exception:
                    page_num = -1
                
                current = {
                    "title": getattr(item, 'title', 'Untitled'),
                    "page": page_num,
                    "level": level,
                    "type": str(type(item).__name__)
                }
                items.append(current)
                
                children = getattr(item, 'children', None)
                
                if isinstance(children, list) and children:
                    items.extend(extract_bookmarks(children, level + 1))
                
                elif callable(children):
                    try:
                        potential_list = children()
                        if isinstance(potential_list, list) and potential_list:
                            items.extend(extract_bookmarks(potential_list, level + 1))
                    except:
                        pass

            return items

        outline_data = extract_bookmarks(reader.outline)
        
        if not outline_data:
            raise ValueError("No bookmarks found or extracted successfully. Cannot proceed with segmentation.")

        # 3. Total de páginas y metadatos auxiliares
        total_pages = len(reader.pages)

        # 4. Generación del Prompt
        segmentation_prompt = generate_segmentation_prompt(
            bookmark_data=outline_data,
            pdftk_metadata=None,  # Opcional, según tu prompt_generator
            total_pages=total_pages,
            pdf_path=pdf_path
        )

        # 5. Llamada a la API con estrategia de tareas
        raw_response = get_gemini_response(
            prompt=segmentation_prompt,
            model='gemini-2.5-flash',
            task_type='segmentation'
        )

        # 6. Parseo de la Respuesta JSON (robusto ante markdown)
        try:
            start_idx = raw_response.find('[')
            end_idx = raw_response.rfind(']') + 1
            
            if start_idx == -1 or end_idx == 0:
                raise ValueError("No valid JSON array found in response")
                
            commands_list = json.loads(raw_response[start_idx:end_idx])
            
            if not isinstance(commands_list, list):
                raise ValueError("Root element of JSON is not a list")

        except Exception as parse_err:
            logging.error(f"Error parseando JSON de segmentación: {parse_err}")
            logging.debug(f"Respuesta cruda: {raw_response}")
            return {
                "status": "failed", 
                "reason": f"JSON Parsing Failed: {parse_err}", 
                "raw_response": raw_response
            }

        # 7. Ejecución de Comandos pdftk
        successful_segments = 0
        failed_segments = []

        for cmd_obj in commands_list:
            # Support both old and new schemas
            if 'pdftk_command' in cmd_obj:
                pdftk_cmd = cmd_obj['pdftk_command']
                component_name = cmd_obj.get('component_name', 'Unknown_Component')
            elif 'command' in cmd_obj:
                pdftk_cmd = cmd_obj['command']
                component_name = cmd_obj.get('filename', 'Unknown_Component').replace('.pdf', '')
            else:
                logging.warning(f"Objeto de comando inválido (falta comando): {cmd_obj}")
                continue

            # Build a safe filename
            safe_filename = "".join(c for c in component_name if c.isalnum() or c in (' ', '-', '_')).strip()
            if not safe_filename.endswith('.pdf'):
                safe_filename += '.pdf'
            if not safe_filename.replace('.pdf', '').strip():
                safe_filename = f"Unknown_Component_{commands_list.index(cmd_obj):02d}.pdf"

            output_path = os.path.join(dest_folder, safe_filename)
            full_cmd_str = pdftk_cmd.replace("IN_FILE", f'"{pdf_path}"').replace("OUT_FILE", f'"{output_path}"')
            
            logging.info(f"Ejecutando: {full_cmd_str}")
            
            try:
                result = subprocess.run(
                    full_cmd_str, 
                    shell=True, 
                    check=True, 
                    capture_output=True, 
                    text=True,
                    timeout=180
                )
                successful_segments += 1
                
            except subprocess.CalledProcessError as e:
                logging.error(f"Error ejecutando pdftk para {safe_filename}: {e.stderr}")
                failed_segments.append(safe_filename)
            except subprocess.TimeoutExpired:
                logging.error(f"Timeout ejecutando pdftk para {safe_filename}")
                failed_segments.append(safe_filename)

        # 8. Reporte de Resultados
        logging.info(f"Segmentación finalizada. Éxitos: {successful_segments}, Fallos: {len(failed_segments)}")
        
        status = "success" if successful_segments > 0 else "failed"
        if successful_segments > 0 and failed_segments:
            status = "partial_success"
            
        return {
            "status": status,
            "total_commands": len(commands_list),
            "successful_segments": successful_segments,
            "failed_segments": failed_segments,
            "output_dir": dest_folder
        }

    except Exception as e:
        logging.error(f"Error general en segmentación de {pdf_path}: {e}", exc_info=True)
        return {"status": "crashed", "reason": str(e)}


def run_segmentation_pipeline(classifications_file: str, base_output_dir: str):
    """
    Itera sobre el archivo de clasificaciones y segmenta los libros con marcadores válidos.
    """
    logging.info("Iniciando Pipeline de Segmentación...")
    
    if not os.path.exists(classifications_file):
        logging.error(f"Archivo {classifications_file} no encontrado. Ejecuta pipe.py primero.")
        return

    books_to_process = []
    try:
        with open(classifications_file, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue
                record = json.loads(line)
                evidence = record.get('final_evidence', {})
                if evidence.get('has_pypdf_outline') is True:
                    books_to_process.append(record)
    except Exception as e:
        logging.error(f"Error leyendo clasificaciones: {e}")
        return

    logging.info(f"Libros elegibles para segmentación: {len(books_to_process)}")
    
    if not books_to_process:
        logging.warning("No hay libros elegibles para segmentación.")
        return

    results_summary = []
    
    for index, record in enumerate(books_to_process, 1):
        pdf_path = record['file_path']
        classification = record.get('classification_result', {}).get('classification', 'Unknown')
        
        logging.info(f"[{index}/{len(books_to_process)}] Procesando: {classification} - {os.path.basename(pdf_path)}")
        
        result = segment_single_book(
            pdf_path=pdf_path,
            output_base_dir=base_output_dir,
            classification_data=record
        )
        
        result['file_path'] = pdf_path
        result['classification'] = classification
        result['timestamp'] = datetime.utcnow().isoformat() + "Z"
        results_summary.append(result)

    # Persistencia del log
    try:
        with open(SEGMENTATION_LOG_FILE, 'w', encoding='utf-8') as f:
            for res in results_summary:
                f.write(json.dumps(res, ensure_ascii=False) + '\n')
        logging.info(f"Log de segmentación guardado en {SEGMENTATION_LOG_FILE}")
    except Exception as e:
        logging.error(f"Error guardando log: {e}")

    success_count = sum(1 for r in results_summary if r.get('status') in ('success', 'partial_success'))
    logging.info(f"Pipeline completado. Éxitos totales: {success_count}/{len(books_to_process)}")


if __name__ == "__main__":
    # Verificación de pdftk
    try:
        subprocess.run(["pdftk", "--version"], check=True, capture_output=True, text=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        logging.critical("ERROR: 'pdftk' no está instalado o no está en el PATH.")
    else:
        run_segmentation_pipeline(CLASSIFICATIONS_FILE, OUTPUT_DIR_BASE)
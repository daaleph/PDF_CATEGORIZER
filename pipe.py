# pipe.py (Minor Enhancement: Add File Size Pre-Scan for Risky Files)

#!/usr/bin/env python3
"""
Master orchestration script for the Book Categorizer project.
Enhanced with file size logging for risky files.
"""

import logging
import os
import json
import argparse
import sys

# --- Import your custom modules ---
from metadata_checker import check_book_metadata
from layout_analyzer import analyze_book_layout
from get_gemini_response import get_gemini_response

# --- Configuration ---
SCAN_DIRECTORIES = ["BOOKS"]
OUTPUT_FILE = "book_classifications.jsonl"
FORCE_REPROCESS = False

def find_all_pdfs(directories: list) -> list:
    """Recursively finds all .pdf files in a list of directories."""
    pdf_files = []
    for directory in directories:
        for root, _, files in os.walk(directory):
            for file in files:
                if file.lower().endswith(".pdf"):
                    pdf_files.append(os.path.join(root, file))
    return sorted(pdf_files)

def load_processed_files(output_path: str) -> set:
    """Loads the set of already processed file paths from the output file."""
    if not os.path.exists(output_path):
        return set()
    
    processed = set()
    with open(output_path, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                data = json.loads(line)
                processed.add(data['final_evidence']['file'])
            except (json.JSONDecodeError, KeyError):
                continue
    return processed

def get_file_size_mb(pdf_path: str) -> float:
    """Get file size in MB for risk assessment."""
    try:
        return os.path.getsize(pdf_path) / (1024 * 1024)
    except:
        return 0

def classify_book_structure(pdf_path: str, evidence_data: dict) -> dict:
    """
    Envía las evidencias extraídas (metadatos y layout) al modelo Gemini
    para obtener la clasificación estructural del libro.
    
    Esta función actúa como el puente entre el análisis local y la IA.
    """
    logging.info(f"--- Iniciando Clasificación IA para: {os.path.basename(pdf_path)} ---")

    # 1. Construcción del Prompt (Mantiene la riqueza algorítmica original)
    # Se define la estructura de salida esperada para asegurar el parseo JSON
    system_instruction = """
    You are an expert PDF document archivist. Analyze the provided evidence to classify the structural complexity of the book.
    Return a valid JSON object with exactly two keys:
    1. "classification": String (e.g., "Level 1", "Level 2", "Level 5").
    2. "justification": String explaining why this level fits the evidence.
    """

    user_prompt = f"""
    Based on the evidence below, classify the book '{os.path.basename(pdf_path)}'.
    
    Evidence Data:
    {json.dumps(evidence_data, indent=2)}
    
    Classification Levels Guide:
    - Level 1: Simple Linear Monograph (Flat structure, standard metadata).
    - Level 2: Standard Hierarchical Textbook (Good metadata, nested bookmarks).
    - Level 3: Handbook (Flat but long metadata, mixed layout).
    - Level 4: Reference Manual (Complex layout, dense metadata).
    - Level 5: Inferred Structure / Broken Metadata (No bookmarks, reliance on layout analysis).
    
    Output strictly the JSON object.
    """

    try:
        # 2. Llamada a la API con Estrategia de Tareas (El ajuste crítico)
        # Se utiliza task_type='classification' para activar la lista de modelos 
        # ligeros y eficientes definida en get_gemini_response.py
        raw_response = get_gemini_response(
            prompt=user_prompt,
            system_instruction=system_instruction, # Nota: Asegúrate de que tu función acepte esto o pásalo en 'contents'
            model='gemini-2.5-flash', # Modelo de preferencia inicial
            task_type='classification'  # <--- ACTIVACIÓN DE LA RESILIENCIA ESTRATÉGICA
        )

        # 3. Validación y Parseo de la Respuesta (Cohesión con el sistema)
        # A veces el modelo devuelve texto antes del JSON, limpiamos si es necesario
        # (Aunque get_gemini_response devuelve .text.strip(), añadimos una capa extra de seguridad)
        
        try:
            # Intento directo de parseo JSON
            result = json.loads(raw_response)
            
            # Validación de campos obligatorios
            if "classification" not in result or "justification" not in result:
                raise ValueError("Missing keys in JSON response")
                
            logging.info(f"Clasificación exitosa: {result['classification']}")
            return result

        except json.JSONDecodeError as json_err:
            logging.error(f"Error de sintaxis JSON en la respuesta de la IA: {json_err}")
            logging.debug(f"Respuesta cruda recibida: {raw_response[:200]}...")
            
            # Intento de recuperación: buscar el objeto JSON dentro del texto si falló el strip directo
            start = raw_response.find('{')
            end = raw_response.rfind('}') + 1
            if start != -1 and end > start:
                try:
                    recovered_json = json.loads(raw_response[start:end])
                    logging.warning("JSON recuperado mediante limpieza de caracteres extra.")
                    return recovered_json
                except:
                    pass
            
            # Si falla todo, devolvemos una estructura de error controlada
            return {
                "classification": "Unknown",
                "justification": f"JSON Parsing Error: {str(json_err)}"
            }

    except Exception as e:
        logging.error(f"Excepción crítica durante la clasificación de {pdf_path}: {e}", exc_info=True)
        # Estructura de fallo para mantener la integridad del pipeline downstream
        return {
            "classification": "Error",
            "justification": str(e)
        }

def process_single_book(pdf_path: str, output_jsonl_path: str) -> dict:
    """
    Procesa un único libro PDF: extrae evidencia técnica, clasifica mediante IA
    y persiste el resultado en el archivo .jsonl principal.

    Args:
        pdf_path (str): Ruta completa al archivo PDF.
        output_jsonl_path (str): Ruta al archivo donde se guardarán los resultados.

    Returns:
        dict: El resultado final procesado (incluyendo evidencia y clasificación).
    """
    logging.info(f"--- Procesando libro: {os.path.basename(pdf_path)} ---")

    # 1. Inicialización de la estructura de evidencia
    # Esta estructura contiene los datos "duros" que la IA analizará.
    evidence_data = {
        'file_path': pdf_path,
        'file_size_mb': round(os.path.getsize(pdf_path) / (1024 * 1024), 2),
        'analysis_type': 'pending', 
        'has_pypdf_outline': False,
        'pypdf_outline_depth': 0,
        'pypdf_outline_length': 0,
        'distinct_font_sizes': 0,
        'page_number_style_transition_found': False
    }

    try:
        # 2. Fase de Análisis Técnico (Extracción de Evidencia)
        # Estrategia: Primero intentar metadatos (rápido), luego layout (visual) si falla.
        
        # --- Intento 1: Análisis de Metadatos (Bookmarks) ---
        try:
            # Esto asume que check_pdf_bookmarks devuelve un dict con las claves esperadas
            # o lanza una excepción si no encuentra nada.
            # Se adapta a las claves definidas en 'evidence_data' para coherencia.
            metadata_result = check_book_metadata(pdf_path)
            
            if metadata_result and metadata_result.get('has_bookmarks'):
                evidence_data.update(metadata_result)
                evidence_data['analysis_type'] = 'metadata_check'
                logging.info("Análisis exitoso vía metadatos (bookmarks).")
            else:
                raise ValueError("No bookmarks found or metadata invalid.")
                
        except Exception as metadata_error:
            logging.warning(f"Análisis de metadatos falló o vacío: {metadata_error}")
            logging.info("Pasando a análisis de layout (visual)...")

            # --- Intento 2: Análisis de Layout (Visual Heuristics) ---
            try:
                layout_result = analyze_book_layout(pdf_path)
                
                if layout_result:
                    evidence_data.update(layout_result)
                    evidence_data['analysis_type'] = 'layout_analysis'
                    logging.info("Análisis exitoso vía layout (visual).")
                else:
                    raise ValueError("Layout analysis returned no data.")
                    
            except Exception as layout_error:
                logging.error(f"Análisis de layout también falló: {layout_error}")
                # Dejamos analysis_type como 'failed' o 'unknown' para que la IA lo maneje
                evidence_data['analysis_type'] = 'analysis_failed'

        # 3. Fase de Clasificación con IA (Integración del nuevo método)
        # Aquí es donde llamamos al método ajustado previamente.
        classification_result = classify_book_structure(pdf_path, evidence_data)

        # 4. Consolidación de Resultados Finales
        final_record = {
            "file_path": pdf_path,
            "final_evidence": evidence_data,
            "classification_result": classification_result
        }

        # 5. Persistencia Atómica en JSONL
        # Usamos modo 'append' para acumular resultados de múltiples libros.
        try:
            with open(output_jsonl_path, 'a', encoding='utf-8') as f:
                # ensure_ascii=False para preservar caracteres especiales en títulos de libros
                f.write(json.dumps(final_record, ensure_ascii=False) + '\n')
        except IOError as io_err:
            logging.error(f"Error escribiendo en {output_jsonl_path}: {io_err}")
            # Relanzamos para detener el pipe si hay error de disco
            raise

        logging.info(f"Clasificación completada y guardada para: {os.path.basename(pdf_path)}")
        return final_record

    except Exception as e:
        # Manejo robusto de errores para no detener el procesamiento de todo el lote
        logging.error(f"Excepción crítica en process_single_book para {pdf_path}: {e}", exc_info=True)
        
        # Opcional: Guardar registro del fallo en el JSONL para auditoría
        fail_record = {
            "file_path": pdf_path,
            "final_evidence": evidence_data,
            "classification_result": {
                "classification": "System Error",
                "justification": f"Pipeline crashed: {str(e)}"
            }
        }
        
        try:
            with open(output_jsonl_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(fail_record, ensure_ascii=False) + '\n')
        except:
            pass # Ignorar error de escritura si ya estamos en un estado de fallo
            
        return fail_record


def main():
    """
    Main function to orchestrate the entire classification process for the corpus.
    """
    parser = argparse.ArgumentParser(description="Run the full book classification pipeline.")
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force reprocessing of all files, even if they exist in the output file.'
    )
    args = parser.parse_args()

    all_pdfs = find_all_pdfs(SCAN_DIRECTORIES)
    total_files = len(all_pdfs)
    print(f"Found {total_files} PDF files to process in {SCAN_DIRECTORIES}.")

    processed_files = set()
    if not args.force:
        processed_files = load_processed_files(OUTPUT_FILE)
        print(f"Found {len(processed_files)} already processed files. Will skip them.")
    else:
        print("Force reprocessing is enabled. All files will be processed.")
        # Clear the output file if forcing re-process
        if os.path.exists(OUTPUT_FILE):
            open(OUTPUT_FILE, 'w').close()


    with open(OUTPUT_FILE, 'a', encoding='utf-8') as f_out:
        for i, pdf_path in enumerate(all_pdfs):
            
            if pdf_path in processed_files:
                print(f"({i+1}/{total_files}) Skipping already processed file: {pdf_path}")
                continue
            
            result_record = process_single_book(pdf_path, "book_classifications.jsonl")
            
            if result_record:
                # Write the result as a single line of JSON
                f_out.write(json.dumps(result_record) + '\n')
                f_out.flush() # Ensure data is written immediately

    print("\n" + "*"*80)
    print("Pipeline finished successfully.")
    print(f"All classification results have been saved to '{OUTPUT_FILE}'.")
    print("*"*80)


if __name__ == "__main__":
    main()

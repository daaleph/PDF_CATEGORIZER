# segmentation_pipe.py (Enhanced with Quick Fixes)

#!/usr/bin/env python3
"""
Master orchestration script for the LLM-Powered PDF Segmentation Pipeline.
Enhanced with PyMuPDF slicing fallback, password cache, and partial success logging.
"""

import os
import json
import subprocess
import argparse
import sys
import pandas as pd
import re
import time
from datetime import datetime, UTC
import fitz  # For fallback slicing

# --- System Components ---
from get_gemini_response import get_gemini_response
from prompt_generator import generate_segmentation_prompt
from extract_chapter import get_chapter_data, get_pdftk_metadata, remove_pdf_password_if_needed, get_page_count

# --- Configuration ---
OUTPUT_DIR = "segmented_output"
LOGS_DIR = "logs"
SEGMENTATION_LOG_FILE = os.path.join(LOGS_DIR, "segmentation.jsonl")
SKIPPED_LOG_FILE = os.path.join(LOGS_DIR, "skipped_books.txt")
CLASSIFICATIONS_FILE = "book_classifications.jsonl"

# Quick Fix 3: Password Cache
password_cache = {}  # {pdf_path: removed_status}

def get_cached_password_removal(pdf_path):
    if pdf_path not in password_cache:
        password_cache[pdf_path] = remove_pdf_password_if_needed(pdf_path)
    return password_cache[pdf_path]

def setup_directories():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(LOGS_DIR, exist_ok=True)

def load_processed_files() -> set:
    if not os.path.exists(SEGMENTATION_LOG_FILE):
        return set()
    processed = set()
    with open(SEGMENTATION_LOG_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                data = json.loads(line)
                if data.get('status') == 'SUCCESS':
                    processed.add(data['file_path'])
            except json.JSONDecodeError:
                continue
    return processed

def get_total_pages(pdf_path: str) -> int:
    """
    Wrapper for enhanced get_page_count with fallback.
    """
    # Quick Fix 3: Use cached password removal
    password_removed = get_cached_password_removal(pdf_path)
    if password_removed:
        print("  -> Password removed (cached); proceeding with page count.")
    return get_page_count(pdf_path)

def get_fallback_page_count(pdf_path: str) -> int:
    """
    PyMuPDF fallback for total pages if pdftk fully fails.
    """
    try:
        doc = fitz.open(pdf_path)
        return len(doc)
    except Exception as e:
        print(f"  -> PyMuPDF fallback failed for '{pdf_path}': {e}", file=sys.stderr)
        return 0

def log_result(file_path, status, message, commands_executed=0, commands_total=0):
    log_entry = {
        "timestamp": datetime.now(UTC).isoformat() + "Z",
        "file_path": file_path,
        "status": status,
        "message": message,
        "commands_executed": commands_executed,
        "commands_total": commands_total,
    }
    with open(SEGMENTATION_LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(json.dumps(log_entry) + '\n')

def sanitize_filename(name):
    """Removes invalid characters for file and directory names."""
    return re.sub(r'[<>:"/\\|?*\']', '_', name)

# Quick Fix 2: PyMuPDF Slicing Fallback Function
def extract_pages_pymupdf(pdf_path: str, start: int, end: int, output_filename: str) -> bool:
    """
    Fallback: Extract page range using PyMuPDF.
    start/end 1-indexed.
    """
    try:
        doc = fitz.open(pdf_path)
        output_doc = fitz.open()
        for p in range(start - 1, min(end, len(doc))):
            output_doc.insert_pdf(doc, from_page=p, to_page=p)
        output_doc.save(output_filename)
        output_doc.close()
        doc.close()
        return True
    except Exception as e:
        print(f"  -> PyMuPDF slicing error: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Run the full PDF segmentation pipeline.")
    parser.add_argument('--force', action='store_true', help='Force reprocessing of all files.')
    args = parser.parse_args()

    setup_directories()
    
    print("--- Starting PDF Segmentation Pipeline ---")
    
    try:
        # --- ROBUST LOADING LOGIC ---
        records = []
        with open(CLASSIFICATIONS_FILE, 'r', encoding='utf-8') as f:
            full_content = f.read()
        corrected_content = full_content.replace('}{', '}\n{')
        for line in corrected_content.splitlines():
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                record = {
                    'file_path': data.get('file_path'),
                    **data.get('classification_result', {}),
                    **data.get('final_evidence', {})
                }
                records.append(record)
            except json.JSONDecodeError as e:
                print(f"WARNING: Skipping malformed JSON in '{CLASSIFICATIONS_FILE}': {e}", file=sys.stderr)
        
        if not records:
            print(f"FATAL: No valid records in '{CLASSIFICATIONS_FILE}'.")
            sys.exit(1)

        df = pd.DataFrame(records)

    except Exception as e:
        print(f"FATAL: Could not parse '{CLASSIFICATIONS_FILE}': {e}", file=sys.stderr)
        sys.exit(1)

    processed_files = set() if args.force else load_processed_files()
    if not args.force:
        print(f"Found {len(processed_files)} previous successes. Skipping.")

    safe_mask = (df['analysis_type'] == 'metadata_check') & (~df['file_path'].isin(processed_files))
    safe_queue = df[safe_mask]
    unsafe_queue = df[~safe_mask]

    print(f"Found {len(safe_queue)} new books to process.")
    
    with open(SKIPPED_LOG_FILE, 'w', encoding='utf-8') as f:
        f.write(f"# Skipped Books Log - {datetime.now(UTC).isoformat()}\n")
        for _, row in unsafe_queue.iterrows():
            reason = "Already processed" if row['file_path'] in processed_files else f"analysis_type '{row['analysis_type']}'"
            f.write(f"{row['file_path']} | REASON: {reason}\n")
    print(f"Logged {len(unsafe_queue)} skips to '{SKIPPED_LOG_FILE}'.")

    for i, (_, book) in enumerate(safe_queue.iterrows()):
        pdf_path = book['file_path']
        print("\n" + "="*80)
        print(f"Processing ({i+1}/{len(safe_queue)}): {pdf_path}")
        print("="*80)
        
        # Quick Fix 3: Cached password removal
        password_removed = get_cached_password_removal(pdf_path)
        if password_removed:
            print("  -> Password removed (cached); retrying extraction.")
        
        print("  - Extracting bookmark data (PyPDF)...")
        try:
            bookmark_data = get_chapter_data(pdf_path)
        except Exception as e:
            print(f"  -> WARNING: PyPDF failed for '{pdf_path}': {e}", file=sys.stderr)
            bookmark_data = None
            
        print("  - Extracting pdftk metadata...")
        try:
            pdftk_metadata = get_pdftk_metadata(pdf_path)
        except Exception as e:
            print(f"  -> WARNING: pdftk failed for '{pdf_path}': {e}", file=sys.stderr)
            pdftk_metadata = None
        
        # Use PyPDF as primary; pdftk secondary
        if pdftk_metadata and bookmark_data:
            metadata_to_use = pdftk_metadata  # Prefer pdftk if both
        elif bookmark_data:
            print("  -> Using PyPDF-only metadata.")
            metadata_to_use = bookmark_data
            pdftk_metadata = None  # Flag for prompt
        elif pdftk_metadata:
            metadata_to_use = pdftk_metadata
        else:
            log_result(pdf_path, "FAILURE", "No metadata from PyPDF or pdftk.")
            continue
            
        print("  - Getting total page count...")
        total_pages = get_total_pages(pdf_path)
        if total_pages == 0:
            print("  -> pdftk page count failed. Falling back to PyMuPDF.")
            total_pages = get_fallback_page_count(pdf_path)
            if total_pages == 0:
                log_result(pdf_path, "FAILURE", "No page count from any source.")
                continue
            print(f"  -> Fallback page count: {total_pages}")
        
        # Proceed even with partial metadata
        if not metadata_to_use:
            log_result(pdf_path, "FAILURE", "No usable metadata after fallbacks.")
            continue
        
        try:
            # Adjust prompt for partial data
            prompt = generate_segmentation_prompt(
                bookmark_data if bookmark_data else metadata_to_use,
                pdftk_metadata,
                total_pages,
                pdf_path
            )
            raw_response = get_gemini_response(prompt, 'gemini-2.5-flash')
            cleaned_response = raw_response.replace("```json\n", "").replace("```", "")
            try:
                response_json = json.loads(cleaned_response)
            except Exception as e:
                print(f"  -> LLM parse error: {e}. Retrying with gemini-3-flash.")
                raw_response = get_gemini_response(prompt, 'gemini-3-flash')
                cleaned_response = raw_response.replace("```json\n", "").replace("```", "")
                response_json = json.loads(cleaned_response)
            
            if not response_json.get("segmentation_commands"):
                print("  -> Empty commands from LLM. Retrying with 2.5 pro model.")
                raw_response = get_gemini_response(prompt, 'gemini-2.5-pro')
                cleaned_response = raw_response.replace("```json\n", "").replace("```", "")
                response_json = json.loads(cleaned_response)
            
            if not response_json.get("segmentation_commands"):
                print("  -> Empty commands from LLM. Retrying with pro model.")
                raw_response = get_gemini_response(prompt, 'gemini-3-pro-preview')
                cleaned_response = raw_response.replace("```json\n", "").replace("```", "")
                response_json = json.loads(cleaned_response)
                
        except Exception as e:
            log_result(pdf_path, "FAILURE", f"LLM error: {e}")
            print(f"  -> ERROR: LLM failed: {e}", file=sys.stderr)
            continue

        commands = response_json.get("segmentation_commands", [])
        if not isinstance(commands, list):
            log_result(pdf_path, "FAILURE", "Invalid LLM structure.")
            print("  -> ERROR: Invalid LLM JSON.")
            continue
            
        if not commands:
            log_result(pdf_path, "SUCCESS", "LLM skipped due to insufficient metadata.")
            print("  -> INFO: LLM skipped safely.")
            continue

        commands_executed_count = 0
        try:
            base_name = sanitize_filename(os.path.splitext(os.path.basename(pdf_path))[0])
            # Handle relative path for output dir
            book_output_dir_parts = pdf_path.split(os.sep)[:-1]  # Use os.sep for cross-platform
            book_output_dir = os.path.join(OUTPUT_DIR, *book_output_dir_parts, base_name)
            os.makedirs(book_output_dir, exist_ok=True)
            print(f"  - Output directory: {book_output_dir}")

            for cmd_obj in commands:
                component_name = sanitize_filename(cmd_obj['component_name'])
                pdftk_command_template = cmd_obj['pdftk_command']
                output_filename = os.path.join(book_output_dir, f"{component_name}.pdf")
                final_command = pdftk_command_template.replace("IN_FILE", f'"{pdf_path}"').replace("OUT_FILE", f'"{output_filename}"')
                
                print(f"    - Executing: {final_command}")
                success = False
                # Quick Fix 2: pdftk with fallback
                try:
                    subprocess.run(final_command, shell=True, check=True, capture_output=True, timeout=120)
                    success = True
                except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
                    print(f"    -> pdftk failed for {component_name}: {e}. Trying PyMuPDF fallback...")
                    # Parse page range from command (e.g., "cat 1-5" -> start=1, end=5)
                    page_match = re.search(r'cat\s+(\d+)-?(\d*)', final_command)
                    if page_match:
                        start = int(page_match.group(1))
                        end = int(page_match.group(2)) if page_match.group(2) else get_total_pages(pdf_path)
                        success = extract_pages_pymupdf(pdf_path, start, end, output_filename)
                        if success:
                            print(f"    -> PyMuPDF fallback succeeded for {component_name} (pages {start}-{end}).")
                        else:
                            print(f"    -> PyMuPDF fallback failed for {component_name}.")
                
                if success:
                    commands_executed_count += 1

            # Quick Fix 4: Accurate logging with threshold
            partial_success = (commands_executed_count / len(commands)) >= 0.5 if commands else False
            status = "SUCCESS" if partial_success else "PARTIAL_FAILURE"
            message = f"Segmentation partial ({commands_executed_count}/{len(commands)} extracted)."
            log_result(pdf_path, status, message, commands_executed_count, len(commands))
            if not partial_success:
                print("  -> PARTIAL FAILURE: <50% components extracted. Review log.")
            else:
                print("  -> SUCCESS: Book segmented.")
                print("  -> Throttling: Sleeping 10s to cool down API keys...")
                time.sleep(10)

        except Exception as e:
            error_details = str(e)
            log_result(pdf_path, "FAILURE", f"Execution failed: {error_details}", commands_executed_count, len(commands))
            print(f"  -> ERROR: Execution failed: {error_details}", file=sys.stderr)
            continue

    print("\n--- Pipeline Finished ---")

if __name__ == "__main__":
    main()

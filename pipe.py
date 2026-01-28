# pipe.py (Minor Enhancement: Add File Size Pre-Scan for Risky Files)

#!/usr/bin/env python3
"""
Master orchestration script for the Book Categorizer project.
Enhanced with file size logging for risky files.
"""

import os
import json
import argparse
import sys

# --- Import your custom modules ---
from metadata_checker import check_book_metadata
from layout_analyzer import analyze_book_layout
from ai_classifier import generate_classification_prompt
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

def process_single_book(pdf_path: str):
    """
    Runs the full analysis and classification pipeline for a single book.
    """
    size_mb = get_file_size_mb(pdf_path)
    if size_mb > 50:
        print(f"  -> WARNING: Large file ({size_mb:.1f} MB) - may timeout.")
    
    print("\n" + "="*80)
    print(f"Processing: {pdf_path} ({size_mb:.1f} MB)")
    print("="*80)

    # Stage 1: Metadata Check
    metadata_evidence = check_book_metadata(pdf_path)

    # This dictionary will hold all evidence sent to the AI
    final_evidence = metadata_evidence.copy()

    # Stage 2: Layout Analysis (if needed)
    if metadata_evidence.get("next_step") == "run_layout_analysis":
        layout_evidence = analyze_book_layout(pdf_path)
        if layout_evidence:
            # Merge layout evidence into the final evidence payload
            final_evidence.update(layout_evidence)
        else:
            print(f"-> WARNING: Layout analysis failed for {pdf_path}. Proceeding with metadata only.")

    # Stage 3: AI Classification
    print("\n--- Generating AI Prompt ---")
    prompt = generate_classification_prompt(final_evidence)
    
    ai_response = {
        "classification": "ERROR",
        "justification": "Failed to get response from AI.",
        "raw_output": ""
    }
    
    try:
        raw_response = get_gemini_response(prompt, "gemini-2.5-flash")
        print(f"RAW RESPONSE: {raw_response}")
        ai_response["raw_output"] = raw_response
        
        # Parse the structured response from the AI
        level_line = ""
        justification_line = ""
        for line in raw_response.splitlines():
            if line.upper().startswith("LEVEL:"):
                level_line = line.split(":", 1)[1].strip()
            elif line.upper().startswith("JUSTIFICATION:"):
                justification_line = line.split(":", 1)[1].strip()
        
        if level_line:
            ai_response["classification"] = level_line
            ai_response["justification"] = justification_line
        else:
            ai_response["justification"] = "AI response was not in the expected format."

    except Exception as e:
        print(f"-> ERROR: AI classification failed for {pdf_path}.", file=sys.stderr)
        print(f"   Details: {e}", file=sys.stderr)
        ai_response["justification"] = f"An exception occurred: {str(e)}"

    print("\n--- Classification Result ---")
    print(f"  Level: {ai_response['classification']}")
    print(f"  Justification: {ai_response['justification']}")

    # Combine all data into a single record
    final_record = {
        "file_path": pdf_path,
        "classification_result": ai_response,
        "final_evidence": final_evidence,
    }

    return final_record


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
                
            result_record = process_single_book(pdf_path)
            
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

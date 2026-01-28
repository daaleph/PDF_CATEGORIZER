# metadata_checker.py (Enhanced with Retries and Fallbacks)

# metadata_checker.py (Enhanced with Password Cache)

#!/usr/bin/env python3
import json
import argparse
import sys
from extract_chapter import get_chapter_data, remove_pdf_password_if_needed, get_pdftk_metadata

# Quick Fix 3: Password Cache (global for module)
password_cache = {}

def get_cached_password_removal(pdf_path):
    if pdf_path not in password_cache:
        password_cache[pdf_path] = remove_pdf_password_if_needed(pdf_path)
    return password_cache[pdf_path]

def check_book_metadata(pdf_path):
    """
    Performs Stage 1 analysis using PyPDF (primary) and pdftk (secondary) with retries.
    """
    print(f"--- Analyzing Metadata for: {pdf_path} ---")
    
    # Quick Fix 3: Cached password removal
    password_removed = get_cached_password_removal(pdf_path)
    if password_removed:
        print("-> Password removed (cached); proceeding.")
    
    bookmarks = get_chapter_data(pdf_path)  # PyPDF primary
    
    try:
        # Use enhanced get_pdftk_metadata with retries
        pdftk_metadata = get_pdftk_metadata(pdf_path)
        has_pdftk_metadata = bool(pdftk_metadata)
    except Exception as e:
        print(f"-> WARNING: pdftk failed for '{pdf_path}': {e}")
        has_pdftk_metadata = False

    evidence = {
        "file": pdf_path,
        "analysis_type": "metadata_check",
        "has_pypdf_outline": bool(bookmarks),
        "pypdf_outline_depth": max(b['level'] for b in bookmarks) + 1 if bookmarks else 0,
        "pypdf_outline_length": len(bookmarks),
        "has_pdftk_metadata": has_pdftk_metadata,
    }

    if not bookmarks and not has_pdftk_metadata:
        print("-> Metadata check FAILED. Proceed to layout.")
        evidence["next_step"] = "run_layout_analysis"
    else:
        print("-> Metadata check PASSED.")
        evidence["next_step"] = "classify_with_ai"

    return evidence

def main():
    parser = argparse.ArgumentParser(description="Stage 1: Check PDF for explicit metadata.")
    parser.add_argument("pdf_filepath", type=str, help="The path to the PDF file.")
    args = parser.parse_args()
    
    try:
        evidence = check_book_metadata(args.pdf_filepath)
        print("\n--- Evidence Summary ---")
        evidence.pop('next_step', None)
        print(json.dumps(evidence, indent=2))
    except FileNotFoundError:
        print(f"Error: File '{args.pdf_filepath}' not found.", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
import fitz  # PyMuPDF
import json
import argparse
import sys
from collections import Counter
import re

def analyze_page_number_style(page_text):
    """Detects Roman or Arabic numerals in the last part of page text."""
    # A simple regex to find numbers at the end of a string
    arabic_match = re.search(r'\b(\d{1,4})\b\s*$', page_text)
    roman_match = re.search(r'\b([ivxlcdm]+)\b\s*$', page_text.lower())

    if arabic_match:
        return "arabic"
    if roman_match:
        return "roman"
    return "none"

def analyze_book_layout(pdf_path, max_pages=50):
    """
    Performs Stage 2 layout analysis on a PDF.
    """
    print(f"--- Performing Layout Analysis for: {pdf_path} ---")
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        print(f"Error opening PDF with PyMuPDF: {e}", file=sys.stderr)
        return None

    font_sizes = Counter()
    page_number_styles = []
    num_pages_to_scan = min(len(doc), max_pages)

    for i in range(num_pages_to_scan):
        page = doc.load_page(i)
        
        # 1. Profile font sizes
        blocks = page.get_text("dict")["blocks"]
        for block in blocks:
            if "lines" in block:
                for line in block["lines"]:
                    for span in line["spans"]:
                        font_sizes[round(span["size"])] += 1
                        
        # 2. Detect page numbering style
        full_text = page.get_text().strip()
        if full_text:
            # Check the last 50 chars for a page number
            style = analyze_page_number_style(full_text[-50:])
            if style != "none":
                page_number_styles.append(style)

    # 3. Synthesize findings
    num_distinct_font_sizes = len(font_sizes)
    most_common_fonts = font_sizes.most_common(5)
    
    # Check for the key transition from Roman to Arabic numerals
    transition_found = False
    if 'roman' in page_number_styles and 'arabic' in page_number_styles:
        try:
            last_roman_idx = len(page_number_styles) - 1 - page_number_styles[::-1].index('roman')
            first_arabic_idx = page_number_styles.index('arabic')
            if first_arabic_idx > last_roman_idx:
                transition_found = True
        except ValueError:
            pass # Should not happen if both are in list

    evidence = {
        "file": pdf_path,
        "analysis_type": "layout_analysis",
        "distinct_font_sizes": num_distinct_font_sizes,
        "top_5_font_sizes": most_common_fonts,
        "page_number_style_transition_found": transition_found,
        "detected_page_number_styles": list(dict.fromkeys(page_number_styles)) # unique styles found
    }
    
    print("-> Layout analysis complete.")
    return evidence

def main():
    parser = argparse.ArgumentParser(description="Stage 2: Analyze PDF layout for structural clues.")
    parser.add_argument("pdf_filepath", type=str, help="The path to the PDF file.")
    args = parser.parse_args()

    try:
        evidence = analyze_book_layout(args.pdf_filepath)
        if evidence:
            print("\n--- Layout Evidence Summary ---")
            print(json.dumps(evidence, indent=2))
    except FileNotFoundError:
        print(f"Error: The file '{args.pdf_filepath}' was not found.", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()

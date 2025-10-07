# extract_chapter.py (Fully Enhanced with Retries, Fallbacks, and Resilience)

#!/usr/bin/env python3
"""
extract_chapter.py
Extracts and prints the outline (bookmarks/chapters) from a given PDF file.
Enhanced with retries, PyMuPDF fallback for page count, improved password handling,
and full resilience against timeouts/errors.
"""

import argparse
import sys
import pypdf
import subprocess
import os
import time
import fitz  # PyMuPDF for fallback page count

def get_page_count_fallback(pdf_path: str) -> int:
    """
    Fallback page count using PyMuPDF (fitz).
    """
    try:
        doc = fitz.open(pdf_path)
        return len(doc)
    except Exception as e:
        print(f"  -> WARNING: PyMuPDF fallback failed for '{pdf_path}': {e}", file=sys.stderr)
        return 0

def get_page_count(pdf_path: str, max_retries: int = 3) -> int:
    """
    Gets the total number of pages from a PDF using pdftk with retries.
    Falls back to PyMuPDF if all retries fail. Resilient to errors.
    """
    abs_pdf_path = os.path.abspath(pdf_path)
    for retry in range(max_retries):
        try:
            # Use binary capture to avoid internal thread decode errors
            result = subprocess.run(
                ["pdftk", abs_pdf_path, "dump_data_utf8"],
                capture_output=True,
                check=True,
                timeout=120  # Increased timeout
            )
            # Manually decode stdout with 'replace' to handle invalid bytes
            stdout_decoded = result.stdout.decode('utf-8', errors='replace')
            for line in stdout_decoded.splitlines():
                if line.startswith("NumberOfPages:"):
                    return int(line.split(":")[1].strip())
            # If no NumberOfPages, fallback immediately
            print(f"  -> No page count in pdftk output for '{pdf_path}'. Falling back to PyMuPDF.")
            return get_page_count_fallback(pdf_path)
        except subprocess.TimeoutExpired:
            if retry < max_retries - 1:
                wait = min(2 ** retry, 15)
                print(f"  -> pdftk timeout (retry {retry+1}/{max_retries}), waiting {wait}s...")
                time.sleep(wait)
                continue
            else:
                print(f"  -> All pdftk retries timed out for '{pdf_path}'. Falling back to PyMuPDF.")
                return get_page_count_fallback(pdf_path)
        except Exception as e:
            print(f"  -> pdftk error (retry {retry+1}/{max_retries}) for '{pdf_path}': {e}", file=sys.stderr)
            if retry == max_retries - 1:
                print(f"  -> All pdftk retries failed. Falling back to PyMuPDF.")
                return get_page_count_fallback(pdf_path)
            time.sleep(2 ** retry)
    return 0

def remove_pdf_password_if_needed(pdf_path, max_retries: int = 3):
    """
    Checks if the PDF has an owner password by attempting a pdftk dump_data_utf8 with retries.
    If password detected, uses Ghostscript (with verification), falls back to qpdf.
    Handles timeouts/non-zero exits gracefully.
    """
    # Convert to absolute path to avoid relative path issues
    abs_pdf_path = os.path.abspath(pdf_path)
    
    for retry in range(max_retries):
        try:
            # Run without check=True to handle non-zero exits manually
            result = subprocess.run(
                ["pdftk", abs_pdf_path, "dump_data_utf8"],
                capture_output=True,
                timeout=120  # Increased timeout
            )
            # Manually decode stderr for error check
            stderr_decoded = result.stderr.decode('utf-8', errors='replace')
            if result.returncode == 0:
                # If successful, no password issue
                return False
            if "OWNER PASSWORD REQUIRED" in stderr_decoded:
                print(f"  -> PDF '{pdf_path}' has owner password. Attempting removal with Ghostscript...")
                
                # Get original page count first (with fallback)
                original_pages = get_page_count(pdf_path)
                if original_pages == 0:
                    print(f"  -> Could not get original page count for '{pdf_path}'. Skipping decryption.", file=sys.stderr)
                    return False
                
                # Try Ghostscript first
                try:
                    unprotected_path = abs_pdf_path.replace('.pdf', '_unprotected.pdf')
                    gs_cmd = [
                        "gswin64c",
                        "-sPDFPassword=",
                        "-dNOPAUSE",
                        "-dBATCH",
                        "-sDEVICE=pdfwrite",
                        f"-sOutputFile=\"{unprotected_path}\"",
                        "-f",
                        f"\"{abs_pdf_path}\""
                    ]
                    gs_result = subprocess.run(gs_cmd, capture_output=True, check=True, timeout=300)  # Longer for GS
                    if gs_result.returncode == 0:
                        new_pages = get_page_count(unprotected_path)
                        if new_pages == original_pages and new_pages > 0:
                            os.replace(unprotected_path, abs_pdf_path)
                            print(f"  -> Successfully removed password from '{pdf_path}' with Ghostscript (pages: {original_pages}).")
                            return True
                        else:
                            print(f"  -> Ghostscript output invalid (pages: {new_pages} vs {original_pages}). Falling back to qpdf.")
                            if os.path.exists(unprotected_path):
                                os.remove(unprotected_path)
                    else:
                        print(f"  -> Ghostscript failed: {gs_result.stderr.decode('utf-8', errors='replace')}. Falling back to qpdf.")
                except subprocess.TimeoutExpired:
                    print("  -> Ghostscript timed out. Falling back to qpdf.")
                except Exception as gs_e:
                    print(f"  -> Ghostscript error: {gs_e}. Falling back to qpdf.")
                
                # Fallback: qpdf
                print("  -> Attempting qpdf...")
                try:
                    qpdf_unprotected_path = abs_pdf_path.replace('.pdf', '_qpdf_unprotected.pdf')
                    qpdf_cmd = ["qpdf", "--decrypt", f"\"{abs_pdf_path}\"", f"\"{qpdf_unprotected_path}\""]
                    qpdf_result = subprocess.run(qpdf_cmd, capture_output=True, check=True, timeout=120)
                    if qpdf_result.returncode == 0:
                        new_pages = get_page_count(qpdf_unprotected_path)
                        if new_pages == original_pages and new_pages > 0:
                            os.replace(qpdf_unprotected_path, abs_pdf_path)
                            print(f"  -> Successfully removed password from '{pdf_path}' with qpdf (pages: {original_pages}).")
                            return True
                        else:
                            print(f"  -> qpdf output invalid (pages: {new_pages} vs {original_pages}).")
                            if os.path.exists(qpdf_unprotected_path):
                                os.remove(qpdf_unprotected_path)
                    else:
                        print(f"  -> qpdf failed: {qpdf_result.stderr.decode('utf-8', errors='replace')}.")
                except subprocess.TimeoutExpired:
                    print("  -> qpdf timed out.")
                except Exception as qpdf_e:
                    print(f"  -> qpdf error: {qpdf_e}.")
                
                print(f"  -> Decryption failed after retries. Skipping for '{pdf_path}'.")
                return False
            else:
                # Non-password error: Log and skip
                print(f"  -> pdftk non-password error (code {result.returncode}, retry {retry+1}): {stderr_decoded}")
                if retry == max_retries - 1:
                    return False
                time.sleep(2 ** retry)
                continue
        except subprocess.TimeoutExpired:
            if retry < max_retries - 1:
                wait = min(2 ** retry, 15)
                print(f"  -> pdftk timeout in password check (retry {retry+1}/{max_retries}), waiting {wait}s...")
                time.sleep(wait)
                continue
            else:
                print(f"  -> All password check retries timed out. Skipping.")
                return False
        except Exception as e:
            print(f"  -> Unexpected password check error (retry {retry+1}): {e}")
            if retry == max_retries - 1:
                return False
            time.sleep(2 ** retry)
    return False

def get_chapter_data(pdf_path):
    """
    Reads a PDF file and extracts its outline (bookmarks) using PyPDF (primary, fast).
    """
    try:
        reader = pypdf.PdfReader(pdf_path)
    except pypdf.errors.PdfReadError as e:
        print(f"Error: Could not read the PDF file. It might be corrupted or encrypted.", file=sys.stderr)
        print(f"Details: {e}", file=sys.stderr)
        return []

    chapter_data = []
    outlines = reader.outline

    if not outlines:
        return []

    # Recursive function to process the nested outline structure
    def process_outline_item(item, level=0):
        if isinstance(item, pypdf.generic.Destination):
            try:
                page_number = reader.get_page_number(item.page) + 1
                chapter_data.append({
                    "title": item.title,
                    "page": page_number,
                    "level": level
                })
            except Exception:
                pass
        elif isinstance(item, list):
            for sub_item in item:
                process_outline_item(sub_item, level + 1)

    for item in outlines:
        process_outline_item(item, level=0)

    return chapter_data

def get_pdftk_metadata(pdf_path, max_retries: int = 3):
    """
    Extracts bookmark metadata using pdftk with retries (secondary to PyPDF).
    If fails, returns empty list (use PyPDF as primary).
    """
    # Handle password first
    password_removed = remove_pdf_password_if_needed(pdf_path)
    if password_removed:
        print("  -> Password removed; proceeding with metadata extraction.")

    # Convert to absolute path
    abs_pdf_path = os.path.abspath(pdf_path)
    
    for retry in range(max_retries):
        try:
            # Use binary capture
            result = subprocess.run(
                ["pdftk", abs_pdf_path, "dump_data_utf8"],
                capture_output=True,
                check=True,
                timeout=120
            )
            # Manually decode
            stdout_decoded = result.stdout.decode('utf-8', errors='replace')
            lines = stdout_decoded.splitlines()
            chapter_data = []
            current_bookmark = {}

            for line in lines:
                if line.startswith("BookmarkBegin"):
                    current_bookmark = {}
                elif line.startswith("BookmarkTitle: "):
                    current_bookmark["title"] = line[len("BookmarkTitle: "):]
                elif line.startswith("BookmarkLevel: "):
                    try:
                        current_bookmark["level"] = int(line[len("BookmarkLevel: "):]) - 1
                    except ValueError:
                        continue
                elif line.startswith("BookmarkPageNumber: "):
                    try:
                        current_bookmark["page"] = int(line[len("BookmarkPageNumber: "):])
                    except ValueError:
                        continue
                    if "title" in current_bookmark and "page" in current_bookmark and "level" in current_bookmark:
                        chapter_data.append(current_bookmark)

            return chapter_data
        except subprocess.TimeoutExpired:
            if retry < max_retries - 1:
                wait = min(2 ** retry, 15)
                print(f"  -> pdftk timeout in metadata (retry {retry+1}/{max_retries}), waiting {wait}s...")
                time.sleep(wait)
                continue
            else:
                print("  -> All pdftk metadata retries failed. Using PyPDF only.")
                return []  # Fallback to empty; use PyPDF in caller
        except Exception as e:
            print(f"  -> pdftk metadata error (retry {retry+1}): {e}")
            if retry == max_retries - 1:
                print("  -> All retries failed. Using PyPDF only.")
                return []
            time.sleep(2 ** retry)
    return []

# Main function unchanged
def main():
    parser = argparse.ArgumentParser(
        description="Extracts and prints the chapter outline from a PDF file.",
        formatter_class=argparse.RawTextFormatter,
        epilog="Example:\n  python3 %(prog)s 'DesigningData-IntensiveApplications.pdf'"
    )
    parser.add_argument(
        "pdf_filepath",
        type=str,
        help="The path to the PDF file to process."
    )
    args = parser.parse_args()

    try:
        chapters = get_chapter_data(args.pdf_filepath)
    except FileNotFoundError:
        print(f"Error: The file '{args.pdf_filepath}' was not found.", file=sys.stderr)
        sys.exit(1)

    if chapters is None:
        sys.exit(1)

    if chapters:
        print(f"Chapter Data for '{args.pdf_filepath}':")
        for chapter in chapters:
            indent = "  " * chapter["level"]
            print(f"{indent}Title: {chapter['title']}, Page: {chapter['page']}")
    else:
        print(f"No outline/bookmark data found in '{args.pdf_filepath}'.")

if __name__ == "__main__":
    main()
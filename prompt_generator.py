# prompt_generator.py (Improved)
import json

def generate_segmentation_prompt(bookmark_data: list, pdftk_metadata: list, total_pages: int, pdf_path: str) -> str:
    """
    Constructs a detailed, structured, and unambiguous prompt for the Gemini API 
    to request pdftk commands for segmenting a book into individual components.
    """
    # This prompt has been heavily revised for clarity and to prevent chapter aggregation.
    prompt_rules = """
You are a master PDF document analyst. Your sole task is to generate a JSON object containing a list of `pdftk` command-line instructions. These commands will segment a book PDF into its core components based on the provided bookmark data (Table of Contents).

**Your Primary Goal:**
Analyze the bookmark data to identify the precise start and end page for each distinct component of the book.

**Required Components to Identify (if present):**
- Title Page (Mandatory, almost always page 1)
- Table of Contents (Mandatory)
- Foreword
- Preface
- Dedication
- Acknowledgments
- **Each individual Chapter** (CRITICAL: Every chapter must be a separate entry)
- **Each individual Appendix** (CRITICAL: Every appendix must be a separate entry)
- Glossary
- Bibliography / References
- Index

---
**CRITICAL OUTPUT RULES**
---
1.  **JSON ONLY:** Your entire response MUST be a single, valid JSON object. Do not wrap it in markdown, code ticks, or add any explanatory text outside of the JSON structure itself.
2.  **ROOT STRUCTURE:** The JSON object must have a single root key named `"segmentation_commands"`, which contains a list of command objects.
3.  **COMMAND OBJECT STRUCTURE:** Each object in the `"segmentation_commands"` list must have exactly three string keys:
    - `"component_name"`: A file-safe name for the output PDF. Use leading zeros for sorting (e.g., "00_Title_Page", "01_Table_of_Contents", "05_Chapter_03_Methodology").
    - `"pdftk_command"`: The precise `pdftk IN_FILE cat START-END output OUT_FILE` command. You must use the literal placeholders "IN_FILE" and "OUT_FILE".
    - `"justification"`: A brief, single-sentence explanation of how you determined the page range using the bookmark titles.

4.  **CRITICAL RULE - NO CHAPTER AGGREGATION:** You **MUST** generate a separate command object for each individual chapter. For instance, if you identify "Chapter 1", "Chapter 2", and "Chapter 3", you must output three distinct command objects in the list. **NEVER group chapters** (e.g., "Chapters 1-3") into a single command. This is the most important rule.

5.  **PAGE RANGE LOGIC:**
    - The end page of a component is the page number immediately before the start page of the very next component.
    - The very last component in the book (e.g., the final chapter or appendix) must end at the `total_pages` number.
    - Infer components like a "Title Page" or "Copyright Page" from the page gap between the start of the PDF and the first major bookmark (like "Table of Contents").

6.  **BE CONSERVATIVE:** If the provided bookmark data is too sparse, ambiguous, or corrupted to confidently determine the page ranges for the mandatory components, you MUST return an empty list for the `"segmentation_commands"` value. It is better to fail safely (`"segmentation_commands": []`) than to guess and produce incorrect segments.

---
**INPUT DATA**
---

**1. Total Pages in PDF:**
{total_pages}

**2. Bookmark Data (from PyPDF or similar):**
```json
{bookmark_json_string}
```

**3. Pdftk Metadata (additional context):**
```json
{pdftk_json_string}
```
"""
    return prompt_rules.format(
        total_pages=total_pages,
        bookmark_json_string=json.dumps(bookmark_data, separators=(',', ':')), 
        pdftk_json_string=json.dumps(pdftk_metadata, separators=(',', ':'))
    )

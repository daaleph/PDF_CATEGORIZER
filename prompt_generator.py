# prompt_generator.py
import json

def generate_segmentation_prompt(bookmark_data: list, pdftk_metadata: list, total_pages: int, pdf_path: str) -> str:
    """
    Constructs a detailed, structured prompt for the Gemini API to request pdftk commands.
    """
    prompt_rules = """
You are an expert PDF document analyst. Your task is to generate a JSON object containing `pdftk` command-line instructions to segment a book into its key components based on its bookmark data (Table of Contents).

**Your Task:**
Analyze in-depth the provided context bookmark data, pdftk metadata and total page count to identify the physical page ranges for the following components:
- Title Page (Mandatory)
- Table of Contents (Mandatory)
- Each individual Chapter (Mandatory)
- Preface (If exists)
- Foreword (If exists)
- Dedication (If exists)
- Acknowledgments (If exists)
- Each individual Appendix (If exists)
- Glossary (If exists)
- Bibliography/References (If exists)

Note that the in provided context, objects of the form 
**
    "title": "Greedy versus Non-Greedy",
    "level": 1,
    "page": 17
** where just in this object the double asterisk mean curly brackets
have highly useful contexts to identify physical page ranges of the desired components where `level` variable compared with the entire context can be used to infer the nesting level that in fact is an indirect measure to look for the desired components because multiple objects with the same level and semantically probable to be expected components

**Output Rules:**
1.  Your entire output MUST be a single, valid JSON object. Do not include any text, code formatting ticks, or explanations outside of the JSON structure.
2.  The root of the JSON object must be a key "segmentation_commands" whose value is a list of command objects.
3.  Each object in the list must have three string keys:
    - "component_name": A file-safe, descriptive name for the output PDF (e.g., "00_Table_of_Contents", "Chapter_01_Introduction", "Appendix_A_Data_Tables"). Use leading zeros for proper file sorting.
    - "pdftk_command": The exact `pdftk IN_FILE cat START-END output OUT_FILE` command. Use the placeholder "IN_FILE" for the input path and "OUT_FILE" for the output path.
    - "justification": A brief, single-sentence explanation of how you determined the page range from the bookmark titles and page numbers.
4.  **Inferring Page Ranges:**
    - The end page of any component is the page number immediately preceding the start page of the *next* component in the outline.
    - The final component in the book ends at the total page count.
    - **Title Page:** This is almost always page 1.
    - **Copyright/Dedication:** These often follow the title page. You must infer their presence and length from the gap before the Table of Contents or Preface.
    - **Table of Contents:** Typically starts on a page titled "Contents" or similar and ends right before the first major section like "Introduction", "Preface", or "Chapter 1".
5.  **BE CONSERVATIVE and ROBUST:**
    - If the bookmark data is ambiguous, sparse, or of poor quality, and you cannot confidently identify the required components, your JSON output for "segmentation_commands" should be an EMPTY LIST `[]`.
    - It is better to return an empty list than to guess and produce incorrect commands.

**Input PDF File Path (for use in commands):**
{pdf_path}

**Total Pages in PDF:**
{total_pages}

**Bookmark Data (Table of Contents):**
```json
{bookmark_json_string}
```

**Pdftk Metadata:**
```json
{pdftk_json_string}
```
"""
    return prompt_rules.format(
    pdf_path=pdf_path,
    total_pages=total_pages,
    bookmark_json_string=json.dumps(bookmark_data, indent=2),
    pdftk_json_string=json.dumps(pdftk_metadata, indent=2)
)
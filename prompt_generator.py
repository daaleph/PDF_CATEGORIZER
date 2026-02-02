# prompt_generator.py (Improved)
import json, os


def generate_segmentation_prompt(bookmark_data: list, pdftk_metadata: list, total_pages: int, pdf_path: str) -> str:
    """
    Construye un prompt altamente estricto y reforzado para forzar el esquema JSON exacto con las claves nuevas,
    placeholders consistentes (IN_FILE / OUT_FILE) y justificación breve.
    Incluye ejemplos claros de lo que es correcto e incorrecto para evitar cualquier desviación.
    """
    
    # Convertir los bookmarks a string JSON legible (sin truncar demasiado)
    bookmarks_json = json.dumps(bookmark_data, indent=2, ensure_ascii=False)

    # Información opcional de pdftk (puede ser None)
    pdftk_info = ""
    if pdftk_metadata:
        pdftk_info = f"- pdftk metadata lines: {' | '.join(pdftk_metadata)}\n"

    prompt = f"""
You are an expert PDF segmentation engineer specializing in generating precise, executable `pdftk` commands from bookmark structures.

TASK:
Analyze the provided bookmark hierarchy and total page count, then generate a JSON array of objects that define how to split the PDF into logical components (front matter, each chapter/section, appendices, bibliography, index, etc.).

CRITICAL RULES:
1. Output ONLY a valid JSON array. No explanatory text, no markdown fences, no extra characters before or after the array.
2. Each object in the array MUST have EXACTLY these three keys:
   - "component_name": string → Clean, filesystem-safe name for the section (no extension, no invalid chars like / \\ : * ? " < > |). Use numbering like "01_", "02_" for ordering.
   - "pdftk_command": string → The exact `pdftk` command using placeholders:
        - Use "IN_FILE" instead of the real input path.
        - Use "OUT_FILE" instead of the real output path.
        - Format: "pdftk IN_FILE cat START-END output OUT_FILE" (or "cat START" if single page).
   - "justification": string → Brief one-sentence reason for the chosen page range (e.g., "Starts at bookmark page X, ends just before next bookmark at Y").
3. DO NOT use any other keys (no "command", "filename", "page_range", "title", etc.).
4. Cover the entire document without gaps or overlaps unless explicitly justified.
5. Prioritize individual extraction of: Front Cover, Title Page, Table of Contents, Preface/Acknowledgements, EACH CHAPTER, Appendices, Bibliography/References, Index, Back Cover.

DATA PROVIDED:
- File: {os.path.basename(pdf_path)}
- Total Pages: {total_pages}
{pdftk_info}- Bookmarks (title, page, level):
{bookmarks_json}

EXAMPLES OF CORRECT OUTPUT:
[
  {{
    "component_name": "00_Front_Cover",
    "pdftk_command": "pdftk IN_FILE cat 1 output OUT_FILE",
    "justification": "Page 1 has no bookmark and is visually the cover."
  }},
  {{
    "component_name": "01_Title_Page",
    "pdftk_command": "pdftk IN_FILE cat 2-3 output OUT_FILE",
    "justification": "Title and copyright pages before Table of Contents bookmark at page 4."
  }},
  {{
    "component_name": "02_Table_of_Contents",
    "pdftk_command": "pdftk IN_FILE cat 4-8 output OUT_FILE",
    "justification": "Bookmark 'Contents' starts at page 4 and ends just before Chapter 1 at page 9."
  }},
  {{
    "component_name": "03_Chapter_01_Introduction",
    "pdftk_command": "pdftk IN_FILE cat 9-25 output OUT_FILE",
    "justification": "Chapter 1 bookmark at page 9; next chapter starts at page 26."
  }}
]

EXAMPLES OF INCORRECT OUTPUT (DO NOT DO THIS):
- Using wrong keys: "command", "filename", "page_range"
- Adding extra keys
- Including markdown fences like ```json
- Adding explanations outside the JSON
- Using real file paths instead of IN_FILE/OUT_FILE

Generate the JSON array now based on the provided bookmark data:
"""
    return prompt
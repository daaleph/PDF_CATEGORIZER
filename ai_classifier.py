# ai_classifier.py
# (This uses the get_gemini_response function from your template)
import json

def generate_classification_prompt(evidence: dict) -> str:
    """Creates a detailed prompt for the AI classifier."""
    
    hierarchy_definitions = """
    **Level 1: Simple Linear Monograph:** Flat chapter structure, minimal formatting changes.
    **Level 2: Standard Hierarchical Textbook:** Consistent, deep hierarchy (e.g., 1.1, 1.1.1), predictable formatting.
    **Level 3: Composite Edited Handbook/Collection:** Chapters by different authors; inconsistent internal structure per chapter.
    **Level 4A: Hierarchical with Asymmetric Appendices:** A Level 2 book with large, structurally different back-matter (Appendices, Glossary).
    **Level 4B: Modular Reference Collection:** A bundle of separate manuals (e.g., tutorial, API reference), not one book.
    **Level 5: Degraded or Typographically Inferred Structure:** Lacks explicit metadata (bookmarks). Structure must be inferred from layout alone (font sizes, spacing).
    """

    prompt = f"""
    Please act as an expert in computational document analysis. Your task is to classify the structural complexity of a book based on the evidence gathered by analysis scripts.

    **Book File:**
    {evidence.get('file')}

    **Structural Complexity Hierarchy:**
    {hierarchy_definitions}

    **Evidence Collected:**
    ```json
    {json.dumps(evidence, indent=2)}
    ```

    **Analysis and Classification Task:**
    Based *only* on the evidence provided, assign the book to the most appropriate structural complexity level from the hierarchy. Provide a single-line justification for your choice.

    **Format your response as follows:**
    LEVEL: [Your chosen level, e.g., Level 2]
    JUSTIFICATION: [Your single-line justification]
    """
    return prompt

# PDF_CATEGORIZER & SEGMENTATION System

## 1. Introduction

The **PDF_CATEGORIZER** system is a sophisticated two-phase pipeline designed for in-depth analysis and processing of large PDF collections.

1.  **Phase 1: Classification**: The system first analyzes each PDF to determine its **structural complexity**. It uses a combination of metadata analysis and layout inspection to classify books into categories, such as a "Simple Linear Monograph" (Level 1) or a "Standard Hierarchical Textbook" (Level 2). This crucial step identifies which books have reliable, machine-readable data.
2.  **Phase 2: Segmentation**: For books identified as having high-quality metadata, the system uses the Gemini AI to intelligently generate precise command-line instructions. It then executes these commands to automatically split the PDF into its constituent parts, such as the table of contents, individual chapters, and appendices.

This powerful workflow allows you to deconstruct an entire library of books into well-named, chapter-level files, making the content ready for targeted analysis, Retrieval-Augmented Generation (RAG), or ingestion into other AI models with limited context windows.

## 2. Prerequisites

This system relies on Python and several external command-line tools. Ensure you have the following installed:

*   **Python 3**: Download from [python.org](https://python.org/).
*   **Google Gemini API Key**: Obtain one from [Google AI for Developers](https://ai.google.dev/).
*   **pdftk**: A powerful command-line tool for manipulating PDFs. It must be installed and accessible from your system's PATH.
*   **Ghostscript**: Required for handling certain types of PDF processing and password removal. It must be installed and in your system's PATH.
*   **qpdf**: A command-line tool for PDF transformation, used here as a fallback for password removal. It must be installed and in your system's PATH.

## 3. Setup and Configuration

1.  **Download the Project**: Unzip or clone the `PDF_CATEGORIZER` project to your local machine.
2.  **Open a Terminal**: Navigate to the root directory of the `PDF_CATEGORIZER` project.
3.  **Install Dependencies**: It is highly recommended to use a Python virtual environment. Install the required packages using the following command:
    ```bash
    pip install google-generativeai python-dotenv pypdf PyMuPDF pandas
    ```
4.  **Create Environment File**: Create a new file named `.env` in the project's root directory.
5.  **Set API Key**: Open the `.env` file and add your Gemini API key:
    ```
    GEMINI_API_KEY=YOUR_API_KEY
    ```

## 4. How to Use the System: A Two-Step Process

**Step 1: Place Your PDFs**

Place the PDF books you wish to process into the `BOOKS/` directory. The system will recursively scan any subdirectories as well.

**Step 2: Run the Classification Pipeline**

The first step is to classify every book in your collection. Open your terminal in the project root and run:

```bash
python pipe.py
```

This script will:
*   Iterate through every PDF file it finds.
*   Use `metadata_checker.py` to check for a valid table of contents (bookmarks).
*   If no metadata is found, it will fall back to `layout_analyzer.py` to inspect the visual structure.
*   Send the collected evidence to the Gemini API, which assigns a structural complexity level to the book.
*   Save all results to a file named **`book_classifications.jsonl`**. This file is a detailed log of your collection and the input for the next phase.

You can also explore the `graphs/` folder, which contains scripts to visualize the classification results and gain insights into your corpus.

**Step 3: Run the Segmentation Pipeline**

After classification is complete, you can segment the eligible books. In the same terminal, run:

```bash
python segmentation_pipe.py
```

This script performs the following critical actions:
1.  It reads the `book_classifications.jsonl` file.
2.  It **filters for "safe" books**—those that were classified using `metadata_check`, as this confirms they have a reliable table of contents suitable for segmentation.
3.  For each safe book, it sends the bookmark data to the Gemini AI, instructing it to act as an expert and return a list of `pdftk` commands to extract each chapter.
4.  It receives the JSON response and executes each command, effectively splitting the PDF.

## 5. Understanding the Outputs

After running the pipeline, your project directory will contain the following:

*   **`segmented_output/`**: This directory contains the final result. It mirrors the structure of your original `BOOKS/` folder, but inside each book's subfolder, you will find the cleanly separated PDF files (e.g., `00_Title_Page.pdf`, `Chapter_01_Introduction.pdf`).
*   **`book_classifications.jsonl`**: The JSONL file containing the detailed classification results for every book. You can learn more about the classification levels by reading `StructuralComplexityClassificationSystem.md`.
*   **`logs/`**:
    *   `segmentation.jsonl`: A log detailing the success or failure of the segmentation process for each book.
    *   `skipped_books.txt`: A list of books that were not segmented, typically because they lacked the necessary metadata (i.e., they were classified as Level 5).
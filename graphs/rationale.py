# graphs/rationale.py

RATIONALE = {
    "chart_1_overall_composition": """
    **Chart Rationale: Overall Corpus Composition**

    **What it Shows:** This chart provides a high-level inventory of the structural complexity across the entire book collection. Each bar represents the total number of books assigned to a specific complexity level by the AI classifier.

    **How to Interpret:**
    - **Dominant Levels:** The longest bars identify the most common structural types in your corpus. A large 'Level 2' bar indicates a collection of modern, well-structured books. A large 'Level 5' bar is a critical finding, highlighting a significant number of metadata-poor books that require advanced layout analysis.
    - **Pipeline Justification:** This view validates the design of your analysis pipeline. If both Level 2 and Level 5 are prominent, it confirms the necessity of a multi-stage approach that handles both "easy" metadata-rich cases and "hard" layout-dependent cases.
    - **Effort Estimation:** The distribution helps prioritize future parsing efforts. If most books are Level 2, refining the metadata-based parser yields the most value. If Level 5 dominates, improving the layout-analysis heuristics is key.
    """,

    "chart_2_complexity_by_category": """
    **Chart Rationale: Complexity by Book Category**

    **What it Shows:** This stacked bar chart compares the structural makeup of the 'CS_BOOKS' and 'PSY_BOOKS' collections, revealing systematic differences in publishing standards and document types between the two fields.

    **How to Interpret:**
    - **Disciplinary Patterns:** Observe the proportional differences in colors between the bars. A higher proportion of Level 2 and 4 (Hierarchical/Reference) in the CS bar is expected, reflecting the prevalence of structured technical manuals and modern textbooks.
    - **Content Age and Type:** A larger slice of Level 5 (Inferred Structure) or Level 1 (Monograph) in the PSY bar might indicate a higher prevalence of older, scanned material or narrative-driven pop-science books, which tend to have simpler or less reliable metadata.
    - **Parser Adaptability:** This chart demonstrates why a single parsing strategy would be suboptimal. The system must be flexible enough to handle the different "structural signatures" of each subject area.
    """,

    "chart_3_diagnostic_heatmap": """
    **Chart Rationale: Analysis Method vs. Final Classification (Pipeline Performance)**

    **What it Shows:** This heatmap is a crucial diagnostic tool that correlates the analysis method used ('metadata_check' or 'layout_analysis') with the final complexity level assigned to a book.

    **How to Interpret:**
    - **The "Success Diagonal":** High numbers along the diagonal from top-left to bottom-right indicate a healthy pipeline.
        - **Top-Left Quadrant:** Shows that well-structured books (Levels 1-4) were correctly identified using the fast 'metadata_check'.
        - **Bottom-Right Cell:** Shows that metadata-poor books were correctly passed to the 'layout_analysis' fallback.
    - **Investigating Anomalies:** Any significant numbers *off* this diagonal are points of interest. For example, a Level 2 book that required 'layout_analysis' might point to a PDF with faulty bookmarks that `pypdf` couldn't read, revealing a potential edge case to handle. This chart is key for debugging and improving the pipeline's efficiency.
    """,
    
    "chart_4_outline_scatter": """
    **Chart Rationale: Outline Properties vs. Structural Complexity**

    **What it Shows:** This scatter plot visualizes the "metadata signature" of books that contain a machine-readable outline (bookmarks). Each point is a book, positioned by the length (number of entries) and depth (nesting level) of its outline.

    **How to Interpret:**
    - **Structural Clusters:** Different complexity levels form distinct clusters.
        - **Level 1 (Monographs):** Typically cluster at the bottom (low depth = 1) with low-to-moderate length.
        - **Level 2 (Textbooks):** Spread across the upper-right, showing both high depth (>=2) and high length.
        - **Level 3 (Handbooks):** May appear as outliers with low depth but very high length, reflecting many top-level, un-nested chapter entries.
    - **Identifying Outliers:** A book that is far from its colored cluster is an anomaly worth investigating. This plot provides a powerful visual method for understanding the typical metadata shape of each structural category.
    """,

    "chart_5_complexity_anatomy": """
    **Chart Rationale: Anatomy of Structural Complexity Levels**

    **What it Shows:** This radar chart presents a "fingerprint" for each complexity level by plotting its average characteristics across five key scaled metrics. It provides the most comprehensive view of what defines each category.

    **How to Interpret:**
    - **Category Signatures:** Each colored polygon represents the "signature" of a complexity level.
        - **Level 5's Profile:** Will be heavily skewed towards 'Typographic Variety', with near-zero values for all metadata-related axes ('Has Bookmarks', 'Hierarchy Depth', 'ToC Length'). This is the visual definition of a book requiring layout analysis.
        - **Level 2's Profile:** Will show a large, balanced shape with high scores across all axes, representing the ideal, well-structured modern book.
        - **Level 1 vs. Level 2:** Level 1 will have a high 'Has Bookmarks' score but low 'Hierarchy Depth', clearly distinguishing it from the deeper structure of Level 2.
    - **Comparing Levels:** The shapes allow for quick visual comparison. The difference between a Level 2 textbook and a Level 4B reference manual becomes obvious through the extreme values for hierarchy and length in the latter.
    """
}
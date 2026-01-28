#!/usr/bin/env python3
"""
Generates categorical distribution plots to show how metadata properties
(outline length and depth) vary across the final classification levels.

This is a key validation chart that visually confirms the characteristics
of each structural complexity level based on its source metadata.
This version uses a vertical layout and automatic text wrapping for the rationale.
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from load_results import load_classification_data
import textwrap

def add_rationale_box(fig):
    """
    Adds a detailed interpretation box to the figure.
    The text is programmatically wrapped paragraph by paragraph to ensure
    correct formatting and control over the horizontal size of the box.
    """
    WRAP_WIDTH = 25  # characters. Adjust this single value as needed.

    # --- SIMPLIFIED, MAINTAINABLE TEXT BLOCK ---
    # Use all-caps for emphasis instead of HTML tags for reliability.
    # Paragraphs are separated by a blank line.
    rationale_text = textwrap.dedent(f"""
        HOW TO INTERPRET THESE CHARTS:
        These plots validate the classification by analyzing the quality of the embedded PDF bookmarks (the machine-readable ToC).

                                     
        TOP PLOT (OUTLINE LENGTH):
                                     
        • Shows the total number of bookmarks. The log scale is essential to visualize the vast range from simple books (10-50) to large references (1000+).
                                     
        • High values signify a granular, detailed structure (e.g., Textbooks, Handbooks).

                                     
        BOTTOM PLOT (OUTLINE DEPTH):
                                     
        • Shows how deeply nested the bookmarks are (e.g., Chapter → Section → Subsection).
                                     
        • High depth (>2) is the hallmark of a Level 2 or Level 4 hierarchical book.
                                     
        • Low depth (1) indicates a flat Level 1 or Level 3 structure.

                                     
        NOTE: Level 5 books lack metadata and are clustered at 0, confirming the diagnosis.
    """).strip()

    # --- Programmatic Wrapping Logic ---
    # Split the text into paragraphs, wrap each one, then join them back
    # with double newlines for proper paragraph spacing.
    paragraphs = rationale_text.split('\n\n')
    wrapped_paragraphs = [textwrap.fill(p, width=WRAP_WIDTH) for p in paragraphs]
    final_text = '\n\n'.join(wrapped_paragraphs)

    props = dict(boxstyle='round,pad=0.5', facecolor='seashell', alpha=0.95)
    font_properties = {'family': 'monospace', 'size': 8}
    
    fig.text(0.98, 0.5, final_text, transform=fig.transFigure,
             verticalalignment='center', horizontalalignment='right',
             bbox=props, fontdict=font_properties)


def create_metadata_distribution_charts(df: pd.DataFrame):
    """
    Generates categorical distribution plots to show how metadata properties
    vary across the final classification levels.
    """
    if df.empty:
        print("DataFrame is empty. No data to plot.")
        return

    plt.style.use('seaborn-v0_8-whitegrid')
    
    fig, axes = plt.subplots(2, 1, figsize=(16, 18))
    fig.suptitle('Analysis of Metadata Properties by Final Classification Level', fontsize=24, weight='bold')

    class_order = sorted(df['classification'].unique())
    wrapped_labels = [textwrap.fill(label, 15) for label in class_order]

    # --- Plot 1: Outline Length Distribution (Top Plot) ---
    ax1 = axes[0]
    sns.stripplot(
        data=df, x='classification', y='outline_length', order=class_order,
        ax=ax1, jitter=0.3, alpha=0.7, palette='viridis',
        hue='classification', legend=False, s=8
    )
    ax1.set_yscale('log')
    ax1.set_ylim(bottom=1)
    ax1.set_title('Outline Length (Number of Bookmarks)', fontsize=18, pad=15)
    ax1.set_xlabel('', fontsize=14)
    ax1.set_ylabel('Number of Bookmarks (Log Scale)', fontsize=16)
    ax1.set_xticks(range(len(class_order)))
    ax1.set_xticklabels([])

    # --- Plot 2: Outline Depth Distribution (Bottom Plot) ---
    ax2 = axes[1]
    sns.boxplot(
        data=df, x='classification', y='outline_depth', order=class_order,
        ax=ax2, palette='plasma', hue='classification', legend=False
    )
    sns.stripplot(
        data=df, x='classification', y='outline_depth', order=class_order,
        ax=ax2, jitter=0.2, alpha=0.6, color='black'
    )
    ax2.set_title('Outline Depth (Nesting Level)', fontsize=18, pad=15)
    ax2.set_xlabel('Classification Level', fontsize=16)
    ax2.set_ylabel('Max Nesting Depth', fontsize=16)
    ax2.set_xticks(range(len(class_order)))
    ax2.set_xticklabels(wrapped_labels, fontsize=12, rotation=45, ha='right')
    max_depth = df['outline_depth'].max()
    if pd.notna(max_depth) and max_depth > 0:
        ax2.set_yticks(range(int(max_depth) + 2))
    ax2.set_ylim(bottom=-0.5)

    add_rationale_box(fig)

    # Adjust rect to reserve space on the RIGHT for the text box
    # A value of 0.8 leaves 20% of the figure width for the rationale box.
    plt.tight_layout(rect=[0, 0, 0.8, 0.95]) 
    
    output_filename = "chart_6_metadata_by_class.png"
    plt.savefig(output_filename)
    print(f"\nGenerated updated chart (with automatic wrapping): {output_filename}")
    plt.show()

if __name__ == '__main__':
    try:
        df_results = load_classification_data()
        
        df_results['classification'] = df_results['classification'].str.extract(r'(Level [1-5][AB]?)')[0]
        
        class_order = sorted(df_results['classification'].dropna().unique())
        df_results['classification'] = pd.Categorical(
            df_results['classification'], 
            categories=class_order, 
            ordered=True
        )

        create_metadata_distribution_charts(df_results)

    except FileNotFoundError:
        print("Error: 'book_classifications.jsonl' not found. Run the main pipe.py script first.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
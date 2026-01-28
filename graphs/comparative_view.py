import pandas as pd
import matplotlib.pyplot as plt
from load_results import load_classification_data

def add_rationale_box(ax):
    """Adds an interpretation box to the chart."""
    rationale_text = (
        "How to Interpret This Chart:\n\n"
        "This chart compares the structural makeup of the two main book categories.\n"
        "It reveals systematic differences in publishing standards between domains.\n\n"
        "- CS_BOOKS often show more Level 2/4 (highly structured, metadata-rich)\n"
        "  due to modern digital-first publishing (e.g., LaTeX, doc generators).\n"
        "- PSY_BOOKS may have a higher share of Level 1 (monographs) and\n"
        "  Level 5 (older, scanned books with degraded structure)."
    )
    
    props = dict(boxstyle='round,pad=0.5', facecolor='ivory', alpha=0.9)
    
    # Place text box in the top left, a common empty space in bar charts
    ax.text(1.05, 0.5, rationale_text, transform=ax.transAxes, fontsize=9,
            verticalalignment='top', horizontalalignment='left', bbox=props)

# Load the data
df = load_classification_data()

# --- Chart 2: Complexity by Top-Level Category ---
# Create a cross-tabulation of counts
ct = pd.crosstab(df['top_level_category'], df['classification'])

# Ensure the columns (complexity levels) are in a logical order
complexity_order = sorted(df['classification'].unique())
ct = ct.reindex(columns=complexity_order, fill_value=0)

# Create the stacked bar chart
fig, ax = plt.subplots(figsize=(12, 8)) # Increased size
ct.plot(kind='bar', stacked=True, ax=ax, cmap='Spectral', width=0.7)

# Add labels and title
ax.set_title('Structural Complexity by Book Category (CS vs. PSY)', fontsize=16, pad=20)
ax.set_xlabel('Top-Level Category', fontsize=12)
ax.set_ylabel('Number of Books', fontsize=12)
ax.tick_params(axis='x', rotation=0)
ax.legend(title='Complexity Level', bbox_to_anchor=(1.02, 1), loc='upper left')

# Add the rationale box
add_rationale_box(ax)

plt.tight_layout(rect=[0, 0, 0.85, 1]) # Adjust layout to make space for legend
plt.savefig("chart_2_complexity_by_category.png")
print("Generated updated chart: chart_2_complexity_by_category.png")
plt.show()
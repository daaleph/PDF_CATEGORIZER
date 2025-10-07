import matplotlib.pyplot as plt
import seaborn as sns
from load_results import load_classification_data

def add_rationale_box(ax):
    """Adds an interpretation box to the chart."""
    rationale_text = (
        "How to Interpret This Scatter Plot:\n\n"
        "This plot visualizes the structural signature of metadata-rich books.\n\n"
        "- Level 1 (Monographs): Cluster at low depth (Y-axis), showing a flat structure.\n"
        "- Level 2/4 (Textbooks/References): Spread across high depth and high length\n"
        "  (top-right), indicating complex, nested outlines.\n"
        "- Level 3 (Handbooks): May appear with low depth but high length, suggesting\n"
        "  many top-level chapters with little internal nesting in the bookmarks."
    )
    
    props = dict(boxstyle='round,pad=0.5', facecolor='lavender', alpha=0.9)
    
    # Place text box in a region that is often sparse
    ax.text(0.5, 0.98, rationale_text, transform=ax.transAxes, fontsize=9,
            verticalalignment='top', horizontalalignment='right', bbox=props)

# Load the data and filter for books that had an outline
df = load_classification_data()
df_metadata = df[df['has_pypdf_outline'] == True].copy()

# --- Chart 4: Outline Properties vs. Complexity ---
fig, ax = plt.subplots(figsize=(12, 8))

sns.scatterplot(
    data=df_metadata,
    x='outline_length',
    y='outline_depth',
    hue='classification',
    style='classification',
    s=120,
    alpha=0.8,
    palette='deep',
    ax=ax
)

ax.set_title('Metadata Quality: Outline Properties vs. Structural Complexity', fontsize=16, pad=20)
ax.set_xlabel('Outline Length (Number of Bookmarks)', fontsize=12)
ax.set_ylabel('Outline Depth (Nesting Level)', fontsize=12)
ax.legend(title='Complexity Level')
ax.set_xscale('log')

# Add the rationale box
add_rationale_box(ax)

plt.tight_layout()
plt.savefig("chart_4_outline_scatter.png")
print("Generated updated chart: chart_4_outline_scatter.png")
plt.show()
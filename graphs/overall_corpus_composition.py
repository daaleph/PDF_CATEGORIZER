import matplotlib.pyplot as plt
import seaborn as sns
from load_results import load_classification_data

def add_rationale_box(ax):
    """Adds an interpretation box to the chart."""
    rationale_text = (
        "How to Interpret This Chart:\n\n"
        "This chart provides a high-level overview of the corpus.\n"
        "It answers: What is the most common structural type?\n\n"
        "- A large bar for Level 2 indicates a collection of modern,\n"
        "  well-structured books with good metadata.\n"
        "- A large bar for Level 5 signifies that many books lack\n"
        "  metadata, making the layout analysis pipeline essential."
    )
    
    props = dict(boxstyle='round,pad=0.5', facecolor='aliceblue', alpha=0.9)
    
    # Place the text box in a suitable position.
    # The transform=ax.transAxes means coordinates are relative to the axes (0,0 is bottom-left, 1,1 is top-right).
    ax.text(0.95, 0.05, rationale_text, transform=ax.transAxes, fontsize=9,
            verticalalignment='bottom', horizontalalignment='right', bbox=props)


# Load the data
df = load_classification_data()

# --- Chart 1: Overall Corpus Composition ---
plt.style.use('seaborn-v0_8-whitegrid')
fig, ax = plt.subplots(figsize=(12, 7)) # Increased size slightly for the box

# Count the occurrences of each classification
classification_counts = df['classification'].value_counts().sort_values(ascending=True)

# Create the horizontal bar plot
bars = ax.barh(classification_counts.index, classification_counts.values, color=sns.color_palette("viridis", len(classification_counts)))

# Add labels and title
ax.set_title('Distribution of Structural Complexity Across All Books', fontsize=16, pad=20)
ax.set_xlabel('Number of Books', fontsize=12)
ax.set_ylabel('Complexity Level', fontsize=12)

# Add data labels to each bar for clarity
for bar in bars:
    width = bar.get_width()
    ax.text(width + 0.1, bar.get_y() + bar.get_height()/2, f'{int(width)}', va='center', ha='left')

# Add the rationale box to the plot
add_rationale_box(ax)

plt.tight_layout(rect=[0, 0, 1, 0.96])
plt.savefig("chart_1_overall_composition.png")
print("Generated updated chart: chart_1_overall_composition.png")
plt.show()
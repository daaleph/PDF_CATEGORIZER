import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
# Add the textwrap import
import textwrap
from load_results import load_classification_data

# Load the data
df = load_classification_data()

# --- Chart 3: Analysis Method vs. Final Complexity ---
# Create the crosstab
crosstab = pd.crosstab(df['analysis_type'], df['classification'])

# Create the heatmap
fig, ax = plt.subplots(figsize=(10, 6)) # Increased height slightly for wrapped labels
sns.heatmap(crosstab, annot=True, fmt='d', cmap='YlGnBu', linewidths=.5, ax=ax)

# Add labels and title
ax.set_title('Analysis Method vs. Final Classification', fontsize=16, pad=20)
ax.set_ylabel('Analysis Method Used', fontsize=12)
ax.set_xlabel('Assigned Complexity Level', fontsize=12)

# --- NEW CODE FOR WRAPPING LABELS ---
# Get the current labels
labels = [label.get_text() for label in ax.get_xticklabels()]
# Wrap the labels to a specific width (e.g., 15 characters)
wrapped_labels = [textwrap.fill(label, 15) for label in labels]
# Set the new wrapped labels
ax.set_xticklabels(wrapped_labels)
# --- END OF NEW CODE ---

# Use tight_layout() to adjust the plot and prevent labels from being cut off
plt.tight_layout()
plt.savefig("chart_3_diagnostic_heatmap_wrapped_labels.png")
plt.show()
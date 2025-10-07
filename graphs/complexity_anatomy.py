# graphs/complexity_anatomy.py
import pandas as pd
import plotly.graph_objects as go
import plotly.subplots as sp
from sklearn.preprocessing import MinMaxScaler
from load_results import load_classification_data
import math

def create_complexity_subplot_radar_chart(df: pd.DataFrame):
    """
    Generates a figure with multiple radar chart subplots to visualize the 
    defining characteristics of each structural complexity level, avoiding overlap.
    """
    if df.empty:
        print("DataFrame is empty. No data to plot.")
        return

    # --- 1. Data Preparation (Same as before) ---
    metrics = [
        'has_pypdf_outline',
        'outline_depth',
        'outline_length',
        'distinct_font_sizes',
        'page_number_transition'
    ]
    
    df_radar = df.copy()
    df_radar[metrics[3]] = df_radar[metrics[3]].fillna(0)
    df_radar[metrics[4]] = df_radar[metrics[4]].fillna(False).astype(int)
    df_radar[metrics[0]] = df_radar[metrics[0]].astype(int)

    class_profile = df_radar.groupby('classification')[metrics].mean()

    # --- 2. Data Scaling (Crucial for comparison across different units) ---
    scaler = MinMaxScaler()
    scaled_profiles = pd.DataFrame(scaler.fit_transform(class_profile), 
                                   index=class_profile.index, 
                                   columns=class_profile.columns)
    
    # --- 3. Subplot Grid Calculation (NEW) ---
    # Dynamically determine the grid layout to accommodate all levels.
    levels = sorted(df['classification'].unique())
    num_levels = len(levels)
    cols = 3  # Let's aim for a max of 3 columns
    rows = math.ceil(num_levels / cols)
    
    # Create a list of specs for the subplots, specifying 'polar' type for each.
    specs = [[{'type': 'polar'}] * cols for _ in range(rows)]
    
    # Create subplot titles from the classification levels
    subplot_titles = [f"<b>{level}</b>" for level in levels]

    fig = sp.make_subplots(
        rows=rows, 
        cols=cols, 
        specs=specs, 
        subplot_titles=subplot_titles
    )

    # --- 4. Chart Creation with Subplots (ENHANCED) ---
    metric_labels = {
        'has_pypdf_outline': 'Has Bookmarks',
        'outline_depth': 'Hierarchy Depth',
        'outline_length': 'ToC Length',
        'distinct_font_sizes': 'Typographic Variety',
        'page_number_transition': 'Uses Roman Numerals'
    }
    radar_labels = [metric_labels[m] for m in metrics]

    # Loop through each level and add its trace to the correct subplot
    for i, level in enumerate(levels):
        # Plotly subplot indexing is 1-based
        row = i // cols + 1
        col = i % cols + 1

        fig.add_trace(go.Scatterpolar(
            r=scaled_profiles.loc[level].values,
            theta=radar_labels,
            fill='toself',
            name=level, # Although legend is hidden, name is good for hover data
            hovertemplate=f"<b>Characteristic:</b> %{{theta}}<br><b>Scaled Value:</b> %{{r:.2f}}<extra></extra>"
        ), row=row, col=col)

    # --- 5. Layout Update for Subplots (ENHANCED) ---
    # This part is more complex as we need to update the layout for the entire figure
    # and potentially each subplot's axes if needed.
    fig.update_layout(
        title={
            'text': "Anatomy of Structural Complexity Levels (Comparative View)",
            'y':0.97,
            'x':0.5,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': {'size': 24, 'family': 'Arial, bold'}
        },
        showlegend=False,  # Legend is redundant as each subplot is titled
        font_family="Arial",
        height=rows * 450, # Dynamically adjust height based on number of rows
        width=1400,
        margin=dict(l=40, r=40, t=80, b=40)
    )

    # Standardize the radial axis for all subplots to ensure they are comparable
    polar_update = dict(
        radialaxis=dict(
            visible=True,
            range=[0, 1],
            showticklabels=False, # Hiding labels cleans up the look
            ticks=''
        )
    )
    fig.update_polars(polar_update)
    
    # Set the font size for the subplot titles
    for annotation in fig['layout']['annotations']:
        annotation['font'] = {'size': 16, 'family': 'Arial, bold'}


    fig.write_image("chart_5_complexity_anatomy_subplots.png", width=1400, height=rows * 450, scale=2)
    print("\nGenerated enhanced chart: chart_5_complexity_anatomy_subplots.png")
    fig.show()


if __name__ == '__main__':
    try:
        df_results = load_classification_data()
        # Ensure a logical order for plotting
        class_order = sorted(df_results['classification'].unique())
        df_results['classification'] = pd.Categorical(df_results['classification'], categories=class_order, ordered=True)
        
        create_complexity_subplot_radar_chart(df_results)
        
    except FileNotFoundError:
        print("Error: 'book_classifications.jsonl' not found. Run the main pipe.py script first.")
    except Exception as e:
        print(f"An error occurred: {e}")
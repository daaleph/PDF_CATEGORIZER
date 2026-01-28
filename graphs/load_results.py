# load_results.py
import pandas as pd
import json

def load_classification_data(filepath="../book_classifications.jsonl"):
    """
    Loads the .jsonl classification results into a pandas DataFrame.
    """
    records = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            data = json.loads(line)
            # Flatten the nested JSON for easier analysis
            record = {
                'file_path': data['file_path'],
                'classification': data['classification_result']['classification'],
                'justification': data['classification_result']['justification'],
                'has_pypdf_outline': data['final_evidence']['has_pypdf_outline'],
                'outline_depth': data['final_evidence'].get('pypdf_outline_depth', 0),
                'outline_length': data['final_evidence'].get('pypdf_outline_length', 0),
                'analysis_type': data['final_evidence'].get('analysis_type', 'metadata_check'),
                'distinct_font_sizes': data['final_evidence'].get('distinct_font_sizes'),
                'page_number_transition': data['final_evidence'].get('page_number_style_transition_found')
            }
            # Add a top-level category column based on the file path
            record['top_level_category'] = data['file_path'].split('/')[0]
            records.append(record)
    
    df = pd.DataFrame(records)
    return df

if __name__ == '__main__':
    # Example of how to use it
    df = load_classification_data()
    print("Data loaded successfully!")
    print(df.head())
    print(f"\nDataFrame Info:")
    df.info()
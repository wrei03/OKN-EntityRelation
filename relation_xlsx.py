import json
import os
import pandas as pd

# Function to extract the related variable from the filename
def extract_related_variable(filename):
    parts = filename.split('_')
    if len(parts) > 1:
        return parts[1]
    return ''

# Function to process JSON files in a given folder
def process_json_folder(folder_path, dataset_name, year):
    relationships_data = []
    
    for filename in os.listdir(folder_path):
        if filename.endswith('.json'):
            related_variable = extract_related_variable(filename)
            json_file_path = os.path.join(folder_path, filename)
            with open(json_file_path, 'r') as file:
                data = json.load(file)
                
                # Process relationships
                if 'relationships' in data:
                    for relationship in data['relationships']:
                        relationship['Dataset'] = dataset_name
                        relationship['Year'] = year
                        relationship['Related Variable'] = related_variable
                        relationships_data.append(relationship)
    
    return relationships_data

# Process NIBRS_jsonblock folder
spi_folder_path = 'fixed_jsons'
spi_relationships_data = process_json_folder(spi_folder_path, 'SPI', 2016)

# Create a DataFrame from the relationships data
relationships_df = pd.DataFrame(spi_relationships_data)

# Rename columns to match the required format
relationships_df.rename(columns={
    'relationship': 'Relation', 
    'source_entity': 'Source Entity', 
    'target_entity': 'Target Entity', 
    'description': 'Related Variable Description'
}, inplace=True)

# Convert necessary columns to strings to ensure they are hashable
relationships_df['Relation'] = relationships_df['Relation'].astype(str)
relationships_df['Source Entity'] = relationships_df['Source Entity'].astype(str)
relationships_df['Target Entity'] = relationships_df['Target Entity'].astype(str)

# Add the additional required columns if not already present
required_relationship_columns = ['Relation', 'Dataset', 'Year', 'Source Entity', 'Target Entity', 'Related Variable', 'Related Variable Description', 'Reason (optional)']
for col in required_relationship_columns:
    if col not in relationships_df.columns:
        relationships_df[col] = ''

# Reorder columns to match the specified format
relationships_df = relationships_df[required_relationship_columns]

# Load the existing Excel file
excel_file_path = 'datasets_statistics.xlsx'
existing_relationships_df = pd.read_excel(excel_file_path, sheet_name='Relationship')

# Append the new data to the existing data
combined_relationships_df = pd.concat([existing_relationships_df, relationships_df], ignore_index=True)

# Remove duplicate relationships again after combining
combined_relationships_df.drop_duplicates(subset=['Relation', 'Source Entity', 'Target Entity'], keep='first', inplace=True)

# Write the combined DataFrame to the specified sheet
with pd.ExcelWriter(excel_file_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
    combined_relationships_df.to_excel(writer, sheet_name='Relationship', index=False)

print("Data has been successfully written to the Excel sheet.")
from dotenv import load_dotenv, find_dotenv
import os
import openai
import pandas as pd
import json
import time
import tiktoken

# Load environment variables from .env file
load_dotenv()

# Set the API key
openai.api_key = os.environ.get('OPENAI_API_KEY')

# Initialize the client
client = openai.Client(
    api_key=openai.api_key,
)

'''
client = openai.OpenAI(
    api_key=os.environ['OPENAI_API_KEY'],
)
'''

# Read the CSV file
csv_file = 'spi_2016_codebook.csv'
df = pd.read_csv(csv_file)

# Ensure dataframe columns
df['Answer_Meaning'] = df['Answer_Meaning'].fillna('')
df['Description'] = df['Description'].fillna('')

# Concatenate 'Description' and 'Answer_Meaning' for each unique 'Question_Code'
df_grouped = df.groupby('Question_Code').agg({
    'Description': 'first',
    'Answer_Meaning': lambda x: ' '.join(x)
}).reset_index()

df_grouped['long_description'] = df_grouped['Description'] + ' ' + df_grouped['Answer_Meaning']

# Load the list of question codes from the extracted texts file
extracted_texts_file = 'extracted_texts.txt'
if os.path.exists(extracted_texts_file):
    with open(extracted_texts_file, 'r') as file:
        existing_question_codes = set(file.read().splitlines())
else:
    existing_question_codes = set()

# Define the base prompt
base_prompt = """
The main purpose of the Survey of Prison Inmates (SPI) dataset is to provide nationally representative data on the characteristics of inmates in state and federal correctional facilities. This includes data on inmates' criminal history, drug and alcohol use, mental health issues, participation in substance use and mental health treatment, educational and economic background, and experiences with prison programs and services. This data allows researchers, clinicians, policymakers, and the general public to better understand and improve the nation's correctional system and inmate rehabilitation efforts. You are an expert on Ontology and Social Science, and you are currently working on the SPI dataset codebook to extract entities for constructing an Ontology. The Ontology is for the topic of "substance abuse, mental health, and rehabilitation within correctional facilities". Therefore, entities related to criminal history, substance use, economic status, education, mental health, prison programs, infrastructure, law, and similar topics are relevant and potentially support the reasoning of this research.

Currently, we have a list of extracted entities and relations. The entities and relations may be extracted from the documents directly, or they may be summarized or categorized in a reasonable way. Please extract entities and relationships that can serve the topic from the following questions in the SPI survey sheet:

%s

Please generate the results in JSON format as follows:
{
    "variable": "%s",
    "entities": [
        {
            "entity": "SurveyPeriod",
            "description": "The time frame covered by the survey, including the current incarceration period."
        },
        {
            "entity": "IncarcerationReason",
            "description": "The primary reason for the inmate's incarceration."
        },
        {
            "entity": "SubstanceUseHistory",
            "description": "The inmate's history of drug and alcohol use prior to incarceration."
        },
        {
            "entity": "MentalHealthHistory",
            "description": "The inmate's history of mental health issues and treatment."
        },
        {
            "entity": "RehabilitationProgramParticipation",
            "description": "The inmate's participation in rehabilitation programs while incarcerated."
        }
    ],
    "relationships": [
        {
            "relationship": "hasSurveyPeriod",
            "source_entity": "Survey",
            "target_entity": "SurveyPeriod",
            "description": "Relates the survey to the time period covered, including the current incarceration period."
        },
        {
            "relationship": "hasIncarcerationReason",
            "source_entity": "Inmate",
            "target_entity": "IncarcerationReason",
            "description": "Indicates the primary reason for the inmate's incarceration."
        },
        {
            "relationship": "hasSubstanceUseHistory",
            "source_entity": "Inmate",
            "target_entity": "SubstanceUseHistory",
            "description": "Details the inmate's history of drug and alcohol use prior to incarceration."
        },
        {
            "relationship": "hasMentalHealthHistory",
            "source_entity": "Inmate",
            "target_entity": "MentalHealthHistory",
            "description": "Details the inmate's history of mental health issues and treatment."
        },
        {
            "relationship": "hasRehabilitationProgramParticipation",
            "source_entity": "Inmate",
            "target_entity": "RehabilitationProgramParticipation",
            "description": "Indicates the inmate's participation in rehabilitation programs while incarcerated."
        }
    ]
}
"""

# Create the 'jsons' folder if it doesn't exist
if not os.path.exists('jsons'):
    os.makedirs('jsons')

encoding = tiktoken.encoding_for_model("gpt-4o")

def count_tokens(prompt):
    return len(encoding.encode(prompt))

# Function to handle retries and rate limits
def create_completion_with_retry(client, prompt, token, max_retries=50, delay=2):
    retries = 0
    while retries < max_retries:
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=token+25,
                temperature=0.7
            )
            return response
        except openai.RateLimitError:
            print(f"Rate limit exceeded. Retrying in {delay} seconds...")
            time.sleep(delay)
            retries += 1
            delay *= 2
        except Exception as e:
            print(f"An error occurred: {e}")
            break
    raise Exception("Failed to create completion after several retries")

# Loop through each long description and Question_Code, and send a request to the OpenAI API
results = []

for index, row in df_grouped.iterrows():
    question_code = row['Question_Code']
    
    # Check if the question code exists in the extracted texts
    if question_code in existing_question_codes:
        print(f"Skipping Question_Code {question_code} as it already exists in {extracted_texts_file}")
        continue
    else:
        print(f"Processing Question_Code {question_code} as it does not exist in {extracted_texts_file}")

    long_description = row['long_description']
    
    # Create the complete prompt for each long description and Question_Code
    full_prompt = base_prompt % (long_description, question_code)
    
    # Estimate token count
    token_count = len(full_prompt.split())
    if token_count > 4096:  # should be gpt-4o token limit
        print(f"Prompt too long for Question_Code {question_code}. Token count: {token_count}")
        continue

    response = create_completion_with_retry(client, full_prompt, token_count)
    
    # Get the generated JSON
    json_output = response.choices[0].message.content
    
    # Save the JSON to a file
    file_name = f"jsons/{index}_{question_code}.json"
    with open(file_name, 'w') as f:
        f.write(json_output)
    
    # Append to results
    results.append(json_output)
    
    # Save the processed question code to the extracted texts file
    with open(extracted_texts_file, 'a') as file:
        file.write(f"{question_code}\n")

# Print the results
for result in results:
    print(result)

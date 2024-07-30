import os
import json

def fix_unterminated_strings(json_text):
    in_string = False
    escape = False
    fixed_text = []

    for char in json_text:
        if char == '"' and not escape:
            in_string = not in_string
        if char == '\\' and in_string:
            escape = not escape
        else:
            escape = False

        if in_string and char == '\n':
            fixed_text.append('"')
            in_string = False
        fixed_text.append(char)

    if in_string:
        fixed_text.append('"')

    return ''.join(fixed_text)

def ensure_even_quotes(json_text):
    if json_text.count('"') % 2 != 0:
        json_text += '"'
    return json_text

def fix_unbalanced_brackets(json_text):
    open_braces = json_text.count('{')
    close_braces = json_text.count('}')
    open_brackets = json_text.count('[')
    close_brackets = json_text.count(']')

    json_text += '}' * (open_braces - close_braces)
    json_text += ']' * (open_brackets - close_brackets)
    
    json_text = ensure_even_quotes(json_text)
    json_text = fix_unterminated_strings(json_text)

    return json_text

def clean_and_format_json(input_text):
    input_text = fix_unbalanced_brackets(input_text)

    json_start = input_text.find('{')
    json_end = input_text.rfind('}') + 1
    json_text = input_text[json_start:json_end]

    try:
        json_data = json.loads(json_text)
    except json.JSONDecodeError as e:
        line_number = input_text[:e.pos].count('\n') + 1
        column_number = e.pos - input_text.rfind('\n', 0, e.pos)
        print(f"Error decoding JSON: {e.msg} at line {line_number} column {column_number} (char {e.pos})")
        print("Partial JSON Text:", json_text[max(0, e.pos - 20):e.pos + 20])  # Print part of the text around the error for debugging
        return None

    return json_data

def save_json_to_file(json_data, output_file):
    with open(output_file, 'w') as f:
        json.dump(json_data, f, indent=4)

def process_json_files(input_folder, output_folder, skipped_files_log):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    skipped_files = []

    for filename in os.listdir(input_folder):
        if filename.endswith(".json"):
            input_file_path = os.path.join(input_folder, filename)
            with open(input_file_path, 'r') as f:
                input_text = f.read()

            cleaned_json_data = clean_and_format_json(input_text)
            if cleaned_json_data:
                output_file_path = os.path.join(output_folder, filename.replace(".json", "_fix.json"))
                save_json_to_file(cleaned_json_data, output_file_path)
                print(f"Cleaned JSON data has been saved to {output_file_path}")
            else:
                skipped_files.append(filename)
                print(f"Failed to clean and format JSON data for {filename}")

    with open(skipped_files_log, 'w') as f:
        for file in skipped_files:
            f.write(file + '\n')

# Set the input and output folder paths
input_folder = 'jsons'
output_folder = 'fixed_jsons'
skipped_files_log = 'skipped_files.txt'

process_json_files(input_folder, output_folder, skipped_files_log)

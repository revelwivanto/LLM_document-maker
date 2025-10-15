import requests
import time
import os
import json

# --- Configuration ---
API_KEY = '732f30b3-9537-4df9-93a7-6f99e5fca9b3'
BASE_URL = 'https://api.templated.io/v1'

# --- API Functions ---

def get_all_templates(api_key):
    """Fetches a list of all available templates from the API."""
    print("Fetching available templates...")
    url = f"{BASE_URL}/templates"
    headers = {'Authorization': f'Bearer {api_key}'}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raises an error for bad responses (4xx or 5xx)
        print("Successfully fetched templates.")
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching templates: {e}")
        return None

def get_template_layers(api_key, template_id):
    """Fetches the layer details for a specific template."""
    url = f"{BASE_URL}/template/{template_id}/layers"
    headers = {'Authorization': f'Bearer {api_key}'}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching layers for template {template_id}: {e}")
        return None

def render_template(api_key, template_id, layers_data):
    """Sends a render request to the API and downloads the result."""
    print(f"Sending render request for template: {template_id}")
    url = f"{BASE_URL}/render"
    headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {api_key}'}
    payload = {'template': template_id, 'layers': layers_data, 'format': 'jpg'}

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        
        render_details = response.json()
        print("Render request accepted. Details:")
        print(f"  - Render ID: {render_details.get('id')}")
        print(f"  - Template Name: {render_details.get('templateName')}")

        image_url = render_details.get('url')
        if image_url:
            print("Downloading the generated image...")
            image_response = requests.get(image_url)
            image_response.raise_for_status()
            
            file_name = f"output_{render_details.get('id')}.jpg"
            with open(file_name, 'wb') as f:
                f.write(image_response.content)
            print(f"SUCCESS! Saved image as {file_name}")
        else:
            print("ERROR: Render response did not contain a download URL.")

    except requests.exceptions.RequestException as e:
        print(f"Render request failed: {e}")
        if e.response:
            print(f"   Response: {e.response.text}")

# --- Helper Functions ---

def load_data_from_json(filepath):
    """Loads and validates shared data from a JSON file."""
    if not os.path.exists(filepath):
        print(f"Error: JSON file not found at '{filepath}'")
        return None
    try:
        with open(filepath, mode='r', encoding='utf-8') as infile:
            data = json.load(infile)
        # Basic validation
        if 'sharedData' not in data or 'documents' not in data:
            print("Error: JSON must contain 'sharedData' and 'documents' keys.")
            return None
        if not isinstance(data['documents'], list) or not data['documents']:
            print("Error: 'documents' key must contain a non-empty list.")
            return None
        print(f"Successfully loaded shared data and {len(data['documents'])} document(s) from JSON.")
        return data
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in file '{filepath}'. Please check the format.")
        return None
    except Exception as e:
        print(f"Error reading JSON file: {e}")
        return None

# --- Main Application Logic ---

def main():
    """Main function to run the interactive CLI application."""
    templates = get_all_templates(API_KEY)
    if not templates:
        return

    print("\n--- Available Templates ---")
    for i, tpl in enumerate(templates):
        print(f"  [{i + 1}] {tpl.get('name')} (ID: ...{tpl.get('id')[-12:]})")

    # --- Get User's Template Selection ---
    while True:
        try:
            choice_str = input("\nEnter the number(s) of the templates you want to use, separated by commas (e.g., 1,3): ")
            choices = [int(c.strip()) for c in choice_str.split(',')]
            selected_templates = [templates[i - 1] for i in choices]
            break
        except (ValueError, IndexError):
            print("Invalid input. Please enter numbers from the list.")

    # --- Gather All Unique Layers from Selected Templates ---
    unique_layers = {}
    all_template_layers = {}
    print("\nAnalyzing selected templates to determine required data...")
    for tpl in selected_templates:
        tpl_id = tpl.get('id')
        layers = get_template_layers(API_KEY, tpl_id)
        if layers:
            all_template_layers[tpl_id] = layers
            for layer in layers:
                if layer.get('type') in ['text', 'image']:
                    unique_layers[layer.get('layer')] = layer.get('type')

    # --- Prompt User for Data Source ---
    all_user_data_sets = []
    print("\n--- How would you like to provide data? ---")
    print("  [1] Manually enter data in the console")
    print("  [2] Import data from a JSON file")
    
    while True:
        data_source_choice = input("\nEnter an option (1 or 2): ")
        if data_source_choice == '1':
            # --- Manual Data Entry ---
            print("\n--- Please Provide Data for the Following Fields ---")
            user_data = {}
            for layer_name, layer_type in unique_layers.items():
                prompt = f"Enter value for '{layer_name}'"
                prompt += " (as image URL): " if layer_type == 'image' else ": "
                user_data[layer_name] = input(prompt)
            all_user_data_sets.append(user_data)
            break
        elif data_source_choice == '2':
            # --- JSON Data Import ---
            while True:
                json_path = input("\nEnter the path to your JSON file: ")
                loaded_data = load_data_from_json(json_path)
                if loaded_data:
                    shared_data = loaded_data.get('sharedData', {})
                    documents = loaded_data.get('documents', [])
                    for doc_specific_data in documents:
                        # Merge shared data with document-specific data
                        # The document's data will overwrite shared data if keys conflict
                        final_data = {**shared_data, **doc_specific_data}
                        all_user_data_sets.append(final_data)
                    break
            break
        else:
            print("Invalid choice. Please enter 1 or 2.")

    # --- Render Each Selected Template for Each Data Set ---
    print(f"\n--- Starting Generation Process for {len(all_user_data_sets)} Data Set(s) ---")
    for i, user_data in enumerate(all_user_data_sets):
        print(f"\n--- Processing Data Set {i + 1} of {len(all_user_data_sets)} ---")
        for tpl in selected_templates:
            tpl_id = tpl.get('id')
            
            payload_layers = {}
            required_layers = all_template_layers.get(tpl_id, [])
            for layer in required_layers:
                layer_name = layer.get('layer')
                layer_type = layer.get('type')
                user_value = user_data.get(layer_name)
                
                if user_value:
                    if layer_type == 'text':
                        payload_layers[layer_name] = {'text': user_value}
                    elif layer_type == 'image':
                        payload_layers[layer_name] = {'image_url': user_value}

            render_template(API_KEY, tpl_id, payload_layers)
            time.sleep(1)

if __name__ == "__main__":
    main()


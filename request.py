import requests

# --- Configuration ---
API_KEY = '732f30b3-9537-4df9-93a7-6f99e5fca9b3'
# IMPORTANT: Make sure this is the correct ID from your template's URL in the editor
INVOICE_TEMPLATE_ID = '41c2a881-46c9-41fc-afc7-731f756ed7ed'


# --- API Details ---
url = 'https://api.templated.io/v1/render'
headers = {
  'Content-Type': 'application/json',
  'Authorization': f'Bearer {API_KEY}'
}

# --- Layer Data ---
invoice_layers_data = {
    'logo': {'image_url' : 'https://www.pelindotpk.co.id/business-entities'},
    'Sender-name': {'text': 'PT. Terminal Petikemas Surabaya'},
    'sender-address': {'text': 'Jl. Tanjung Mutiara No.1, Surabaya'},
    'invoice-number': {'text': 'INV/2025/X/101'},
    'date': {'text': 'October 13, 2025'},
    'client-name': {'text': 'Peter Fields'},
    'client-address': {'text': '123 Anywhere St, Any City'},
    'client-phone': {'text': '+123 456 7890'},
    'item1-name': {'text': 'Dell UltraSharp U2723QE Monitor'},
    'item1-quantity': {'text': '10'},
    'item1-price': {'text': 'Rp 8.000.000'},
    'item1-total': {'text': 'Rp 80.000.000'},
    'item2-name': {'text': 'Custom Build PC (Ryzen 7, 32GB RAM)'},
    'item2-quantity': {'text': '10'},
    'item2-price': {'text': 'Rp 15.000.000'},
    'item2-total': {'text': 'Rp 150.000.000'},
    'total-price': {'text': 'Total : Rp 230.000.000'},
}

data = {
    'template': INVOICE_TEMPLATE_ID,
    'layers': invoice_layers_data,
    'format': 'pdf' 
}

print(f"Sending render request for template: {INVOICE_TEMPLATE_ID}")
response = requests.post(url, json=data, headers=headers)

# --- MODIFIED RESPONSE HANDLING ---
if response.status_code == 200:
    print("Render request accepted. Details below:")

    # Parse the JSON response from the server
    render_details = response.json()

    # Print the details in a readable format
    print("-----------------------------------------")
    print(f"  Render ID:     {render_details.get('id')}")
    print(f"  Download URL:  {render_details.get('url')}")
    print(f"  Dimensions:    {render_details.get('width')}x{render_details.get('height')}")
    print(f"  Format:        {render_details.get('format')}")
    print(f"  Template ID:   {render_details.get('templateId')}")
    print(f"  Template Name: {render_details.get('templateName')}")
    print(f"  Created At:    {render_details.get('createdAt')}")
    print("-----------------------------------------")

    # Automatically download the generated image
    image_url = render_details.get('url')
    if image_url:
        print("\nDownloading the generated image...")
        image_response = requests.get(image_url)
        if image_response.status_code == 200:
            # Use the unique render ID for the filename
            file_name = f"output_{render_details.get('id')}.pdf"
            with open(file_name, 'wb') as f:
                f.write(image_response.content)
            print(f"SUCCESS! Saved image as {file_name}")
        else:
            print(f"ERROR: Download failed with status code: {image_response.status_code}")
else:
    print(f" Render request failed. Response code: {response.status_code}")
    print(f"Response: {response.text}")
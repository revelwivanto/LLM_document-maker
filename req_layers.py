import requests

# Assume these variables are defined in your script
API_KEY = "732f30b3-9537-4df9-93a7-6f99e5fca9b3"
template_id = "41c2a881-46c9-41fc-afc7-731f756ed7ed"

# Construct the URL and headers
url = f"https://api.templated.io/v1/template/{template_id}/layers"
headers = {
    "Authorization": f"Bearer {API_KEY}"
}

# Make the GET request
response = requests.get(url, headers=headers)

# Check the response and print the data
if response.status_code == 200:
    # .json() parses the JSON response into a Python dictionary
    layers_data = response.json()
    print("Successfully fetched layers:")
    print(layers_data)
else:
    print(f"Failed to fetch layers. Status code: {response.status_code}")
    print(f"Response: {response.text}")
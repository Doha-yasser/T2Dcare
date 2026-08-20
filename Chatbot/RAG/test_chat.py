import requests

url = "http://127.0.0.1:8000/chat"
payload = {
    "question": "What dietary advice should be given to adults with type 2 diabetes?",
    "history": []
}

response = requests.post(url, json=payload)
print("Status:", response.status_code)
print(response.json())
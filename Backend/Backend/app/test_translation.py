# test_translation.py
import requests
import json

BASE_URL = "http://127.0.0.1:8000/api"

def test_translation():
    # Test basic translation
    response = requests.post(f"{BASE_URL}/translation/translate", json={
        "text": "Hello, how are you?",
        "target_language": "es"
    })
    print("Translation:", response.json())
    
    # Test local phrases
    response = requests.post(f"{BASE_URL}/translation/local-phrases", json={
        "destination": "Paris",
        "user_language": "en"
    })
    print("Local Phrases:", response.json())
    
    # Test supported languages
    response = requests.get(f"{BASE_URL}/translation/supported-languages")
    print("Supported Languages:", response.json())

if __name__ == "__main__":
    test_translation()

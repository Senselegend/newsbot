import requests
import os

def list_gemini_models(api_key):
    url = "https://generativelanguage.googleapis.com/v1beta/models"
    params = {"key": api_key}
    resp = requests.get(url, params=params)
    print(resp.status_code, resp.text)

# Используйте ваш ключ:
list_gemini_models(os.environ["GEMINI_API_KEY"])
# Last modified: 2024-03-26
import requests
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def list_gemini_models(api_key):
    url = "https://generativelanguage.googleapis.com/v1beta/models"
    params = {"key": api_key}
    resp = requests.get(url, params=params)
    logger.info(f"Response status: {resp.status_code}")
    logger.debug(f"Response content: {resp.text}")

# Используйте ваш ключ:
list_gemini_models(os.environ["GEMINI_API_KEY"])

def test_request():
    try:
        resp = requests.get("https://api.example.com/test")
        logger.info(f"Response status: {resp.status_code}")
        logger.debug(f"Response content: {resp.text}")
    except Exception as e:
        logger.error(f"Request failed: {e}")

if __name__ == "__main__":
    test_request()
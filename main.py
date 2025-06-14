# Last modified: 2024-03-26
from dotenv import load_dotenv
load_dotenv()

# Отключаем предупреждение urllib3 о LibreSSL
import warnings
warnings.filterwarnings("ignore", category=Warning)

from app import app  # noqa: F401

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=1338, debug=True)

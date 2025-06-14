from dotenv import load_dotenv

load_dotenv()
import os
import logging
from db import db
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
import requests
from werkzeug.middleware.proxy_fix import ProxyFix
from logging.handlers import RotatingFileHandler

if not os.path.exists('logs'):
    try:
        os.makedirs('logs')
    except FileExistsError:
        # Директория уже существует, игнорируем ошибку
        pass

log_file = os.path.join('logs', 'app.log')
file_handler = RotatingFileHandler(log_file, maxBytes=2*1024*1024, backupCount=5, encoding='utf-8')
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter('[%(asctime)s] %(levelname)s in %(module)s: %(message)s')
file_handler.setFormatter(formatter)
logging.getLogger().addHandler(file_handler)
logging.getLogger().setLevel(logging.WARN)

for logger_name in logging.root.manager.loggerDict:
    logging.getLogger(logger_name).addHandler(file_handler)
    logging.getLogger(logger_name).setLevel(logging.WARN)


import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="urllib3")


# create the app
app = Flask(__name__)


@app.route('/check_gemini_models', methods=['GET'])
def check_gemini_models():
    api_key = os.getenv("GEMINI_API_KEY")
    url = f"https://generativelanguage.googleapis.com/v1/models?key={api_key}"
    try:
        resp = requests.get(url, timeout=5)
        return resp.text, resp.status_code, {'Content-Type': 'application/json'}
    except requests.exceptions.RequestException as e:
        return {"error": f"Request error: {str(e)}"}, 500
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}, 500

@app.route('/check_location', methods=['GET'])
def check_location():
    # Получаем IP пользователя
    user_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    # Проверяем доступность Google Gemini API
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    test_url = f"https://generativelanguage.googleapis.com/v1/models?key={gemini_api_key}"
    try:
        resp = requests.get(test_url, timeout=5)
        google_status = resp.status_code
    except requests.exceptions.RequestException as e:
        google_status = f"Request error: {str(e)}"
    except Exception as e:
        google_status = f"Unexpected error: {str(e)}"
    return jsonify({
        "your_ip": user_ip,
        "google_api_status": google_status
    })

@app.template_filter('nl2br')
def nl2br_filter(s):
    if not s:
        return ''
    return s.replace('\n', '<br>')

# Добавляем глобальные переменные для шаблонов
@app.context_processor
def inject_now():
    from datetime import datetime
    return {'now': datetime.now()}

app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1) # needed for url_for to generate with https

# configure the database, relative to the app instance folder
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///telegram_bot.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Bot configuration
app.config['TELEGRAM_BOT_TOKEN'] = os.environ.get("TELEGRAM_BOT_TOKEN")
app.config['OPENROUTER_API_KEY'] = os.environ.get("OPENROUTER_API_KEY")
app.config['GEMINI_API_KEY'] = os.environ.get("GEMINI_API_KEY")
app.config['SITE_URL'] = os.environ.get("SITE_URL", "https://smartlab-bot.replit.app")
app.config['SITE_NAME'] = os.environ.get("SITE_NAME", "News Bot")

# initialize the app with the extension, flask-sqlalchemy >= 3.0.x
db.init_app(app)

with app.app_context():
    # Make sure to import the models here or their tables won't be created
    import models  # noqa: F401
    db.create_all()
    
    # Import routes
    import routes  # noqa: F401

# Last modified: 2024-03-26
from dotenv import load_dotenv

load_dotenv()
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

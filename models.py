# Last modified: 2024-03-26
from dotenv import load_dotenv

load_dotenv()
from db import db
from datetime import datetime, timedelta
from sqlalchemy import Text, Index
from zoneinfo import ZoneInfo

MSK = ZoneInfo("Europe/Moscow")
UTC = ZoneInfo("UTC")

import logging
logger = logging.getLogger(__name__)

class NewsArticle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(255), unique=True, nullable=False)  # Added 'url' attribute
    title = db.Column(db.String(255), nullable=True)  # было False
    original_content = db.Column(db.Text, nullable=True)  # было False
    created_at = db.Column(db.DateTime, nullable=False)
    summary = db.Column(db.Text, nullable=True)
    hashtags = db.Column(db.String(255), nullable=True)
    is_posted = db.Column(db.Boolean, default=False)
    posted_at = db.Column(db.DateTime, nullable=True)

    def __init__(self, **kwargs):
        super().__init__()
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        # Привести created_at к Europe/Moscow
        if hasattr(self, 'created_at') and self.created_at:
            if self.created_at.tzinfo is None:
                self.created_at = self.created_at.replace(tzinfo=UTC).astimezone(MSK)
            else:
                self.created_at = self.created_at.astimezone(MSK)
        # Привести posted_at к Europe/Moscow
        if hasattr(self, 'posted_at') and self.posted_at:
            if self.posted_at.tzinfo is None:
                self.posted_at = self.posted_at.replace(tzinfo=UTC).astimezone(MSK)
            else:
                self.posted_at = self.posted_at.astimezone(MSK)

    def __repr__(self):
        return f'<NewsArticle {self.title}>'

    @classmethod
    def cleanup_old_records(cls, days: int = 30) -> int:
        """Удаление старых записей"""
        try:
            cutoff_date = datetime.now(MSK) - timedelta(days=days)
            deleted = cls.query.filter(cls.created_at < cutoff_date).delete()
            db.session.commit()
            return deleted
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка при очистке старых записей: {e}")
            return 0

class BotSettings(db.Model):
    ai_provider = db.Column(db.String(20), default="openrouter")  # openrouter или gemini
    id = db.Column(db.Integer, primary_key=True)
    channel_id = db.Column(db.String(100), nullable=True)
    posting_enabled = db.Column(db.Boolean, default=False)
    posting_interval = db.Column(db.Integer, default=60)  # minutes
    max_articles_per_day = db.Column(db.Integer, default=100)
    custom_hashtags = db.Column(db.String(500), default="#новости #smartlab")
    summary_style = db.Column(db.String(50), default="formal")  # engaging, formal, casual
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @staticmethod
    def get_current():
        settings = BotSettings.query.first()
        if not settings:
            settings = BotSettings()
            db.session.add(settings)
            db.session.commit()
        return settings

class PostingLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    article_id = db.Column(db.Integer, db.ForeignKey('news_article.id', ondelete='CASCADE'), nullable=False)
    channel_id = db.Column(db.String(100), nullable=False)
    message_id = db.Column(db.String(100), nullable=True)
    status = db.Column(db.String(20), default='pending')  # pending, success, failed
    error_message = db.Column(Text, nullable=True)
    posted_at = db.Column(db.DateTime, default=lambda: datetime.now(MSK))
    article = db.relationship('NewsArticle', backref=db.backref('posting_logs', lazy=True, cascade="all, delete-orphan"))

    def __init__(self, **kwargs):
        super().__init__()
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        # Привести posted_at к Europe/Moscow
        if hasattr(self, 'posted_at') and self.posted_at:
            if self.posted_at.tzinfo is None:
                self.posted_at = self.posted_at.replace(tzinfo=UTC).astimezone(MSK)
            else:
                self.posted_at = self.posted_at.astimezone(MSK)

class AnalyticsData(db.Model):
    """Модель для хранения аналитических данных"""
    id = db.Column(db.Integer, primary_key=True)
    article_id = db.Column(db.Integer, db.ForeignKey('news_article.id'), nullable=False)
    ai_provider = db.Column(db.String(50), nullable=False)
    summary_generation_time = db.Column(db.Float, nullable=True)
    hashtags_generation_time = db.Column(db.Float, nullable=True)
    summary_length = db.Column(db.Integer, nullable=True)
    hashtags_count = db.Column(db.Integer, nullable=True)
    views_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.now(MSK))
    
    # Связь с NewsArticle
    article = db.relationship('NewsArticle', backref=db.backref('analytics', lazy=True))
    
    def __init__(self, **kwargs):
        """Конструктор с поддержкой произвольных параметров"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    @classmethod
    def cleanup_old_records(cls, days: int = 30) -> int:
        """Удаление старых записей"""
        try:
            cutoff_date = datetime.now(MSK) - timedelta(days=days)
            deleted = cls.query.filter(cls.created_at < cutoff_date).delete()
            db.session.commit()
            return deleted
        except Exception as e:
            db.session.rollback()
            logger.error(f"Ошибка при очистке старых записей: {e}")
            return 0

# Добавляем индексы для оптимизации запросов
Index('idx_article_created', NewsArticle.created_at)
Index('idx_article_posted', NewsArticle.is_posted, NewsArticle.summary.isnot(None))
Index('idx_posting_log_date', PostingLog.posted_at)
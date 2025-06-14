from app import app
from models import db, NewsArticle, PostingLog
from zoneinfo import ZoneInfo

MSK = ZoneInfo("Europe/Moscow")

with app.app_context():
    for article in NewsArticle.query.all():
        if article.created_at and article.created_at.tzinfo is None:
            article.created_at = article.created_at.replace(tzinfo=ZoneInfo('UTC')).astimezone(MSK)
        if article.posted_at and article.posted_at.tzinfo is None:
            article.posted_at = article.posted_at.replace(tzinfo=ZoneInfo('UTC')).astimezone(MSK)
    for log in PostingLog.query.all():
        if log.posted_at and log.posted_at.tzinfo is None:
            log.posted_at = log.posted_at.replace(tzinfo=ZoneInfo('UTC')).astimezone(MSK)
    db.session.commit()

print("Migration to Europe/Moscow timezone complete.")
# Last modified: 2024-03-26
from app import app
from models import db, NewsArticle, PostingLog
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def migrate_to_msk():
    try:
        with app.app_context():
            # Миграция NewsArticle
            articles = NewsArticle.query.all()
            for article in articles:
                if article.published_at:
                    article.published_at = article.published_at.astimezone(ZoneInfo("Europe/Moscow"))
            db.session.commit()
            logger.info(f"Migrated {len(articles)} articles to Moscow timezone")

            # Миграция PostingLog
            logs = PostingLog.query.all()
            for log in logs:
                if log.posted_at:
                    log.posted_at = log.posted_at.astimezone(ZoneInfo("Europe/Moscow"))
            db.session.commit()
            logger.info(f"Migrated {len(logs)} posting logs to Moscow timezone")

            logger.info("Migration to Europe/Moscow timezone complete.")
    except Exception as e:
        logger.error(f"Error during migration: {e}")
        raise

if __name__ == "__main__":
    migrate_to_msk()
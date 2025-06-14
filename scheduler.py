from dotenv import load_dotenv

load_dotenv()
import logging
import time
from datetime import datetime, timedelta
from threading import Thread
from app import app
from db import db
from models import NewsArticle, BotSettings, PostingLog
from scraper import SmartLabScraper
from ai_service import AIService
from telegram_bot import TelegramBotService
from typing import Optional

logger = logging.getLogger(__name__)

class NewsScheduler:
    def __init__(self):
        self.scraper = SmartLabScraper()
        self.telegram_service = TelegramBotService()
        self.running = False
        self.thread = None


    def start(self):
        """Start the scheduler in a background thread"""
        if not self.running:
            self.running = True
            self.thread = Thread(target=self._run_scheduler, daemon=True)
            self.thread.start()
            logger.info("News scheduler started")

    def stop(self):
        """Stop the scheduler"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("News scheduler stopped")

    def _run_scheduler(self):
        """Main scheduler loop"""
        last_scrape_time = datetime.min
        last_post_time = datetime.min
        
        while self.running:
            try:
                with app.app_context():
                    settings = BotSettings.get_current()
                    
                    current_time = datetime.utcnow()
                    
                    # Scrape news every 15 minutes
                    if current_time - last_scrape_time > timedelta(minutes=15):
                        self._scrape_and_process_news()
                        last_scrape_time = current_time
                    
                    # Post news based on settings
                    if (settings.posting_enabled and 
                        current_time - last_post_time > timedelta(minutes=settings.posting_interval)):
                        self._post_pending_articles(settings)
                        last_post_time = current_time
                
                # Sleep for 60 seconds before next check
                time.sleep(60)
                
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                time.sleep(60)  # Wait before retrying

    def _scrape_and_process_news(self):
        """Scrape news and process new articles"""
        try:
            logger.info("Starting news scrape...")
            start_time = time.time()
            
            # Получаем новости из всех источников
            news_items = self.get_all_news(limit=150)
            
            new_articles_count = 0
            skipped_count = 0
            error_count = 0
            
            for item in news_items:
                try:
                    url = item['url']
                    
                    # Check if article already exists
                    existing = NewsArticle.query.filter_by(url=url).first()
                    if existing:
                        skipped_count += 1
                        continue
                    
                    # Get full article content
                    article_data = self.scraper.get_article_content(url)
                    if not article_data:
                        logger.warning(f"Could not get content for: {url}")
                        continue
                    
                    # Используем дату из article_data или из item, или текущее время
                    created_at = article_data.get('published_at') or item.get('published_at') or datetime.utcnow()

                    article = NewsArticle(
                        url=url,
                        title=article_data['title'],
                        original_content=article_data['content'],
                        created_at=created_at
                    )
                    db.session.add(article)
                    db.session.commit()
                    
                    # Сохраняем ID статьи для аналитики
                    article_data['article_id'] = article.id
                    
                    # Generate summary and hashtags
                    self._process_article_ai(article, article_data)
                    
                    new_articles_count += 1
                    logger.warning(f"Processed new article: {article.title[:50]}...")
                except Exception as item_error:
                    logger.error(f"Error processing article {item.get('url', 'unknown')}: {item_error}")
                    error_count += 1
                    continue
            
            execution_time = time.time() - start_time
            logger.warning(f"Scraping completed in {execution_time:.2f}s. {new_articles_count} new articles processed, {skipped_count} skipped, {error_count} errors.")
            
            # Очистка старых записей раз в день
            if datetime.utcnow().hour == 3:  # В 3 часа ночи
                from models import AnalyticsData
                logger.info("Запуск очистки старых записей...")
                result = AnalyticsData.cleanup_old_records(days=30)
                logger.info(f"Очистка старых записей: {'успешно' if result else 'ошибка'}")
            
        except Exception as e:
            logger.error(f"Error in news scraping: {e}")

    def _process_article_ai(self, article: NewsArticle, article_data: dict):
        """Process article with AI for summary and hashtags"""
        try:
            settings = BotSettings.get_current()
            ai_service = AIService(ai_provider=getattr(settings, "ai_provider", "openrouter"))

            # Замеряем время генерации резюме
            summary_start_time = time.time()
            
            # Generate summary
            summary = ai_service.summarize_article(
                article_data, 
                style=settings.summary_style
            )
            
            summary_time = time.time() - summary_start_time

            if summary:
                article.summary = summary

            # Замеряем время генерации хештегов
            hashtags_start_time = time.time()
            
            # Generate hashtags
            hashtags = ai_service.generate_hashtags(
                article_data,
                custom_tags=settings.custom_hashtags
            )
            
            hashtags_time = time.time() - hashtags_start_time

            if hashtags:
                article.hashtags = ' '.join(hashtags)

            db.session.commit()
            
            # Сохраняем аналитику
            try:
                from models import AnalyticsData
                
                analytics = AnalyticsData(
                    article_id=article.id,
                    ai_provider=ai_service.ai_provider,
                    summary_generation_time=summary_time,
                    hashtags_generation_time=hashtags_time,
                    summary_length=len(summary) if summary else 0,
                    hashtags_count=len(hashtags) if hashtags else 0
                )
                db.session.add(analytics)
                db.session.commit()
                
                logger.info(f"Сохранена аналитика для статьи {article.id}: резюме {summary_time:.2f}с, хештеги {hashtags_time:.2f}с")
            except Exception as analytics_error:
                logger.error(f"Ошибка при сохранении аналитики: {analytics_error}")

        except Exception as e:
            logger.error(f"Error processing article with AI: {e}")

    def get_all_news(self, limit=20):
        try:
            # Распределяем лимит между источниками
            per_source_limit = limit // 3
            
            # Получаем новости из разных источников
            news = self.scraper.get_latest_news(limit=per_source_limit)
            news += self.scraper.get_latest_rbc(limit=per_source_limit)
            
            # Добавляем новости из Ведомостей
            try:
                vedomosti_news = self.scraper.get_latest_vedomosti(limit=per_source_limit)
                news += vedomosti_news
                logger.info(f"Добавлено {len(vedomosti_news)} новостей из Ведомостей")
            except Exception as e:
                logger.error(f"Ошибка при получении новостей из Ведомостей: {e}")
            
            # Сортируем по дате публикации (от новых к старым)
            return sorted(news, key=lambda x: x.get('published_at', datetime.min), reverse=True)
        except Exception as e:
            logger.error(f"Error getting all news: {e}")
            return []

    def _post_pending_articles(self, settings: BotSettings):
        """Post unposted articles to Telegram channel"""
        try:
            if not settings.channel_id:
                logger.warning("No channel ID configured")
                return
            
            # Check daily posting limit
            today = datetime.utcnow().date()
            today_posts = PostingLog.query.filter(
                PostingLog.posted_at >= today,
                PostingLog.status == 'success'
            ).count()
            
            if today_posts >= settings.max_articles_per_day:
                logger.warning(f"Daily posting limit reached: {today_posts}/{settings.max_articles_per_day}")
                return
            
            # Get unposted articles with summaries
            unposted = NewsArticle.query.filter(
                NewsArticle.is_posted == False,
                NewsArticle.summary.isnot(None)
            ).order_by(NewsArticle.created_at.desc()).limit(5).all()
            
            posted_count = 0
            
            for article in unposted:
                if posted_count >= (settings.max_articles_per_day - today_posts):
                    break
                
                # Format message
                hashtags = article.hashtags.split() if article.hashtags else []
                message = self.telegram_service.format_message_for_telegram(
                    article.summary,
                    hashtags,
                    article.url
                )
                
                # Send to channel
                result = self.telegram_service.send_message_sync(
                    settings.channel_id,
                    message,
                    article.id
                )
                
                if result['success']:
                    article.is_posted = True
                    article.posted_at = datetime.utcnow()
                    posted_count += 1
                    logger.warning(f"Posted article: {article.title[:50]}...")
                else:
                    logger.error(f"Failed to post article: {result['error']}")
                
                # Small delay between posts
                time.sleep(2)
            
            db.session.commit()
            
            if posted_count > 0:
                logger.warning(f"Posted {posted_count} articles to channel")
            
        except Exception as e:
            logger.error(f"Error posting articles: {e}")

    def manual_scrape(self):
        """Manually trigger a news scrape"""
        with app.app_context():
            self._scrape_and_process_news()

    def manual_post(self, article_id: int, channel_id: Optional[str] = None):
        """Manually post a specific article"""
        with app.app_context():
            article = NewsArticle.query.get(article_id)
            if not article:
                return {"success": False, "error": "Article not found"}
            
            if not article.summary:
                return {"success": False, "error": "Article has no summary"}
            
            settings = BotSettings.get_current()
            target_channel = channel_id or settings.channel_id
            
            if not target_channel:
                return {"success": False, "error": "No channel specified"}
            
            # Format and send message
            hashtags = article.hashtags.split() if article.hashtags else []
            message = self.telegram_service.format_message_for_telegram(
                article.summary,
                hashtags,
                article.url
            )
            
            result = self.telegram_service.send_message_sync(
                target_channel,
                message,
                article.id
            )
            
            if result['success']:
                article.is_posted = True
                article.posted_at = datetime.utcnow()
                db.session.commit()
            
            return result

# Global scheduler instance
news_scheduler = NewsScheduler()

import unittest
import sys
import os
from datetime import datetime

# Добавляем родительскую директорию в sys.path для импорта модулей
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from db import db
from models import NewsArticle, BotSettings, AnalyticsData
from scraper import SmartLabScraper
from ai_service import AIService

class TestIntegration(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app = app.test_client()
        with app.app_context():
            db.create_all()
            
            # Создаем тестовые настройки
            settings = BotSettings(
                ai_provider='openrouter',
                summary_style='engaging',
                custom_hashtags='#тест'
            )
            db.session.add(settings)
            db.session.commit()
            
    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()
    
    def test_article_creation(self):
        """Тест создания статьи в базе данных"""
        with app.app_context():
            # Создаем тестовую статью
            article = NewsArticle(
                url='https://test.com/article',
                title='Тестовая статья',
                original_content='Содержание тестовой статьи',
                created_at=datetime.utcnow()
            )
            db.session.add(article)
            db.session.commit()
            
            # Проверяем, что статья создана
            saved_article = NewsArticle.query.filter_by(url='https://test.com/article').first()
            self.assertIsNotNone(saved_article)
            self.assertEqual(saved_article.title, 'Тестовая статья')
    
    def test_analytics_creation(self):
        """Тест создания аналитики для статьи"""
        with app.app_context():
            # Создаем тестовую статью
            article = NewsArticle(
                url='https://test.com/article',
                title='Тестовая статья',
                original_content='Содержание тестовой статьи',
                created_at=datetime.utcnow()
            )
            db.session.add(article)
            db.session.commit()
            
            # Создаем аналитику для статьи
            analytics = AnalyticsData(
                article_id=article.id,
                ai_provider='openrouter',
                summary_generation_time=1.5,
                hashtags_generation_time=0.8,
                summary_length=150,
                hashtags_count=4
            )
            db.session.add(analytics)
            db.session.commit()
            
            # Проверяем, что аналитика создана
            saved_analytics = AnalyticsData.query.filter_by(article_id=article.id).first()
            self.assertIsNotNone(saved_analytics)
            self.assertEqual(saved_analytics.summary_generation_time, 1.5)
            self.assertEqual(saved_analytics.hashtags_count, 4)
    
    def test_cleanup_old_records(self):
        """Тест очистки старых записей"""
        with app.app_context():
            # Создаем тестовые статьи с разными датами
            old_date = datetime(2020, 1, 1)
            recent_date = datetime.utcnow()
            
            # Старая статья
            old_article = NewsArticle(
                url='https://test.com/old',
                title='Старая статья',
                original_content='Содержание старой статьи',
                created_at=old_date,
                is_posted=True
            )
            db.session.add(old_article)
            
            # Новая статья
            new_article = NewsArticle(
                url='https://test.com/new',
                title='Новая статья',
                original_content='Содержание новой статьи',
                created_at=recent_date
            )
            db.session.add(new_article)
            db.session.commit()
            
            # Запускаем очистку старых записей
            result = AnalyticsData.cleanup_old_records(days=365)
            self.assertTrue(result)
            
            # Проверяем, что старая статья удалена, а новая осталась
            self.assertIsNone(NewsArticle.query.filter_by(url='https://test.com/old').first())
            self.assertIsNotNone(NewsArticle.query.filter_by(url='https://test.com/new').first())
    
    def test_web_routes(self):
        """Тест основных маршрутов веб-интерфейса"""
        # Тест главной страницы
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)
        
        # Тест страницы статей
        response = self.app.get('/articles')
        self.assertEqual(response.status_code, 200)
        
        # Тест страницы настроек
        response = self.app.get('/settings')
        self.assertEqual(response.status_code, 200)
        
        # Тест страницы аналитики
        response = self.app.get('/analytics')
        self.assertEqual(response.status_code, 200)

if __name__ == '__main__':
    unittest.main()
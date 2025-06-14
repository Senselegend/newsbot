import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Добавляем родительскую директорию в sys.path для импорта модулей
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_service import AIService

class TestAIService(unittest.TestCase):
    def setUp(self):
        self.ai_service = AIService(ai_provider="openrouter")
        self.test_article = {
            'title': 'Тестовая новость',
            'content': 'Содержание тестовой новости для проверки работы сервиса',
            'quotes': ['Важная цитата для тестирования'],
            'tags': ['тест', 'новость']
        }
    
    def test_clean_summary(self):
        """Тест очистки резюме от лишних префиксов"""
        # Тест с префиксом
        summary = "вот краткая сводка: Это тестовое резюме"
        result = self.ai_service._clean_summary(summary)
        self.assertEqual(result, "Это тестовое резюме")
        
        # Тест без префикса
        summary = "Это тестовое резюме без префикса"
        result = self.ai_service._clean_summary(summary)
        self.assertEqual(result, "Это тестовое резюме без префикса")
        
        # Тест с пустой строкой
        summary = ""
        result = self.ai_service._clean_summary(summary)
        self.assertEqual(result, "")
        
        # Тест с None
        summary = None
        result = self.ai_service._clean_summary(summary)
        self.assertEqual(result, "")
    
    def test_get_prompt_hash(self):
        """Тест создания хэша запроса"""
        prompt1 = "Тестовый запрос"
        prompt2 = "Другой запрос"
        
        hash1 = self.ai_service._get_prompt_hash(prompt1)
        hash2 = self.ai_service._get_prompt_hash(prompt1)  # Тот же запрос
        hash3 = self.ai_service._get_prompt_hash(prompt2)  # Другой запрос
        
        # Хэши для одинаковых запросов должны совпадать
        self.assertEqual(hash1, hash2)
        
        # Хэши для разных запросов должны отличаться
        self.assertNotEqual(hash1, hash3)
    
    def test_cache_response(self):
        """Тест кэширования ответов"""
        prompt_hash = "test_hash"
        response = "Тестовый ответ"
        
        # Проверяем, что кэш пуст
        self.assertIsNone(self.ai_service._get_cached_response(prompt_hash))
        
        # Добавляем ответ в кэш
        self.ai_service._cache_response(prompt_hash, response)
        
        # Проверяем, что ответ сохранен в кэше
        self.assertEqual(self.ai_service._get_cached_response(prompt_hash), response)
    
    @patch('ai_service.requests.post')
    def test_summarize_article_gemini(self, mock_post):
        """Тест генерации резюме через Gemini API"""
        # Настраиваем мок
        self.ai_service.ai_provider = "gemini"
        self.ai_service.gemini_api_key = "test_key"
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": "Тестовое резюме новости"}]}}]
        }
        mock_post.return_value = mock_response
        
        # Вызываем тестируемый метод
        result = self.ai_service.summarize_article(self.test_article)
        
        # Проверяем результат
        self.assertEqual(result, "Тестовое резюме новости")
        
        # Проверяем вызов API
        mock_post.assert_called_once()
    
    @patch('ai_service.AIService._call_openrouter_api')
    def test_summarize_article_openrouter(self, mock_api_call):
        """Тест генерации резюме через OpenRouter API"""
        # Настраиваем мок
        self.ai_service.ai_provider = "openrouter"
        self.ai_service.api_key = "test_key"
        
        mock_api_call.return_value = {
            "choices": [{"message": {"content": "Тестовое резюме новости"}}]
        }
        
        # Вызываем тестируемый метод
        result = self.ai_service.summarize_article(self.test_article)
        
        # Проверяем результат
        self.assertEqual(result, "Тестовое резюме новости")
        
        # Проверяем вызов API
        mock_api_call.assert_called_once()
    
    def test_fallback_hashtags(self):
        """Тест создания резервных хештегов"""
        # Тест с российской новостью
        article_data = {
            'title': 'Новости России',
            'content': 'Содержание новости о рубле и экономике России'
        }
        result = self.ai_service._fallback_hashtags(article_data)
        self.assertTrue(any(tag.startswith('🇷🇺') for tag in result))
        
        # Тест с американской новостью
        article_data = {
            'title': 'Новости США',
            'content': 'Содержание новости о долларе и ФРС'
        }
        result = self.ai_service._fallback_hashtags(article_data)
        self.assertTrue(any(tag.startswith('🇺🇸') for tag in result))
        
        # Тест с пользовательскими тегами
        result = self.ai_service._fallback_hashtags(article_data, custom_tags="#тест #пользовательский")
        self.assertIn("#тест", result[0])
        self.assertIn("#пользовательский", result[0])

if __name__ == '__main__':
    unittest.main()
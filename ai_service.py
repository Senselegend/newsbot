# Last modified: 2024-03-26
import os
import logging
import re
import requests
import hashlib
import time
from functools import lru_cache
from typing import Dict, List, Optional, Tuple, Any
from models import BotSettings
from dotenv import load_dotenv
from clean_summary import clean_summary
from fix_political_references import fix_political_references
from validate_summary import validate_summary_quality

load_dotenv()
logger = logging.getLogger(__name__)

class AIService:
    def __init__(self, ai_provider=None):
        self.ai_provider = ai_provider or "openrouter"
        self.gemini_api_key = os.environ.get("GEMINI_API_KEY")
        self.api_key = os.environ.get("OPENROUTER_API_KEY")
        self.backup_key = os.environ.get("OPENROUTER_BACKUP_KEY")
        self.backup_key2 = os.environ.get("OPENROUTER_BACKUP_KEY1")
        self.model = "deepseek/deepseek-r1-0528:free"
        self.site_url = os.environ.get("SITE_URL", "https://smartlab-bot.replit.app")
        self.site_name = os.environ.get("SITE_NAME", "News Bot")
        # Кэш для хранения результатов API запросов
        self._cache = {}

    def _get_prompt_hash(self, prompt: str, model: Optional[str] = None, temperature: Optional[float] = None) -> str:
        """Создает хэш строки запроса для кэширования"""
        hash_input = f"{prompt}|{model or self.model}|{temperature or 0.7}"
        return hashlib.md5(hash_input.encode('utf-8')).hexdigest()

    def _get_cached_response(self, prompt_hash: str) -> Optional[str]:
        """Получает кэшированный ответ по хэшу запроса"""
        return self._cache.get(prompt_hash)

    def _cache_response(self, prompt_hash: str, response: str) -> None:
        """Сохраняет ответ в кэш"""
        self._cache[prompt_hash] = response
        # Ограничиваем размер кэша
        if len(self._cache) > 100:
            # Удаляем случайный элемент
            self._cache.pop(next(iter(self._cache)))

    def _call_openrouter_api(self, payload: Dict[str, Any], api_key: Optional[str] = None) -> Dict[str, Any]:
        """Calls OpenRouter API with proper error handling"""
        url = "https://openrouter.ai/api/v1/chat/completions"
        key = api_key or self.api_key
        if key:
            logger.debug(f"Вызов OpenRouter API с ключом: {key[:5]}...")
        else:
            logger.warning("Вызов OpenRouter API без ключа")
            raise ValueError("API key is required for OpenRouter API calls")
        headers = {
            "Authorization": f"Bearer {key}" if key else "",
            "Content-Type": "application/json",
            "HTTP-Referer": self.site_url,
            "X-Title": self.site_name,
        }
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            logger.error(f"OpenRouter API error: {e} {getattr(e.response, 'text', '')}")
            raise

    # Используем внешние функции вместо методов класса
    def _clean_summary(self, summary: Optional[str]) -> str:
        return clean_summary(summary)
        
    def _validate_summary_quality(self, summary: str) -> bool:
        return validate_summary_quality(summary)
        
    def _fix_political_references(self, text: str) -> str:
        return fix_political_references(text)
        
    def build_summary_prompt(self, article_data: Dict[str, Any], style: str) -> str:
        """Builds a prompt for article summarization"""
        title = article_data.get('title', '')
        content = article_data.get('content', '')
        quotes = article_data.get('quotes', [])
        quotes_text = ""
        if quotes:
            important_quotes = [q for q in quotes if len(q) > 30][:3]
            if important_quotes:
                quotes_text = "\n\nВажные цитаты:\n" + "\n".join([f'- \"{q}\"' for q in important_quotes])
        if style == "engaging":
            prompt = f"""Ты - редактор финансового новостного канала. Твоя задача - создать лаконичную новостную сводку для Telegram-канала.

ИСХОДНАЯ НОВОСТЬ:
Заголовок: {title}
Содержание: {content}{quotes_text}

ТРЕБОВАНИЯ К ФОРМАТУ:
1. Начни с 1-2 эмодзи, затем добавь хештеги по теме (#компания #тема #регион)
2. Основной текст должен быть кратким и информативным (2-4 предложения)
3. Разделяй абзацы пустой строкой для лучшей читабельности
4. Если есть цитаты, выделяй их отдельной строкой, начиная с имени автора и двоеточия
5. Для важных цифр и показателей используй жирный шрифт (например, **+15%**)

ТРЕБОВАНИЯ К СОДЕРЖАНИЮ:
1. Пиши только самую важную информацию, без лишних деталей
2. Используй деловой, но понятный язык
3. Для финансовых новостей указывай конкретные цифры и проценты
4. Для геополитических новостей указывай основные заявления сторон
5. ВАЖНО: Дональд Трамп сейчас действующий президент США (с 2025 года)
6. Всегда завершай сводку полным предложением

Ответь только текстом сводки в указанном формате."""
        elif style == "formal":
            prompt = f"""Создай деловую сводку финансовой новости для Telegram-канала.

ИСХОДНАЯ НОВОСТЬ:
Заголовок: {title}
Содержание: {content}{quotes_text}

ТРЕБОВАНИЯ К ФОРМАТУ:
1. Начни с 1-2 эмодзи, связанных с темой (🇷🇺 для России, 🇺🇸 для США, 📊 для рынков)
2. Сразу после эмодзи добавь хештеги (#компания #отчетность #регион)
3. Основной текст должен быть кратким и информативным (2-4 предложения)
4. Разделяй абзацы пустой строкой для лучшей читабельности
5. Для важных цифр используй точные значения (например, $2,1 млрд (+23% г/г))

ТРЕБОВАНИЯ К СОДЕРЖАНИЮ:
1. Деловой и точный стиль изложения
2. Указывай конкретные цифры, проценты и факты
3. Для финансовых новостей выделяй ключевые показатели
4. Если есть цитаты руководства, выделяй их отдельной строкой
5. ВАЖНО: Дональд Трамп сейчас действующий президент США (с 2025 года)
6. Всегда завершай сводку полным предложением

Только текст сводки в указанном формате:"""
        else:
            prompt = f"""Создай новостную сводку для Telegram-канала с акцентом на геополитику.

ИСХОДНАЯ НОВОСТЬ:
Заголовок: {title}
Содержание: {content}{quotes_text}

ТРЕБОВАНИЯ К ФОРМАТУ:
1. Начни с 1-2 эмодзи, отражающих срочность или важность (⚠️ для важных, 🔥 для срочных, ✴️ для рыночных событий)
2. Добавь хештеги по теме и региону (#геополитика #страна #событие)
3. Основной текст должен быть кратким и информативным
4. Для заявлений официальных лиц используй формат "ИМЯ: цитата"
5. Разделяй разные заявления или факты пустой строкой

ТРЕБОВАНИЯ К СОДЕРЖАНИЮ:
1. Указывай только ключевые факты и заявления
2. Для рыночных событий указывай изменения цен (например, #нефть = +10%)
3. Для геополитических новостей перечисляй основные заявления сторон
4. Используй короткие предложения и абзацы
5. ВАЖНО: Дональд Трамп сейчас действующий президент США (с 2025 года)
6. Всегда завершай сводку полным предложением

Только текст сводки в указанном формате:"""
        return prompt

    def summarize_article(self, article_data: Dict, style: str = "engaging") -> Optional[str]:
        start_time = time.time()
        prompt = self.build_summary_prompt(article_data, style)
        
        # Проверяем кэш
        prompt_hash = self._get_prompt_hash(prompt)
        cached_response = self._get_cached_response(prompt_hash)
        if cached_response:
            logger.info(f"Используем кэшированный ответ для резюме (хэш: {prompt_hash[:8]})")
            return cached_response
            
        if self.ai_provider == "gemini":
            api_key = self.gemini_api_key
            if not api_key:
                logger.error("Cannot summarize: GEMINI_API_KEY not set")
                return None
            url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.0-flash-001:generateContent?key={api_key}"
            data = {
                "contents": [
                    {"parts": [{"text": prompt}]}
                ]
            }
            try:
                resp = requests.post(url, json=data, timeout=15)
                if resp.status_code == 200:
                    result = resp.json()
                    summary = result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                    if summary:
                        cleaned_summary = self._clean_summary(summary)
                        # Сохраняем в кэш
                        self._cache_response(prompt_hash, cleaned_summary)
                        
                        # Логируем время выполнения
                        execution_time = time.time() - start_time
                        logger.info(f"Gemini API: сгенерировано резюме за {execution_time:.2f}с")
                        
                        return cleaned_summary
                logger.error(f"Gemini API error: {resp.status_code} {resp.text}")
                return None
            except Exception as e:
                logger.error(f"Gemini API exception: {e}")
                return None
        elif self.ai_provider == "openrouter":
            if not self.api_key:
                logger.error("Cannot summarize: OPENROUTER_API_KEY not set")
                return None
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 500,
                "temperature": 0.7
            }
            for key in [self.api_key, self.backup_key, self.backup_key2]:
                if not key:
                    continue
                try:
                    result = self._call_openrouter_api(payload, api_key=key)
                    logger.warning(f"OpenRouter success with key {key[:12] if key else 'None'}...")  # Покажет первые символы ключа
                    response_content = result["choices"][0]["message"]["content"]
                    if response_content:
                        cleaned_summary = self._clean_summary(response_content.strip())
                        # Сохраняем в кэш
                        self._cache_response(prompt_hash, cleaned_summary)
                        
                        # Логируем время выполнения
                        execution_time = time.time() - start_time
                        logger.info(f"OpenRouter API: сгенерировано резюме за {execution_time:.2f}с")
                        
                        return cleaned_summary
                except Exception as e:
                    logger.warning(f"OpenRouter error with key {key[:12] if key else 'None'}...: {e}")
                    continue
            return None
        else:
            logger.error(f"Unknown ai_provider: {self.ai_provider}")
            return None

    def build_hashtag_prompt(self, article_data: Dict[str, Any], custom_tags: str = "") -> str:
        """Builds a prompt for hashtag generation"""
        title = article_data.get('title', '')
        content = article_data.get('content', '')[:1000]
        existing_tags = article_data.get('tags', [])
        prompt = f"""Создай хештеги с эмодзи для этой новости в формате заголовка.

НОВОСТЬ:
Заголовок: {title}
Содержание: {content}
Существующие теги: {', '.join(existing_tags) if existing_tags else 'нет'}

ТРЕБОВАНИЯ:
1. Начни с подходящего эмодзи флага или символа (🇷🇺 для России, 🇺🇸 для США, 💰 для финансов, ⚡ для энергетики и т.д.)
2. Хештеги на русском языке через пробел
3. Только самые релевантные темы (3-4 хештега максимум)
4. Используй популярные финансовые/экономические теги
5. Формат: 🇷🇺#санкции #россия #экономика (одной строкой)

Только строку с эмодзи и хештегами:"""
        return prompt

    def generate_hashtags(self, article_data: Dict, custom_tags: str = "") -> List[str]:
        start_time = time.time()
        prompt = self.build_hashtag_prompt(article_data, custom_tags)
        
        # Проверяем кэш
        prompt_hash = self._get_prompt_hash(prompt, temperature=0.5)
        cached_response = self._get_cached_response(prompt_hash)
        if cached_response:
            logger.info(f"Используем кэшированный ответ для хештегов (хэш: {prompt_hash[:8]})")
            return [cached_response]
            
        if self.ai_provider == "gemini":
            api_key = self.gemini_api_key
            if not api_key:
                logger.warning("Cannot generate hashtags: GEMINI_API_KEY not set")
                return self._fallback_hashtags(article_data, custom_tags)
            url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.0-flash-001:generateContent?key={api_key}"
            data = {
                "contents": [
                    {"parts": [{"text": prompt}]}
                ]
            }
            try:
                resp = requests.post(url, json=data, timeout=15)
                if resp.status_code == 200:
                    result = resp.json()
                    hashtags = result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                    if hashtags:
                        hashtag_line = hashtags.strip()
                        # Сохраняем в кэш
                        self._cache_response(prompt_hash, hashtag_line)
                        
                        # Логируем время выполнения
                        execution_time = time.time() - start_time
                        logger.info(f"Gemini API: сгенерированы хештеги за {execution_time:.2f}с")
                        
                        return [hashtag_line]
                logger.error(f"Gemini API error: {resp.status_code} {resp.text}")
                return self._fallback_hashtags(article_data, custom_tags)
            except Exception as e:
                logger.error(f"Gemini API exception: {e}")
                return self._fallback_hashtags(article_data, custom_tags)
        elif self.ai_provider == "openrouter":
            if not self.api_key:
                logger.warning("Cannot generate hashtags: OPENROUTER_API_KEY not set")
                return self._fallback_hashtags(article_data, custom_tags)
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 150,
                "temperature": 0.5
            }
            for key in [self.api_key, self.backup_key, self.backup_key2]:
                if not key:
                    continue
                try:
                    result = self._call_openrouter_api(payload, api_key=key)
                    hashtags_text = result["choices"][0]["message"]["content"].strip()
                    if hashtags_text:
                        lines = hashtags_text.split('\n')
                        hashtag_line = lines[0].strip()
                        content = article_data.get('content', '')[:1000]
                        if not re.search(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]', hashtag_line):
                            if any(word in content.lower() for word in ['россия', 'рф', 'рубль', 'газпром']):
                                hashtag_line = '🇷🇺' + hashtag_line
                            elif any(word in content.lower() for word in ['сша', 'доллар', 'фрс']):
                                hashtag_line = '🇺🇸' + hashtag_line
                            elif any(word in content.lower() for word in ['китай', 'юань']):
                                hashtag_line = '🇨🇳' + hashtag_line
                            else:
                                hashtag_line = '💰' + hashtag_line
                        if custom_tags:
                            custom_list = [tag.strip() for tag in custom_tags.split() if tag.strip().startswith('#')]
                            if custom_list:
                                hashtag_line += ' ' + ' '.join(custom_list)
                                
                        # Сохраняем в кэш
                        self._cache_response(prompt_hash, hashtag_line)
                        
                        # Логируем время выполнения
                        execution_time = time.time() - start_time
                        logger.info(f"OpenRouter API: сгенерированы хештеги за {execution_time:.2f}с")
                        
                        return [hashtag_line]
                    return self._fallback_hashtags(article_data, custom_tags)
                except Exception as e:
                    logger.warning(f"OpenRouter error with key {key[:8] if key else 'None'}...: {e}")
                    continue
            return self._fallback_hashtags(article_data, custom_tags)
        else:
            logger.error(f"Unknown ai_provider: {self.ai_provider}")
            return self._fallback_hashtags(article_data, custom_tags)

    def _fallback_hashtags(self, article_data: Dict, custom_tags: str = "") -> List[str]:
        """
        Создает хештеги на основе содержимого статьи, если AI не смог их сгенерировать
        """
        content = (article_data.get('title', '') + ' ' + article_data.get('content', '')).lower()
        emoji = '💰'
        if any(word in content for word in ['россия', 'рф', 'рубль', 'газпром', 'роснефть']):
            emoji = '🇷🇺'
        elif any(word in content for word in ['сша', 'доллар', 'фрс', 'америк']):
            emoji = '🇺🇸'
        elif any(word in content for word in ['китай', 'юань', 'пекин']):
            emoji = '🇨🇳'
        elif any(word in content for word in ['нефть', 'газ', 'энергетик']):
            emoji = '⚡'
        elif any(word in content for word in ['санкции', 'ограничени']):
            emoji = '🚫'
        hashtags = []
        keyword_map = {
            'рубль': '#рубль',
            'доллар': '#доллар', 
            'нефть': '#нефть',
            'газ': '#газ',
            'санкции': '#санкции',
            'россия': '#россия',
            'экономика': '#экономика',
            'банк': '#банки',
            'инвестиции': '#инвестиции'
        }
        for keyword, hashtag in keyword_map.items():
            if keyword in content and hashtag not in hashtags:
                hashtags.append(hashtag)
        if not hashtags:
            hashtags = ['#новости', '#экономика']
        hashtag_line = emoji + ' ' + ' '.join(hashtags[:4])
        if custom_tags:
            custom_list = [tag.strip() for tag in custom_tags.split() if tag.strip().startswith('#')]
            if custom_list:
                hashtag_line += ' ' + ' '.join(custom_list)
        return [hashtag_line]
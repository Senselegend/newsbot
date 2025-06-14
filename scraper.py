# Last modified: 2024-03-26
from dotenv import load_dotenv

load_dotenv()
import requests
from bs4 import BeautifulSoup, Tag
import trafilatura
import logging
import re
import time
from urllib.parse import urljoin, urlparse
from typing import List, Dict, Optional, Tuple
from db import db
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

class SmartLabScraper:
    def __init__(self):
        self.base_url = "https://smartlab.news/"
        self.session = requests.Session()
        # Set headers to mimic a real browser
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        # Кэш для хранения результатов парсинга
        self._cache = {}
        self._cache_ttl = 3600  # 1 час

    def _get_cached_data(self, url: str) -> Optional[Dict]:
        """Получает кэшированные данные по URL"""
        if url in self._cache:
            timestamp, data = self._cache[url]
            if time.time() - timestamp < self._cache_ttl:
                return data
        return None

    def _cache_data(self, url: str, data: Dict) -> None:
        """Сохраняет данные в кэш"""
        self._cache[url] = (time.time(), data)
        # Ограничиваем размер кэша
        if len(self._cache) > 100:
            # Удаляем самые старые записи
            oldest_url = min(self._cache.items(), key=lambda x: x[1][0])[0]
            self._cache.pop(oldest_url)

    def get_latest_news(self, limit: int = 20) -> List[Dict]:
        try:
            # Проверяем кэш
            cached_data = self._get_cached_data(f"{self.base_url}#limit={limit}")
            if cached_data:
                logger.info("Используем кэшированные данные для SmartLab")
                return cached_data[:limit]
                
            start_time = time.time()
            response = self.session.get(self.base_url, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            articles = []
            news_items = soup.find_all(['article', 'div'], class_=re.compile(r'(news|article|item|post)', re.I))
            if not news_items:
                news_items = soup.find_all('a', href=re.compile(r'/read/\\d+'))
            for item in news_items[:limit]:
                try:
                    link_elem = None
                    if isinstance(item, Tag) and getattr(item, 'name', None) == 'a':
                        link_elem = item
                    elif isinstance(item, Tag):
                        link_elem = item.find('a', href=re.compile(r'/read/\\d+'))
                    if not (isinstance(link_elem, Tag) and link_elem.has_attr('href')):
                        continue
                    url = str(link_elem['href'])
                    if url.startswith('/'):
                        url = urljoin(self.base_url, url)
                    elif not url.startswith('http'):
                        continue
                    title = link_elem.get_text(strip=True)
                    if not title and isinstance(item, Tag):
                        title_elem = item.find(['h1', 'h2', 'h3', 'h4', 'span'])
                        title = title_elem.get_text(strip=True) if title_elem else "Без заголовка"
                    if len(title) < 10:
                        continue
                    preview = ""
                    if isinstance(item, Tag):
                        preview_elem = item.find(['p', 'div'])
                        if preview_elem:
                            preview = preview_elem.get_text(strip=True)[:200]
                        
                        # Извлекаем дату публикации
                        published_at = None
                        date_elem = item.find(class_=re.compile(r'(?i)(date|time|published)'))
                        if date_elem:
                            date_text = date_elem.get_text(strip=True)
                            try:
                                # Пытаемся распознать дату
                                if re.search(r'\d{2}\.\d{2}\.\d{4}', date_text):
                                    published_at = datetime.strptime(date_text, '%d.%m.%Y')
                                elif re.search(r'\d{2}\.\d{2}', date_text):
                                    # Если только день и месяц, добавляем текущий год
                                    current_year = datetime.now().year
                                    published_at = datetime.strptime(f"{date_text}.{current_year}", '%d.%m.%Y')
                            except ValueError:
                                pass
                        
                        articles.append({
                            'url': url,
                            'title': title,
                            'preview': preview,
                            'published_at': published_at or datetime.utcnow()
                        })
                except Exception as e:
                    logger.warning(f"Error parsing news item: {e}")
                    continue
                    
            # Сохраняем в кэш
            self._cache_data(f"{self.base_url}#limit={limit}", articles)
            
            execution_time = time.time() - start_time
            logger.warning(f"Found {len(articles)} articles from SmartLab in {execution_time:.2f}s")
            return articles
        except Exception as e:
            logger.error(f"Error scraping SmartLab news: {e}")
            return []

    def get_article_content(self, url: str) -> Optional[Dict]:
        """
        Get full article content from a specific URL
        Returns dictionary with title, content, tags, quotes
        """
        # Проверяем кэш
        cached_data = self._get_cached_data(url)
        if cached_data:
            logger.info(f"Используем кэшированные данные для статьи: {url}")
            return cached_data
            
        try:
            start_time = time.time()
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            # Use trafilatura for better content extraction
            downloaded = trafilatura.fetch_url(url)
            if not downloaded:
                logger.warning(f"Could not download content from {url}")
                return None
                
            content = trafilatura.extract(downloaded)
            if not content:
                logger.warning(f"Could not extract content from {url}")
                return None
            
            # Also parse with BeautifulSoup for additional data
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract title
            title = ""
            title_elem = soup.find(['h1', 'h2'], class_=re.compile(r'(title|heading)', re.I))
            if title_elem:
                title = title_elem.get_text(strip=True)
            else:
                # Fallback to trafilatura title extraction
                title_match = re.search(r'^([^\n]+)', content)
                title = title_match.group(1) if title_match else "Без заголовка"
            
            # Extract quotes (important for preserving them fully as requested)
            quotes = []
            quote_elements = soup.find_all(['blockquote', 'q', 'cite'])
            for quote_elem in quote_elements:
                quote_text = quote_elem.get_text(strip=True)
                if len(quote_text) > 20:  # Only meaningful quotes
                    quotes.append(quote_text)
            
            # Look for quoted text in the content (text in quotes)
            quote_pattern = r'["«»""]([^"«»""]{20,}?)["«»""]'
            content_quotes = re.findall(quote_pattern, content, re.DOTALL)
            quotes.extend([q.strip() for q in content_quotes])
            
            # Extract tags/categories
            tags = []
            tag_elements = soup.find_all(['a', 'span'], class_=re.compile(r'(tag|category|label)', re.I))
            for tag_elem in tag_elements:
                tag_text = tag_elem.get_text(strip=True)
                if tag_text and len(tag_text) < 50:  # Reasonable tag length
                    tags.append(tag_text.lower())
            
            # Extract publication date
            published_at = None
            date_elem = soup.find(class_=re.compile(r'(?i)(date|time|published)'))
            if date_elem:
                date_text = date_elem.get_text(strip=True)
                try:
                    # Пытаемся распознать дату
                    if re.search(r'\d{2}\.\d{2}\.\d{4}', date_text):
                        published_at = datetime.strptime(date_text, '%d.%m.%Y')
                    elif re.search(r'\d{2}\.\d{2}', date_text):
                        # Если только день и месяц, добавляем текущий год
                        current_year = datetime.now().year
                        published_at = datetime.strptime(f"{date_text}.{current_year}", '%d.%m.%Y')
                except ValueError:
                    pass
            
            result = {
                'title': title,
                'content': content,
                'quotes': quotes,
                'tags': list(set(tags)),  # Remove duplicates
                'url': url,
                'published_at': published_at or datetime.utcnow()
            }
            
            # Сохраняем в кэш
            self._cache_data(url, result)
            
            execution_time = time.time() - start_time
            logger.info(f"Extracted article content from {url} in {execution_time:.2f}s")
            
            return result

        except Exception as e:
            logger.error(f"Error getting article content from {url}: {e}")
            return None

    def get_latest_rbc(self, limit: int = 20) -> list[dict]:
        """Получить свежие новости с rbc.ru"""
        # Проверяем кэш
        cached_data = self._get_cached_data("https://www.rbc.ru/#limit=" + str(limit))
        if cached_data:
            logger.info("Используем кэшированные данные для RBC")
            return cached_data[:limit]
            
        logger.warning("Вызван get_latest_rbc")
        url = "https://www.rbc.ru/"
        try:
            start_time = time.time()
            resp = self.session.get(url, timeout=20)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.content, 'html.parser')
            articles = []
            
            # Пробуем разные селекторы для поиска новостей
            news_items = soup.find_all('a', class_=re.compile(r'(?i)main__feed__link'))
            if not news_items:
                logger.warning("Не найдены элементы по main__feed__link, пробуем другие селекторы")
                news_items = soup.find_all('a', class_=re.compile(r'(?i)(item__link|news-feed__item)'))
            if not news_items:
                # Пробуем найти по структуре URL
                news_items = soup.find_all('a', href=re.compile(r'https?://www\.rbc\.ru/.*?/\d{2}/\d{2}/\d{4}/'))
            
            logger.warning(f"RBC: найдено {len(news_items)} элементов")
            
            for item in news_items:
                try:
                    if not isinstance(item, Tag):
                        continue
                    
                    if not item.has_attr('href'):
                        continue
                        
                    news_url = item['href']
                    if not news_url.startswith('http'):
                        news_url = urljoin(url, news_url)
                        
                    title = item.get_text(strip=True)
                    if not title:
                        title_elem = item.find(['h1', 'h2', 'h3', 'h4', 'span'])
                        if title_elem:
                            title = title_elem.get_text(strip=True)
                            
                    if not news_url or not title or len(title) < 10:
                        continue
                        
                    preview = ""
                    preview_elem = item.find(['p', 'div', 'span'], class_=re.compile(r'(?i)(preview|summary|description)'))
                    if preview_elem:
                        preview = preview_elem.get_text(strip=True)[:200]
                    
                    # Извлекаем дату публикации из URL
                    published_at = None
                    date_match = re.search(r'/(\d{4})/(\d{2})/(\d{2})/', news_url)
                    if date_match:
                        year, month, day = map(int, date_match.groups())
                        try:
                            published_at = datetime(year, month, day)
                        except ValueError:
                            pass
                        
                    articles.append({
                        'url': news_url,
                        'title': title,
                        'preview': preview,
                        'published_at': published_at or datetime.utcnow()
                    })
                    
                    if len(articles) >= limit:
                        break
                        
                except Exception as e:
                    logger.warning(f"RBC parse error: {e}")
                    continue
            
            # Сохраняем в кэш
            self._cache_data("https://www.rbc.ru/#limit=" + str(limit), articles)
            
            execution_time = time.time() - start_time
            logger.warning(f"Found {len(articles)} articles from RBC in {execution_time:.2f}s")
            return articles
            
        except Exception as e:
            logger.error(f"Error scraping RBC: {e}")
            return []
    
    def get_latest_vedomosti(self, limit: int = 20) -> List[Dict]:
        """Получить свежие новости с vedomosti.ru"""
        # Проверяем кэш
        cached_data = self._get_cached_data("https://www.vedomosti.ru/economics#limit=" + str(limit))
        if cached_data:
            logger.info("Используем кэшированные данные для Vedomosti")
            return cached_data[:limit]
            
        url = "https://www.vedomosti.ru/economics"
        try:
            start_time = time.time()
            resp = self.session.get(url, timeout=20)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.content, 'html.parser')
            articles = []
            
            news_items = soup.find_all('a', class_=re.compile(r'(?i)(article|news-item)'))
            if not news_items:
                news_items = soup.find_all('div', class_=re.compile(r'(?i)(article|news-item)'))
                
            logger.warning(f"Vedomosti: найдено {len(news_items)} элементов")
            
            for item in news_items[:limit]:
                try:
                    # Извлекаем URL
                    if isinstance(item, Tag) and item.name == 'a' and item.has_attr('href'):
                        news_url = item['href']
                    else:
                        link_elem = item.find('a')
                        if not link_elem or not link_elem.has_attr('href'):
                            continue
                        news_url = link_elem['href']
                        
                    if not news_url.startswith('http'):
                        news_url = urljoin(url, news_url)
                    
                    # Извлекаем заголовок
                    title_elem = item.find(['h1', 'h2', 'h3', 'h4', 'span'], class_=re.compile(r'(?i)(title|heading)'))
                    title = title_elem.get_text(strip=True) if title_elem else item.get_text(strip=True)
                    
                    if not title or len(title) < 10:
                        continue
                    
                    # Извлекаем превью
                    preview = ""
                    preview_elem = item.find(['p', 'div'], class_=re.compile(r'(?i)(preview|summary|description)'))
                    if preview_elem:
                        preview = preview_elem.get_text(strip=True)[:200]
                    
                    # Извлекаем дату публикации
                    published_at = None
                    date_elem = item.find(class_=re.compile(r'(?i)(date|time|published)'))
                    if date_elem:
                        date_text = date_elem.get_text(strip=True)
                        try:
                            # Пытаемся распознать дату
                            if re.search(r'\d{2}\.\d{2}\.\d{4}', date_text):
                                published_at = datetime.strptime(date_text, '%d.%m.%Y')
                            elif re.search(r'\d{2}\.\d{2}', date_text):
                                # Если только день и месяц, добавляем текущий год
                                current_year = datetime.now().year
                                published_at = datetime.strptime(f"{date_text}.{current_year}", '%d.%m.%Y')
                        except ValueError:
                            pass
                    
                    articles.append({
                        'url': news_url,
                        'title': title,
                        'preview': preview,
                        'published_at': published_at or datetime.utcnow()
                    })
                    
                except Exception as e:
                    logger.warning(f"Vedomosti parse error: {e}")
                    continue
            
            # Сохраняем в кэш
            self._cache_data("https://www.vedomosti.ru/economics#limit=" + str(limit), articles)
            
            execution_time = time.time() - start_time
            logger.warning(f"Found {len(articles)} articles from Vedomosti in {execution_time:.2f}s")
            return articles
            
        except Exception as e:
            logger.error(f"Error scraping Vedomosti: {e}")
            return []
    
    def extract_hashtags_from_content(self, content: str, existing_tags: Optional[List[str]] = None) -> List[str]:
        hashtags = set()
        if existing_tags is None:
            existing_tags = []
        for tag in existing_tags:
            clean_tag = re.sub(r'[^\w\s]', '', tag).strip()
            if clean_tag:
                hashtags.add(f"#{clean_tag}")
        financial_terms = [
            'рубль', 'доллар', 'евро', 'валюта', 'курс',
            'нефть', 'газ', 'золото', 'акции', 'облигации',
            'банк', 'кредит', 'процент', 'инфляция',
            'экономика', 'бюджет', 'налог', 'инвестиции',
            'рынок', 'биржа', 'торги', 'котировки',
            'россия', 'рф', 'цб', 'минфин', 'правительство',
            'санкции', 'экспорт', 'импорт', 'пошлина'
        ]
        content_lower = content.lower()
        for term in financial_terms:
            if term in content_lower:
                hashtags.add(f"#{term}")
        return list(hashtags)[:8]
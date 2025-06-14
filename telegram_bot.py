from dotenv import load_dotenv

load_dotenv()
import os
import logging
import asyncio
import requests
from typing import Optional, Dict
from app import db
from models import PostingLog, BotSettings

logger = logging.getLogger(__name__)

class TelegramBotService:
    def __init__(self):
        self.token = os.environ.get("TELEGRAM_BOT_TOKEN")
        self.base_url = f"https://api.telegram.org/bot{self.token}" if self.token else None
        
        if not self.token:
            logger.warning("TELEGRAM_BOT_TOKEN not found in environment variables")

    def send_message_to_channel(self, channel_id: str, message: str, article_id: Optional[int] = None) -> Dict:
        """
        Send message to Telegram channel using HTTP API
        Returns dict with success status and message info
        """
        if not self.base_url:
            return {"success": False, "error": "Bot token not configured"}
        
        if not channel_id:
            return {"success": False, "error": "Channel ID not provided"}
        
        try:
            # Ensure channel_id has proper format
            if not channel_id.startswith('@') and not channel_id.startswith('-'):
                channel_id = '@' + channel_id
            
            # Проверяем длину сообщения и обрезаем при необходимости
            if len(message) > 4000:
                message = message[:3997] + "..."
                logger.warning(f"Message truncated to {len(message)} characters")
            
            # Prepare request data
            data = {
                'chat_id': channel_id,
                'text': message,
                'parse_mode': 'HTML',
                'disable_web_page_preview': False
            }
            
            # Send message via HTTP API
            response = requests.post(f"{self.base_url}/sendMessage", json=data, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            if not result.get('ok'):
                error_msg = result.get('description', 'Unknown error')
                logger.error(f"Telegram API error: {error_msg}")
                
                # Log the failed attempt
                if article_id:
                    log_entry = PostingLog()
                    log_entry.article_id = article_id
                    log_entry.channel_id = channel_id
                    log_entry.status = 'failed'
                    log_entry.error_message = error_msg
                    db.session.add(log_entry)
                    db.session.commit()
                
                return {"success": False, "error": error_msg}
            
            message_data = result.get('result', {})
            message_id = message_data.get('message_id')
            
            # Log the successful posting
            if article_id:
                log_entry = PostingLog()
                log_entry.article_id = article_id
                log_entry.channel_id = channel_id
                log_entry.message_id = str(message_id) if message_id else None
                log_entry.status = 'success'
                db.session.add(log_entry)
                db.session.commit()
            
            logger.warning(f"Successfully sent message to {channel_id}")
            return {
                "success": True,
                "message_id": message_id,
                "chat_id": message_data.get('chat', {}).get('id')
            }
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Network error: {str(e)}"
            logger.error(error_msg)
            
            # Log the failed attempt
            if article_id:
                log_entry = PostingLog()
                log_entry.article_id = article_id
                log_entry.channel_id = channel_id
                log_entry.status = 'failed'
                log_entry.error_message = error_msg
                db.session.add(log_entry)
                db.session.commit()
            
            return {"success": False, "error": error_msg}
        
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(error_msg)
            
            if article_id:
                log_entry = PostingLog()
                log_entry.article_id = article_id
                log_entry.channel_id = channel_id
                log_entry.status = 'failed'
                log_entry.error_message = error_msg
                db.session.add(log_entry)
                db.session.commit()
            
            return {"success": False, "error": error_msg}

    def send_message_sync(self, channel_id: str, message: str, article_id: Optional[int] = None) -> Dict:
        """
        Synchronous wrapper for sending messages
        """
        return self.send_message_to_channel(channel_id, message, article_id)

    def edit_message(self, channel_id, message_id, new_text):
        """
        Edit a previously sent message in Telegram
        Returns dict with success status and error info if any
        """
        if not self.base_url:
            return {"success": False, "error": "Bot token not configured"}
            
        # Ensure channel_id has proper format
        if not channel_id.startswith('@') and not channel_id.startswith('-'):
            channel_id = '@' + channel_id
            
        try:
            # Convert message_id to int if it's a string
            try:
                message_id = int(message_id)
            except (ValueError, TypeError):
                return {"success": False, "error": f"Invalid message_id: {message_id}"}
                
            data = {
                'chat_id': channel_id,
                'message_id': message_id,
                'text': new_text,
                'parse_mode': 'HTML',
                'disable_web_page_preview': False
            }
            
            response = requests.post(f"{self.base_url}/editMessageText", json=data, timeout=30)
            
            # Check if response is valid JSON
            try:
                result = response.json()
            except ValueError:
                logger.error(f"Invalid JSON response from Telegram: {response.text}")
                return {"success": False, "error": "Invalid response from Telegram API"}
                
            if not result.get('ok'):
                error_msg = result.get('description', 'Unknown error')
                logger.error(f"Ошибка Telegram при редактировании: {error_msg}")
                return {"success": False, "error": error_msg}
                
            return {"success": True}
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error when editing message: {e}")
            return {"success": False, "error": f"Network error: {str(e)}"}
            
        except Exception as e:
            logger.exception("Ошибка при редактировании сообщения в Telegram")
            return {"success": False, "error": str(e)}

    def test_channel_access(self, channel_id: str) -> Dict:
        """
        Test if bot can access the channel using HTTP API
        """
        if not self.base_url:
            return {"success": False, "error": "Bot token not configured"}
        
        try:
            # Ensure channel_id has proper format
            if not channel_id.startswith('@') and not channel_id.startswith('-'):
                channel_id = '@' + channel_id
            
            # Try to get chat info
            response = requests.get(f"{self.base_url}/getChat", params={'chat_id': channel_id}, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            if not result.get('ok'):
                error_msg = result.get('description', 'Unknown error')
                return {"success": False, "error": f"Telegram API error: {error_msg}"}
            
            chat_data = result.get('result', {})
            return {
                "success": True,
                "chat_title": chat_data.get('title', channel_id),
                "chat_type": chat_data.get('type', 'unknown'),
                "chat_id": chat_data.get('id')
            }
            
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"Network error: {str(e)}"}
        except Exception as e:
            return {"success": False, "error": f"Unexpected error: {str(e)}"}

    def test_channel_access_sync(self, channel_id: str) -> Dict:
        """
        Synchronous wrapper for testing channel access
        """
        return self.test_channel_access(channel_id)

    def format_message_for_telegram(self, summary: str, hashtags: list, url: str) -> str:
        """
        Format message for Telegram posting with hashtags as header
        """
        # Clean up summary - remove excessive caps
        formatted_summary = self._normalize_text_case(summary) if summary else ""
        
        # Экранируем специальные HTML символы в тексте
        formatted_summary = self._escape_html(formatted_summary)
        
        # Format hashtags as header
        hashtag_string = ' '.join(hashtags) if hashtags else ''
        
        # Construct message with hashtags as header
        message_parts = []
        
        if hashtag_string:
            # Hashtags go first as header
            message_parts.append(hashtag_string)
            # Summary goes right after hashtags without extra line break
            message_parts.append(formatted_summary)
        else:
            message_parts.append(formatted_summary)
        
        # Add source link (временно отключено)
        # message_parts.append(f"<a href=\"{url}\">Источник</a>")
        
        # Join with single line break between hashtags and summary
        return '\n'.join(message_parts)
        
    def _escape_html(self, text: str) -> str:
        """
        Экранирует специальные HTML символы в тексте
        """
        if not text:
            return ""
            
        # Заменяем специальные символы HTML
        replacements = [
            ('&', '&amp;'),
            ('<', '&lt;'),
            ('>', '&gt;')
        ]
        
        for old, new in replacements:
            text = text.replace(old, new)
            
        return text

    def _normalize_text_case(self, text: str) -> str:
        """
        Convert excessive caps to normal sentence case
        """
        if not text:
            return text
        
        # If more than 70% of letters are uppercase, convert to sentence case
        letters = [c for c in text if c.isalpha()]
        if letters:
            upper_count = sum(1 for c in letters if c.isupper())
            if upper_count / len(letters) > 0.7:
                # Convert to sentence case
                sentences = text.split('. ')
                normalized_sentences = []
                for sentence in sentences:
                    if sentence:
                        # Capitalize first letter, lowercase the rest, but preserve quotes and special formatting
                        sentence = sentence.lower()
                        sentence = sentence[0].upper() + sentence[1:] if len(sentence) > 1 else sentence.upper()
                    normalized_sentences.append(sentence)
                text = '. '.join(normalized_sentences)
        
        return text

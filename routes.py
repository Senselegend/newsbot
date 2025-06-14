from dotenv import load_dotenv

load_dotenv()
from flask import render_template, request, redirect, url_for, flash, jsonify
from app import app, db
from models import NewsArticle, BotSettings, PostingLog, AnalyticsData
from scraper import SmartLabScraper
from ai_service import AIService
from telegram_bot import TelegramBotService
from scheduler import news_scheduler
import logging
from datetime import datetime, timedelta
import requests
from flask import current_app
import os
import json
import time

logger = logging.getLogger(__name__)

@app.route('/clear_logs', methods=['POST'])
def clear_logs():
    log_path = os.path.join('logs', 'app.log')
    try:
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write('')
        flash('Логи успешно очищены!', 'success')
    except Exception as e:
        flash(f'Ошибка очистки логов: {e}', 'error')
    return redirect(url_for('logs'))

@app.route('/check_tokens')
def check_tokens():
    from flask import request, abort
    secret = request.args.get('secret')
    expected = os.environ.get('SESSION_SECRET', 'your-session-secret')
    if secret != expected:
        abort(403)
    tokens = {
        'TELEGRAM_BOT_TOKEN': bool(os.environ.get('TELEGRAM_BOT_TOKEN')),
        'OPENROUTER_API_KEY': bool(os.environ.get('OPENROUTER_API_KEY')),
        'GEMINI_API_KEY': bool(os.environ.get('GEMINI_API_KEY')),
        'SESSION_SECRET': bool(os.environ.get('SESSION_SECRET')),
    }
    return render_template('check_tokens.html', tokens=tokens)

@app.route('/test_gemini_api', methods=['GET'])
def test_gemini_api():
    """Проверка доступности Google Gemini API"""
    from ai_service import AIService
    ai_service = AIService(ai_provider="gemini")
    try:
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"
        params = {"key": ai_service.gemini_api_key}
        json_data = {"contents": [{"parts": [{"text": "Say hello"}]}]}
        resp = requests.post(url, params=params, json=json_data, timeout=10)
        if resp.status_code == 200:
            return jsonify({"success": True, "message": "Gemini API доступен"})
        else:
            return jsonify({"success": False, "error": f"Ошибка: {resp.status_code} {resp.text}"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/test_openrouter_api', methods=['GET'])
def test_openrouter_api():
    """Проверка доступности OpenRouter API"""
    api_key = current_app.config.get('OPENROUTER_API_KEY')
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    try:
        resp = requests.get("https://openrouter.ai/api/v1", headers=headers, timeout=10)
        if resp.status_code == 200:
            return jsonify({"success": True, "message": "OpenRouter API доступен"})
        else:
            return jsonify({"success": False, "error": f"Ошибка: {resp.status_code} {resp.text}"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/test_telegram_message', methods=['POST'])
def test_telegram_message():
    """Отправить тестовое сообщение в Telegram"""
    from telegram_bot import TelegramBotService
    settings = BotSettings.get_current()
    channel_id = settings.channel_id
    if not channel_id:
        return jsonify({"success": False, "error": "ID канала не задан в настройках"})
    telegram_service = TelegramBotService()
    result = telegram_service.send_message_sync(channel_id, "Тестовое сообщение от News Bot! ✅")
    return jsonify(result)


@app.route('/')
def index():
    """Main dashboard page"""
    settings = BotSettings.get_current()
    
    # Get recent articles
    recent_articles = NewsArticle.query.order_by(NewsArticle.created_at.desc()).limit(10).all()
    
    # Get posting stats
    total_articles = NewsArticle.query.count()
    posted_articles = NewsArticle.query.filter_by(is_posted=True).count()
    pending_articles = NewsArticle.query.filter(
        NewsArticle.is_posted == False,
        NewsArticle.summary.isnot(None)
    ).count()
    
    # Recent posts
    recent_posts = PostingLog.query.order_by(PostingLog.posted_at.desc()).limit(5).all()
    
    # Получаем статистику по времени генерации
    avg_summary_time = db.session.query(db.func.avg(AnalyticsData.summary_generation_time)).scalar() or 0
    avg_hashtags_time = db.session.query(db.func.avg(AnalyticsData.hashtags_generation_time)).scalar() or 0
    
    return render_template('index.html',
                         settings=settings,
                         recent_articles=recent_articles,
                         total_articles=total_articles,
                         posted_articles=posted_articles,
                         pending_articles=pending_articles,
                         recent_posts=recent_posts,
                         avg_summary_time=avg_summary_time,
                         avg_hashtags_time=avg_hashtags_time)

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    """Bot settings page"""
    settings = BotSettings.get_current()
    
    if request.method == 'POST':
        try:
            # Update settings
            settings.channel_id = request.form.get('channel_id', '').strip()
            settings.posting_enabled = request.form.get('posting_enabled') == 'on'
            settings.posting_interval = int(request.form.get('posting_interval', 60))
            settings.max_articles_per_day = int(request.form.get('max_articles_per_day', 100))
            settings.custom_hashtags = request.form.get('custom_hashtags', '').strip()
            settings.summary_style = request.form.get('summary_style', 'engaging')
            settings.ai_provider = request.form.get('ai_provider', 'openrouter')
            settings.updated_at = datetime.utcnow()
            
            db.session.commit()
            flash('Настройки успешно сохранены!', 'success')
            
            # Start scheduler if posting is enabled
            if settings.posting_enabled:
                news_scheduler.start()
            else:
                news_scheduler.stop()
                
        except ValueError as e:
            flash('Ошибка в настройках: проверьте числовые значения', 'error')
        except Exception as e:
            flash(f'Ошибка сохранения настроек: {str(e)}', 'error')
        
        return redirect(url_for('settings'))
    
    return render_template('settings.html', settings=settings)

@app.route('/test_channel', methods=['POST'])
def test_channel():
    """Test Telegram channel access"""
    channel_id = request.form.get('channel_id', '').strip()
    
    if not channel_id:
        return jsonify({'success': False, 'error': 'Channel ID is required'})
    
    telegram_service = TelegramBotService()
    result = telegram_service.test_channel_access_sync(channel_id)
    
    return jsonify(result)

@app.route('/manual_scrape', methods=['POST'])
def manual_scrape():
    """Manually trigger news scraping"""
    try:
        news_scheduler.manual_scrape()
        flash('Парсинг новостей запущен!', 'success')
    except Exception as e:
        flash(f'Ошибка при запуске парсинга: {str(e)}', 'error')
    
    return redirect(url_for('index'))

@app.route('/articles')
def articles():
    """List all articles"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Фильтры
    filter_posted = request.args.get('posted')
    filter_source = request.args.get('source')
    
    query = NewsArticle.query
    
    # Применяем фильтры
    if filter_posted == 'yes':
        query = query.filter(NewsArticle.is_posted == True)
    elif filter_posted == 'no':
        query = query.filter(NewsArticle.is_posted == False)
        
    if filter_source:
        query = query.filter(NewsArticle.url.like(f'%{filter_source}%'))
    
    articles = query.order_by(NewsArticle.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('articles.html', 
                          articles=articles, 
                          filter_posted=filter_posted,
                          filter_source=filter_source)

@app.route('/article/<int:article_id>')
def article_detail(article_id):
    """Article detail page"""
    article = NewsArticle.query.get_or_404(article_id)
    
    # Get posting history for this article
    posting_logs = PostingLog.query.filter_by(article_id=article_id).order_by(PostingLog.posted_at.desc()).all()
    
    # Получаем аналитику
    analytics = AnalyticsData.query.filter_by(article_id=article_id).first()
    
    return render_template('article_detail.html', 
                          article=article, 
                          posting_logs=posting_logs,
                          analytics=analytics)

@app.route('/post_article/<int:article_id>', methods=['POST'])
def post_article(article_id):
    """Manually post an article"""
    channel_id = request.form.get('channel_id', '').strip()
    
    result = news_scheduler.manual_post(article_id, channel_id)
    
    if result['success']:
        flash('Статья успешно опубликована!', 'success')
    else:
        flash(f'Ошибка публикации: {result["error"]}', 'error')
    
    return redirect(url_for('article_detail', article_id=article_id))

@app.route('/edit_summary/<int:article_id>', methods=['POST'])
def edit_summary(article_id):
    """Ручное редактирование резюме"""
    article = NewsArticle.query.get_or_404(article_id)
    
    try:
        summary = request.form.get('summary', '').strip()
        if summary:
            article.summary = summary
            db.session.commit()
            flash('Резюме успешно обновлено!', 'success')
        else:
            flash('Резюме не может быть пустым', 'error')
    except Exception as e:
        flash(f'Ошибка при обновлении резюме: {e}', 'error')
    
    return redirect(url_for('article_detail', article_id=article_id))

@app.route('/regenerate_summary/<int:article_id>', methods=['POST'])
def regenerate_summary(article_id):
    """Regenerate article summary"""
    article = NewsArticle.query.get_or_404(article_id)
    
    try:
        settings = BotSettings.get_current()
        provider = getattr(settings, "ai_provider", "openrouter")
        ai_service = AIService(ai_provider=provider)
        scraper = SmartLabScraper()
        
        # Get article content again
        article_data = scraper.get_article_content(article.url)
        if not article_data:
            flash('Не удалось получить содержимое статьи', 'error')
            return redirect(url_for('article_detail', article_id=article_id))
        
        # Добавляем ID статьи для аналитики
        article_data['article_id'] = article.id
        
        # Замеряем время генерации
        start_time = time.time()
        
        # Generate new summary
        summary = ai_service.summarize_article(article_data, style=settings.summary_style)
        
        summary_time = time.time() - start_time
        
        if summary:
            article.summary = summary
            
            # Замеряем время генерации хештегов
            hashtags_start_time = time.time()
            
            # Also regenerate hashtags
            hashtags = ai_service.generate_hashtags(article_data, custom_tags=settings.custom_hashtags)
            
            hashtags_time = time.time() - hashtags_start_time
            
            if hashtags:
                article.hashtags = ' '.join(hashtags)
            db.session.commit()
            
            # Сохраняем аналитику
            try:
                analytics = AnalyticsData.query.filter_by(article_id=article.id).first()
                if not analytics:
                    analytics = AnalyticsData(
                        article_id=article.id,
                        ai_provider=ai_service.ai_provider
                    )
                    db.session.add(analytics)
                
                analytics.summary_generation_time = summary_time
                analytics.hashtags_generation_time = hashtags_time
                analytics.summary_length = len(summary)
                analytics.hashtags_count = len(hashtags) if hashtags else 0
                db.session.commit()
            except Exception as analytics_error:
                logger.error(f"Ошибка при сохранении аналитики: {analytics_error}")
            
            # Обновляем сообщения в Telegram, если статья уже была опубликована
            try:
                telegram_service = TelegramBotService()
                for log in article.posting_logs:
                    if log.status == 'success' and log.message_id:
                        new_message = telegram_service.format_message_for_telegram(
                            article.summary,
                            article.hashtags.split() if article.hashtags else [],
                            article.url
                        )
                        edit_result = telegram_service.edit_message(
                            channel_id=log.channel_id,
                            message_id=log.message_id,
                            new_text=new_message
                        )
                        if not edit_result.get('success'):
                            logger.warning(f"Не удалось обновить сообщение в Telegram: {edit_result.get('error')}")
            except Exception as telegram_error:
                logger.error(f"Ошибка при обновлении сообщений в Telegram: {telegram_error}")
                # Продолжаем выполнение, даже если не удалось обновить сообщения
                
            flash('Резюме и хештеги обновлены!', 'success')
        else:
            logger.error("summarize_article вернул пустое значение для article_id=%s", article_id)
            flash('Не удалось создать резюме', 'error')
    except Exception as e:
        logger.exception(f'Ошибка при создании резюме для article_id={article_id}: {e}')
        flash(f'Ошибка при создании резюме: {e}', 'error')
    
    return redirect(url_for('article_detail', article_id=article_id))

@app.route('/delete_article/<int:article_id>', methods=['POST'])
def delete_article(article_id):
    """Delete an article"""
    article = NewsArticle.query.get_or_404(article_id)
    
    try:
        # Delete associated posting logs
        PostingLog.query.filter_by(article_id=article_id).delete()
        
        # Delete the article
        db.session.delete(article)
        db.session.commit()
        
        flash('Статья удалена!', 'success')
        return redirect(url_for('articles'))
        
    except Exception as e:
        flash(f'Ошибка удаления статьи: {str(e)}', 'error')
        return redirect(url_for('article_detail', article_id=article_id))

@app.route('/delete_multiple_articles', methods=['POST'])
def delete_multiple_articles():
    """Delete multiple articles at once"""
    article_ids = request.form.getlist('article_ids')
    
    if not article_ids:
        flash('Не выбрано ни одной статьи для удаления', 'warning')
        return redirect(url_for('articles'))
    
    try:
        # Удаляем связанные записи в PostingLog
        for article_id in article_ids:
            PostingLog.query.filter_by(article_id=article_id).delete()
        
        # Удаляем аналитику
        AnalyticsData.query.filter(AnalyticsData.article_id.in_(article_ids)).delete(synchronize_session=False)
        
        # Удаляем статьи
        deleted_count = NewsArticle.query.filter(NewsArticle.id.in_(article_ids)).delete(synchronize_session=False)
        
        db.session.commit()
        
        flash(f'Удалено статей: {deleted_count}', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при удалении статей: {str(e)}', 'error')
        logger.error(f"Ошибка при массовом удалении статей: {e}")
    
    return redirect(url_for('articles'))

@app.route('/posting_logs')
def posting_logs():
    """View posting logs"""
    page = request.args.get('page', 1, type=int)
    per_page = 50
    
    logs = PostingLog.query.order_by(PostingLog.posted_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('posting_logs.html', logs=logs)

@app.route('/api/stats')
def api_stats():
    """API endpoint for dashboard stats"""
    try:
        # Article stats
        total_articles = NewsArticle.query.count()
        posted_articles = NewsArticle.query.filter_by(is_posted=True).count()
        pending_articles = NewsArticle.query.filter(
            NewsArticle.is_posted == False,
            NewsArticle.summary.isnot(None)
        ).count()
        
        # Recent activity
        today = datetime.utcnow().date()
        today_posts = PostingLog.query.filter(
            PostingLog.posted_at >= today,
            PostingLog.status == 'success'
        ).count()
        
        # Recent articles
        recent_count = NewsArticle.query.filter(
            NewsArticle.created_at >= datetime.utcnow() - timedelta(hours=24)
        ).count()
        
        # Аналитика по времени генерации
        avg_summary_time = db.session.query(db.func.avg(AnalyticsData.summary_generation_time)).scalar() or 0
        avg_hashtags_time = db.session.query(db.func.avg(AnalyticsData.hashtags_generation_time)).scalar() or 0
        
        # Статистика по источникам
        sources = {}
        for domain in ['smartlab.news', 'rbc.ru', 'vedomosti.ru']:
            count = NewsArticle.query.filter(NewsArticle.url.like(f'%{domain}%')).count()
            sources[domain] = count
        
        return jsonify({
            'total_articles': total_articles,
            'posted_articles': posted_articles,
            'pending_articles': pending_articles,
            'today_posts': today_posts,
            'recent_articles': recent_count,
            'avg_summary_time': round(avg_summary_time, 2),
            'avg_hashtags_time': round(avg_hashtags_time, 2),
            'sources': sources
        })
        
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/analytics')
def api_analytics():
    """API endpoint для получения данных для графиков"""
    try:
        # Статистика по дням
        days = 7
        result = []
        for i in range(days):
            day = datetime.utcnow().date() - timedelta(days=i)
            day_start = datetime.combine(day, datetime.min.time())
            day_end = datetime.combine(day, datetime.max.time())
            
            posts_count = PostingLog.query.filter(
                PostingLog.posted_at >= day_start,
                PostingLog.posted_at <= day_end,
                PostingLog.status == 'success'
            ).count()
            
            articles_count = NewsArticle.query.filter(
                NewsArticle.created_at >= day_start,
                NewsArticle.created_at <= day_end
            ).count()
            
            result.append({
                'date': day.strftime('%Y-%m-%d'),
                'posts': posts_count,
                'articles': articles_count
            })
        
        return jsonify({
            'daily_stats': result
        })
        
    except Exception as e:
        logger.error(f"Error getting analytics: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/logs')
def logs():
    log_path = os.path.join('logs', 'app.log')
    logs = []
    if os.path.exists(log_path):
        with open(log_path, encoding='utf-8') as f:
            for line in f.readlines()[-500:]:
                # Пропускаем сообщения от Flask _internal
                if 'in _internal:' in line:
                    continue
                explanation = ''
                if '429' in line and 'openrouter' in line.lower():
                    explanation = 'Ошибка 429: превышен лимит запросов к OpenRouter API. Подождите или смените ключ.'
                elif 'telegram' in line.lower() and 'error' in line.lower():
                    explanation = 'Ошибка Telegram: проверьте токен, права доступа или ID канала.'
                elif 'error' in line.lower() or 'exception' in line.lower():
                    explanation = 'Ошибка Python: проверьте стек вызова ниже.'
                logs.append({'raw': line, 'explanation': explanation})
    else:
        logs = [{'raw': 'Лог-файл не найден.', 'explanation': ''}]
    return render_template('logs.html', logs=logs)

@app.route('/analytics')
def analytics():
    """Страница с аналитикой"""
    # Получаем общую статистику
    total_articles = NewsArticle.query.count()
    posted_articles = NewsArticle.query.filter_by(is_posted=True).count()
    
    # Статистика по источникам
    sources = {}
    for domain in ['smartlab.news', 'rbc.ru', 'vedomosti.ru']:
        count = NewsArticle.query.filter(NewsArticle.url.like(f'%{domain}%')).count()
        sources[domain] = count
    
    # Статистика по времени генерации
    avg_summary_time = db.session.query(db.func.avg(AnalyticsData.summary_generation_time)).scalar() or 0
    avg_hashtags_time = db.session.query(db.func.avg(AnalyticsData.hashtags_generation_time)).scalar() or 0
    
    # Статистика по дням
    days = 7
    daily_stats = []
    for i in range(days):
        day = datetime.utcnow().date() - timedelta(days=i)
        day_start = datetime.combine(day, datetime.min.time())
        day_end = datetime.combine(day, datetime.max.time())
        
        posts_count = PostingLog.query.filter(
            PostingLog.posted_at >= day_start,
            PostingLog.posted_at <= day_end,
            PostingLog.status == 'success'
        ).count()
        
        articles_count = NewsArticle.query.filter(
            NewsArticle.created_at >= day_start,
            NewsArticle.created_at <= day_end
        ).count()
        
        daily_stats.append({
            'date': day.strftime('%d.%m'),
            'posts': posts_count,
            'articles': articles_count
        })
    
    # Переворачиваем список, чтобы даты шли в хронологическом порядке
    daily_stats.reverse()
    
    return render_template('analytics.html',
                          total_articles=total_articles,
                          posted_articles=posted_articles,
                          sources=sources,
                          avg_summary_time=round(avg_summary_time, 2),
                          avg_hashtags_time=round(avg_hashtags_time, 2),
                          daily_stats=json.dumps(daily_stats))

# Initialize scheduler on startup - using newer Flask pattern
def initialize_scheduler():
    """Initialize the news scheduler"""
    try:
        settings = BotSettings.get_current()
        if settings.posting_enabled:
            news_scheduler.start()
    except Exception as e:
        logger.error(f"Error initializing scheduler: {e}")

# Call initialization when the module is imported
with app.app_context():
    initialize_scheduler()
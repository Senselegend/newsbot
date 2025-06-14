# Last modified: 2024-03-26
def clean_summary(summary):
    """
    Очищает и форматирует сгенерированное резюме
    """
    import re
    import logging
    from fix_political_references import fix_political_references
    from validate_summary import validate_summary_quality
    
    logger = logging.getLogger(__name__)
    
    if summary is None or not summary:
        return ""
        
    # Удаляем лишние префиксы
    prefixes_to_remove = [
        'вот краткая сводка:', 'сводка новости:', 'краткое содержание:',
        'резюме:', 'основные моменты:', 'итак,', 'в итоге,', 'вот резюме:'
    ]
    summary_lower = summary.lower()
    for prefix in prefixes_to_remove:
        if summary_lower.startswith(prefix):
            summary = summary[len(prefix):].strip()
            break
    
    # Исправляем некорректные упоминания о Трампе и других политиках
    # и форматируем текст
    summary = fix_political_references(summary)
    
    # Форматируем цитаты
    # Ищем паттерны типа "Имя Фамилия сказал: "цитата"" и заменяем на "ИМЯ ФАМИЛИЯ: цитата"
    quote_patterns = [
        (r'([А-Я][а-я]+\s+[А-Я][а-я]+)\s+(?:сказал|заявил|отметил|подчеркнул|сообщил)(?:а|и|о)?[,:]?\s*[«""]([^«""]+)[»""]', r'\1: \2'),
        (r'([А-Я][а-я]+)\s+(?:сказал|заявил|отметил|подчеркнул|сообщил)(?:а|и|о)?[,:]?\s*[«""]([^«""]+)[»""]', r'\1: \2'),
    ]
    
    for pattern, replacement in quote_patterns:
        summary = re.sub(pattern, replacement, summary)
    
    # Выделяем процентные изменения жирным шрифтом
    summary = re.sub(r'(\+\d+(?:\.\d+)?%|\-\d+(?:\.\d+)?%)', r'**\1**', summary)
    
    # Проверяем качество резюме после всех изменений
    if not validate_summary_quality(summary):
        logger.warning(f"Резюме не соответствует требуемому формату: {summary[:50]}...")
        return ""
        
    return summary
def validate_summary_quality(summary):
    """
    Проверяет качество резюме
    """
    import re
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Проверка на минимальную длину
    if len(summary) < 30:
        logger.warning("Резюме слишком короткое")
        return False
        
    # Проверка на наличие незавершенных предложений
    if summary.endswith(('...', '…')) or summary.endswith((',', ':', ';', '-')):
        logger.warning("Резюме обрывается на середине")
        return False
        
    # Проверка на наличие маркеров незавершенности
    incomplete_markers = ['продолжение следует', 'читайте далее', 'подробнее']
    if any(marker in summary.lower() for marker in incomplete_markers):
        logger.warning("Резюме содержит маркеры незавершенности")
        return False
        
    # Проверка на наличие вопросов в конце (часто признак незавершенности)
    if summary.rstrip().endswith('?'):
        logger.warning("Резюме заканчивается вопросом")
        return False
        
    # Проверка на наличие эмодзи в начале
    emoji_pattern = re.compile(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]')
    first_line = summary.split('\n')[0] if '\n' in summary else summary
    first_chars = first_line[:10]
    if not emoji_pattern.search(first_chars):
        logger.warning("Нет эмодзи в начале сообщения")
        return False
        
    # Проверка на наличие хештегов в первой строке
    if not re.search(r'#\w+', first_line):
        logger.warning("Нет хештегов в первой строке")
        return False
        
    # Проверка на слишком много разрывов строк (разрешаем до 15)
    newline_count = summary.count('\n')
    if newline_count > 15:
        logger.warning(f"Слишком много разрывов строк: {newline_count}")
        return False
        
    # Проверка на слишком длинные абзацы (более 200 символов без разрыва строки)
    paragraphs = summary.split('\n\n')
    for paragraph in paragraphs:
        if len(paragraph.strip()) > 200:
            logger.warning("Обнаружен слишком длинный абзац")
            return False
        
    return True
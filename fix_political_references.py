# Last modified: 2024-03-26
def fix_political_references(text):
    """
    Исправляет некорректные упоминания политиков и форматирует текст
    """
    import re
    
    # Исправляем упоминания о Трампе
    trump_patterns = [
        (r'бывш(ий|его|ему) президент(а|у|ом)? США Дональд(а|у|ом)? Трамп(а|у|ом)?', 'президент США Дональд Трамп'),
        (r'экс-президент(а|у|ом)? США Дональд(а|у|ом)? Трамп(а|у|ом)?', 'президент США Дональд Трамп'),
        (r'Дональд Трамп, бывший президент США', 'Дональд Трамп, президент США'),
        (r'45(-й)? президент США', 'президент США'),
        (r'ТРАМП,', 'ТРАМП:'),  # Формат цитирования
    ]
    
    for pattern, replacement in trump_patterns:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    
    # Исправляем форматирование текста
    
    # Удаляем лишние пробелы перед знаками препинания
    text = re.sub(r'\s+([.,;:!?])', r'\1', text)
    
    # Удаляем множественные пробелы
    text = re.sub(r'\s{2,}', ' ', text)
    
    # Удаляем множественные переносы строк (оставляем максимум один)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Удаляем разделительную линию в конце, если она есть
    text = re.sub(r'\n+_{5,}$', '', text)
    
    # Проверяем и форматируем первую строку (эмодзи и хештеги)
    lines = text.split('\n')
    first_line = lines[0]
    
    # Проверяем наличие эмодзи в начале
    emoji_pattern = re.compile(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]')
    emojis = emoji_pattern.findall(first_line[:10])
    
    # Проверяем наличие хештегов
    hashtags = re.findall(r'#\w+', first_line)
    
    # Если нет эмодзи или хештегов, добавляем стандартные
    if not emojis or not hashtags:
        # Определяем тему новости
        lower_text = text.lower()
        
        # Выбираем подходящие эмодзи
        if any(word in lower_text for word in ['россия', 'рф', 'рубль']):
            emoji = '🇷🇺'
        elif any(word in lower_text for word in ['сша', 'америк', 'доллар']):
            emoji = '🇺🇸'
        elif any(word in lower_text for word in ['китай', 'юань']):
            emoji = '🇨🇳'
        elif any(word in lower_text for word in ['нефть', 'газ', 'энергетик']):
            emoji = '🛢'
        elif any(word in lower_text for word in ['финанс', 'банк', 'акци']):
            emoji = '💰'
        else:
            emoji = '📊'
            
        # Выбираем подходящие хештеги
        if not hashtags:
            if any(word in lower_text for word in ['россия', 'рф']):
                hashtags = ['#россия']
            elif any(word in lower_text for word in ['сша', 'америк']):
                hashtags = ['#сша']
            else:
                hashtags = ['#новости']
                
            if any(word in lower_text for word in ['нефть', 'газ']):
                hashtags.append('#нефть')
            elif any(word in lower_text for word in ['акци', 'облигац']):
                hashtags.append('#рынки')
                
        # Формируем новую первую строку
        new_first_line = emoji + ' ' + ' '.join(hashtags)
        
        # Удаляем эмодзи и хештеги из оригинальной первой строки
        clean_first_line = re.sub(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]', '', first_line)
        clean_first_line = re.sub(r'#\w+', '', clean_first_line).strip()
        
        # Объединяем новую первую строку с очищенным текстом
        if clean_first_line:
            lines[0] = new_first_line + ' ' + clean_first_line
        else:
            lines[0] = new_first_line
            
        text = '\n'.join(lines)
    
    return text
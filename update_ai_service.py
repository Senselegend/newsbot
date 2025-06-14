#!/usr/bin/env python3
# Last modified: 2024-03-26
"""
Скрипт для обновления файла ai_service.py
"""
import os
import shutil

# Путь к файлам
base_dir = '/Users/s.karagezyan/Downloads/NewsBot'
ai_service_path = os.path.join(base_dir, 'ai_service.py')
ai_service_fixed_path = os.path.join(base_dir, 'ai_service_fixed.py')
backup_path = os.path.join(base_dir, 'ai_service.py.bak')

# Создаем резервную копию
shutil.copy2(ai_service_path, backup_path)
print(f"Создана резервная копия: {backup_path}")

# Заменяем файл
shutil.copy2(ai_service_fixed_path, ai_service_path)
print(f"Файл ai_service.py обновлен")

print("Обновление завершено успешно!")
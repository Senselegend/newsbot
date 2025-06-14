#!/usr/bin/env python3
# Last modified: 2024-03-26
"""
Скрипт для обновления файла ai_service.py
"""
import os
import shutil
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def update_ai_service():
    try:
        # Создаем резервную копию
        backup_dir = "old"
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(backup_dir, f"ai_service.py.bak_{timestamp}")
        shutil.copy2("ai_service.py", backup_path)
        logger.info(f"Создана резервная копия: {backup_path}")
        
        # Обновляем файл
        with open("ai_service.py", "w") as f:
            f.write("# Updated AI service code\n")
        logger.info("Файл ai_service.py обновлен")
        
        logger.info("Обновление завершено успешно!")
    except Exception as e:
        logger.error(f"Ошибка при обновлении: {e}")
        raise

if __name__ == "__main__":
    update_ai_service()
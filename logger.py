# logger_class.py
import logging
from logging.handlers import RotatingFileHandler
import os
from datetime import datetime


class DataCollectorLogger:

    def __init__(self, log_folder='data_collection', log_filename='process_run.log'):
        """Инициализация логгера"""
        self.log_folder = log_folder
        self.log_filename = log_filename
        self.log_path = os.path.join(os.getcwd(), log_folder, log_filename)

        os.makedirs(log_folder, exist_ok=True)

        # Создаем папку если не существует
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)

        # Создаем логгер
        self.logger = logging.getLogger('DataCollector')
        self.logger.setLevel(logging.DEBUG)

        # Убираем все существующие handlers
        self.logger.handlers.clear()

        # Настройка формата для русского языка
        self._setup_handlers()

        self.log_info("Инициализация логгера завершена")

    def _setup_handlers(self):
        """Настройка обработчиков логов"""
        # Формат с поддержкой UTF-8
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # File handler с ротацией
        file_handler = RotatingFileHandler(
            self.log_path,
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=3,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)

        # Добавляем handlers
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def log_debug(self, message):
        """Логирование отладки"""
        self.logger.debug(message)

    def log_info(self, message):
        """Логирование информации"""
        self.logger.info(message)

    def log_warning(self, message):
        """Логирование предупреждения"""
        self.logger.warning(message)

    def log_error(self, message):
        """Логирование ошибки"""
        self.logger.error(message)

    def log_critical(self, message):
        """Логирование критической ошибки"""
        self.logger.critical(message)

    def log_function_call(self, func_name, status, message=""):
        """Логирование вызова функции"""
        log_message = f"Функция: {func_name} - Статус: {status}"
        if message:
            log_message += f" - {message}"
        self.log_debug(log_message)

    def get_log_path(self):
        """Получить путь к файлу логов"""
        return self.log_path

    def close(self):
        """Закрытие логгера"""
        for handler in self.logger.handlers:
            handler.close()
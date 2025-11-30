#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
G2A Market GUI Application
Модернизированное GUI-приложение для автоматизации работы с G2A маркетплейсом
"""

import sys
import asyncio
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from gui.main_window import MainWindow
import qasync


def setup_directories():
    """Создание необходимых директорий"""
    directories = ['keys', 'result', 'logs', 'temp_parsing']
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)


def main():
    """Главная функция запуска приложения"""
    # В PyQt6 High DPI scaling включен по умолчанию
    # Устанавливаем только политику округления
    try:
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
    except AttributeError:
        # Если этот метод тоже не существует, продолжаем
        pass
    
    # Создаем приложение
    app = QApplication(sys.argv)
    app.setApplicationName("G2A Market GUI")
    app.setOrganizationName("G2A Tools")
    
    # Создаем event loop для async операций
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    
    # Настройка директорий
    setup_directories()
    
    # Создаем и показываем главное окно
    window = MainWindow()
    window.show()
    
    # Запуск приложения
    with loop:
        loop.run_forever()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Приложение закрыто пользователем")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Главное окно приложения
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QTabWidget,
    QStatusBar, QMenuBar, QMenu
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction, QIcon

from gui.tabs.dashboard_tab import DashboardTab
from gui.tabs.keys_tab import KeysTab
from gui.tabs.parsing_tab import ParsingTab
from gui.tabs.offers_tab import OffersTab
from gui.tabs.settings_tab import SettingsTab
from gui.styles import MAIN_STYLE


class MainWindow(QMainWindow):
    """Главное окно приложения"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        """Инициализация интерфейса"""
        self.setWindowTitle("G2A Market Automation Tool")
        self.setGeometry(100, 100, 1400, 900)
        
        # Применяем стили
        self.setStyleSheet(MAIN_STYLE)
        
        # Создаем центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Основной layout
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Создаем вкладки
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.TabPosition.North)
        self.tabs.setMovable(False)
        
        # Добавляем вкладки
        self.dashboard_tab = DashboardTab()
        self.keys_tab = KeysTab()
        self.parsing_tab = ParsingTab()
        self.offers_tab = OffersTab()
        self.settings_tab = SettingsTab()
        
        self.tabs.addTab(self.dashboard_tab, "📊 Dashboard")
        self.tabs.addTab(self.keys_tab, "🔑 Keys Management")
        self.tabs.addTab(self.parsing_tab, "💰 Price Parsing")
        self.tabs.addTab(self.offers_tab, "📦 Offers")
        self.tabs.addTab(self.settings_tab, "⚙️ Settings")
        
        layout.addWidget(self.tabs)
        
        # Создаем меню
        self.create_menu()
        
        # Создаем статус бар
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Готово к работе")
        
        # Таймер для обновления статистики
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_stats)
        self.update_timer.start(5000)  # Обновление каждые 5 секунд
        
    def create_menu(self):
        """Создание меню"""
        menubar = self.menuBar()
        
        # Меню File
        file_menu = menubar.addMenu("&File")
        
        refresh_action = QAction("Refresh All", self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self.refresh_all)
        file_menu.addAction(refresh_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Меню Tools
        tools_menu = menubar.addMenu("&Tools")
        
        clear_logs_action = QAction("Clear All Logs", self)
        clear_logs_action.triggered.connect(self.clear_all_logs)
        tools_menu.addAction(clear_logs_action)
        
        # Меню Help
        help_menu = menubar.addMenu("&Help")
        
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
    def refresh_all(self):
        """Обновление всех данных"""
        self.statusBar.showMessage("Обновление данных...")
        self.dashboard_tab.refresh()
        self.keys_tab.refresh()
        self.offers_tab.refresh()
        self.statusBar.showMessage("Данные обновлены", 3000)
        
    def clear_all_logs(self):
        """Очистка всех логов"""
        self.parsing_tab.clear_log()
        self.offers_tab.clear_log()
        self.statusBar.showMessage("Логи очищены", 3000)
        
    def update_stats(self):
        """Обновление статистики в фоне"""
        # Обновляем дашборд
        self.dashboard_tab.update_stats()
        
    def show_about(self):
        """Показать информацию о программе"""
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.about(
            self,
            "О программе",
            "<h3>G2A Market Automation Tool</h3>"
            "<p>Версия: 2.0.0</p>"
            "<p>Современное GUI-приложение для автоматизации работы с G2A маркетплейсом</p>"
            "<p><b>Функции:</b></p>"
            "<ul>"
            "<li>Управление ключами</li>"
            "<li>Парсинг цен конкурентов</li>"
            "<li>Автоматическое создание офферов</li>"
            "<li>Мониторинг продаж</li>"
            "</ul>"
        )
    
    def closeEvent(self, event):
        """Обработка закрытия окна"""
        from PyQt6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self,
            'Выход',
            'Вы действительно хотите выйти?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Останавливаем таймеры
            self.update_timer.stop()
            event.accept()
        else:
            event.ignore()

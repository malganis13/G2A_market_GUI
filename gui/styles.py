#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Стили для GUI приложения
"""

MAIN_STYLE = """
    /* Общие стили */
    QMainWindow, QWidget {
        background-color: #1e1e1e;
        color: #e0e0e0;
        font-family: 'Segoe UI', Arial, sans-serif;
        font-size: 10pt;
    }
    
    /* Вкладки */
    QTabWidget::pane {
        border: 1px solid #3a3a3a;
        background-color: #252525;
        border-radius: 4px;
    }
    
    QTabBar::tab {
        background-color: #2d2d2d;
        color: #a0a0a0;
        padding: 10px 20px;
        margin-right: 2px;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
        min-width: 120px;
    }
    
    QTabBar::tab:selected {
        background-color: #0d7377;
        color: #ffffff;
        font-weight: bold;
    }
    
    QTabBar::tab:hover:!selected {
        background-color: #3a3a3a;
    }
    
    /* Кнопки */
    QPushButton {
        background-color: #0d7377;
        color: white;
        border: none;
        padding: 8px 16px;
        border-radius: 4px;
        font-weight: bold;
        min-height: 30px;
    }
    
    QPushButton:hover {
        background-color: #14a085;
    }
    
    QPushButton:pressed {
        background-color: #0a5d5f;
    }
    
    QPushButton:disabled {
        background-color: #3a3a3a;
        color: #666666;
    }
    
    /* Кнопки удаления */
    QPushButton[class="danger"] {
        background-color: #d32f2f;
    }
    
    QPushButton[class="danger"]:hover {
        background-color: #f44336;
    }
    
    /* Таблицы */
    QTableWidget {
        background-color: #2d2d2d;
        alternate-background-color: #323232;
        gridline-color: #3a3a3a;
        border: 1px solid #3a3a3a;
        border-radius: 4px;
    }
    
    QTableWidget::item {
        padding: 5px;
        border: none;
    }
    
    QTableWidget::item:selected {
        background-color: #0d7377;
        color: white;
    }
    
    QHeaderView::section {
        background-color: #1e1e1e;
        color: #e0e0e0;
        padding: 8px;
        border: none;
        border-bottom: 2px solid #0d7377;
        font-weight: bold;
    }
    
    /* Текстовые поля */
    QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox {
        background-color: #2d2d2d;
        border: 1px solid #3a3a3a;
        border-radius: 4px;
        padding: 6px;
        color: #e0e0e0;
    }
    
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, 
    QSpinBox:focus, QDoubleSpinBox:focus {
        border: 1px solid #0d7377;
    }
    
    /* Combobox */
    QComboBox {
        background-color: #2d2d2d;
        border: 1px solid #3a3a3a;
        border-radius: 4px;
        padding: 6px;
        color: #e0e0e0;
        min-height: 25px;
    }
    
    QComboBox:hover {
        border: 1px solid #0d7377;
    }
    
    QComboBox::drop-down {
        border: none;
        width: 20px;
    }
    
    QComboBox QAbstractItemView {
        background-color: #2d2d2d;
        border: 1px solid #3a3a3a;
        selection-background-color: #0d7377;
    }
    
    /* Checkbox */
    QCheckBox {
        spacing: 8px;
    }
    
    QCheckBox::indicator {
        width: 18px;
        height: 18px;
        border: 2px solid #3a3a3a;
        border-radius: 3px;
        background-color: #2d2d2d;
    }
    
    QCheckBox::indicator:checked {
        background-color: #0d7377;
        border-color: #0d7377;
    }
    
    /* Progress Bar */
    QProgressBar {
        border: 1px solid #3a3a3a;
        border-radius: 4px;
        text-align: center;
        background-color: #2d2d2d;
        color: white;
        height: 25px;
    }
    
    QProgressBar::chunk {
        background-color: #0d7377;
        border-radius: 3px;
    }
    
    /* GroupBox */
    QGroupBox {
        border: 2px solid #3a3a3a;
        border-radius: 6px;
        margin-top: 12px;
        padding-top: 18px;
        font-weight: bold;
    }
    
    QGroupBox::title {
        subcontrol-origin: margin;
        left: 15px;
        padding: 0 5px;
        color: #0d7377;
    }
    
    /* ScrollBar */
    QScrollBar:vertical {
        background-color: #2d2d2d;
        width: 12px;
        border: none;
    }
    
    QScrollBar::handle:vertical {
        background-color: #3a3a3a;
        min-height: 20px;
        border-radius: 6px;
    }
    
    QScrollBar::handle:vertical:hover {
        background-color: #0d7377;
    }
    
    QScrollBar:horizontal {
        background-color: #2d2d2d;
        height: 12px;
        border: none;
    }
    
    QScrollBar::handle:horizontal {
        background-color: #3a3a3a;
        min-width: 20px;
        border-radius: 6px;
    }
    
    QScrollBar::handle:horizontal:hover {
        background-color: #0d7377;
    }
    
    /* Label */
    QLabel {
        color: #e0e0e0;
    }
    
    QLabel[class="header"] {
        font-size: 14pt;
        font-weight: bold;
        color: #0d7377;
        padding: 10px 0;
    }
    
    QLabel[class="subheader"] {
        font-size: 11pt;
        font-weight: bold;
        color: #14a085;
        padding: 5px 0;
    }
    
    /* Status Bar */
    QStatusBar {
        background-color: #1e1e1e;
        color: #a0a0a0;
        border-top: 1px solid #3a3a3a;
    }
    
    /* Menu */
    QMenuBar {
        background-color: #1e1e1e;
        color: #e0e0e0;
        border-bottom: 1px solid #3a3a3a;
    }
    
    QMenuBar::item:selected {
        background-color: #0d7377;
    }
    
    QMenu {
        background-color: #2d2d2d;
        border: 1px solid #3a3a3a;
    }
    
    QMenu::item:selected {
        background-color: #0d7377;
    }
    
    /* Tooltip */
    QToolTip {
        background-color: #2d2d2d;
        color: #e0e0e0;
        border: 1px solid #0d7377;
        padding: 5px;
        border-radius: 3px;
    }
"""

# Цвета для логов
LOG_COLORS = {
    'success': '#4caf50',
    'error': '#f44336',
    'warning': '#ff9800',
    'info': '#2196f3',
    'debug': '#9e9e9e'
}

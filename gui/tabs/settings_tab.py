#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Вкладка настроек
"""

import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QGroupBox, QTextEdit, QCheckBox, QFileDialog,
    QMessageBox, QSpinBox
)
from PyQt6.QtCore import Qt, pyqtSignal


class SettingsTab(QWidget):
    """Вкладка настроек"""
    
    settings_changed = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.load_settings()
        
    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Заголовок
        header = QLabel("⚙️ Settings")
        header.setProperty("class", "header")
        layout.addWidget(header)
        
        # G2A API настройки
        g2a_group = QGroupBox("🔑 G2A API Configuration")
        g2a_layout = QVBoxLayout()
        
        # Client ID
        client_id_layout = QHBoxLayout()
        client_id_layout.addWidget(QLabel("Client ID:"))
        self.client_id_input = QLineEdit()
        self.client_id_input.setPlaceholderText("Enter your G2A Client ID")
        client_id_layout.addWidget(self.client_id_input)
        g2a_layout.addLayout(client_id_layout)
        
        # Client Secret
        client_secret_layout = QHBoxLayout()
        client_secret_layout.addWidget(QLabel("Client Secret:"))
        self.client_secret_input = QLineEdit()
        self.client_secret_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.client_secret_input.setPlaceholderText("Enter your G2A Client Secret")
        client_secret_layout.addWidget(self.client_secret_input)
        
        show_secret_btn = QPushButton("👁️ Show")
        show_secret_btn.setCheckable(True)
        show_secret_btn.clicked.connect(self.toggle_secret_visibility)
        client_secret_layout.addWidget(show_secret_btn)
        g2a_layout.addLayout(client_secret_layout)
        
        # ⭐ Client Email (НОВОЕ ПОЛЕ!)
        client_email_layout = QHBoxLayout()
        client_email_layout.addWidget(QLabel("Client Email:"))
        self.client_email_input = QLineEdit()
        self.client_email_input.setPlaceholderText("your_email@gmail.com (required for auth!)")
        client_email_layout.addWidget(self.client_email_input)
        g2a_layout.addLayout(client_email_layout)
        
        # Важное предупреждение
        email_warning = QLabel(
            "<b style='color: #ff9800;'>⚠️ IMPORTANT:</b> Email is required for API authentication! "
            "Use the same email as your G2A account."
        )
        email_warning.setWordWrap(True)
        email_warning.setStyleSheet("padding: 5px; background-color: #3a3a3a; border-radius: 3px;")
        g2a_layout.addWidget(email_warning)
        
        # API Base URL
        api_url_layout = QHBoxLayout()
        api_url_layout.addWidget(QLabel("API Base URL:"))
        self.api_url_input = QLineEdit()
        self.api_url_input.setText("https://api.g2a.com")
        api_url_layout.addWidget(self.api_url_input)
        g2a_layout.addLayout(api_url_layout)
        
        # Кнопка сохранения
        save_g2a_btn = QPushButton("💾 Save G2A Settings")
        save_g2a_btn.clicked.connect(self.save_g2a_settings)
        g2a_layout.addWidget(save_g2a_btn)
        
        # Информация
        info_label = QLabel(
            "<small><i>Get your API credentials from G2A Developer Dashboard:<br>"
            "<a href='https://www.g2a.com/developer'>https://www.g2a.com/developer</a></i></small>"
        )
        info_label.setOpenExternalLinks(True)
        info_label.setStyleSheet("color: #888; padding: 5px;")
        g2a_layout.addWidget(info_label)
        
        g2a_group.setLayout(g2a_layout)
        layout.addWidget(g2a_group)
        
        # Proxy настройки
        proxy_group = QGroupBox("🌐 Proxy Configuration")
        proxy_layout = QVBoxLayout()
        
        self.use_proxy_check = QCheckBox("Enable Proxy")
        proxy_layout.addWidget(self.use_proxy_check)
        
        # Proxy список
        proxy_layout.addWidget(QLabel("Proxy List (one per line, format: host:port:user:pass):"))
        self.proxy_text = QTextEdit()
        self.proxy_text.setMaximumHeight(100)
        self.proxy_text.setPlaceholderText("proxy1.example.com:8080:username:password\nproxy2.example.com:8080")
        proxy_layout.addWidget(self.proxy_text)
        
        # Кнопки
        proxy_buttons_layout = QHBoxLayout()
        
        load_proxy_btn = QPushButton("📁 Load from File")
        load_proxy_btn.clicked.connect(self.load_proxy_from_file)
        proxy_buttons_layout.addWidget(load_proxy_btn)
        
        save_proxy_btn = QPushButton("💾 Save Proxy Settings")
        save_proxy_btn.clicked.connect(self.save_proxy_settings)
        proxy_buttons_layout.addWidget(save_proxy_btn)
        
        proxy_buttons_layout.addStretch()
        proxy_layout.addLayout(proxy_buttons_layout)
        
        proxy_group.setLayout(proxy_layout)
        layout.addWidget(proxy_group)
        
        # Telegram настройки
        telegram_group = QGroupBox("📨 Telegram Notifications")
        telegram_layout = QVBoxLayout()
        
        self.telegram_enabled_check = QCheckBox("Enable Telegram Notifications")
        telegram_layout.addWidget(self.telegram_enabled_check)
        
        # Bot Token
        token_layout = QHBoxLayout()
        token_layout.addWidget(QLabel("Bot Token:"))
        self.telegram_token_input = QLineEdit()
        self.telegram_token_input.setPlaceholderText("123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")
        token_layout.addWidget(self.telegram_token_input)
        telegram_layout.addLayout(token_layout)
        
        # Chat ID
        chat_layout = QHBoxLayout()
        chat_layout.addWidget(QLabel("Chat ID:"))
        self.telegram_chat_input = QLineEdit()
        self.telegram_chat_input.setPlaceholderText("Your Telegram Chat ID")
        chat_layout.addWidget(self.telegram_chat_input)
        telegram_layout.addLayout(chat_layout)
        
        save_telegram_btn = QPushButton("💾 Save Telegram Settings")
        save_telegram_btn.clicked.connect(self.save_telegram_settings)
        telegram_layout.addWidget(save_telegram_btn)
        
        telegram_group.setLayout(telegram_layout)
        layout.addWidget(telegram_group)
        
        # Настройки парсинга
        parsing_group = QGroupBox("🔍 Parsing Settings")
        parsing_layout = QVBoxLayout()
        
        # Задержка
        delay_layout = QHBoxLayout()
        delay_layout.addWidget(QLabel("Default delay between requests (seconds):"))
        self.parsing_delay_spin = QSpinBox()
        self.parsing_delay_spin.setRange(1, 30)
        self.parsing_delay_spin.setValue(2)
        delay_layout.addWidget(self.parsing_delay_spin)
        delay_layout.addStretch()
        parsing_layout.addLayout(delay_layout)
        
        # Таймаут
        timeout_layout = QHBoxLayout()
        timeout_layout.addWidget(QLabel("Request timeout (seconds):"))
        self.parsing_timeout_spin = QSpinBox()
        self.parsing_timeout_spin.setRange(5, 120)
        self.parsing_timeout_spin.setValue(30)
        timeout_layout.addWidget(self.parsing_timeout_spin)
        timeout_layout.addStretch()
        parsing_layout.addLayout(timeout_layout)
        
        save_parsing_btn = QPushButton("💾 Save Parsing Settings")
        save_parsing_btn.clicked.connect(self.save_parsing_settings)
        parsing_layout.addWidget(save_parsing_btn)
        
        parsing_group.setLayout(parsing_layout)
        layout.addWidget(parsing_group)
        
        layout.addStretch()
    
    def toggle_secret_visibility(self):
        """Переключение видимости secret"""
        if self.client_secret_input.echoMode() == QLineEdit.EchoMode.Password:
            self.client_secret_input.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self.client_secret_input.setEchoMode(QLineEdit.EchoMode.Password)
    
    def load_settings(self):
        """Загрузка настроек"""
        try:
            # Загружаем G2A настройки
            try:
                from g2a_config import G2A_CLIENT_ID, G2A_CLIENT_SECRET, G2A_API_BASE, G2A_CLIENT_EMAIL
                self.client_id_input.setText(G2A_CLIENT_ID)
                self.client_secret_input.setText(G2A_CLIENT_SECRET)
                self.client_email_input.setText(G2A_CLIENT_EMAIL)
                self.api_url_input.setText(G2A_API_BASE)
            except ImportError:
                pass
            
            # Загружаем proxy
            proxy_file = "proxy.txt"
            if os.path.exists(proxy_file):
                with open(proxy_file, 'r', encoding='utf-8') as f:
                    self.proxy_text.setPlainText(f.read())
                    
        except Exception as e:
            print(f"Error loading settings: {e}")
    
    def save_g2a_settings(self):
        """Сохранение G2A настроек с ПОЛНЫМ конфигом"""
        client_id = self.client_id_input.text().strip()
        client_secret = self.client_secret_input.text().strip()
        client_email = self.client_email_input.text().strip()
        api_url = self.api_url_input.text().strip()
        
        if not client_id or not client_secret or not client_email:
            QMessageBox.warning(
                self, 
                "Warning", 
                "Please fill in all required fields!\n\nClient ID, Client Secret and Email are required for API authentication."
            )
            return
        
        # Проверка формата email
        if "@" not in client_email or "." not in client_email:
            QMessageBox.warning(self, "Warning", "Please enter a valid email address!")
            return
        
        try:
            # Создаем ПОЛНЫЙ конфиг со всеми переменными!
            config_content = f'''# G2A API Configuration
# Generated by GUI Settings

SANDBOX_MODE = False  # True = тесты, False = продакшн

MIN_PRICE_TO_SELL = 0.3 # Минимальная цена в EUR для выставления на продажу

# Папки
KEYS_FOLDER = "keys"
RESULT_FOLDER = "result"
PROXY_FILE = "proxy.txt"

# Парсинг
PRICE_EXPIRY_DAYS = 3
DELAY_BETWEEN_REQUESTS = 1
REQUEST_TIMEOUT = 20

TELEGRAM_BOT_TOKEN = "bot_token"
TELEGRAM_CHAT_ID = "id"
DEFAULT_PREFIX = "pref"

ADMIN_API_KEY = "akblfkykc635671"
G2A_BASE_URL = "https://www.g2a.com/category/gaming-c1"
G2A_BASE_PARAMS = "f%5Bplatform%5D%5B0%5D=1&f%5Btype%5D%5B0%5D=10"

AUTO_PRICE_CHANGE_ENABLED = True
AUTO_PRICE_CHECK_INTERVAL = 1800
AUTO_PRICE_MIN_OFFER_PRICE = 0.5
AUTO_PRICE_UNDERCUT_AMOUNT = 0.01
AUTO_PRICE_INCREASE_THRESHOLD = 0.1
AUTO_PRICE_DAILY_LIMIT = 30
AUTO_PRICE_MIN_PRICE = 0.1
AUTO_PRICE_MAX_PRICE = 100.0

# G2A API CREDENTIALS (ЗАПОЛНЯЕТСЯ ИЗ GUI)
G2A_CLIENT_ID = "{client_id}"
G2A_CLIENT_SECRET = "{client_secret}"
G2A_CLIENT_EMAIL = "{client_email}"  # ОБЯЗАТЕЛЬНО для API ключа!
G2A_API_BASE = "{api_url}"
DATABASE_FILE = "g2a_data.db"

SERVER_CLIENT_ID = "L5AvJbpDDvupje8vTyPh"
SERVER_CLIENT_SECRET = "rWiZlvPUPMIERui17UaaOohWhRjEslRq"
API_BASE_URL = "https://domen.ngrok.app"

# Регионы
REGION_CODES = {{
    "GLOBAL": 8355,
    "EUROPE": 878,
    "NORTH_AMERICA": 879,
    "ASIA": 883,
    "LATAM": 8794
}}

COUNTRY_TO_REGION = {{
    "AD": "EUROPE", "AL": "EUROPE", "AT": "EUROPE", "AX": "EUROPE", "BA": "EUROPE",
    "BE": "EUROPE", "BG": "EUROPE", "CH": "EUROPE", "CY": "EUROPE", "CZ": "EUROPE",
    "DE": "EUROPE", "DK": "EUROPE", "EE": "EUROPE", "ES": "EUROPE", "FI": "EUROPE",
    "FO": "EUROPE", "FR": "EUROPE", "GB": "EUROPE", "GG": "EUROPE", "GI": "EUROPE",
    "GL": "EUROPE", "GR": "EUROPE", "HR": "EUROPE", "HU": "EUROPE", "IE": "EUROPE",
    "IM": "EUROPE", "IS": "EUROPE", "IT": "EUROPE", "JE": "EUROPE", "LI": "EUROPE",
    "LT": "EUROPE", "LU": "EUROPE", "LV": "EUROPE", "MC": "EUROPE", "ME": "EUROPE",
    "MK": "EUROPE", "MT": "EUROPE", "NL": "EUROPE", "NO": "EUROPE", "PL": "EUROPE",
    "PT": "EUROPE", "RO": "EUROPE", "RS": "EUROPE", "SE": "EUROPE", "SI": "EUROPE",
    "SJ": "EUROPE", "SK": "EUROPE", "SM": "EUROPE", "VA": "EUROPE",
    "BY": "EUROPE", "MD": "EUROPE", "TR": "EUROPE", "UA": "EUROPE",
    "US": "NORTH_AMERICA", "CA": "NORTH_AMERICA", "MX": "NORTH_AMERICA",
    "AR": "LATAM", "BO": "LATAM", "BR": "LATAM", "BS": "LATAM", "BZ": "LATAM",
    "CL": "LATAM", "CO": "LATAM", "CR": "LATAM", "EC": "LATAM", "GF": "LATAM",
    "GT": "LATAM", "GY": "LATAM", "HN": "LATAM", "NI": "LATAM", "PA": "LATAM",
    "PE": "LATAM", "PY": "LATAM", "SR": "LATAM", "SV": "LATAM", "UY": "LATAM",
    "VE": "LATAM",
    "JP": "ASIA", "CN": "ASIA", "KR": "ASIA", "IN": "ASIA", "TH": "ASIA",
    "VN": "ASIA", "MY": "ASIA", "SG": "ASIA", "ID": "ASIA", "PH": "ASIA",
    "AU": "ASIA", "NZ": "ASIA", "KZ": "ASIA", "UZ": "ASIA"
}}

HEADERS = {{
    "host": "www.g2a.com",
    "connection": "keep-alive",
    "sec-ch-ua": '"Chromium";v="140", "Not=A?Brand";v="24", "Google Chrome";v="140"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "upgrade-insecure-requests": "1",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9",
    "sec-fetch-site": "none",
    "sec-fetch-mode": "navigate",
    "sec-fetch-user": "?1",
    "sec-fetch-dest": "document",
    "accept-language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
}}

# Server configuration (for OAuth)
YOUR_SERVER_CONFIG = {{
    "redirect_uri": "http://localhost:8000/callback",
    "port": 8000
}}

def generate_credentials():
    return {{
        "client_id": G2A_CLIENT_ID,
        "client_secret": G2A_CLIENT_SECRET,
        "email": G2A_CLIENT_EMAIL
    }}

def save_credentials_to_file(credentials, filename="g2a_credentials.json"):
    import json
    with open(filename, 'w') as f:
        json.dump(credentials, f, indent=2)
'''
            
            with open('g2a_config.py', 'w', encoding='utf-8') as f:
                f.write(config_content)
            
            QMessageBox.information(
                self,
                "Success",
                "✅ G2A API settings saved successfully!\n\n"
                "🔄 Please RESTART the application to apply changes.\n\n"
                "🔑 Your email has been added to API authentication."
            )
            self.settings_changed.emit()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save settings:\n{str(e)}")
    
    def load_proxy_from_file(self):
        """Загрузка proxy из файла"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Proxy File",
            "",
            "Text Files (*.txt);;All Files (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.proxy_text.setPlainText(f.read())
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load proxy file:\n{str(e)}")
    
    def save_proxy_settings(self):
        """Сохранение proxy настроек"""
        try:
            with open('proxy.txt', 'w', encoding='utf-8') as f:
                f.write(self.proxy_text.toPlainText())
            
            QMessageBox.information(self, "Success", "Proxy settings saved successfully!")
            self.settings_changed.emit()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save proxy settings:\n{str(e)}")
    
    def save_telegram_settings(self):
        """Сохранение Telegram настроек"""
        try:
            config = {
                "enabled": self.telegram_enabled_check.isChecked(),
                "token": self.telegram_token_input.text().strip(),
                "chat_id": self.telegram_chat_input.text().strip()
            }
            
            import json
            with open('telegram_config.json', 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
            
            QMessageBox.information(self, "Success", "Telegram settings saved successfully!")
            self.settings_changed.emit()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save Telegram settings:\n{str(e)}")
    
    def save_parsing_settings(self):
        """Сохранение настроек парсинга"""
        try:
            config = {
                "delay": self.parsing_delay_spin.value(),
                "timeout": self.parsing_timeout_spin.value()
            }
            
            import json
            with open('parsing_config.json', 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
            
            QMessageBox.information(self, "Success", "Parsing settings saved successfully!")
            self.settings_changed.emit()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save parsing settings:\n{str(e)}")

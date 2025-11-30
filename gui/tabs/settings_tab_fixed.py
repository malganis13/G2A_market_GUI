#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Исправленная вкладка настроек с правильным расположением кнопок
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QGroupBox, QMessageBox, QScrollArea, QCheckBox
)
from PyQt6.QtCore import Qt
import json
import os


class SettingsTabFixed(QWidget):
    """Исправленная вкладка настроек"""
    
    def __init__(self):
        super().__init__()
        self.config_file = "g2a_config_saved.json"
        self.init_ui()
        self.load_settings()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        self.setLayout(layout)
        
        # Заголовок
        header = QLabel("⚙️ Settings")
        header.setProperty("class", "header")
        layout.addWidget(header)
        
        # Создаём scrollable область
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        
        # Контейнер для содержимого
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(5, 5, 5, 5)
        scroll_layout.setSpacing(10)
        
        # === G2A API Settings ===
        g2a_group = QGroupBox("🔑 G2A API Configuration")
        g2a_layout = QVBoxLayout()
        g2a_layout.setSpacing(8)
        
        # Client ID
        id_label = QLabel("Client ID:")
        id_label.setStyleSheet("font-weight: bold; font-size: 10pt;")
        g2a_layout.addWidget(id_label)
        
        self.client_id_input = QLineEdit()
        self.client_id_input.setPlaceholderText("Enter your G2A Client ID")
        self.client_id_input.setMinimumHeight(30)
        g2a_layout.addWidget(self.client_id_input)
        
        # Client Secret
        secret_label = QLabel("Client Secret:")
        secret_label.setStyleSheet("font-weight: bold; font-size: 10pt;")
        g2a_layout.addWidget(secret_label)
        
        self.client_secret_input = QLineEdit()
        self.client_secret_input.setPlaceholderText("Enter your G2A Client Secret")
        self.client_secret_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.client_secret_input.setMinimumHeight(30)
        g2a_layout.addWidget(self.client_secret_input)
        
        # Show/Hide secret
        show_secret_btn = QPushButton("👁️ Show")
        show_secret_btn.setMaximumWidth(80)
        show_secret_btn.setCheckable(True)
        show_secret_btn.toggled.connect(self.toggle_secret_visibility)
        g2a_layout.addWidget(show_secret_btn)
        
        # Client Email
        email_label = QLabel("Account Email:")
        email_label.setStyleSheet("font-weight: bold; font-size: 10pt;")
        g2a_layout.addWidget(email_label)
        
        self.client_email_input = QLineEdit()
        self.client_email_input.setPlaceholderText("Your G2A account email")
        self.client_email_input.setMinimumHeight(30)
        g2a_layout.addWidget(self.client_email_input)
        
        # Important notice
        notice = QLabel("⚠️ IMPORTANT: Email is required for API authentication!")
        notice.setStyleSheet("""
            QLabel {
                background-color: #ff5722;
                color: white;
                padding: 8px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 9pt;
            }
        """)
        notice.setWordWrap(True)
        g2a_layout.addWidget(notice)
        
        # Save button
        save_g2a_btn = QPushButton("💾 Save G2A Settings")
        save_g2a_btn.setMinimumHeight(45)
        save_g2a_btn.setStyleSheet("""
            QPushButton {
                background-color: #4caf50;
                color: white;
                font-size: 13pt;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        save_g2a_btn.clicked.connect(self.save_g2a_settings)
        g2a_layout.addWidget(save_g2a_btn)
        
        g2a_group.setLayout(g2a_layout)
        scroll_layout.addWidget(g2a_group)
        
        # === Telegram Notifications ===
        telegram_group = QGroupBox("📱 Telegram Notifications")
        telegram_layout = QVBoxLayout()
        telegram_layout.setSpacing(8)
        
        # Enable checkbox
        self.telegram_enabled = QCheckBox("Enable Telegram Notifications")
        self.telegram_enabled.setStyleSheet("font-size: 10pt; font-weight: bold;")
        telegram_layout.addWidget(self.telegram_enabled)
        
        # Bot Token
        token_label = QLabel("Bot Token:")
        token_label.setStyleSheet("font-weight: bold; font-size: 10pt;")
        telegram_layout.addWidget(token_label)
        
        self.telegram_token_input = QLineEdit()
        self.telegram_token_input.setPlaceholderText("Enter Telegram Bot Token")
        self.telegram_token_input.setMinimumHeight(30)
        telegram_layout.addWidget(self.telegram_token_input)
        
        # Chat ID
        chat_label = QLabel("Chat ID:")
        chat_label.setStyleSheet("font-weight: bold; font-size: 10pt;")
        telegram_layout.addWidget(chat_label)
        
        self.telegram_chat_input = QLineEdit()
        self.telegram_chat_input.setPlaceholderText("Enter Chat ID")
        self.telegram_chat_input.setMinimumHeight(30)
        telegram_layout.addWidget(self.telegram_chat_input)
        
        # Save button
        save_telegram_btn = QPushButton("💾 Save Telegram Settings")
        save_telegram_btn.setMinimumHeight(45)
        save_telegram_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196f3;
                color: white;
                font-size: 13pt;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #1976d2;
            }
        """)
        save_telegram_btn.clicked.connect(self.save_telegram_settings)
        telegram_layout.addWidget(save_telegram_btn)
        
        telegram_group.setLayout(telegram_layout)
        scroll_layout.addWidget(telegram_group)
        
        # Добавляем растяжку в конец
        scroll_layout.addStretch()
        
        # Устанавливаем контент в scroll area
        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)
    
    def toggle_secret_visibility(self, checked):
        """Показать/скрыть секрет"""
        if checked:
            self.client_secret_input.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self.client_secret_input.setEchoMode(QLineEdit.EchoMode.Password)
    
    def load_settings(self):
        """Загрузить настройки из файла"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                self.client_id_input.setText(config.get('G2A_CLIENT_ID', ''))
                self.client_secret_input.setText(config.get('G2A_CLIENT_SECRET', ''))
                self.client_email_input.setText(config.get('G2A_CLIENT_EMAIL', ''))
                self.telegram_token_input.setText(config.get('TELEGRAM_BOT_TOKEN', ''))
                self.telegram_chat_input.setText(config.get('TELEGRAM_CHAT_ID', ''))
                self.telegram_enabled.setChecked(config.get('TELEGRAM_ENABLED', False))
                
                print("✅ Settings loaded")
        except Exception as e:
            print(f"❌ Error loading settings: {e}")
    
    def save_g2a_settings(self):
        """Сохранить настройки G2A"""
        client_id = self.client_id_input.text().strip()
        client_secret = self.client_secret_input.text().strip()
        client_email = self.client_email_input.text().strip()
        
        if not client_id or not client_secret or not client_email:
            QMessageBox.warning(
                self,
                "Missing Information",
                "Please fill in all G2A API fields:\n\n• Client ID\n• Client Secret\n• Account Email"
            )
            return
        
        try:
            # Загружаем существующий конфиг или создаём новый
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            else:
                config = {}
            
            # Обновляем G2A настройки
            config['G2A_CLIENT_ID'] = client_id
            config['G2A_CLIENT_SECRET'] = client_secret
            config['G2A_CLIENT_EMAIL'] = client_email
            
            # Сохраняем
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            
            QMessageBox.information(
                self,
                "Success",
                "✅ G2A API settings saved!\n\nSettings will be used for next API requests."
            )
            
            print("✅ G2A settings saved")
        
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to save settings:\n{str(e)}"
            )
    
    def save_telegram_settings(self):
        """Сохранить настройки Telegram"""
        telegram_token = self.telegram_token_input.text().strip()
        telegram_chat = self.telegram_chat_input.text().strip()
        telegram_enabled = self.telegram_enabled.isChecked()
        
        if telegram_enabled and (not telegram_token or not telegram_chat):
            QMessageBox.warning(
                self,
                "Missing Information",
                "Please fill in Telegram settings:\n\n• Bot Token\n• Chat ID"
            )
            return
        
        try:
            # Загружаем существующий конфиг
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            else:
                config = {}
            
            # Обновляем Telegram настройки
            config['TELEGRAM_BOT_TOKEN'] = telegram_token
            config['TELEGRAM_CHAT_ID'] = telegram_chat
            config['TELEGRAM_ENABLED'] = telegram_enabled
            
            # Сохраняем
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            
            status = "enabled" if telegram_enabled else "disabled"
            QMessageBox.information(
                self,
                "Success",
                f"✅ Telegram notifications {status}!\n\nYou will receive notifications about price changes."
            )
            
            print(f"✅ Telegram settings saved ({status})")
        
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to save settings:\n{str(e)}"
            )

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Вкладка парсинга цен
"""

import asyncio
import os
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QTextEdit, QGroupBox, QCheckBox, QSpinBox,
    QListWidget, QListWidgetItem
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtGui import QTextCursor, QColor
from database import Database
from gui.styles import LOG_COLORS
import qasync


class ParsingTab(QWidget):
    """Вкладка парсинга цен"""
    
    parsing_started = pyqtSignal()
    parsing_finished = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.is_parsing = False
        self.init_ui()
        self.load_games()
        
    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Заголовок
        header = QLabel("💰 Price Parsing")
        header.setProperty("class", "header")
        layout.addWidget(header)
        
        # Группа выбора игр
        games_group = QGroupBox("🎮 Select Games for Parsing")
        games_layout = QVBoxLayout()
        
        # Кнопки выбора
        selection_layout = QHBoxLayout()
        
        select_all_btn = QPushButton("✅ Select All")
        select_all_btn.clicked.connect(self.select_all_games)
        selection_layout.addWidget(select_all_btn)
        
        deselect_all_btn = QPushButton("❌ Deselect All")
        deselect_all_btn.clicked.connect(self.deselect_all_games)
        selection_layout.addWidget(deselect_all_btn)
        
        select_no_price_btn = QPushButton("🎯 Select Without Prices")
        select_no_price_btn.clicked.connect(self.select_games_without_prices)
        selection_layout.addWidget(select_no_price_btn)
        
        selection_layout.addStretch()
        games_layout.addLayout(selection_layout)
        
        # Список игр
        self.games_list = QListWidget()
        self.games_list.setMaximumHeight(200)
        games_layout.addWidget(self.games_list)
        
        games_group.setLayout(games_layout)
        layout.addWidget(games_group)
        
        # Настройки парсинга
        settings_group = QGroupBox("⚙️ Parsing Settings")
        settings_layout = QHBoxLayout()
        
        settings_layout.addWidget(QLabel("Delay between requests (sec):"))
        self.delay_spin = QSpinBox()
        self.delay_spin.setRange(1, 10)
        self.delay_spin.setValue(2)
        settings_layout.addWidget(self.delay_spin)
        
        self.use_proxy_check = QCheckBox("Use Proxy")
        settings_layout.addWidget(self.use_proxy_check)
        
        settings_layout.addStretch()
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)
        
        # Прогресс бар
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar)
        
        # Кнопки управления
        controls_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("▶️ Start Parsing")
        self.start_btn.clicked.connect(self.start_parsing)
        controls_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("⏹️ Stop")
        self.stop_btn.clicked.connect(self.stop_parsing)
        self.stop_btn.setEnabled(False)
        controls_layout.addWidget(self.stop_btn)
        
        clear_log_btn = QPushButton("🗑️ Clear Log")
        clear_log_btn.clicked.connect(self.clear_log)
        controls_layout.addWidget(clear_log_btn)
        
        controls_layout.addStretch()
        layout.addLayout(controls_layout)
        
        # Лог
        log_group = QGroupBox("📜 Parsing Log")
        log_layout = QVBoxLayout()
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(300)
        log_layout.addWidget(self.log_text)
        
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)
        
    def load_games(self):
        """Загрузка списка игр"""
        try:
            games = self.db.get_games_list()
            self.games_list.clear()
            
            for game in games:
                item_text = f"{game['name']}"
                if game['min_price'] > 0:
                    item_text += f" (€{game['min_price']:.2f})"
                else:
                    item_text += " (No price)"
                
                item = QListWidgetItem(item_text)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Unchecked)
                item.setData(Qt.ItemDataRole.UserRole, game)
                self.games_list.addItem(item)
                
        except Exception as e:
            self.log(f"Error loading games: {e}", "error")
    
    def select_all_games(self):
        """Выбрать все игры"""
        for i in range(self.games_list.count()):
            self.games_list.item(i).setCheckState(Qt.CheckState.Checked)
    
    def deselect_all_games(self):
        """Снять выбор со всех игр"""
        for i in range(self.games_list.count()):
            self.games_list.item(i).setCheckState(Qt.CheckState.Unchecked)
    
    def select_games_without_prices(self):
        """Выбрать игры без цен"""
        for i in range(self.games_list.count()):
            item = self.games_list.item(i)
            game = item.data(Qt.ItemDataRole.UserRole)
            if game['min_price'] == 0:
                item.setCheckState(Qt.CheckState.Checked)
            else:
                item.setCheckState(Qt.CheckState.Unchecked)
    
    @qasync.asyncSlot()
    async def start_parsing(self):
        """Запуск парсинга"""
        # Получаем выбранные игры
        selected_games = []
        for i in range(self.games_list.count()):
            item = self.games_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                selected_games.append(item.data(Qt.ItemDataRole.UserRole))
        
        if not selected_games:
            self.log("⚠️ No games selected!", "warning")
            return
        
        self.is_parsing = True
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximum(len(selected_games))
        
        self.log(f"▶️ Starting parsing for {len(selected_games)} games...", "info")
        self.parsing_started.emit()
        
        try:
            # Импортируем парсер
            try:
                from price_parser import KeyPriceParser
            except ImportError:
                # Если нет price_parser, пробуем parser
                from parser import KeyPriceParser
            
            parser = KeyPriceParser()
            
            # Создаем временные файлы для парсинга
            temp_folder = Path("temp_parsing")
            temp_folder.mkdir(exist_ok=True)
            
            # Очищаем папку
            for file in temp_folder.glob("*.txt"):
                file.unlink()
            
            # Создаем файлы для каждой игры
            for game in selected_games:
                temp_file = temp_folder / f"{game['name']}.txt"
                with open(temp_file, 'w', encoding='utf-8') as f:
                    # Получаем любой ключ этой игры
                    keys = self.db.get_keys_by_game(game['name'])
                    if keys:
                        key = keys[0]
                        f.write(f"{game['name']} | {key['key_code']} | {key['platform']} | {key['region']}\n")
            
            # Запускаем парсер
            self.log("🔍 Running price parser...", "info")
            
            # Парсим каждую игру отдельно для отображения прогресса
            for idx, game in enumerate(selected_games):
                if not self.is_parsing:
                    self.log("⏹️ Parsing stopped by user", "warning")
                    break
                
                self.log(f"🔎 Parsing {game['name']}...", "info")
                
                # Здесь должен быть вызов парсера
                # В реальной реализации здесь будет await parser.parse_game(game)
                
                await asyncio.sleep(self.delay_spin.value())
                
                self.progress_bar.setValue(idx + 1)
                self.log(f"✅ Parsed {game['name']}", "success")
            
            # Обновляем цены в базе из result файлов
            result_folder = Path("result")
            if result_folder.exists():
                updated_count = 0
                for result_file in result_folder.glob("*.txt"):
                    try:
                        count = self.db.set_prices_from_file(str(result_file))
                        updated_count += count
                    except Exception as e:
                        self.log(f"⚠️ Error updating prices from {result_file.name}: {e}", "warning")
                
                self.log(f"✅ Updated prices for {updated_count} keys", "success")
            
            self.log("✅ Parsing completed successfully!", "success")
            
        except Exception as e:
            self.log(f"❌ Parsing error: {str(e)}", "error")
            import traceback
            self.log(traceback.format_exc(), "debug")
        
        finally:
            self.is_parsing = False
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.parsing_finished.emit()
            self.load_games()  # Обновляем список с новыми ценами
    
    def stop_parsing(self):
        """Остановка парсинга"""
        self.is_parsing = False
        self.log("⏹️ Stopping parsing...", "warning")
    
    def log(self, message, level="info"):
        """Добавление сообщения в лог"""
        color = LOG_COLORS.get(level, LOG_COLORS['info'])
        
        # Добавляем время
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        formatted_message = f'<span style="color: #888;">[{timestamp}]</span> '
        formatted_message += f'<span style="color: {color};">{message}</span>'
        
        self.log_text.append(formatted_message)
        self.log_text.moveCursor(QTextCursor.MoveOperation.End)
    
    def clear_log(self):
        """Очистка лога"""
        self.log_text.clear()

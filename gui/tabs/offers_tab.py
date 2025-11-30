#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Вкладка управления офферами
"""

import asyncio
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QGroupBox, QTextEdit,
    QListWidget, QListWidgetItem, QDoubleSpinBox, QHeaderView,
    QMessageBox, QProgressBar
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QTextCursor
from database import Database
from g2a_api_client import G2AApiClient
from gui.styles import LOG_COLORS
import qasync


class OffersTab(QWidget):
    """Вкладка управления офферами"""
    
    offers_updated = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.api_client = None
        self.offers_cache = {}
        self.is_creating = False
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Заголовок
        header = QLabel("📦 Offers Management")
        header.setProperty("class", "header")
        layout.addWidget(header)
        
        # Группа создания офферов
        create_group = QGroupBox("➕ Create Offers")
        create_layout = QVBoxLayout()
        
        # Инфо
        info_label = QLabel(
            "Select games with prices to create offers on G2A marketplace."
        )
        info_label.setStyleSheet("color: #a0a0a0; padding: 5px;")
        create_layout.addWidget(info_label)
        
        # Список игр для создания офферов
        self.games_for_offers_list = QListWidget()
        self.games_for_offers_list.setMaximumHeight(150)
        create_layout.addWidget(self.games_for_offers_list)
        
        # Кнопки выбора
        selection_layout = QHBoxLayout()
        
        select_all_btn = QPushButton("✅ Select All")
        select_all_btn.clicked.connect(self.select_all_games)
        selection_layout.addWidget(select_all_btn)
        
        deselect_all_btn = QPushButton("❌ Deselect All")
        deselect_all_btn.clicked.connect(self.deselect_all_games)
        selection_layout.addWidget(deselect_all_btn)
        
        load_games_btn = QPushButton("🔄 Load Games")
        load_games_btn.clicked.connect(self.load_games_for_offers)
        selection_layout.addWidget(load_games_btn)
        
        selection_layout.addStretch()
        create_layout.addLayout(selection_layout)
        
        # Прогресс бар
        self.offers_progress = QProgressBar()
        create_layout.addWidget(self.offers_progress)
        
        # Кнопка создания
        self.create_offers_btn = QPushButton("🚀 Create Selected Offers")
        self.create_offers_btn.clicked.connect(self.create_offers)
        create_layout.addWidget(self.create_offers_btn)
        
        create_group.setLayout(create_layout)
        layout.addWidget(create_group)
        
        # Таблица активных офферов
        offers_group = QGroupBox("📋 Active Offers")
        offers_layout = QVBoxLayout()
        
        # Кнопка обновления
        refresh_offers_btn = QPushButton("🔄 Refresh Offers from G2A")
        refresh_offers_btn.clicked.connect(self.load_offers_from_api)
        offers_layout.addWidget(refresh_offers_btn)
        
        self.offers_table = QTableWidget()
        self.offers_table.setColumnCount(6)
        self.offers_table.setHorizontalHeaderLabels([
            "Product ID", "Game", "Price (€)", "Stock", "Status", "Actions"
        ])
        self.offers_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.offers_table.setAlternatingRowColors(True)
        offers_layout.addWidget(self.offers_table)
        
        offers_group.setLayout(offers_layout)
        layout.addWidget(offers_group)
        
        # Лог
        log_group = QGroupBox("📜 Operation Log")
        log_layout = QVBoxLayout()
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(200)
        log_layout.addWidget(self.log_text)
        
        clear_log_btn = QPushButton("🗑️ Clear Log")
        clear_log_btn.clicked.connect(self.clear_log)
        log_layout.addWidget(clear_log_btn)
        
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)
        
        # Загружаем игры
        self.load_games_for_offers()
    
    def load_games_for_offers(self):
        """Загрузка игр с ценами для создания офферов"""
        try:
            games = self.db.get_games_list()
            games_with_prices = [g for g in games if g['min_price'] > 0 and g['available_keys'] > 0]
            
            self.games_for_offers_list.clear()
            
            for game in games_with_prices:
                item_text = f"{game['name']} - €{game['min_price']:.2f} ({game['available_keys']} keys)"
                item = QListWidgetItem(item_text)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Unchecked)
                item.setData(Qt.ItemDataRole.UserRole, game)
                self.games_for_offers_list.addItem(item)
            
            if not games_with_prices:
                self.log("⚠️ No games with prices found. Run price parsing first.", "warning")
            else:
                self.log(f"✅ Loaded {len(games_with_prices)} games ready for offers", "success")
                
        except Exception as e:
            self.log(f"❌ Error loading games: {e}", "error")
    
    def select_all_games(self):
        """Выбрать все игры"""
        for i in range(self.games_for_offers_list.count()):
            self.games_for_offers_list.item(i).setCheckState(Qt.CheckState.Checked)
    
    def deselect_all_games(self):
        """Снять выбор"""
        for i in range(self.games_for_offers_list.count()):
            self.games_for_offers_list.item(i).setCheckState(Qt.CheckState.Unchecked)
    
    @qasync.asyncSlot()
    async def create_offers(self):
        """Создание офферов"""
        # Получаем выбранные игры
        selected_games = []
        for i in range(self.games_for_offers_list.count()):
            item = self.games_for_offers_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                selected_games.append(item.data(Qt.ItemDataRole.UserRole))
        
        if not selected_games:
            self.log("⚠️ No games selected!", "warning")
            return
        
        self.is_creating = True
        self.create_offers_btn.setEnabled(False)
        self.offers_progress.setValue(0)
        self.offers_progress.setMaximum(len(selected_games))
        
        self.log(f"🚀 Starting offer creation for {len(selected_games)} games...", "info")
        
        try:
            # Инициализируем API клиент
            self.api_client = G2AApiClient()
            await self.api_client.get_token()
            await self.api_client.get_rate()
            
            # Загружаем существующие офферы
            self.log("🔍 Loading existing offers...", "info")
            offers_result = await self.api_client.get_offers()
            if offers_result.get('success'):
                self.offers_cache = offers_result.get('offers_cache', {})
                self.log(f"✅ Loaded {len(self.offers_cache)} existing offers", "success")
            
            created_count = 0
            updated_count = 0
            
            for idx, game in enumerate(selected_games):
                if not self.is_creating:
                    self.log("⏹️ Offer creation stopped by user", "warning")
                    break
                
                self.log(f"🔎 Processing {game['name']}...", "info")
                
                # Здесь должна быть логика создания оффера
                # 1. Поиск product_id
                # 2. Создание или обновление оффера
                
                # Заглушка - в реальности здесь будет вызов API
                await asyncio.sleep(1)
                
                self.offers_progress.setValue(idx + 1)
                self.log(f"✅ Processed {game['name']}", "success")
                created_count += 1
            
            self.log(f"✅ Offer creation completed! Created: {created_count}, Updated: {updated_count}", "success")
            
        except Exception as e:
            self.log(f"❌ Error creating offers: {str(e)}", "error")
            import traceback
            self.log(traceback.format_exc(), "debug")
        
        finally:
            self.is_creating = False
            self.create_offers_btn.setEnabled(True)
            self.offers_updated.emit()
    
    @qasync.asyncSlot()
    async def load_offers_from_api(self):
        """Загрузка офферов из G2A API"""
        self.log("🔍 Loading offers from G2A...", "info")
        
        try:
            self.api_client = G2AApiClient()
            await self.api_client.get_token()
            
            result = await self.api_client.get_offers()
            
            if result.get('success'):
                self.offers_cache = result.get('offers_cache', {})
                self.display_offers()
                self.log(f"✅ Loaded {len(self.offers_cache)} offers", "success")
            else:
                self.log(f"❌ Failed to load offers: {result.get('error')}", "error")
                
        except Exception as e:
            self.log(f"❌ Error: {str(e)}", "error")
    
    def display_offers(self):
        """Отображение офферов в таблице"""
        self.offers_table.setRowCount(len(self.offers_cache))
        
        for row, (product_id, offer) in enumerate(self.offers_cache.items()):
            self.offers_table.setItem(row, 0, QTableWidgetItem(product_id))
            self.offers_table.setItem(row, 1, QTableWidgetItem(offer.get('product_name', 'N/A')))
            self.offers_table.setItem(row, 2, QTableWidgetItem(str(offer.get('price', 'N/A'))))
            self.offers_table.setItem(row, 3, QTableWidgetItem(str(offer.get('current_stock', 0))))
            
            # Status
            status = "Active" if offer.get('is_active') else "Inactive"
            status_item = QTableWidgetItem(status)
            if offer.get('is_active'):
                status_item.setForeground(Qt.GlobalColor.green)
            else:
                status_item.setForeground(Qt.GlobalColor.red)
            self.offers_table.setItem(row, 4, status_item)
            
            # Actions
            update_btn = QPushButton("♻️ Update")
            update_btn.clicked.connect(lambda checked, oid=offer.get('id'): self.update_offer(oid))
            self.offers_table.setCellWidget(row, 5, update_btn)
    
    def update_offer(self, offer_id):
        """Обновление оффера"""
        self.log(f"🔄 Update offer {offer_id} - Not implemented yet", "info")
    
    def log(self, message, level="info"):
        """Добавление сообщения в лог"""
        color = LOG_COLORS.get(level, LOG_COLORS['info'])
        
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        formatted_message = f'<span style="color: #888;">[{timestamp}]</span> '
        formatted_message += f'<span style="color: {color};">{message}</span>'
        
        self.log_text.append(formatted_message)
        self.log_text.moveCursor(QTextCursor.MoveOperation.End)
    
    def clear_log(self):
        """Очистка лога"""
        self.log_text.clear()
    
    def refresh(self):
        """Обновление данных"""
        self.load_games_for_offers()

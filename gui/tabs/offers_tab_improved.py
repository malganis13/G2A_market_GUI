#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Улучшенная вкладка управления офферами с поиском и контекстным меню
"""

import asyncio
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QGroupBox, QLineEdit,
    QHeaderView, QMessageBox, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QAction
from database import Database
from g2a_api_client import G2AApiClient
import qasync


class OffersTabImproved(QWidget):
    """Улучшенная вкладка офферов"""
    
    offers_updated = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.api_client = None
        self.offers_cache = {}
        self.filtered_offers = {}
        self.init_ui()
        
        # Автообновление каждые 5 минут
        self.auto_refresh_timer = QTimer()
        self.auto_refresh_timer.timeout.connect(self.auto_refresh_offers)
        self.auto_refresh_timer.start(300000)  # 5 минут
        
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        self.setLayout(layout)
        
        # Заголовок
        header_layout = QHBoxLayout()
        header = QLabel("📦 Offers Management")
        header.setProperty("class", "header")
        header_layout.addWidget(header)
        
        self.auto_refresh_label = QLabel("🔄 Auto-refresh: ON")
        self.auto_refresh_label.setStyleSheet("color: #4caf50; font-size: 9pt;")
        header_layout.addWidget(self.auto_refresh_label)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Панель управления (компактная)
        control_layout = QHBoxLayout()
        control_layout.setSpacing(6)
        
        # Поиск
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search offers by game name...")
        self.search_input.textChanged.connect(self.filter_offers)
        self.search_input.setMaximumHeight(28)
        control_layout.addWidget(self.search_input)
        
        # Кнопка обновления
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.load_offers_from_api)
        refresh_btn.setMaximumWidth(100)
        refresh_btn.setMaximumHeight(28)
        control_layout.addWidget(refresh_btn)
        
        # Кнопка создания
        create_btn = QPushButton("➕ Create")
        create_btn.clicked.connect(self.show_create_dialog)
        create_btn.setMaximumWidth(100)
        create_btn.setMaximumHeight(28)
        control_layout.addWidget(create_btn)
        
        layout.addLayout(control_layout)
        
        # Статистика
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(10)
        
        self.total_offers_label = QLabel("📦 Total: 0")
        self.total_offers_label.setStyleSheet("font-size: 9pt; color: #0d7377;")
        stats_layout.addWidget(self.total_offers_label)
        
        self.active_offers_label = QLabel("✅ Active: 0")
        self.active_offers_label.setStyleSheet("font-size: 9pt; color: #4caf50;")
        stats_layout.addWidget(self.active_offers_label)
        
        self.inactive_offers_label = QLabel("❌ Inactive: 0")
        self.inactive_offers_label.setStyleSheet("font-size: 9pt; color: #ff5252;")
        stats_layout.addWidget(self.inactive_offers_label)
        
        stats_layout.addStretch()
        
        self.last_update_label = QLabel("Last update: Never")
        self.last_update_label.setStyleSheet("color: #888; font-size: 8pt;")
        stats_layout.addWidget(self.last_update_label)
        
        layout.addLayout(stats_layout)
        
        # Таблица офферов (компактная)
        self.offers_table = QTableWidget()
        self.offers_table.setColumnCount(6)
        self.offers_table.setHorizontalHeaderLabels([
            "Game", "Price (€)", "Stock", "Status", "Product ID", "Offer ID"
        ])
        
        # Настройка ширины колонок
        header = self.offers_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Game name
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        
        self.offers_table.setColumnWidth(1, 80)  # Price
        self.offers_table.setColumnWidth(2, 60)  # Stock
        self.offers_table.setColumnWidth(3, 70)  # Status
        self.offers_table.setColumnWidth(4, 100)  # Product ID
        self.offers_table.setColumnWidth(5, 100)  # Offer ID
        
        self.offers_table.setAlternatingRowColors(True)
        self.offers_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.offers_table.customContextMenuRequested.connect(self.show_context_menu)
        self.offers_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        layout.addWidget(self.offers_table)
        
        # Информация
        info_label = QLabel(
            "👉 Right-click on offers for actions | Double-click to edit price | Search to filter"
        )
        info_label.setStyleSheet("color: #888; font-size: 8pt; padding: 4px;")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
    
    def filter_offers(self):
        """Фильтрация офферов по поисковому запросу"""
        search_text = self.search_input.text().lower()
        
        if not search_text:
            self.filtered_offers = self.offers_cache.copy()
        else:
            self.filtered_offers = {
                pid: offer for pid, offer in self.offers_cache.items()
                if search_text in offer.get('product_name', '').lower()
            }
        
        self.display_offers()
    
    @qasync.asyncSlot()
    async def load_offers_from_api(self):
        """Загрузка офферов из G2A API"""
        try:
            self.api_client = G2AApiClient()
            await self.api_client.get_token()
            
            result = await self.api_client.get_offers()
            
            if result.get('success'):
                self.offers_cache = result.get('offers_cache', {})
                self.filtered_offers = self.offers_cache.copy()
                self.display_offers()
                self.update_stats()
                
                # Обновляем время
                from datetime import datetime
                now = datetime.now().strftime("%H:%M:%S")
                self.last_update_label.setText(f"Last update: {now}")
            else:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to load offers:\n{result.get('error')}"
                )
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load offers:\n{str(e)}")
            import traceback
            traceback.print_exc()
    
    def display_offers(self):
        """Отображение офферов в таблице"""
        self.offers_table.setRowCount(len(self.filtered_offers))
        
        for row, (product_id, offer) in enumerate(self.filtered_offers.items()):
            # Game name
            self.offers_table.setItem(row, 0, QTableWidgetItem(offer.get('product_name', 'N/A')))
            
            # Price
            price_str = str(offer.get('price', 'N/A'))
            if isinstance(offer.get('price'), (int, float)):
                price_str = f"{offer['price']:.2f}"
            self.offers_table.setItem(row, 1, QTableWidgetItem(price_str))
            
            # Stock
            stock_item = QTableWidgetItem(str(offer.get('current_stock', 0)))
            stock_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.offers_table.setItem(row, 2, stock_item)
            
            # Status
            is_active = offer.get('is_active', False)
            status_text = "Active" if is_active else "Inactive"
            status_item = QTableWidgetItem(status_text)
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            if is_active:
                status_item.setForeground(Qt.GlobalColor.green)
            else:
                status_item.setForeground(Qt.GlobalColor.red)
            
            self.offers_table.setItem(row, 3, status_item)
            
            # Product ID
            pid_item = QTableWidgetItem(product_id)
            pid_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.offers_table.setItem(row, 4, pid_item)
            
            # Offer ID
            oid_item = QTableWidgetItem(str(offer.get('id', 'N/A')))
            oid_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.offers_table.setItem(row, 5, oid_item)
    
    def update_stats(self):
        """Обновление статистики"""
        total = len(self.offers_cache)
        active = sum(1 for o in self.offers_cache.values() if o.get('is_active'))
        inactive = total - active
        
        self.total_offers_label.setText(f"📦 Total: {total}")
        self.active_offers_label.setText(f"✅ Active: {active}")
        self.inactive_offers_label.setText(f"❌ Inactive: {inactive}")
    
    def show_context_menu(self, position):
        """Показ контекстного меню"""
        row = self.offers_table.rowAt(position.y())
        if row < 0:
            return
        
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #2d2d2d;
                border: 1px solid #444;
            }
            QMenu::item {
                padding: 5px 20px;
                color: #e0e0e0;
            }
            QMenu::item:selected {
                background-color: #0d7377;
            }
        """)
        
        # Получаем данные оффера
        product_id = self.offers_table.item(row, 4).text()
        offer_id = self.offers_table.item(row, 5).text()
        is_active = "Active" in self.offers_table.item(row, 3).text()
        
        # Действия
        update_price_action = QAction("💰 Update Price", self)
        update_price_action.triggered.connect(lambda: self.update_offer_price(offer_id))
        menu.addAction(update_price_action)
        
        update_stock_action = QAction("📦 Update Stock", self)
        update_stock_action.triggered.connect(lambda: self.update_offer_stock(offer_id))
        menu.addAction(update_stock_action)
        
        menu.addSeparator()
        
        if is_active:
            deactivate_action = QAction("⏸️ Deactivate Offer", self)
            deactivate_action.triggered.connect(lambda: self.toggle_offer_status(offer_id, False))
            menu.addAction(deactivate_action)
        else:
            activate_action = QAction("▶️ Activate Offer", self)
            activate_action.triggered.connect(lambda: self.toggle_offer_status(offer_id, True))
            menu.addAction(activate_action)
        
        menu.addSeparator()
        
        delete_action = QAction("🗑️ Delete Offer", self)
        delete_action.triggered.connect(lambda: self.delete_offer(offer_id))
        menu.addAction(delete_action)
        
        menu.addSeparator()
        
        view_details_action = QAction("🔍 View Details", self)
        view_details_action.triggered.connect(lambda: self.view_offer_details(product_id))
        menu.addAction(view_details_action)
        
        menu.exec(self.offers_table.viewport().mapToGlobal(position))
    
    def update_offer_price(self, offer_id):
        """Обновление цены оффера"""
        QMessageBox.information(self, "Info", f"💰 Update price for offer {offer_id}\n\nФункция в разработке")
    
    def update_offer_stock(self, offer_id):
        """Обновление стока оффера"""
        QMessageBox.information(self, "Info", f"📦 Update stock for offer {offer_id}\n\nФункция в разработке")
    
    def toggle_offer_status(self, offer_id, activate):
        """Активация/деактивация оффера"""
        action = "activate" if activate else "deactivate"
        QMessageBox.information(self, "Info", f"▶️ {action.title()} offer {offer_id}\n\nФункция в разработке")
    
    def delete_offer(self, offer_id):
        """Удаление оффера"""
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"🗑️ Are you sure you want to delete offer {offer_id}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            QMessageBox.information(self, "Info", "Функция удаления в разработке")
    
    def view_offer_details(self, product_id):
        """Просмотр деталей оффера"""
        if product_id in self.offers_cache:
            offer = self.offers_cache[product_id]
            details = f"""
            📊 Offer Details
            
            Product ID: {product_id}
            Offer ID: {offer.get('id', 'N/A')}
            Game: {offer.get('product_name', 'N/A')}
            Price: €{offer.get('price', 'N/A')}
            Stock: {offer.get('current_stock', 0)}
            Status: {'Active' if offer.get('is_active') else 'Inactive'}
            Type: {offer.get('offer_type', 'N/A')}
            """
            QMessageBox.information(self, "Offer Details", details)
    
    def show_create_dialog(self):
        """Диалог создания офферов"""
        QMessageBox.information(
            self,
            "Create Offers",
            "➕ Функция создания офферов в разработке.\n\n"
            "Используйте старую вкладку Offers для создания."
        )
    
    def auto_refresh_offers(self):
        """Автоматическое обновление"""
        asyncio.create_task(self.load_offers_from_api())
        self.auto_refresh_label.setText("🔄 Auto-refreshed")
        QTimer.singleShot(2000, lambda: self.auto_refresh_label.setText("🔄 Auto-refresh: ON"))

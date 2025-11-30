#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Полная вкладка офферов с всеми функциями из g2a-automation
"""

import asyncio
import json
import os
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QGroupBox, QLineEdit,
    QHeaderView, QMessageBox, QMenu, QInputDialog, QSpinBox, QDoubleSpinBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QAction, QColor
from database import Database
from g2a_api_client import G2AApiClient
import qasync


class AutoPriceSettings:
    """Управление настройками автоизменения"""
    
    def __init__(self, settings_file="auto_price_settings.json"):
        self.settings_file = settings_file
        self.settings = self.load_settings()
    
    def load_settings(self):
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"❌ Ошибка загрузки настроек: {e}")
        
        return {
            "enabled": False,
            "check_interval": 1800,
            "competitor_offset": 0.05,  # +0.05€ от мин. конкурента
            "min_price": 0.1,
            "max_price": 100.0,
            "daily_limit": 30,
            "excluded_products": [],  # Черный список
            "included_products": [],  # Белый список
            "protect_single_seller": True
        }
    
    def save_settings(self):
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4, ensure_ascii=False)
            print(f"✅ Настройки сохранены")
        except Exception as e:
            print(f"❌ Ошибка сохранения: {e}")
    
    def is_product_allowed(self, product_id):
        """Проверить разрешено ли автоизменение"""
        product_id = str(product_id)
        
        if not self.settings.get("enabled", False):
            return False
        
        excluded = self.settings.get("excluded_products", [])
        if product_id in [str(e) for e in excluded]:
            return False
        
        included = self.settings.get("included_products", [])
        if included:
            return product_id in [str(i) for i in included]
        
        return True
    
    def toggle_product(self, product_id, enabled=True):
        """Включить/выключить автоизменение для товара"""
        product_id = str(product_id)
        excluded = self.settings.get("excluded_products", [])
        included = self.settings.get("included_products", [])
        
        if enabled:
            self.settings["excluded_products"] = [str(p) for p in excluded if str(p) != product_id]
            if product_id not in [str(i) for i in included]:
                self.settings["included_products"].append(product_id)
        else:
            if product_id not in [str(e) for e in excluded]:
                self.settings["excluded_products"].append(product_id)
            self.settings["included_products"] = [str(i) for i in included if str(i) != product_id]
        
        self.save_settings()


class OffersTabFull(QWidget):
    """Полная вкладка офферов"""
    
    offers_updated = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.api_client = None
        self.offers_cache = {}
        self.filtered_offers = {}
        self.auto_settings = AutoPriceSettings()
        self.seller_id = None
        self.init_ui()
        
        # Автообновление каждые 5 минут
        self.auto_refresh_timer = QTimer()
        self.auto_refresh_timer.timeout.connect(self.auto_refresh_offers)
        self.auto_refresh_timer.start(300000)
    
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
        
        # Панель управления
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
        
        # Кнопка настроек
        settings_btn = QPushButton("⚙️ Settings")
        settings_btn.clicked.connect(self.show_auto_settings)
        settings_btn.setMaximumWidth(100)
        settings_btn.setMaximumHeight(28)
        control_layout.addWidget(settings_btn)
        
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
        
        self.auto_enabled_label = QLabel("🤖 Auto: 0")
        self.auto_enabled_label.setStyleSheet("font-size: 9pt; color: #2196f3;")
        stats_layout.addWidget(self.auto_enabled_label)
        
        stats_layout.addStretch()
        
        self.last_update_label = QLabel("Last update: Never")
        self.last_update_label.setStyleSheet("color: #888; font-size: 8pt;")
        stats_layout.addWidget(self.last_update_label)
        
        layout.addLayout(stats_layout)
        
        # Таблица офферов
        self.offers_table = QTableWidget()
        self.offers_table.setColumnCount(7)
        self.offers_table.setHorizontalHeaderLabels([
            "Game", "Price (€)", "Stock", "Status", "Auto", "Product ID", "Offer ID"
        ])
        
        # Настройка ширины колонок
        header = self.offers_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        
        self.offers_table.setColumnWidth(1, 80)
        self.offers_table.setColumnWidth(2, 60)
        self.offers_table.setColumnWidth(3, 70)
        self.offers_table.setColumnWidth(4, 50)
        self.offers_table.setColumnWidth(5, 100)
        self.offers_table.setColumnWidth(6, 100)
        
        self.offers_table.setAlternatingRowColors(True)
        self.offers_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.offers_table.customContextMenuRequested.connect(self.show_context_menu)
        self.offers_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        layout.addWidget(self.offers_table)
        
        # Информация
        info_label = QLabel(
            "👉 Right-click on offers for actions | Auto column shows auto-price status"
        )
        info_label.setStyleSheet("color: #888; font-size: 8pt; padding: 4px;")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
    
    def filter_offers(self):
        """Фильтрация офферов"""
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
                
                # Получаем seller_id
                if self.offers_cache:
                    first_offer = next(iter(self.offers_cache.values()))
                    if first_offer.get('seller_id'):
                        self.seller_id = first_offer['seller_id']
                        print(f"✅ Seller ID: {self.seller_id}")
                
                self.filtered_offers = self.offers_cache.copy()
                self.display_offers()
                self.update_stats()
                
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
        """Отображение офферов"""
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
            status_text = "✅ Active" if is_active else "❌ Inactive"
            status_item = QTableWidgetItem(status_text)
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            if is_active:
                status_item.setForeground(QColor("#4caf50"))
            else:
                status_item.setForeground(QColor("#ff5252"))
            
            self.offers_table.setItem(row, 3, status_item)
            
            # Auto-price status
            auto_enabled = self.auto_settings.is_product_allowed(product_id)
            auto_text = "🟢 ON" if auto_enabled else "🔴 OFF"
            auto_item = QTableWidgetItem(auto_text)
            auto_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            if auto_enabled:
                auto_item.setForeground(QColor("#4caf50"))
            else:
                auto_item.setForeground(QColor("#ff5252"))
            
            self.offers_table.setItem(row, 4, auto_item)
            
            # Product ID
            pid_item = QTableWidgetItem(product_id)
            pid_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.offers_table.setItem(row, 5, pid_item)
            
            # Offer ID
            oid_item = QTableWidgetItem(str(offer.get('id', 'N/A')))
            oid_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.offers_table.setItem(row, 6, oid_item)
    
    def update_stats(self):
        """Обновление статистики"""
        total = len(self.offers_cache)
        active = sum(1 for o in self.offers_cache.values() if o.get('is_active'))
        auto_enabled = sum(1 for pid in self.offers_cache.keys() if self.auto_settings.is_product_allowed(pid))
        
        self.total_offers_label.setText(f"📦 Total: {total}")
        self.active_offers_label.setText(f"✅ Active: {active}")
        self.auto_enabled_label.setText(f"🤖 Auto: {auto_enabled}")
    
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
        
        product_id = self.offers_table.item(row, 5).text()
        offer_id = self.offers_table.item(row, 6).text()
        is_active = "✅" in self.offers_table.item(row, 3).text()
        auto_enabled = "🟢" in self.offers_table.item(row, 4).text()
        
        # Автоизменение
        if auto_enabled:
            auto_action = QAction("🔴 Disable Auto-Price", self)
            auto_action.triggered.connect(lambda: self.toggle_auto_price(product_id, False))
        else:
            auto_action = QAction("🟢 Enable Auto-Price", self)
            auto_action.triggered.connect(lambda: self.toggle_auto_price(product_id, True))
        menu.addAction(auto_action)
        
        menu.addSeparator()
        
        # Действия
        update_price_action = QAction("💰 Update Price", self)
        update_price_action.triggered.connect(lambda: self.update_offer_price(offer_id, product_id))
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
    
    def toggle_auto_price(self, product_id, enable):
        """Вкл/выкл автоизменение для оффера"""
        try:
            if enable and not self.auto_settings.settings.get("enabled", False):
                reply = QMessageBox.question(
                    self,
                    "Enable Global Auto-Price?",
                    "Auto-price is globally disabled!\n\nEnable it globally first?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    self.auto_settings.settings["enabled"] = True
                    self.auto_settings.save_settings()
                else:
                    return
            
            self.auto_settings.toggle_product(product_id, enabled=enable)
            
            action = "enabled" if enable else "disabled"
            QMessageBox.information(self, "Success", f"✅ Auto-price {action} for this offer")
            
            self.display_offers()
            self.update_stats()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to toggle auto-price:\n{str(e)}")
    
    def update_offer_price(self, offer_id, product_id):
        """Обновление цены"""
        current_price = 0
        for pid, offer in self.offers_cache.items():
            if offer.get('id') == offer_id:
                current_price = offer.get('price', 0)
                break
        
        new_price, ok = QInputDialog.getDouble(
            self,
            "Update Price",
            f"Current price: €{current_price:.2f}\n\nEnter new price (€):",
            value=current_price,
            min=0.01,
            max=1000.0,
            decimals=2
        )
        
        if ok:
            asyncio.create_task(self._update_price_async(offer_id, new_price, current_price, product_id))
    
    async def _update_price_async(self, offer_id, new_price, old_price, product_id):
        """Асинхронное обновление цены"""
        try:
            if not self.api_client:
                self.api_client = G2AApiClient()
                await self.api_client.get_token()
            
            # Получаем детали оффера
            for pid, offer in self.offers_cache.items():
                if offer.get('id') == offer_id:
                    update_data = {
                        "offerType": offer.get('offer_type', 'dropshipping'),
                        "variant": {
                            "price": {
                                "retail": str(new_price),
                                "business": str(new_price)
                            },
                            "active": True
                        }
                    }
                    
                    result = await self.api_client.update_offer_partial(offer_id, update_data)
                    
                    if result.get('success'):
                        # Сохраняем статистику
                        self.db.save_price_change(product_id, old_price, new_price, new_price, "manual")
                        
                        QMessageBox.information(self, "Success", f"✅ Price updated to €{new_price:.2f}")
                        await self.load_offers_from_api()
                    else:
                        QMessageBox.critical(self, "Error", f"Failed:\n{result.get('error')}")
                    break
        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to update price:\n{str(e)}")
    
    def update_offer_stock(self, offer_id):
        """Обновление стока"""
        current_stock = 0
        for pid, offer in self.offers_cache.items():
            if offer.get('id') == offer_id:
                current_stock = offer.get('current_stock', 0)
                break
        
        new_stock, ok = QInputDialog.getInt(
            self,
            "Update Stock",
            f"Current stock: {current_stock}\n\nEnter new stock:",
            value=current_stock,
            min=0,
            max=10000
        )
        
        if ok:
            asyncio.create_task(self._update_stock_async(offer_id, new_stock))
    
    async def _update_stock_async(self, offer_id, new_stock):
        try:
            if not self.api_client:
                self.api_client = G2AApiClient()
                await self.api_client.get_token()
            
            for pid, offer in self.offers_cache.items():
                if offer.get('id') == offer_id:
                    update_data = {
                        "offerType": offer.get('offer_type', 'dropshipping'),
                        "variant": {
                            "inventory": {
                                "size": new_stock
                            }
                        }
                    }
                    
                    result = await self.api_client.update_offer_partial(offer_id, update_data)
                    
                    if result.get('success'):
                        QMessageBox.information(self, "Success", f"✅ Stock updated to {new_stock}")
                        await self.load_offers_from_api()
                    else:
                        QMessageBox.critical(self, "Error", result.get('error'))
                    break
        
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
    
    def toggle_offer_status(self, offer_id, activate):
        """Активация/деактивация"""
        asyncio.create_task(self._toggle_status_async(offer_id, activate))
    
    async def _toggle_status_async(self, offer_id, activate):
        try:
            if not self.api_client:
                self.api_client = G2AApiClient()
                await self.api_client.get_token()
            
            for pid, offer in self.offers_cache.items():
                if offer.get('id') == offer_id:
                    update_data = {
                        "offerType": offer.get('offer_type', 'dropshipping'),
                        "variant": {
                            "active": activate
                        }
                    }
                    
                    result = await self.api_client.update_offer_partial(offer_id, update_data)
                    
                    if result.get('success'):
                        action = "activated" if activate else "deactivated"
                        QMessageBox.information(self, "Success", f"✅ Offer {action}")
                        await self.load_offers_from_api()
                    else:
                        QMessageBox.critical(self, "Error", result.get('error'))
                    break
        
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
    
    def delete_offer(self, offer_id):
        """Удаление оффера"""
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"🗑️ Are you sure you want to DELETE this offer?\n\nThis cannot be undone!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            asyncio.create_task(self._delete_offer_async(offer_id))
    
    async def _delete_offer_async(self, offer_id):
        try:
            if not self.api_client:
                self.api_client = G2AApiClient()
                await self.api_client.get_token()
            
            result = await self.api_client.delete_offer(offer_id)
            
            if result.get('success'):
                QMessageBox.information(self, "Success", "✅ Offer deleted")
                await self.load_offers_from_api()
            else:
                QMessageBox.critical(self, "Error", result.get('error'))
        
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
    
    def view_offer_details(self, product_id):
        """Просмотр деталей"""
        if product_id in self.offers_cache:
            offer = self.offers_cache[product_id]
            auto_status = "🟢 ON" if self.auto_settings.is_product_allowed(product_id) else "🔴 OFF"
            
            details = f"""
📊 Offer Details

Product ID: {product_id}
Offer ID: {offer.get('id', 'N/A')}
Game: {offer.get('product_name', 'N/A')}
Price: €{offer.get('price', 'N/A')}
Stock: {offer.get('current_stock', 0)}
Status: {'Active' if offer.get('is_active') else 'Inactive'}
Auto-Price: {auto_status}
Type: {offer.get('offer_type', 'N/A')}
            """
            QMessageBox.information(self, "Offer Details", details)
    
    def show_auto_settings(self):
        """Показать настройки автоизменения"""
        # TODO: Создать диалог настроек
        settings_info = f"""
⚙️ Auto-Price Settings

Global Status: {'ON' if self.auto_settings.settings.get('enabled') else 'OFF'}
Competitor Offset: +€{self.auto_settings.settings.get('competitor_offset', 0.05)}
Min Price: €{self.auto_settings.settings.get('min_price', 0.1)}
Max Price: €{self.auto_settings.settings.get('max_price', 100)}
Daily Limit: {self.auto_settings.settings.get('daily_limit', 30)}
Protect Single Seller: {'YES' if self.auto_settings.settings.get('protect_single_seller') else 'NO'}

Offers with Auto-Price: {sum(1 for pid in self.offers_cache.keys() if self.auto_settings.is_product_allowed(pid))}
        """
        
        QMessageBox.information(self, "Auto-Price Settings", settings_info)
    
    def auto_refresh_offers(self):
        """Автоматическое обновление"""
        asyncio.create_task(self.load_offers_from_api())
        self.auto_refresh_label.setText("🔄 Auto-refreshed")
        QTimer.singleShot(2000, lambda: self.auto_refresh_label.setText("🔄 Auto-refresh: ON"))

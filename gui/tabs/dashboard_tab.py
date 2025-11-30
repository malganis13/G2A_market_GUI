#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Дашборд - главная панель статистики с автообновлением
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QGroupBox, QGridLayout, QPushButton, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont
from database import Database


class StatCard(QWidget):
    """Карточка со статистикой (компактная)"""
    
    def __init__(self, title, value, icon="", color="#0d7377"):
        super().__init__()
        self.init_ui(title, value, icon, color)
        
    def init_ui(self, title, value, icon, color):
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        self.setLayout(layout)
        
        # Стиль карточки (компактный)
        self.setStyleSheet(f"""
            StatCard {{
                background-color: #2d2d2d;
                border-left: 3px solid {color};
                border-radius: 4px;
                padding: 8px;
            }}
        """)
        
        # Иконка и заголовок
        header = QHBoxLayout()
        header.setSpacing(6)
        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 16pt;")
        header.addWidget(icon_label)
        
        title_label = QLabel(title)
        title_label.setStyleSheet("color: #a0a0a0; font-size: 9pt;")
        header.addWidget(title_label)
        header.addStretch()
        
        layout.addLayout(header)
        
        # Значение
        self.value_label = QLabel(str(value))
        self.value_label.setStyleSheet(f"color: {color}; font-size: 20pt; font-weight: bold;")
        layout.addWidget(self.value_label)
        
    def update_value(self, value):
        """Обновление значения"""
        self.value_label.setText(str(value))


class DashboardTab(QWidget):
    """Вкладка Dashboard с автообновлением"""
    
    refresh_requested = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.init_ui()
        self.load_stats()
        
        # Таймер автообновления (каждые 30 секунд)
        self.auto_refresh_timer = QTimer()
        self.auto_refresh_timer.timeout.connect(self.auto_refresh)
        self.auto_refresh_timer.start(30000)  # 30 секунд
        
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        self.setLayout(layout)
        
        # Заголовок с индикатором автообновления
        header_layout = QHBoxLayout()
        header = QLabel("📊 Dashboard")
        header.setProperty("class", "header")
        header_layout.addWidget(header)
        
        self.auto_refresh_label = QLabel("🔄 Auto-refresh: ON")
        self.auto_refresh_label.setStyleSheet("color: #4caf50; font-size: 9pt;")
        header_layout.addWidget(self.auto_refresh_label)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Кнопка обновления (компактная)
        refresh_btn = QPushButton("🔄 Refresh Now")
        refresh_btn.clicked.connect(self.refresh)
        refresh_btn.setMaximumWidth(120)
        refresh_btn.setMaximumHeight(30)
        layout.addWidget(refresh_btn)
        
        # Карточки статистики (2x3 сетка)
        stats_layout = QGridLayout()
        stats_layout.setSpacing(8)
        
        self.total_keys_card = StatCard("Total Keys", "0", "🔑", "#0d7377")
        self.available_keys_card = StatCard("Available", "0", "✅", "#4caf50")
        self.sold_keys_card = StatCard("Sold", "0", "💰", "#ff9800")
        self.active_offers_card = StatCard("Active Offers", "-", "📦", "#2196f3")
        self.total_games_card = StatCard("Total Games", "0", "🎮", "#9c27b0")
        self.inventory_value_card = StatCard("Value", "€0", "💵", "#00bcd4")
        
        stats_layout.addWidget(self.total_keys_card, 0, 0)
        stats_layout.addWidget(self.available_keys_card, 0, 1)
        stats_layout.addWidget(self.sold_keys_card, 0, 2)
        stats_layout.addWidget(self.active_offers_card, 1, 0)
        stats_layout.addWidget(self.total_games_card, 1, 1)
        stats_layout.addWidget(self.inventory_value_card, 1, 2)
        
        layout.addLayout(stats_layout)
        
        # Секция с играми (компактная)
        games_group = QGroupBox("📚 Games Overview")
        games_layout = QVBoxLayout()
        games_layout.setContentsMargins(8, 8, 8, 8)
        
        self.games_label = QLabel("Loading games...")
        self.games_label.setStyleSheet("padding: 6px; font-size: 9pt;")
        self.games_label.setWordWrap(True)
        games_layout.addWidget(self.games_label)
        
        games_group.setLayout(games_layout)
        layout.addWidget(games_group)
        
        # Секция с ценами (компактная)
        prices_group = QGroupBox("💵 Price Statistics")
        prices_layout = QVBoxLayout()
        prices_layout.setContentsMargins(8, 8, 8, 8)
        
        self.prices_label = QLabel("Loading price stats...")
        self.prices_label.setStyleSheet("padding: 6px; font-size: 9pt;")
        self.prices_label.setWordWrap(True)
        prices_layout.addWidget(self.prices_label)
        
        prices_group.setLayout(prices_layout)
        layout.addWidget(prices_group)
        
        # Последнее обновление
        self.last_update_label = QLabel("Last update: Never")
        self.last_update_label.setStyleSheet("color: #888; font-size: 8pt; padding: 4px;")
        layout.addWidget(self.last_update_label)
        
        layout.addStretch()
        
    def load_stats(self):
        """Загрузка полной статистики"""
        try:
            stats = self.db.get_keys_stats()
            
            # Обновляем карточки
            self.total_keys_card.update_value(stats.get('total', 0))
            self.available_keys_card.update_value(stats.get('available', 0))
            self.sold_keys_card.update_value(stats.get('sold', 0))
            
            # Получаем список игр
            games = self.db.get_games_list()
            self.total_games_card.update_value(len(games))
            
            # Обновляем информацию об играх
            if games:
                games_text = f"<b>Total games:</b> {len(games)}<br>"
                games_with_prices = sum(1 for g in games if g['min_price'] > 0)
                games_text += f"<b>Games with prices:</b> {games_with_prices}<br>"
                games_text += f"<b>Games without prices:</b> {len(games) - games_with_prices}<br>"
                
                # Топ-3 игры по количеству ключей
                top_games = sorted(games, key=lambda x: x['available_keys'], reverse=True)[:3]
                if top_games:
                    games_text += "<br><b>Top games by stock:</b><br>"
                    for i, game in enumerate(top_games, 1):
                        games_text += f"{i}. {game['name']}: {game['available_keys']} keys<br>"
                
                self.games_label.setText(games_text)
            else:
                self.games_label.setText("No games found. Add keys to get started.")
            
            # Статистика цен
            if games:
                prices = [g['min_price'] for g in games if g['min_price'] > 0]
                if prices:
                    avg_price = sum(prices) / len(prices)
                    min_price = min(prices)
                    max_price = max(prices)
                    total_value = sum(g['min_price'] * g['available_keys'] for g in games if g['min_price'] > 0)
                    
                    prices_text = f"<b>Average price:</b> €{avg_price:.2f}<br>"
                    prices_text += f"<b>Min price:</b> €{min_price:.2f}<br>"
                    prices_text += f"<b>Max price:</b> €{max_price:.2f}<br>"
                    prices_text += f"<b>Total inventory value:</b> €{total_value:.2f}<br>"
                    prices_text += f"<b>Priced games:</b> {len(prices)}/{len(games)}"
                    
                    self.prices_label.setText(prices_text)
                    self.inventory_value_card.update_value(f"€{total_value:.0f}")
                else:
                    self.prices_label.setText("No prices available. Run price parsing first.")
                    self.inventory_value_card.update_value("€0")
            else:
                self.prices_label.setText("No price data available.")
                self.inventory_value_card.update_value("€0")
            
            # Обновляем время последнего обновления
            from datetime import datetime
            now = datetime.now().strftime("%H:%M:%S")
            self.last_update_label.setText(f"Last update: {now}")
                
        except Exception as e:
            print(f"Error loading stats: {e}")
            import traceback
            traceback.print_exc()
    
    def refresh(self):
        """Ручное обновление статистики"""
        self.load_stats()
        self.refresh_requested.emit()
    
    def auto_refresh(self):
        """Автоматическое обновление (по таймеру)"""
        self.load_stats()
        self.auto_refresh_label.setText("🔄 Auto-refreshed")
        QTimer.singleShot(2000, lambda: self.auto_refresh_label.setText("🔄 Auto-refresh: ON"))
    
    def update_stats(self):
        """Обновление статистики (вызывается извне)"""
        self.load_stats()

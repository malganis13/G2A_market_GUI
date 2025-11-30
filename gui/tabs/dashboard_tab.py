#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Дашборд - главная панель статистики
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QGroupBox, QGridLayout, QPushButton
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from database import Database


class StatCard(QWidget):
    """Карточка со статистикой"""
    
    def __init__(self, title, value, icon="", color="#0d7377"):
        super().__init__()
        self.init_ui(title, value, icon, color)
        
    def init_ui(self, title, value, icon, color):
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Стиль карточки
        self.setStyleSheet(f"""
            StatCard {{
                background-color: #2d2d2d;
                border-left: 4px solid {color};
                border-radius: 6px;
                padding: 15px;
            }}
        """)
        
        # Иконка и заголовок
        header = QHBoxLayout()
        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 24pt;")
        header.addWidget(icon_label)
        
        title_label = QLabel(title)
        title_label.setStyleSheet("color: #a0a0a0; font-size: 10pt;")
        header.addWidget(title_label)
        header.addStretch()
        
        layout.addLayout(header)
        
        # Значение
        self.value_label = QLabel(str(value))
        self.value_label.setStyleSheet(f"color: {color}; font-size: 28pt; font-weight: bold;")
        layout.addWidget(self.value_label)
        
    def update_value(self, value):
        """Обновление значения"""
        self.value_label.setText(str(value))


class DashboardTab(QWidget):
    """Вкладка Dashboard"""
    
    refresh_requested = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.init_ui()
        self.load_stats()
        
    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Заголовок
        header = QLabel("📊 Dashboard")
        header.setProperty("class", "header")
        layout.addWidget(header)
        
        # Кнопка обновления
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.refresh)
        refresh_btn.setMaximumWidth(150)
        layout.addWidget(refresh_btn)
        
        # Карточки статистики
        stats_layout = QGridLayout()
        
        self.total_keys_card = StatCard("Total Keys", "0", "🔑", "#0d7377")
        self.available_keys_card = StatCard("Available Keys", "0", "✅", "#4caf50")
        self.sold_keys_card = StatCard("Sold Keys", "0", "💰", "#ff9800")
        self.active_offers_card = StatCard("Active Offers", "0", "📦", "#2196f3")
        
        stats_layout.addWidget(self.total_keys_card, 0, 0)
        stats_layout.addWidget(self.available_keys_card, 0, 1)
        stats_layout.addWidget(self.sold_keys_card, 1, 0)
        stats_layout.addWidget(self.active_offers_card, 1, 1)
        
        layout.addLayout(stats_layout)
        
        # Секция с играми
        games_group = QGroupBox("📚 Games Overview")
        games_layout = QVBoxLayout()
        
        self.games_label = QLabel("Loading games...")
        self.games_label.setStyleSheet("padding: 10px;")
        games_layout.addWidget(self.games_label)
        
        games_group.setLayout(games_layout)
        layout.addWidget(games_group)
        
        # Секция с ценами
        prices_group = QGroupBox("💵 Price Statistics")
        prices_layout = QVBoxLayout()
        
        self.prices_label = QLabel("Loading price stats...")
        self.prices_label.setStyleSheet("padding: 10px;")
        prices_layout.addWidget(self.prices_label)
        
        prices_group.setLayout(prices_layout)
        layout.addWidget(prices_group)
        
        layout.addStretch()
        
    def load_stats(self):
        """Загрузка статистики"""
        try:
            stats = self.db.get_keys_stats()
            
            # Обновляем карточки
            self.total_keys_card.update_value(stats.get('total', 0))
            self.available_keys_card.update_value(stats.get('available', 0))
            self.sold_keys_card.update_value(stats.get('sold', 0))
            
            # Получаем количество офферов (заглушка, нужна интеграция с API)
            self.active_offers_card.update_value("-")
            
            # Обновляем информацию об играх
            games = self.db.get_games_list()
            if games:
                games_text = f"<b>Total games:</b> {len(games)}<br>"
                games_with_prices = sum(1 for g in games if g['min_price'] > 0)
                games_text += f"<b>Games with prices:</b> {games_with_prices}<br>"
                games_text += f"<b>Games without prices:</b> {len(games) - games_with_prices}"
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
                    prices_text += f"<b>Total inventory value:</b> €{total_value:.2f}"
                    self.prices_label.setText(prices_text)
                else:
                    self.prices_label.setText("No prices available. Run price parsing first.")
            else:
                self.prices_label.setText("No price data available.")
                
        except Exception as e:
            print(f"Error loading stats: {e}")
    
    def refresh(self):
        """Обновление статистики"""
        self.load_stats()
        self.refresh_requested.emit()
    
    def update_stats(self):
        """Обновление статистики (вызывается таймером)"""
        self.load_stats()

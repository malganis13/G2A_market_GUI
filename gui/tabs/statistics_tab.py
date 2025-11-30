#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Вкладка статистики изменений цен
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QGroupBox
)
from PyQt6.QtCore import Qt
from database_improved import DatabaseImproved


class StatisticsTab(QWidget):
    """Вкладка статистики"""
    
    def __init__(self):
        super().__init__()
        self.db = DatabaseImproved()
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        self.setLayout(layout)
        
        # Заголовок
        header = QLabel("📊 Price Change Statistics")
        header.setProperty("class", "header")
        layout.addWidget(header)
        
        # Кнопки периодов
        period_group = QGroupBox("📅 Select Period")
        period_layout = QHBoxLayout()
        
        today_btn = QPushButton("🔥 Today")
        today_btn.clicked.connect(lambda: self.load_stats(1))
        today_btn.setMinimumHeight(50)
        period_layout.addWidget(today_btn)
        
        week_btn = QPushButton("📆 Last 7 Days")
        week_btn.clicked.connect(lambda: self.load_stats(7))
        week_btn.setMinimumHeight(50)
        period_layout.addWidget(week_btn)
        
        month_btn = QPushButton("📅 Last 30 Days")
        month_btn.clicked.connect(lambda: self.load_stats(30))
        month_btn.setMinimumHeight(50)
        period_layout.addWidget(month_btn)
        
        period_group.setLayout(period_layout)
        layout.addWidget(period_group)
        
        # Текстовое поле со статистикой
        self.stats_text = QTextEdit()
        self.stats_text.setReadOnly(True)
        self.stats_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #e0e0e0;
                font-family: 'Courier New', monospace;
                font-size: 9pt;
                border: 1px solid #444;
                border-radius: 5px;
                padding: 10px;
            }
        """)
        layout.addWidget(self.stats_text)
        
        # Информация
        info_label = QLabel("👉 Click on period buttons to view statistics")
        info_label.setStyleSheet("color: #888; font-size: 8pt;")
        layout.addWidget(info_label)
        
        # Загружаем статистику за сегодня по умолчанию
        self.load_stats(1)
    
    def load_stats(self, days: int):
        """Загрузить статистику за период"""
        try:
            stats = self.db.get_stats_for_period(days)
            
            # Очищаем и форматируем вывод
            self.stats_text.clear()
            
            output = f"""
╔════════════════════════════════════════════════════════╗
║  📊 PRICE CHANGE STATISTICS - {stats['period'].upper()}
╚════════════════════════════════════════════════════════╝

📊 SUMMARY:
─────────────────────────────────────────────────────────
    Total Changes:       {stats['total_changes']}
    📈 Price Increases:    {stats['price_increases']}
    📉 Price Decreases:    {stats['price_decreases']}
    💰 Average Change:     €{stats['avg_change']:.2f}
    💸 Total Change:       €{stats['total_change']:.2f}

"""
            
            # Топ игр
            if stats['top_changed_games']:
                output += """
╔════════════════════════════════════════════════════════╗
║  🎮 TOP 20 GAMES WITH MOST CHANGES
╚════════════════════════════════════════════════════════╝

"""
                
                for idx, game in enumerate(stats['top_changed_games'], 1):
                    avg_change = game['avg_change']
                    direction = "📈" if avg_change > 0 else "📉"
                    
                    output += f"""
{idx:2}. {game['game_name']}
    🔄 Changes: {game['change_count']}
    {direction} Avg Change: €{avg_change:.2f}
    💵 Total Change: €{game['total_change']:.2f}

"""
            
            # Последние изменения
            if stats['recent_changes']:
                output += """
╔════════════════════════════════════════════════════════╗
║  🕒 RECENT CHANGES (Last 50)
╚════════════════════════════════════════════════════════╝

"""
                
                # Показываем последние 50 (от новых к старым)
                recent = stats['recent_changes'][::-1][:50]  # Разворачиваем и берем 50
                
                for change in recent:
                    timestamp = change.get('timestamp', '').split('T')
                    date = timestamp[0] if len(timestamp) > 0 else 'N/A'
                    time = timestamp[1].split('.')[0] if len(timestamp) > 1 else 'N/A'
                    
                    direction = "📈" if change['change'] > 0 else "📉"
                    
                    output += f"""
🕒 {date} {time}
    {direction} {change.get('game_name', 'Unknown')}
    Old: €{change['old_price']:.2f} → New: €{change['new_price']:.2f}
    Change: €{change['change']:.2f} ({change.get('change_percent', 0):.1f}%)
    Reason: {change.get('reason', 'N/A')}
─────────────────────────────────────────────────────────
"""
            
            self.stats_text.setPlainText(output)
        
        except Exception as e:
            error_msg = f"""
❌ ERROR LOADING STATISTICS

Error: {str(e)}

Possible reasons:
1. No price changes recorded yet
2. Database file missing
3. JSON stats file corrupted

Make some price changes first!
            """
            self.stats_text.setPlainText(error_msg)
            import traceback
            traceback.print_exc()

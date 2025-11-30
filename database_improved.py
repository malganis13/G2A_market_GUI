#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Улучшенная база данных со статистикой изменений цен
"""

import sqlite3
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional


class DatabaseImproved:
    """Улучшенная база данных"""
    
    def __init__(self, db_file="keys.db", stats_file="price_changes_stats.json"):
        self.db_file = db_file
        self.stats_file = stats_file
        self.conn = sqlite3.connect(db_file, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.create_tables()
    
    def create_tables(self):
        """Создание таблиц"""
        cursor = self.conn.cursor()
        
        # Таблица ключей
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_name TEXT NOT NULL,
                key_value TEXT NOT NULL UNIQUE,
                status TEXT DEFAULT 'available',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                sold_at TIMESTAMP,
                price_sold REAL
            )
        """)
        
        # Таблица цен
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS game_prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_name TEXT NOT NULL,
                product_id TEXT,
                min_price REAL,
                max_price REAL,
                avg_price REAL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Индексы
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_game_name ON keys(game_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON keys(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_game_prices ON game_prices(game_name)")
        
        self.conn.commit()
    
    # ==================== СТАТИСТИКА ИЗМЕНЕНИЙ ЦЕН ====================
    
    def save_price_change(self, product_id: str, old_price: float, new_price: float, 
                          market_price: float, reason: str = "manual", game_name: str = "") -> bool:
        """
        ✅ Сохранить изменение цены в JSON файл
        
        Args:
            product_id: G2A Product ID
            old_price: Старая цена
            new_price: Новая цена
            market_price: Рыночная цена
            reason: Причина (автоизменение, manual, и т.д.)
            game_name: Название игры
        
        Returns:
            True если успешно
        """
        try:
            # Загружаем существующую статистику
            if os.path.exists(self.stats_file):
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    stats = json.load(f)
            else:
                stats = []
            
            # Добавляем новую запись
            stats.append({
                "timestamp": datetime.now().isoformat(),
                "product_id": str(product_id),
                "game_name": game_name,
                "old_price": float(old_price),
                "new_price": float(new_price),
                "market_price": float(market_price),
                "change": round(float(new_price) - float(old_price), 2),
                "change_percent": round(((float(new_price) - float(old_price)) / float(old_price) * 100) if old_price > 0 else 0, 2),
                "reason": reason
            })
            
            # Сохраняем
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(stats, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Статистика сохранена: {product_id} €{old_price} → €{new_price}")
            return True
        
        except Exception as e:
            print(f"❌ Ошибка сохранения статистики: {e}")
            return False
    
    def get_stats_for_period(self, days: int = 1) -> Dict:
        """
        ✅ Получить статистику за период
        
        Args:
            days: Количество дней (1 = сегодня, 7 = неделя, 30 = месяц)
        
        Returns:
            Словарь со статистикой
        """
        try:
            if not os.path.exists(self.stats_file):
                return self._empty_stats()
            
            with open(self.stats_file, 'r', encoding='utf-8') as f:
                all_stats = json.load(f)
            
            # Фильтруем по дате
            cutoff_date = datetime.now() - timedelta(days=days)
            recent_stats = [
                s for s in all_stats
                if datetime.fromisoformat(s.get("timestamp", "")) > cutoff_date
            ]
            
            if not recent_stats:
                return self._empty_stats()
            
            # Рассчитываем статистику
            increases = sum(1 for s in recent_stats if s["change"] > 0)
            decreases = sum(1 for s in recent_stats if s["change"] < 0)
            total_change = sum(s["change"] for s in recent_stats)
            avg_change = total_change / len(recent_stats) if recent_stats else 0
            
            # Топ игр с наибольшими изменениями
            game_changes = {}
            for s in recent_stats:
                game_name = s.get("game_name", "Unknown")
                if game_name not in game_changes:
                    game_changes[game_name] = []
                game_changes[game_name].append(s)
            
            top_games = sorted(
                game_changes.items(),
                key=lambda x: len(x[1]),
                reverse=True
            )[:20]
            
            top_changed_games = []
            for game_name, changes in top_games:
                top_changed_games.append({
                    "game_name": game_name,
                    "change_count": len(changes),
                    "total_change": sum(c["change"] for c in changes),
                    "avg_change": sum(c["change"] for c in changes) / len(changes)
                })
            
            return {
                "period": f"last {days} day(s)",
                "total_changes": len(recent_stats),
                "price_increases": increases,
                "price_decreases": decreases,
                "avg_change": round(avg_change, 2),
                "total_change": round(total_change, 2),
                "top_changed_games": top_changed_games,
                "recent_changes": recent_stats[-50:]  # Последние 50
            }
        
        except Exception as e:
            print(f"❌ Ошибка получения статистики: {e}")
            return self._empty_stats()
    
    def _empty_stats(self) -> Dict:
        """Пустая статистика"""
        return {
            "period": "N/A",
            "total_changes": 0,
            "price_increases": 0,
            "price_decreases": 0,
            "avg_change": 0,
            "total_change": 0,
            "top_changed_games": [],
            "recent_changes": []
        }
    
    # ==================== КЛЮЧИ ====================
    
    def add_key(self, game_name: str, key_value: str) -> bool:
        """Добавить ключ"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO keys (game_name, key_value, status)
                VALUES (?, ?, 'available')
            """, (game_name, key_value))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        except Exception as e:
            print(f"❌ Ошибка добавления ключа: {e}")
            return False
    
    def get_games_list(self) -> List[Dict]:
        """Получить список игр"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT 
                game_name,
                COUNT(*) as total_keys,
                SUM(CASE WHEN status = 'available' THEN 1 ELSE 0 END) as available_keys,
                SUM(CASE WHEN status = 'sold' THEN 1 ELSE 0 END) as sold_keys
            FROM keys
            GROUP BY game_name
            ORDER BY total_keys DESC
        """)
        
        games = []
        for row in cursor.fetchall():
            # Получаем цены
            price_cursor = self.conn.cursor()
            price_cursor.execute("""
                SELECT min_price, max_price, avg_price
                FROM game_prices
                WHERE game_name = ?
                ORDER BY updated_at DESC
                LIMIT 1
            """, (row['game_name'],))
            
            price_row = price_cursor.fetchone()
            
            games.append({
                'name': row['game_name'],
                'total_keys': row['total_keys'],
                'available_keys': row['available_keys'],
                'sold_keys': row['sold_keys'],
                'min_price': price_row['min_price'] if price_row else 0,
                'max_price': price_row['max_price'] if price_row else 0,
                'avg_price': price_row['avg_price'] if price_row else 0
            })
        
        return games
    
    def get_keys_stats(self) -> Dict:
        """Получить общую статистику ключей"""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'available' THEN 1 ELSE 0 END) as available,
                SUM(CASE WHEN status = 'sold' THEN 1 ELSE 0 END) as sold,
                SUM(CASE WHEN status = 'reserved' THEN 1 ELSE 0 END) as reserved,
                COUNT(DISTINCT game_name) as total_games
            FROM keys
        """)
        
        row = cursor.fetchone()
        
        return {
            'total': row['total'] or 0,
            'available': row['available'] or 0,
            'sold': row['sold'] or 0,
            'reserved': row['reserved'] or 0,
            'total_games': row['total_games'] or 0
        }
    
    def update_price(self, game_name: str, product_id: str, min_price: float, 
                     max_price: float, avg_price: float):
        """Обновить цену игры"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO game_prices (game_name, product_id, min_price, max_price, avg_price)
                VALUES (?, ?, ?, ?, ?)
            """, (game_name, product_id, min_price, max_price, avg_price))
            self.conn.commit()
        except Exception as e:
            print(f"❌ Ошибка обновления цены: {e}")
    
    def close(self):
        """Закрыть соединение"""
        self.conn.close()

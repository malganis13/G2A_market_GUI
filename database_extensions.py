#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Расширения для database.py - дополнительные методы
"""

import sqlite3
from pathlib import Path


class DatabaseExtensions:
    """Дополнительные методы для базы данных"""
    
    def __init__(self, db_path="keys.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Инициализация базы данных"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Таблица ключей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_name TEXT NOT NULL,
                key_code TEXT NOT NULL UNIQUE,
                platform TEXT DEFAULT 'Steam',
                region TEXT DEFAULT 'Global',
                price REAL DEFAULT 0.0,
                status TEXT DEFAULT 'available',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                sold_at TIMESTAMP
            )
        ''')
        
        # Индексы
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_game_name ON keys(game_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_status ON keys(status)')
        
        conn.commit()
        conn.close()
    
    def get_all_keys(self):
        """Получение всех ключей"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM keys ORDER BY created_at DESC
        ''')
        
        keys = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return keys
    
    def get_keys_by_game(self, game_name):
        """Получение ключей по названию игры"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM keys WHERE game_name = ? AND status = 'available'
        ''', (game_name,))
        
        keys = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return keys
    
    def delete_key(self, key_id):
        """Удаление ключа"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM keys WHERE id = ?', (key_id,))
        
        conn.commit()
        conn.close()
    
    def update_key_price(self, key_id, price):
        """Обновление цены ключа"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE keys SET price = ? WHERE id = ?
        ''', (price, key_id))
        
        conn.commit()
        conn.close()
    
    def mark_key_as_sold(self, key_id):
        """Отметить ключ как проданный"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE keys 
            SET status = 'sold', sold_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        ''', (key_id,))
        
        conn.commit()
        conn.close()

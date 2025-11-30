import sqlite3
import datetime
from pathlib import Path

try:
    from g2a_config import DATABASE_FILE, PRICE_EXPIRY_DAYS
except ImportError:
    DATABASE_FILE = "g2a_data.db"
    PRICE_EXPIRY_DAYS = 7


class Database:
    """Основной класс для работы с базой данных ключей"""
    
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
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_key_code ON keys(key_code)')
        
        conn.commit()
        conn.close()
    
    def add_key(self, game_name, key_code, platform="Steam", region="Global"):
        """Добавление ключа"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO keys (game_name, key_code, platform, region)
                VALUES (?, ?, ?, ?)
            ''', (game_name, key_code, platform, region))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            raise Exception(f"Key {key_code} already exists in database")
        finally:
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
    
    def get_keys_stats(self):
        """Получение статистики ключей"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Общее количество
        cursor.execute('SELECT COUNT(*) FROM keys')
        total = cursor.fetchone()[0]
        
        # Доступные
        cursor.execute('SELECT COUNT(*) FROM keys WHERE status = "available"')
        available = cursor.fetchone()[0]
        
        # Проданные
        cursor.execute('SELECT COUNT(*) FROM keys WHERE status = "sold"')
        sold = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total': total,
            'available': available,
            'sold': sold
        }
    
    def get_games_list(self):
        """Получение списка игр с количеством ключей"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                game_name as name,
                COUNT(*) as total_keys,
                SUM(CASE WHEN status = 'available' THEN 1 ELSE 0 END) as available_keys,
                MIN(CASE WHEN price > 0 THEN price ELSE NULL END) as min_price,
                MAX(price) as max_price,
                AVG(CASE WHEN price > 0 THEN price ELSE NULL END) as avg_price
            FROM keys
            GROUP BY game_name
            ORDER BY game_name
        ''')
        
        games = []
        for row in cursor.fetchall():
            games.append({
                'name': row['name'],
                'total_keys': row['total_keys'],
                'available_keys': row['available_keys'],
                'min_price': row['min_price'] if row['min_price'] else 0.0,
                'max_price': row['max_price'] if row['max_price'] else 0.0,
                'avg_price': row['avg_price'] if row['avg_price'] else 0.0
            })
        
        conn.close()
        return games
    
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
    
    def set_prices_from_file(self, file_path):
        """Обновление цен из файла result"""
        updated_count = 0
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    # Формат: Game Name | Price
                    parts = [p.strip() for p in line.split('|')]
                    if len(parts) >= 2:
                        game_name = parts[0]
                        try:
                            price = float(parts[1].replace('€', '').replace('$', '').strip())
                            
                            # Обновляем цену для всех ключей этой игры
                            conn = sqlite3.connect(self.db_path)
                            cursor = conn.cursor()
                            
                            cursor.execute('''
                                UPDATE keys SET price = ? WHERE game_name = ?
                            ''', (price, game_name))
                            
                            updated_count += cursor.rowcount
                            conn.commit()
                            conn.close()
                            
                        except ValueError:
                            continue
            
            return updated_count
            
        except Exception as e:
            print(f"Error updating prices from file: {e}")
            return 0


class PriceDatabase:
    """Класс для работы с ценами (совместимость со старым кодом)"""
    
    def __init__(self):
        self.conn = sqlite3.connect(DATABASE_FILE)
        self.create_tables()

    def create_tables(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                price REAL,
                region TEXT,
                date TIMESTAMP
            )
        """)

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS product_ids (
                id TEXT PRIMARY KEY,
                name TEXT,
                g2a_id TEXT,
                region TEXT DEFAULT 'GLOBAL',
                date TIMESTAMP
            )
        """)

        try:
            self.conn.execute("ALTER TABLE product_ids ADD COLUMN region TEXT DEFAULT 'GLOBAL'")
            self.conn.commit()
        except:
            pass

        self.conn.commit()

    def get_price(self, name, region="GLOBAL"):
        cursor = self.conn.execute("""
            SELECT price, date FROM prices 
            WHERE name = ? AND region = ?
        """, (name, region))

        result = cursor.fetchone()
        if not result:
            return None

        price, date_str = result
        stored_date = datetime.datetime.fromisoformat(date_str)
        now = datetime.datetime.now()

        if (now - stored_date).days < PRICE_EXPIRY_DAYS:
            return price
        else:
            return None

    def save_price(self, name, price, region="GLOBAL"):
        now = datetime.datetime.now().isoformat()

        self.conn.execute("""
            INSERT OR REPLACE INTO prices (name, price, region, date)
            VALUES (?, ?, ?, ?)
        """, (name, price, region, now))
        self.conn.commit()

    def get_g2a_id(self, name, region="GLOBAL"):
        cursor = self.conn.execute("""
            SELECT g2a_id, date FROM product_ids 
            WHERE name = ? AND region = ?
        """, (name, region))

        result = cursor.fetchone()
        if not result:
            return None

        g2a_id, date_str = result
        stored_date = datetime.datetime.fromisoformat(date_str)
        now = datetime.datetime.now()

        if (now - stored_date).days < PRICE_EXPIRY_DAYS:
            return g2a_id
        else:
            return None

    def save_g2a_id(self, name, g2a_id, region="GLOBAL"):
        now = datetime.datetime.now().isoformat()

        unique_id = f"{name}_{region}"

        self.conn.execute("""
            INSERT OR REPLACE INTO product_ids (id, name, g2a_id, region, date)
            VALUES (?, ?, ?, ?, ?)
        """, (unique_id, name, g2a_id, region, now))
        self.conn.commit()

    def close(self):
        self.conn.close()

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from fastapi import Response
import sqlite3
from datetime import datetime, timedelta
import secrets
import logging
from typing import Optional, List
import os
import uuid
from telegram_notifier import notifier
import asyncio
from fastapi import Header
from typing import Optional



# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="G2A Merchant API",
    version="1.0.0",
    description="G2A-совместимый API для dropshipping согласно официальной спецификации"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

# Конфигурация
from g2a_config import SERVER_CLIENT_SECRET,SERVER_CLIENT_ID,DATABASE_FILE
CLIENT_ID = SERVER_CLIENT_ID
CLIENT_SECRET = SERVER_CLIENT_SECRET

# Активные токены
active_tokens = {}


# Модели данных согласно G2A спецификации
class TokenRequest(BaseModel):
    grant_type: str
    client_id: str
    client_secret: str


class ReservationItem(BaseModel):
    product_id: int = Field(..., ge=10000000000000, le=99999999999999)  # 14 digits
    quantity: int = Field(..., ge=1)


class OrderRequest(BaseModel):
    reservation_id: str = Field(..., min_length=1, max_length=36)
    g2a_order_id: int = Field(..., ge=10000000000000)


class StockItem(BaseModel):
    product_id: int
    inventory_size: int


class InventoryItem(BaseModel):
    id: str = Field(..., min_length=1, max_length=36)
    value: str
    kind: Optional[str] = "text"  # text, file, account


class InventoryProduct(BaseModel):
    product_id: int
    inventory_size: int
    inventory: List[InventoryItem]


def get_db_connection():
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()

    # Таблица ключей
    cursor.execute("""
            CREATE TABLE IF NOT EXISTS keys (
                id TEXT PRIMARY KEY,
                game_name TEXT NOT NULL,
                product_id INTEGER,
                key_value TEXT UNIQUE NOT NULL,
                status TEXT DEFAULT 'available',
                price REAL,
                prefix TEXT DEFAULT 'sks',
                reserved_at TIMESTAMP,
                sold_at TIMESTAMP,
                reservation_id TEXT,
                order_id TEXT,
                selling_price REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

    # Таблица резерваций
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reservations (
            id TEXT PRIMARY KEY,
            reservation_id TEXT UNIQUE NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            status TEXT DEFAULT 'active',
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Таблица заказов
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id TEXT PRIMARY KEY,
            order_id TEXT UNIQUE NOT NULL,
            reservation_id TEXT NOT NULL,
            g2a_order_id INTEGER NOT NULL,
            status TEXT DEFAULT 'created',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS price_changes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            game_name TEXT NOT NULL,
            old_price REAL NOT NULL,
            new_price REAL NOT NULL,
            market_price REAL NOT NULL,
            change_reason TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_price_changes_date
        ON price_changes(created_at)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_price_changes_product
        ON price_changes(product_id)
    """)

    conn.commit()
    conn.close()


def generate_token():
    return secrets.token_urlsafe(32)

def verify_admin_key(x_api_key: Optional[str] = Header(None)):
    """Проверка админского API ключа"""
    from g2a_config import ADMIN_API_KEY

    if not x_api_key or x_api_key != ADMIN_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "Invalid or missing admin API key"}
        )
    return x_api_key


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials

    if token not in active_tokens:
        raise HTTPException(
            status_code=401,
            detail={"code": "INVALID_TOKEN", "message": "Invalid or expired token"}
        )

    token_data = active_tokens[token]
    if datetime.now() > token_data["expires_at"]:
        del active_tokens[token]
        raise HTTPException(
            status_code=401,
            detail={"code": "TOKEN_EXPIRED", "message": "Token has expired"}
        )

    return token

# OAuth токен endpoint
@app.get("/oauth/token")
async def get_access_token(
        grant_type: str,
        client_id: str,
        client_secret: str
):
    """Получение токена доступа согласно G2A спецификации"""
    logger.info(f"Token request from client: {client_id}")

    if (client_id != CLIENT_ID or
            client_secret != CLIENT_SECRET or
            grant_type != "client_credentials"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "INVALID_CREDENTIALS", "message": "Invalid credentials"}
        )

    access_token = generate_token()
    expires_in = 3600

    active_tokens[access_token] = {
        "expires_at": datetime.now() + timedelta(seconds=expires_in),
        "client_id": client_id
    }

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": expires_in
    }


# Создание резервации
@app.post("/reservation")
async def create_reservation(
        reservation_data: List[ReservationItem],
        token: str = Depends(verify_token)
):
    """Создание резервации согласно G2A спецификации"""
    reservation_id = str(uuid.uuid4())
    logger.info(f"Creating reservation: {reservation_id}")

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        stock_response = []
        expires_at = datetime.now() + timedelta(minutes=30)

        for item in reservation_data:
            product_id = item.product_id
            quantity = item.quantity

            # Проверка наличия ключей
            cursor.execute("""
                SELECT COUNT(*) as available_count
                FROM keys 
                WHERE product_id = ? AND status = 'available'
            """, (product_id,))

            result = cursor.fetchone()
            available = result['available_count'] if result else 0

            if available < quantity:
                # НЕ закрываем соединение здесь
                raise HTTPException(
                    status_code=400,
                    detail={
                        "code": "INSUFFICIENT_STOCK",
                        "message": f"Not enough stock for product {product_id}. Available: {available}, requested: {quantity}",
                        "stock": [{"product_id": product_id, "inventory_size": available}]
                    }
                )

            # Резервация ключей
            cursor.execute("""
                SELECT id FROM keys 
                WHERE product_id = ? AND status = 'available' 
                LIMIT ?
            """, (product_id, quantity))

            keys_to_reserve = cursor.fetchall()
            key_ids = [key['id'] for key in keys_to_reserve]

            # Обновление статуса ключей
            for key_id in key_ids:
                cursor.execute("""
                    UPDATE keys 
                    SET status = 'reserved', 
                        reserved_at = CURRENT_TIMESTAMP,
                        reservation_id = ?
                    WHERE id = ?
                """, (reservation_id, key_id))

            # Создание записи резервации
            cursor.execute("""
                INSERT INTO reservations (id, reservation_id, product_id, quantity, expires_at)
                VALUES (?, ?, ?, ?, ?)
            """, (str(uuid.uuid4()), reservation_id, product_id, quantity, expires_at))

            # Добавление в ответ
            cursor.execute("""
                SELECT COUNT(*) as total_available
                FROM keys 
                WHERE product_id = ? AND status = 'available'
            """, (product_id,))

            remaining_result = cursor.fetchone()
            remaining_stock = remaining_result['total_available'] if remaining_result else 0

            stock_response.append({
                "product_id": product_id,
                "inventory_size": remaining_stock
            })

        conn.commit()
        conn.close()

        return {
            "reservation_id": reservation_id,
            "stock": stock_response
        }

    except HTTPException:
        conn.rollback()
        conn.close()
        raise
    except Exception as e:
        conn.rollback()
        conn.close()
        logger.error(f"Error creating reservation: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"code": "INTERNAL_ERROR", "message": "Internal server error"}
        )

# Создание заказа
@app.post("/order")
async def create_order(
        order_data: OrderRequest,
        token: str = Depends(verify_token)
):
    """Создание заказа согласно G2A спецификации"""
    order_id = str(uuid.uuid4())
    logger.info(f"Creating order: {order_id}")

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Проверка резервации
        cursor.execute("""
            SELECT * FROM reservations 
            WHERE reservation_id = ? AND status = 'active'
        """, (order_data.reservation_id,))

        reservations = cursor.fetchall()
        if not reservations:
            raise HTTPException(
                status_code=404,
                detail={"code": "RESERVATION_NOT_FOUND", "message": "Reservation not found or expired"}
            )

        # Проверка срока резервации
        current_time = datetime.now()
        for reservation in reservations:
            expires_at = datetime.fromisoformat(reservation['expires_at'])
            if expires_at < current_time:
                raise HTTPException(
                    status_code=410,
                    detail={"code": "RESERVATION_EXPIRED", "message": "Reservation expired"}
                )

        # Создание заказа
        cursor.execute("""
            INSERT INTO orders (id, order_id, reservation_id, g2a_order_id)
            VALUES (?, ?, ?, ?)
        """, (str(uuid.uuid4()), order_id, order_data.reservation_id, order_data.g2a_order_id))

        # Получение инвентаря для ответа
        stock_response = []

        # Список для уведомлений
        sold_keys_info = []

        for reservation in reservations:
            product_id = reservation['product_id']
            quantity = reservation['quantity']

            # Получение зарезервированных ключей
            cursor.execute("""
                SELECT id, key_value FROM keys 
                WHERE reservation_id = ? AND product_id = ? AND status = 'reserved'
                LIMIT ?
            """, (order_data.reservation_id, product_id, quantity))

            reserved_keys = cursor.fetchall()

            inventory_items = []
            for key in reserved_keys:
                inventory_items.append({
                    "id": key['id'],
                    "value": key['key_value'],
                    "kind": "text"
                })

                # Получаем полную информацию о ключе для уведомления
                cursor.execute("""
                    SELECT game_name, price, prefix FROM keys 
                    WHERE id = ?
                """, (key['id'],))

                key_info = cursor.fetchone()
                if key_info:
                    sold_keys_info.append({
                        'game_name': key_info['game_name'],
                        'key_value': key['key_value'],
                        'price': key_info['price'] or 0,
                        'prefix': key_info['prefix'] or 'unknown'
                    })

                # Обновление статуса ключа на "продано"
                cursor.execute("""
                    UPDATE keys 
                    SET status = 'sold', 
                        sold_at = CURRENT_TIMESTAMP,
                        order_id = ?
                    WHERE id = ?
                """, (order_id, key['id']))

            # Подсчет оставшегося инвентаря
            cursor.execute("""
                SELECT COUNT(*) as remaining
                FROM keys 
                WHERE product_id = ? AND status = 'available'
            """, (product_id,))

            remaining_result = cursor.fetchone()
            remaining = remaining_result['remaining'] if remaining_result else 0

            stock_response.append({
                "product_id": product_id,
                "inventory_size": remaining,
                "inventory": inventory_items
            })

        # Обновление статуса резервации
        cursor.execute("""
            UPDATE reservations 
            SET status = 'completed' 
            WHERE reservation_id = ?
        """, (order_data.reservation_id,))

        conn.commit()
        conn.close()

        # Отправляем уведомления в Telegram асинхронно
        for key_data in sold_keys_info:
            asyncio.create_task(notifier.send_sale_notification(
                game_name=key_data['game_name'],
                key_value=key_data['key_value'],
                price=key_data['price'],
                prefix=key_data['prefix']
            ))

        logger.info(f"Order {order_id} created successfully, {len(sold_keys_info)} keys sold")

        return {
            "order_id": order_id,
            "stock": stock_response
        }

    except HTTPException:
        conn.rollback()
        conn.close()
        raise
    except Exception as e:
        conn.rollback()
        conn.close()
        logger.error(f"Error creating order: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"code": "INTERNAL_ERROR", "message": "Internal server error"}
        )


# Получение инвентаря заказа
@app.get("/order/{order_id}/inventory")
async def get_inventory_from_order(
        order_id: str,
        token: str = Depends(verify_token)
):
    """Получение инвентаря заказа согласно G2A спецификации"""
    logger.info(f"Getting inventory for order: {order_id}")

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Проверка существования заказа
        cursor.execute("""
            SELECT reservation_id FROM orders 
            WHERE order_id = ?
        """, (order_id,))

        order = cursor.fetchone()
        if not order:
            raise HTTPException(
                status_code=404,
                detail={"code": "ORDER_NOT_FOUND", "message": "Order not found"}
            )

        # Получение всех ключей заказа, сгруппированных по продуктам
        cursor.execute("""
            SELECT DISTINCT product_id FROM keys 
            WHERE order_id = ?
        """, (order_id,))

        products = cursor.fetchall()
        inventory_response = []

        for product in products:
            product_id = product['product_id']

            # Получение ключей для этого продукта
            cursor.execute("""
                SELECT id, key_value FROM keys 
                WHERE order_id = ? AND product_id = ?
            """, (order_id, product_id))

            keys = cursor.fetchall()

            inventory_items = []
            for key in keys:
                inventory_items.append({
                    "id": key['id'],
                    "value": key['key_value'],
                    "kind": "text"
                })

            # Подсчет оставшегося инвентаря
            cursor.execute("""
                SELECT COUNT(*) as remaining
                FROM keys 
                WHERE product_id = ? AND status = 'available'
            """, (product_id,))

            remaining_result = cursor.fetchone()
            remaining = remaining_result['remaining'] if remaining_result else 0

            inventory_response.append({
                "product_id": product_id,
                "inventory_size": remaining,
                "inventory": inventory_items
            })

        conn.close()
        return inventory_response

    except HTTPException:
        conn.close()
        raise
    except Exception as e:
        conn.close()
        logger.error(f"Error getting inventory: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"code": "INTERNAL_ERROR", "message": "Internal server error"}
        )


@app.delete("/reservation/{reservation_id}")
async def release_reservation(
    reservation_id: str,
    token: str = Depends(verify_token)
):
    """Отмена резервации согласно G2A спецификации"""
    logger.info(f"Releasing reservation: {reservation_id}")

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Проверка существования резервации
        cursor.execute("""
            SELECT id FROM reservations 
            WHERE reservation_id = ? AND status = 'active'
        """, (reservation_id,))

        if not cursor.fetchone():
            raise HTTPException(
                status_code=404,
                detail={"code": "RESERVATION_NOT_FOUND", "message": "Active reservation not found"}
            )

        # Освобождение зарезервированных ключей
        cursor.execute("""
            UPDATE keys 
            SET status = 'available', 
                reserved_at = NULL,
                reservation_id = NULL
            WHERE reservation_id = ? AND status = 'reserved'
        """, (reservation_id,))

        # Обновление статуса резервации
        cursor.execute("""
            UPDATE reservations 
            SET status = 'cancelled' 
            WHERE reservation_id = ?
        """, (reservation_id,))

        conn.commit()
        conn.close()

        return Response(status_code=204)

    except HTTPException:
        conn.rollback()
        conn.close()
        raise
    except Exception as e:
        conn.rollback()
        conn.close()
        logger.error(f"Error releasing reservation: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"code": "INTERNAL_ERROR", "message": "Internal server error"}
        )

@app.get("/healthcheck")
async def health_check(token: str = Depends(verify_token)):
    return Response(status_code=204)

@app.post("/admin/keys")
async def add_keys(
    keys_data: List[dict],
    admin_key: str = Depends(verify_admin_key)
):
    """Добавление ключей в базу с префиксом (требует админский ключ)"""
    conn = get_db_connection()
    cursor = conn.cursor()

    added_count = 0
    errors = []

    for key_info in keys_data:
        try:
            key_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO keys (id, game_name, product_id, key_value, price, prefix)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                key_id,
                key_info.get('game_name', 'Unknown Game'),
                key_info.get('product_id'),
                key_info.get('key_value', ''),
                key_info.get('price', 0.0),
                key_info.get('prefix', 'sks')
            ))
            added_count += 1

        except sqlite3.IntegrityError as e:
            errors.append(f"Duplicate key: {key_info.get('key_value', 'unknown')}")
            continue
        except Exception as e:
            errors.append(f"Error with key {key_info.get('key_value', 'unknown')}: {str(e)}")
            continue

    conn.commit()
    conn.close()

    result = {"message": f"Added {added_count} keys"}
    if errors:
        result["errors"] = errors

    return result


@app.get("/admin/stats")
async def get_stats(admin_key: str = Depends(verify_admin_key)):
    """Статистика (требует админский ключ)"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            status,
            COUNT(*) as count,
            COUNT(DISTINCT prefix) as unique_prefixes
        FROM keys
        GROUP BY status
    """)

    stats = {}
    for row in cursor.fetchall():
        stats[row['status']] = {
            'count': row['count'],
            'unique_prefixes': row['unique_prefixes']
        }

    # Добавим статистику по префиксам
    cursor.execute("""
        SELECT
            prefix,
            COUNT(*) as total,
            SUM(CASE WHEN status = 'sold' THEN 1 ELSE 0 END) as sold,
            SUM(CASE WHEN status = 'sold' THEN price ELSE 0 END) as revenue
        FROM keys
        GROUP BY prefix
    """)

    prefix_stats = {}
    for row in cursor.fetchall():
        prefix_stats[row['prefix']] = {
            'total': row['total'],
            'sold': row['sold'],
            'revenue': row['revenue'] or 0
        }

    conn.close()

    return {
        "key_statistics": stats,
        "prefix_statistics": prefix_stats
    }


@app.get("/admin/keys/by-product/{product_id}")
async def get_keys_by_product(
    product_id: int,
    exclude_sold: bool = False,
    admin_key: str = Depends(verify_admin_key)
):
    """Получение всех ключей по product_id (требует админский ключ)"""
    conn = get_db_connection()
    cursor = conn.cursor()

    if exclude_sold:
        cursor.execute("""
            SELECT id, game_name, key_value, status, price
            FROM keys
            WHERE product_id = ? AND status != 'sold'
        """, (product_id,))
    else:
        cursor.execute("""
            SELECT id, game_name, key_value, status, price
            FROM keys
            WHERE product_id = ?
        """, (product_id,))

    keys = cursor.fetchall()
    conn.close()

    result = []
    for key in keys:
        result.append({
            'id': key['id'],
            'game_name': key['game_name'],
            'key_value': key['key_value'],
            'status': key['status'],
            'price': key['price']
        })

    return {"keys": result, "count": len(result)}


@app.patch("/admin/keys/status")
async def update_keys_status(
    data: dict,
    admin_key: str = Depends(verify_admin_key)
):
    """Обновление статуса ключей (требует админский ключ)"""
    key_ids = data.get('key_ids', [])
    new_status = data.get('new_status')

    valid_statuses = ['available', 'reserved', 'sold', 'removed_from_sale']

    if new_status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail={"code": "INVALID_STATUS", "message": f"Status must be one of: {valid_statuses}"}
        )

    if not key_ids:
        raise HTTPException(
            status_code=400,
            detail={"code": "EMPTY_KEY_IDS", "message": "key_ids cannot be empty"}
        )

    conn = get_db_connection()
    cursor = conn.cursor()

    updated_count = 0
    for key_id in key_ids:
        cursor.execute("""
            UPDATE keys
            SET status = ?
            WHERE id = ?
        """, (new_status, key_id))
        updated_count += cursor.rowcount

    conn.commit()
    conn.close()

    return {
        "message": f"Updated {updated_count} keys to status '{new_status}'",
        "updated_count": updated_count
    }


@app.get("/admin/price-stats")
async def get_price_stats(
    period: str = "day",
    admin_key: str = Depends(verify_admin_key)
):
    """Статистика изменений цен (day/week/month)"""
    conn = get_db_connection()
    cursor = conn.cursor()

    now = datetime.now()
    if period == "day":
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        period_name = "Today"
    elif period == "week":
        start_date = now - timedelta(days=7)
        period_name = "Last 7 days"
    elif period == "month":
        start_date = now - timedelta(days=30)
        period_name = "Last 30 days"
    else:
        raise HTTPException(status_code=400, detail="Invalid period. Use: day, week, month")

    cursor.execute("""
        SELECT
            COUNT(*) as total_changes,
            SUM(CASE WHEN change_reason LIKE '%undercut%' THEN 1 ELSE 0 END) as price_decreases,
            SUM(CASE WHEN change_reason LIKE '%increase%' THEN 1 ELSE 0 END) as price_increases,
            AVG(new_price - old_price) as avg_price_change,
            SUM(new_price - old_price) as total_price_change
        FROM price_changes
        WHERE created_at >= ?
    """, (start_date,))

    summary = cursor.fetchone()

    cursor.execute("""
        SELECT
            product_id,
            game_name,
            old_price,
            new_price,
            market_price,
            change_reason,
            created_at
        FROM price_changes
        WHERE created_at >= ?
        ORDER BY created_at DESC
        LIMIT 100
    """, (start_date,))

    changes = []
    for row in cursor.fetchall():
        changes.append({
            'product_id': row['product_id'],
            'game_name': row['game_name'],
            'old_price': row['old_price'],
            'new_price': row['new_price'],
            'market_price': row['market_price'],
            'change_reason': row['change_reason'],
            'change_amount': round(row['new_price'] - row['old_price'], 2),
            'created_at': row['created_at']
        })

    cursor.execute("""
        SELECT
            game_name,
            COUNT(*) as change_count,
            MIN(old_price) as min_old_price,
            MAX(new_price) as max_new_price,
            AVG(new_price - old_price) as avg_change
        FROM price_changes
        WHERE created_at >= ?
        GROUP BY game_name
        ORDER BY change_count DESC
        LIMIT 20
    """, (start_date,))

    top_changed_games = []
    for row in cursor.fetchall():
        top_changed_games.append({
            'game_name': row['game_name'],
            'change_count': row['change_count'],
            'min_old_price': row['min_old_price'],
            'max_new_price': row['max_new_price'],
            'avg_change': round(row['avg_change'], 2)
        })

    conn.close()

    return {
        "period": period_name,
        "summary": {
            "total_changes": summary['total_changes'] or 0,
            "price_decreases": summary['price_decreases'] or 0,
            "price_increases": summary['price_increases'] or 0,
            "avg_price_change": round(summary['avg_price_change'], 2) if summary['avg_price_change'] else 0,
            "total_price_change": round(summary['total_price_change'], 2) if summary['total_price_change'] else 0,
            "today_changes": get_today_price_changes_count()
        },
        "recent_changes": changes,
        "top_changed_games": top_changed_games
    }


def log_price_change(product_id, game_name, old_price, new_price, market_price, reason):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO price_changes (product_id, game_name, old_price, new_price, market_price, change_reason)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (product_id, game_name, old_price, new_price, market_price, reason))

        conn.commit()
        conn.close()

        logger.info(f"[AUTO-PRICE] {game_name} (ID:{product_id}): €{old_price:.2f} -> €{new_price:.2f} | Market: €{market_price:.2f} | Reason: {reason}")
    except Exception as e:
        logger.error(f"[AUTO-PRICE] Error logging price change: {e}")


def get_today_price_changes_count():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        cursor.execute("""
            SELECT COUNT(*) as count
            FROM price_changes
            WHERE created_at >= ?
        """, (today_start,))

        result = cursor.fetchone()
        conn.close()

        return result['count'] if result else 0
    except Exception as e:
        logger.error(f"[AUTO-PRICE] Error counting today's changes: {e}")
        return 0


async def auto_price_adjustment():
    from g2a_config import (
        AUTO_PRICE_CHANGE_ENABLED, AUTO_PRICE_CHECK_INTERVAL,
        AUTO_PRICE_MIN_OFFER_PRICE, AUTO_PRICE_UNDERCUT_AMOUNT,
        AUTO_PRICE_INCREASE_THRESHOLD, AUTO_PRICE_DAILY_LIMIT,
        AUTO_PRICE_MIN_PRICE, AUTO_PRICE_MAX_PRICE,
        G2A_CLIENT_ID, G2A_CLIENT_SECRET, G2A_API_BASE
    )

    if not AUTO_PRICE_CHANGE_ENABLED:
        logger.info("[AUTO-PRICE] Auto price adjustment is DISABLED in config")
        return

    logger.info(f"[AUTO-PRICE] Starting auto price adjustment task. Interval: {AUTO_PRICE_CHECK_INTERVAL}s")

    import httpx
    import hashlib

    while True:
        try:
            if AUTO_PRICE_DAILY_LIMIT > 0:
                today_changes = get_today_price_changes_count()
                if today_changes >= AUTO_PRICE_DAILY_LIMIT:
                    logger.warning(f"[AUTO-PRICE] Daily limit reached ({today_changes}/{AUTO_PRICE_DAILY_LIMIT}). Waiting for next day...")
                    await asyncio.sleep(AUTO_PRICE_CHECK_INTERVAL)
                    continue

            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT DISTINCT product_id, game_name, price
                FROM keys
                WHERE status = 'available' AND price >= ?
                GROUP BY product_id
            """, (AUTO_PRICE_MIN_OFFER_PRICE,))

            products = cursor.fetchall()
            conn.close()

            if not products:
                logger.info("[AUTO-PRICE] No products found matching criteria")
                await asyncio.sleep(AUTO_PRICE_CHECK_INTERVAL)
                continue

            logger.info(f"[AUTO-PRICE] Checking {len(products)} products for price adjustments...")

            api_key_hash = hashlib.sha256(G2A_CLIENT_SECRET.encode()).hexdigest()
            auth_header = f"{G2A_CLIENT_ID}, {api_key_hash}"

            async with httpx.AsyncClient(timeout=30.0) as client:
                for product in products:
                    product_id = product['product_id']
                    game_name = product['game_name']
                    current_price = product['price']

                    if not product_id:
                        continue

                    try:
                        response = await client.get(
                            f"{G2A_API_BASE}/v1/products/{product_id}",
                            headers={"Authorization": auth_header}
                        )

                        if response.status_code != 200:
                            continue

                        data = response.json()

                        if 'minPrice' not in data:
                            continue

                        market_price_cents = data['minPrice'].get('EUR', 0)
                        market_price = market_price_cents / 100.0

                        if market_price <= 0:
                            continue

                        price_diff = market_price - current_price

                        new_price = None
                        reason = None

                        if market_price < current_price:
                            new_price = round(market_price - AUTO_PRICE_UNDERCUT_AMOUNT, 2)
                            reason = "undercut_competitor"

                        elif price_diff >= AUTO_PRICE_INCREASE_THRESHOLD:
                            new_price = round(market_price - AUTO_PRICE_UNDERCUT_AMOUNT, 2)
                            reason = "market_increase"

                        if new_price and new_price != current_price:
                            if new_price < AUTO_PRICE_MIN_PRICE:
                                new_price = AUTO_PRICE_MIN_PRICE
                                reason = f"{reason}_capped_min"
                            elif new_price > AUTO_PRICE_MAX_PRICE:
                                new_price = AUTO_PRICE_MAX_PRICE
                                reason = f"{reason}_capped_max"

                            if abs(new_price - current_price) < 0.01:
                                continue

                            conn = get_db_connection()
                            cursor = conn.cursor()

                            cursor.execute("""
                                UPDATE keys
                                SET price = ?
                                WHERE product_id = ? AND status = 'available'
                            """, (new_price, product_id))

                            conn.commit()
                            conn.close()

                            log_price_change(product_id, game_name, current_price, new_price, market_price, reason)

                            if AUTO_PRICE_DAILY_LIMIT > 0:
                                today_changes = get_today_price_changes_count()
                                if today_changes >= AUTO_PRICE_DAILY_LIMIT:
                                    logger.warning(f"[AUTO-PRICE] Daily limit reached ({today_changes}/{AUTO_PRICE_DAILY_LIMIT})")
                                    break

                        await asyncio.sleep(1)

                    except Exception as e:
                        logger.error(f"[AUTO-PRICE] Error processing {game_name}: {e}")
                        continue

        except Exception as e:
            logger.error(f"[AUTO-PRICE] Error in price adjustment task: {e}")

        await asyncio.sleep(AUTO_PRICE_CHECK_INTERVAL)


async def cleanup_expired_tokens():
    while True:
        try:
            current_time = datetime.now()
            expired_tokens = [
                token for token, data in active_tokens.items()
                if current_time > data["expires_at"]
            ]

            for token in expired_tokens:
                del active_tokens[token]

            if expired_tokens:
                logger.info(f"Удалено {len(expired_tokens)} истекших токенов")

        except Exception as e:
            logger.error(f"Ошибка cleanup токенов: {e}")

        await asyncio.sleep(300)

@app.on_event("startup")
async def startup_event():
    init_database()
    asyncio.create_task(cleanup_expired_tokens())
    asyncio.create_task(auto_price_adjustment())
    logger.info("G2A-compatible API Server started successfully")



if __name__ == "__main__":
    import uvicorn

    init_database()
    uvicorn.run(app, host="0.0.0.0", port=80, reload=True)
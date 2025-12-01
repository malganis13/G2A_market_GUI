#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
G2A API Client with JSON-first configuration loading
"""

import asyncio
import hashlib
import json
import os
from curl_cffi.requests import AsyncSession

# === ЗАГРУЗКА КОНФИГУРАЦИИ ===
G2A_CLIENT_ID = ""
G2A_CLIENT_SECRET = ""
G2A_CLIENT_EMAIL = ""
G2A_API_BASE = "https://api.g2a.com"
REQUEST_TIMEOUT = 60  # Увеличил таймаут до 60 секунд

config_loaded_from = None

# 1. ПРИОРИТЕТ: Загрузка из JSON файла (из GUI Settings)
JSON_CONFIG_FILE = "g2a_config_saved.json"
if os.path.exists(JSON_CONFIG_FILE):
    try:
        with open(JSON_CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
            
        # Загружаем только если ВСЕ поля заполнены
        client_id = config.get('G2A_CLIENT_ID', '').strip()
        client_secret = config.get('G2A_CLIENT_SECRET', '').strip()
        client_email = config.get('G2A_CLIENT_EMAIL', '').strip()
        
        if client_id and client_secret and client_email:
            G2A_CLIENT_ID = client_id
            G2A_CLIENT_SECRET = client_secret
            G2A_CLIENT_EMAIL = client_email
            config_loaded_from = "JSON (GUI Settings)"
            print(f"\n✅ G2A Config loaded from: {JSON_CONFIG_FILE}")
            print(f"   📧 Email: {G2A_CLIENT_EMAIL}")
            print(f"   🔑 Client ID: {G2A_CLIENT_ID[:15]}...\n")
        else:
            print(f"⚠️  {JSON_CONFIG_FILE} exists but incomplete (missing fields)")
    except Exception as e:
        print(f"❌ Error loading {JSON_CONFIG_FILE}: {e}")

# 2. FALLBACK: Загрузка из g2a_config.py (только если JSON не загрузился)
if not G2A_CLIENT_ID or not G2A_CLIENT_SECRET or not G2A_CLIENT_EMAIL:
    try:
        from g2a_config import (
            G2A_API_BASE as _API_BASE,
            G2A_CLIENT_ID as _CLIENT_ID,
            G2A_CLIENT_SECRET as _CLIENT_SECRET,
            REQUEST_TIMEOUT as _TIMEOUT
        )
        
        # Пытаемся загрузить email
        try:
            from g2a_config import G2A_CLIENT_EMAIL as _CLIENT_EMAIL
        except ImportError:
            _CLIENT_EMAIL = ""
        
        # Проверяем что это не плейсхолдеры
        if (_CLIENT_ID and _CLIENT_SECRET and _CLIENT_EMAIL and
            _CLIENT_EMAIL != "G2A_CLIENT_EMAIL" and
            "@" in _CLIENT_EMAIL):
            
            G2A_CLIENT_ID = _CLIENT_ID
            G2A_CLIENT_SECRET = _CLIENT_SECRET
            G2A_CLIENT_EMAIL = _CLIENT_EMAIL
            G2A_API_BASE = _API_BASE
            REQUEST_TIMEOUT = _TIMEOUT
            config_loaded_from = "Python file (g2a_config.py)"
            print(f"\n✅ G2A Config loaded from: g2a_config.py")
            print(f"   📧 Email: {G2A_CLIENT_EMAIL}")
            print(f"   🔑 Client ID: {G2A_CLIENT_ID[:15]}...\n")
        else:
            print("⚠️  g2a_config.py exists but has invalid/placeholder values")
            
    except ImportError:
        print("⚠️  g2a_config.py not found")

# 3. Проверка что конфигурация загружена
if not G2A_CLIENT_ID or not G2A_CLIENT_SECRET or not G2A_CLIENT_EMAIL:
    print("\n" + "="*60)
    print("❌ G2A API CREDENTIALS NOT CONFIGURED!")
    print("="*60)
    print("\nPlease configure your G2A API credentials:")
    print("\n1. Open the application")
    print("2. Go to ⚙️ Settings tab")
    print("3. Fill in:")
    print("   • Client ID")
    print("   • Client Secret")
    print("   • Email (your G2A account email)")
    print("4. Click 'Save G2A Settings'")
    print("5. Restart the application")
    print("\n" + "="*60 + "\n")

from proxy_manager import ProxyManager
from color_utils import print_success, print_error, print_warning, print_info
import functools

def handle_api_exception(e):
    """Вспомогательная функция для обработки исключений API"""
    if ("401" in str(e) or "unauthorized" in str(e).lower()):
        raise e
    return {
        "success": False,
        "error": str(e)
    }

def auto_refresh_token(func):
    """Декоратор для автоматического обновления токена при ошибке 401"""
    @functools.wraps(func)
    async def wrapper(self, *args, **kwargs):
        try:
            return await func(self, *args, **kwargs)
        except Exception as e:
            error_str = str(e).lower()
            if ("401" in error_str or 
                "unauthorized" in error_str or 
                ("token" in error_str and ("expired" in error_str or "invalid" in error_str))):
                
                print_warning("🔄 Токен истек, обновляем и повторяем запрос...")
                try:
                    await self.get_token()
                    print_info("✓ Токен обновлен, повторяем запрос...")
                    return await func(self, *args, **kwargs)
                except Exception as token_error:
                    print_error(f"❌ Ошибка обновления токена: {token_error}")
                    raise e
            else:
                raise e
    return wrapper

class G2AApiClient:
    def __init__(self):
        # Проверка что есть credentials
        if not G2A_CLIENT_ID or not G2A_CLIENT_SECRET or not G2A_CLIENT_EMAIL:
            raise Exception(
                "❌ G2A API credentials not configured!\n\n"
                "Please go to Settings tab (⚙️) and configure:\n"
                "• Client ID\n"
                "• Client Secret\n"
                "• Email (same as your G2A account)\n\n"
                "Then restart the application."
            )
        
        # Проверка что email не плейсхолдер
        if G2A_CLIENT_EMAIL == "G2A_CLIENT_EMAIL" or "@" not in G2A_CLIENT_EMAIL:
            raise Exception(
                f"❌ Invalid email: {G2A_CLIENT_EMAIL}\n\n"
                "Please go to Settings tab and enter your REAL G2A account email!\n"
                "Example: yourname@gmail.com"
            )
        
        print(f"\n🔧 Initializing G2A API Client...")
        print(f"   Config source: {config_loaded_from}")
        print(f"   Email: {G2A_CLIENT_EMAIL}")
        print(f"   Timeout: {REQUEST_TIMEOUT}s\n")
        
        self.api_key = self.generate_api_key()
        self.auth_header = f"{G2A_CLIENT_ID}, {self.api_key}"
        self.session = None
        self.token = None
        self.proxy_manager = ProxyManager()
        
        headers = {
            "Authorization": self.auth_header,
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
        proxy = self.proxy_manager.get_current_proxy()
        self.session = AsyncSession(
            headers=headers,
            timeout=REQUEST_TIMEOUT,
            verify=False,
            proxy=proxy
        )

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    def generate_api_key(self):
        """Генерация API ключа для G2A аутентификации"""
        data = f"{G2A_CLIENT_ID}{G2A_CLIENT_EMAIL}{G2A_CLIENT_SECRET}"
        api_key = hashlib.sha256(data.encode()).hexdigest()
        print(f"🔑 API Key generated")
        print(f"   Formula: sha256(ClientID + Email + Secret)")
        print(f"   Result: {api_key[:20]}...{api_key[-10:]}\n")
        return api_key

    def is_auth_error(self, status_code, response_text=""):
        """Проверка, является ли ошибка связанной с авторизацией"""
        if status_code == 401:
            return True
        
        response_lower = response_text.lower()
        auth_keywords = ["unauthorized", "invalid token", "token expired", "authentication failed"]
        return any(keyword in response_lower for keyword in auth_keywords)

    async def get_token(self):
        """Получение OAuth токена для G2A API"""
        print("🔐 Requesting OAuth token...")
        
        response = await self.session.post(
            f"{G2A_API_BASE}/oauth/token",
            json={
                "grant_type": "client_credentials",
                "client_id": G2A_CLIENT_ID,
                "client_secret": G2A_CLIENT_SECRET,
            }
        )

        if response.status_code == 200:
            token_data = response.json()
            self.token = token_data["access_token"]
            print(f"✅ OAuth token obtained")
            print(f"   Token: {self.token[:15]}...{self.token[-10:]}\n")
        else:
            error_text = response.text
            print(f"❌ Token request failed!")
            print(f"   Status: {response.status_code}")
            print(f"   Response: {error_text}\n")
            raise Exception(f"Token error: {response.status_code} - {error_text}")

    async def get_rate(self):
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get("https://api.exchangerate-api.com/v4/latest/EUR", timeout=5)
                self.rate = response.json()["rates"]["USD"]
        except:
            self.rate = 1.1

    @auto_refresh_token
    async def get_offers(self):
        if not self.session or not self.token:
            raise Exception("API client not initialized or no token.")

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json"
        }

        all_offers = {}
        page = 1

        print(f"📦 Fetching offers from G2A API...")
        
        while True:
            print(f"   Page {page}...", end=" ")
            
            response = await self.session.get(
                f"{G2A_API_BASE}/v3/sales/offers",
                headers=headers,
                params={
                    "itemsPerPage": 100,
                    "page": page
                }
            )

            if response.status_code != 200:
                print(f"❌ Failed (HTTP {response.status_code})")
                if self.is_auth_error(response.status_code, response.text):
                    raise Exception(f"401 Unauthorized: {response.text}")
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}"
                }

            data = response.json()
            offers_data = data.get("data", [])
            meta = data.get("meta", {})
            
            print(f"✓ {len(offers_data)} offers")

            for offer in offers_data:
                product_id = str(offer.get("product", {}).get("id"))
                if product_id and product_id != "None":
                    all_offers[product_id] = {
                        "id": offer.get("id"),
                        "product_name": offer.get("product", {}).get("name", f"ID: {product_id}"),
                        "price": offer.get("price", "N/A"),
                        "current_stock": offer.get("inventory", {}).get("size", 0),
                        "is_active": offer.get("status") == "active",
                        "offer_type": offer.get("type", "game")
                    }

            total_results = meta.get("totalResults", 0)
            items_per_page = meta.get("itemsPerPage", 100)
            current_page = meta.get("page", 1)

            if current_page * items_per_page >= total_results:
                break

            page += 1
        
        print(f"\n✅ Total offers loaded: {len(all_offers)}\n")

        return {
            "success": True,
            "offers_cache": all_offers,
            "total_loaded": len(all_offers)
        }

    @auto_refresh_token
    async def update_price(self, offer_id, new_price):
        """Обновление цены оффера"""
        if not self.token:
            raise Exception("No token available")

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        response = await self.session.patch(
            f"{G2A_API_BASE}/v3/sales/offers/{offer_id}",
            headers=headers,
            json={"price": new_price}
        )

        if response.status_code == 200:
            return {"success": True, "offer_id": offer_id, "new_price": new_price}
        else:
            error_text = response.text
            if self.is_auth_error(response.status_code, error_text):
                raise Exception(f"401 Unauthorized: {error_text}")
            return {
                "success": False,
                "error": f"HTTP {response.status_code}: {error_text}"
            }

    @auto_refresh_token
    async def update_stock(self, offer_id, keys):
        """Обновление стока оффера"""
        if not self.token:
            raise Exception("No token available")

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        response = await self.session.put(
            f"{G2A_API_BASE}/v3/sales/offers/{offer_id}/inventory",
            headers=headers,
            json={"keys": keys}
        )

        if response.status_code == 200:
            return {"success": True, "offer_id": offer_id, "keys_count": len(keys)}
        else:
            error_text = response.text
            if self.is_auth_error(response.status_code, error_text):
                raise Exception(f"401 Unauthorized: {error_text}")
            return {
                "success": False,
                "error": f"HTTP {response.status_code}: {error_text}"
            }

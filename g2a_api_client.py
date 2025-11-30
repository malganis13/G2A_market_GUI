import asyncio
import hashlib
import json
from curl_cffi.requests import AsyncSession
try:
    from g2a_config import G2A_API_BASE, G2A_CLIENT_ID, G2A_CLIENT_SECRET, G2A_CLIENT_EMAIL, REQUEST_TIMEOUT
except ImportError:
    # Если нет G2A_CLIENT_EMAIL в старом конфиге
    from g2a_config import G2A_API_BASE, G2A_CLIENT_ID, G2A_CLIENT_SECRET, REQUEST_TIMEOUT
    G2A_CLIENT_EMAIL = "your_email@gmail.com"  # Заглушка
from proxy_manager import ProxyManager
from color_utils import print_success, print_error, print_warning, print_info
import functools

def handle_api_exception(e):
    """Вспомогательная функция для обработки исключений API"""
    # Если это ошибка авторизации, пробрасываем её для декоратора
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
            # Проверяем, является ли это ошибкой авторизации
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
                # Если это не ошибка авторизации, пробрасываем исключение дальше
                raise e
    return wrapper

class G2AApiClient:
    def __init__(self):
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
        # ИСПОЛЬЗУЕМ EMAIL ИЗ КОНФИГА!
        client_email = G2A_CLIENT_EMAIL
        data = f"{G2A_CLIENT_ID}{client_email}{G2A_CLIENT_SECRET}"
        api_key = hashlib.sha256(data.encode()).hexdigest()
        print(f"🔑 API Key generated with email: {client_email}")
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
        response = await self.session.post(
            f"{G2A_API_BASE}/oauth/token",
            json={
                "grant_type": "client_credentials",
                "client_id": G2A_CLIENT_ID,
                "client_secret": G2A_CLIENT_SECRET,
            }
        )

        if response.status_code == 200:
            self.token = response.json()["access_token"]
        else:
            raise Exception(f"Token error: {response.status_code}")


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

        while True:
            response = await self.session.get(
                f"{G2A_API_BASE}/v3/sales/offers",
                headers=headers,
                params={
                    "itemsPerPage": 100,
                    "page": page
                }
            )

            if response.status_code != 200:
                if self.is_auth_error(response.status_code, response.text):
                    raise Exception(f"401 Unauthorized: {response.text}")
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}"
                }

            data = response.json()
            offers_data = data.get("data", [])
            meta = data.get("meta", {})

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

        return {
            "success": True,
            "offers_cache": all_offers,
            "total_loaded": len(all_offers)
        }

    # ... (остальные методы остаются без изменений, скопирую из текущего файла)

import asyncio
import hashlib
import json
from curl_cffi.requests import AsyncSession
from g2a_config import G2A_API_BASE, G2A_CLIENT_ID, G2A_CLIENT_SECRET, REQUEST_TIMEOUT
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

    def generate_api_key(self):
        """Генерация API ключа для G2A аутентификации"""
        client_email = "qryxy@outlook.com"
        data = f"{G2A_CLIENT_ID}{client_email}{G2A_CLIENT_SECRET}"
        return hashlib.sha256(data.encode()).hexdigest()

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
    async def get_product_price(self, product_id):
        """Получение цены продукта с minPrice и retailMinBasePrice"""
        if not self.session:
            raise Exception("API client not initialized. Use 'async with' statement.")

        url = f"{G2A_API_BASE}/v1/products"
        params = {
            "id": product_id,
            "includeOutOfStock": "true"
        }

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = await self.session.get(url, params=params)
                if response.status_code == 429:
                    print(f"Rate limited on API, waiting...")
                    await asyncio.sleep(2)
                    continue

                if response.status_code != 200:
                    if self.is_auth_error(response.status_code, response.text):
                        raise Exception(f"401 Unauthorized: {response.text}")
                    print(f"API HTTP {response.status_code} for product {product_id}")
                    return None

                data = response.json()
                products = data.get("docs", [])

                if not products:
                    print(f"Не найдена игра по ID {product_id}")
                    return None

                product = products[0]

                # Получаем обе цены
                min_price = product.get("minPrice")
                retail_min_base_price = product.get("retailMinBasePrice")

                if min_price is not None and retail_min_base_price is not None:
                    usd_price = float(min_price) * self.rate
                    return {
                        "min_price": float(min_price),  # Текущая минимальная цена на маркете
                        "min_price_usd": usd_price,  # В долларах для отображения
                        "retail_price": float(retail_min_base_price)  # Цена для выставления
                    }
                else:
                    print(f"Не найдена цена для {product_id}")
                    return None

            except Exception as e:
                print(f"Error getting price for {product_id} (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2)
                else:
                    return None

        return None

    @auto_refresh_token
    async def check_job_status_simple(self, job_id: str):
        if not self.session or not self.token:
            raise Exception("API client not initialized or no token.")

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json"
        }

        try:
            response = await self.session.get(
                f"{G2A_API_BASE}/v3/jobs/{job_id}",
                headers=headers
            )

            if response.status_code == 200:
                data = response.json()
                job_data = data.get("data", {})

                return {
                    "success": True,
                    "status": job_data.get("status"),
                    "elements": job_data.get("elements", [])
                }
            else:
                if self.is_auth_error(response.status_code, response.text):
                    raise Exception(f"401 Unauthorized: {response.text}")
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}"
                }
        except Exception as e:
            return handle_api_exception(e)

    @auto_refresh_token
    async def create_offer(self, product_id: str, price: float, quantity: int = 1, currency: str = "EUR",
                           restrictions=None):
        if not self.session or not self.token:
            raise Exception("API client not initialized or no token. Use 'async with' statement.")

        if price <= 5:
            price = price * 0.97
        elif price > 5:
            price = price * 0.99
        price = round(price, 2)

        variant = {
            "productId": product_id,
            "price": {
                "retail": str(price),
                "business": str(price)
            },
            "inventory": {
                "size": quantity
            },
            "active": True,
            "visibility": "all",
            "regions": ["GLOBAL"]
        }

        if restrictions:
            has_include = "include" in restrictions and restrictions["include"]
            has_exclude = "exclude" in restrictions and restrictions["exclude"]

            if has_include or has_exclude:
                variant["regionRestrictions"] = restrictions

                if has_include:
                    print(f"Применяем ограничения ONLY для {len(restrictions['include'])} стран")
                if has_exclude:
                    print(f"Применяем ограничения EXCEPT для {len(restrictions['exclude'])} стран")

        data = {
            "offerType": "dropshipping",
            "variants": [variant]
        }

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        try:
            response = await self.session.post(
                f"{G2A_API_BASE}/v3/sales/offers",
                json=data,
                headers=headers
            )

            if response.status_code in [200, 201, 202]:
                result = response.json()
                job_id = result.get("data", {}).get("jobId") if "data" in result else result.get("jobId")
                return {
                    "success": True,
                    "data": result,
                    "job_id": job_id,
                    "message": f"Оффер создан успешно для продукта {product_id}. Job ID: {job_id}"
                }
            else:
                error_text = response.text
                if self.is_auth_error(response.status_code, error_text):
                    raise Exception(f"401 Unauthorized: {error_text}")
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {error_text}",
                    "message": "Ошибка создания оффера"
                }
        except Exception as e:
            # Если это ошибка авторизации, пробрасываем её для декоратора
            if ("401" in str(e) or "unauthorized" in str(e).lower()):
                raise e
            return {
                "success": False,
                "error": str(e),
                "message": "Ошибка создания оффера"
            }

    @auto_refresh_token
    async def check_job_status(self, job_id: str):
        """Проверка статуса задачи создания офера"""
        if not self.session or not self.token:
            raise Exception("API client not initialized or no token.")

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json"
        }

        try:
            response = await self.session.get(
                f"{G2A_API_BASE}/v3/job/{job_id}",
                headers=headers
            )

            if response.status_code == 200:
                job_data = response.json()

                return {
                    "success": True,
                    "status": job_data.get("status"),
                    "resource_id": job_data.get("resourceId"),
                    "error_code": job_data.get("code"),
                    "error_message": job_data.get("message"),
                    "raw_data": job_data
                }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    async def wait_for_job_completion(self, job_id: str, max_wait_time: int = 300, check_interval: int = 5):
        """Ожидание завершения задачи создания офера"""
        start_time = asyncio.get_event_loop().time()

        while True:
            result = await self.check_job_status(job_id)

            if not result["success"]:
                return result

            status = result["status"]

            if status == "completed":
                offer_id = result["resource_id"]
                return {
                    "success": True,
                    "status": status,
                    "offer_id": offer_id,
                    "message": f"Офер создан успешно! ID: {offer_id}"
                }

            if status == "failed":
                return {
                    "success": False,
                    "status": status,
                    "error_code": result["error_code"],
                    "error_message": result["error_message"],
                    "message": f"Ошибка создания офера: {result['error_message']}"
                }

            elapsed_time = asyncio.get_event_loop().time() - start_time
            if elapsed_time >= max_wait_time:
                return {
                    "success": False,
                    "error": "timeout",
                    "message": f"Превышено время ожидания ({max_wait_time} секунд). Статус: {status}"
                }

            print(f"Статус задачи {job_id}: {status}. Ожидание {check_interval} секунд...")
            await asyncio.sleep(check_interval)

    async def create_new_offer_with_fallback(self, game_name, product_id, price, offers_cache,restrictions=None):
        try:
            create_result = await self.create_offer(
                product_id=str(product_id),
                price=price,
                quantity=1,
                restrictions=restrictions
            )

            if create_result["success"]:
                job_id = create_result.get("job_id")
                if job_id:
                    print(f"Оффер создается... Job ID: {job_id}")
                    await asyncio.sleep(4)

                    status_result = await self.check_job_status_simple(job_id)
                    if (status_result.get("success") and
                            status_result.get("status") == "complete"):

                        elements = status_result.get("elements", [])
                        if elements and elements[0].get("status") == "completed":
                            real_offer_id = elements[0].get("resourceId")

                            if real_offer_id:
                                offers_cache[str(product_id)] = {
                                    "id": real_offer_id,
                                    "current_stock": 1,
                                    "is_active": True
                                }
                                print_success(f"✅ Игра {game_name} успешно выставлена на продажу за €{price:.2f}")
                                return True
                            else:
                                print_error(f"❌ Не найден resourceId в elements")
                                return False
                        else:
                            print_error(f"❌ Элемент не completed или elements пустой")
                            return False
                    else:
                        print_error(f"❌ Job не завершен успешно: {status_result}")
                        return False
                else:
                    print_error(f"❌ Не получен job_id")
                    return False
            else:
                error_msg = create_result.get('error', '')

                if "409" in str(error_msg) or "already exists" in str(error_msg).lower():
                    print(f"🔍 Оффер уже существует для {product_id}")

                    existing_offer_id = self.extract_offer_id_from_error(error_msg)

                    if existing_offer_id:
                        print(f"📋 Найден offerId в ошибке: {existing_offer_id}")

                        offer_details = await self.get_offer_details(existing_offer_id)

                        if offer_details.get("success"):
                            offer_data = offer_details.get("data", {})
                            current_stock = self.extract_current_stock_from_offer(offer_data)
                            is_active = self.extract_active_status_from_offer(offer_data)

                            offers_cache[str(product_id)] = {
                                "id": existing_offer_id,
                                "current_stock": current_stock,
                                "is_active": is_active
                            }

                            new_stock = current_stock + 1
                            success = await self.update_offer_stock_and_activate(
                                existing_offer_id, new_stock
                            )

                            if success:
                                offers_cache[str(product_id)]['current_stock'] = new_stock
                                offers_cache[str(product_id)]['is_active'] = True

                                status_text = "активирован" if not is_active else "обновлен"
                                print_success(f"✅ Оффер {status_text} для {game_name}: stock {current_stock} → {new_stock}")
                                return True
                            else:
                                print_error(f"❌ Не удалось обновить существующий оффер")
                                return False
                        else:
                            print_error(f"❌ Не удалось получить детали оффера {existing_offer_id}")
                            return False
                    else:
                        print_error(f"❌ Не удалось извлечь offerId из ошибки: {error_msg}")
                        return False
                else:
                    print_error(f"❌ Другая ошибка создания оффера: {error_msg}")
                    return False

        except Exception as e:
            print(f"Ошибка создания оффера: {e}")
            return False

    def extract_offer_id_from_error(self, error_msg):
        try:
            import re
            if isinstance(error_msg, str):
                json_match = re.search(r'\{.*\}', error_msg)
                if json_match:
                    error_json = json.loads(json_match.group())

                    if "data" in error_json and "offerId" in error_json["data"]:
                        return error_json["data"]["offerId"]
                    if "offerId" in error_json:
                        return error_json["offerId"]
            return None
        except Exception as e:
            print(f"Ошибка извлечения offerId: {e}")
            return None

    def extract_current_stock_from_offer(self, offer_data):
        try:
            variants = offer_data.get("variants", [])
            if variants:
                inventory = variants[0].get("inventory", {})
                return inventory.get("size", 0)
            return 0
        except Exception:
            return 0

    async def update_offer_stock_and_activate(self, offer_id, new_quantity):
        try:
            update_data = {
                "inventory": {
                    "size": new_quantity
                },
                "active": True
            }

            result = await self.update_offer_partial(offer_id, update_data)
            return result.get("success", False)
        except Exception as e:
            print(f"Ошибка обновления оффера: {e}")
            return False


    def extract_active_status_from_offer(self, offer_data):
        try:
            variants = offer_data.get("variants", [])
            if variants:
                return variants[0].get("active", False)
            return False
        except Exception:
            return False

    @auto_refresh_token
    async def update_offer_partial(self, offer_id: str, update_data: dict):
        """Частичное обновление оффера (PATCH запрос)"""
        if not self.session or not self.token:
            raise Exception("API client not initialized or no token.")

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        response = await self.session.patch(
            f"{G2A_API_BASE}/v3/sales/offers/{offer_id}",
            json=update_data,
            headers=headers
        )

        if response.status_code in [200, 202]:
            return {
                "success": True,
                "data": response.json() if response.status_code == 200 else {},
                "message": f"Оффер {offer_id} обновлен"
            }
        else:
            if self.is_auth_error(response.status_code, response.text):
                raise Exception(f"401 Unauthorized: {response.text}")
            return {
                "success": False,
                "error": f"HTTP {response.status_code}: {response.text}"
            }
    @auto_refresh_token
    async def get_offer_details(self, offer_id):
        """Получение деталей конкретного оффера по ID"""
        if not self.session or not self.token:
            raise Exception("API client not initialized or no token.")

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json"
        }

        try:
            response = await self.session.get(
                f"{G2A_API_BASE}/v3/sales/offers/{offer_id}",
                headers=headers
            )

            if response.status_code == 200:
                return {
                    "success": True,
                    "data": response.json()
                }
            elif response.status_code == 404:
                return {
                    "success": False,
                    "error": f"Оффер {offer_id} не найден"
                }
            elif response.status_code == 401:
                await self.get_token()
                print('получен новый токен, пробуем еще раз')
                return await self.get_offer_details(offer_id)
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    @auto_refresh_token
    async def get_price_simulation(self, product_id: str, price: float, currency: str = "EUR"):
        """Симуляция цены для расчета комиссии"""
        if not self.session or not self.token:
            raise Exception("API client not initialized or no token.")

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json"
        }

        params = {
            "productId": product_id,
            "price": price,
            "currency": currency
        }

        try:
            response = await self.session.get(
                f"{G2A_API_BASE}/v3/pricing/simulations",
                params=params,
                headers=headers
            )

            if response.status_code == 200:
                data = response.json()
                business_income = data.get("businessIncome", {})

                return {
                    "success": True,
                    "data": data,
                    "your_income": business_income.get("ALL", 0),
                    "commission": price - business_income.get("ALL", 0),
                    "message": f"Симуляция для {product_id}: ваш доход €{business_income.get('ALL', 0):.2f}"
                }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    @auto_refresh_token
    async def update_offer_inventory(self, offer_id: str, new_quantity: int):
        """Обновление количества товара в офере"""
        if not self.session or not self.token:
            raise Exception("API client not initialized or no token.")

        data = {
            "inventory": {
                "size": new_quantity
            }
        }

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        try:
            response = await self.session.patch(
                f"{G2A_API_BASE}/v3/sales/offers/{offer_id}",
                json=data,
                headers=headers
            )

            if response.status_code == 200:
                return {
                    "success": True,
                    "data": response.json(),
                    "message": f"Количество товара в офере {offer_id} обновлено на {new_quantity}"
                }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    @auto_refresh_token
    async def activate_offer(self, offer_id: str, active: bool = True):
        """Активация/деактивация офера"""
        if not self.session or not self.token:
            raise Exception("API client not initialized or no token.")

        data = {
            "status": active
        }

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        try:
            response = await self.session.patch(
                f"{G2A_API_BASE}/v3/sales/offers/{offer_id}",
                json=data,
                headers=headers
            )

            if response.status_code == 200:
                status = "активирован" if active else "деактивирован"
                return {
                    "success": True,
                    "data": response.json(),
                    "message": f"Офер {offer_id} {status}"
                }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    @auto_refresh_token
    async def deactivate_offer(self, offer_id: str, offer_type: str = "dropshipping"):
        """Деактивировать оффер перед удалением"""
        if not self.session or not self.token:
            raise Exception("API client not initialized or no token.")

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        data = {
            "offerType": offer_type,
            "variant": {
                "active": False
            }
        }

        try:
            response = await self.session.patch(
                f"{G2A_API_BASE}/v3/sales/offers/{offer_id}",
                json=data,
                headers=headers
            )

            if response.status_code in [200, 202]:
                return {
                    "success": True,
                    "message": f"Офер {offer_id} деактивирован"
                }
            else:
                if self.is_auth_error(response.status_code, response.text):
                    raise Exception(f"401 Unauthorized: {response.text}")
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    @auto_refresh_token
    async def delete_offer(self, offer_id: str):
        """Удаление офера"""
        if not self.session or not self.token:
            raise Exception("API client not initialized or no token.")

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json"
        }

        try:
            response = await self.session.delete(
                f"{G2A_API_BASE}/v3/sales/offers/{offer_id}",
                headers=headers
            )

            if response.status_code in [200, 204]:
                return {
                    "success": True,
                    "message": f"Офер {offer_id} удален"
                }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

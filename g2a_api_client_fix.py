# Этот файл показывает изменения, которые нужно внести в g2a_api_client.py

# В начале файла, где импорты:
# БЫЛО:
# from g2a_config import G2A_API_BASE, G2A_CLIENT_ID, G2A_CLIENT_SECRET, REQUEST_TIMEOUT

# СТАЛО:
from g2a_config import G2A_API_BASE, G2A_CLIENT_ID, G2A_CLIENT_SECRET, G2A_CLIENT_EMAIL, REQUEST_TIMEOUT

# В методе generate_api_key:
# БЫЛО:
#     def generate_api_key(self):
#         """Generation API key for G2A auth"""
#         client_email = "qryxy@outlook.com"  # Захардкоженный email!
#         data = f"{G2A_CLIENT_ID}{client_email}{G2A_CLIENT_SECRET}"
#         return hashlib.sha256(data.encode()).hexdigest()

# СТАЛО:
def generate_api_key(self):
    """Генерация API ключа для G2A аутентификации"""
    # Используем email из конфига
    client_email = G2A_CLIENT_EMAIL
    data = f"{G2A_CLIENT_ID}{client_email}{G2A_CLIENT_SECRET}"
    return hashlib.sha256(data.encode()).hexdigest()

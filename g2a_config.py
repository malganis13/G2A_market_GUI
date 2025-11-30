
SANDBOX_MODE = False  # True = тесты, False = продакшн

MIN_PRICE_TO_SELL = 0.3 # Минимальная цена в EUR для выставления на продажу
# Папки
KEYS_FOLDER = "keys"
RESULT_FOLDER = "result"
PROXY_FILE = "proxy.txt"

# Парсинг
PRICE_EXPIRY_DAYS = 3
DELAY_BETWEEN_REQUESTS = 1
REQUEST_TIMEOUT = 20

TELEGRAM_BOT_TOKEN = "bot_token"
TELEGRAM_CHAT_ID = "id"
DEFAULT_PREFIX = "pref"


ADMIN_API_KEY = "akblfkykc635671"
G2A_BASE_URL = "https://www.g2a.com/category/gaming-c1"
G2A_BASE_PARAMS = "f%5Bplatform%5D%5B0%5D=1&f%5Btype%5D%5B0%5D=10"

AUTO_PRICE_CHANGE_ENABLED = True
AUTO_PRICE_CHECK_INTERVAL = 1800
AUTO_PRICE_MIN_OFFER_PRICE = 0.5
AUTO_PRICE_UNDERCUT_AMOUNT = 0.01
AUTO_PRICE_INCREASE_THRESHOLD = 0.1
AUTO_PRICE_DAILY_LIMIT = 30
AUTO_PRICE_MIN_PRICE = 0.1
AUTO_PRICE_MAX_PRICE = 100.0
if SANDBOX_MODE:
    G2A_CLIENT_ID = "G2A_CLIENT_ID"
    G2A_CLIENT_SECRET = "G2A_CLIENT_SECRET"
    G2A_API_BASE = "https://sandboxapi.g2a.com"
    DATABASE_FILE = "sandbox_keys.db"
    G2A_CLIENT_EMAIL = "G2A_CLIENT_EMAIL"
else:
    G2A_CLIENT_ID = "G2A_CLIENT_ID"
    G2A_CLIENT_SECRET = "G2A_CLIENT_SECRET"
    G2A_API_BASE = "https://api.g2a.com"
    DATABASE_FILE = "keys.db"
    G2A_CLIENT_EMAIL = "G2A_CLIENT_EMAIL"


SERVER_CLIENT_ID="L5AvJbpDDvupje8vTyPh"
SERVER_CLIENT_SECRET="rWiZlvPUPMIERui17UaaOohWhRjEslRq"
API_BASE_URL = "https://domen.ngrok.app"



# Регионы
REGION_CODES = {
    "GLOBAL": 8355,
    "EUROPE": 878,
    "NORTH_AMERICA": 879,
    "ASIA": 883,
    "LATAM":8794
}

COUNTRY_TO_REGION = {
    # Европа
    "AD": "EUROPE", "AL": "EUROPE", "AT": "EUROPE", "AX": "EUROPE", "BA": "EUROPE",
    "BE": "EUROPE", "BG": "EUROPE", "CH": "EUROPE", "CY": "EUROPE", "CZ": "EUROPE",
    "DE": "EUROPE", "DK": "EUROPE", "EE": "EUROPE", "ES": "EUROPE", "FI": "EUROPE",
    "FO": "EUROPE", "FR": "EUROPE", "GB": "EUROPE", "GG": "EUROPE", "GI": "EUROPE",
    "GL": "EUROPE", "GR": "EUROPE", "HR": "EUROPE", "HU": "EUROPE", "IE": "EUROPE",
    "IM": "EUROPE", "IS": "EUROPE", "IT": "EUROPE", "JE": "EUROPE", "LI": "EUROPE",
    "LT": "EUROPE", "LU": "EUROPE", "LV": "EUROPE", "MC": "EUROPE", "ME": "EUROPE",
    "MK": "EUROPE", "MT": "EUROPE", "NL": "EUROPE", "NO": "EUROPE", "PL": "EUROPE",
    "PT": "EUROPE", "RO": "EUROPE", "RS": "EUROPE", "SE": "EUROPE", "SI": "EUROPE",
    "SJ": "EUROPE", "SK": "EUROPE", "SM": "EUROPE", "VA": "EUROPE",
    "BY": "EUROPE", "MD": "EUROPE", "TR": "EUROPE", "UA": "EUROPE",

    # Северная Америка
    "US": "NORTH_AMERICA", "CA": "NORTH_AMERICA", "MX": "NORTH_AMERICA",

    # Латинская Америка
    "AR": "LATAM", "BO": "LATAM", "BR": "LATAM", "BS": "LATAM", "BZ": "LATAM",
    "CL": "LATAM", "CO": "LATAM", "CR": "LATAM", "EC": "LATAM", "GF": "LATAM",
    "GT": "LATAM", "GY": "LATAM", "HN": "LATAM", "NI": "LATAM", "PA": "LATAM",
    "PE": "LATAM", "PY": "LATAM", "SR": "LATAM", "SV": "LATAM", "UY": "LATAM",
    "VE": "LATAM",

    # Азия
    "JP": "ASIA", "CN": "ASIA", "KR": "ASIA", "IN": "ASIA", "TH": "ASIA",
    "VN": "ASIA", "MY": "ASIA", "SG": "ASIA", "ID": "ASIA", "PH": "ASIA",
    "AU": "ASIA", "NZ": "ASIA", "KZ": "ASIA", "UZ": "ASIA"
}
HEADERS = {
    "host": "www.g2a.com",
    "connection": "keep-alive",
    "sec-ch-ua": "\"Chromium\";v=\"140\", \"Not=A?Brand\";v=\"24\", \"Google Chrome\";v=\"140\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "\"Windows\"",
    "upgrade-insecure-requests": "1",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "sec-fetch-site": "none",
    "sec-fetch-mode": "navigate",
    "sec-fetch-user": "?1",
    "sec-fetch-dest": "document",
    "accept-language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
}


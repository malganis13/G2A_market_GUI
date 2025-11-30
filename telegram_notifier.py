from aiogram import Bot
from g2a_config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
import asyncio


class TelegramNotifier:
    def __init__(self):
        self.bot = Bot(token=TELEGRAM_BOT_TOKEN)

    async def send_sale_notification(self, game_name: str, key_value: str, price: float, prefix: str):
        """Отправка уведомления о продаже"""
        message = (
            f"🎮 <b>Продан ключ!</b>\n\n"
            f"📦 Игра: {game_name}\n"
            f"🔑 Ключ: {key_value}\n"
            f"💰 Цена: €{price:.2f}\n"
            f"👤 Префикс: {prefix}"
        )

        try:
            await self.bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text=message,
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"Ошибка отправки в Telegram: {e}")

    async def close(self):
        await self.bot.session.close()


notifier = TelegramNotifier()
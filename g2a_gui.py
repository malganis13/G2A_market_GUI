import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, simpledialog
import asyncio
import threading
import json
import os
from datetime import datetime
from pathlib import Path
import httpx
import requests
import traceback

# Импорты модулей
from key_manager import KeyManager, G2AOfferCreator
from price_parser import KeyPriceParser
from database import PriceDatabase
from g2a_api_client import G2AApiClient
import g2a_config

# Настройка темы
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class G2AAutomationGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("G2A Automation Tool")
        self.geometry("1400x800")

        # Инициализация компонентов
        self.key_manager = KeyManager()
        self.price_parser = KeyPriceParser()
        self.db = PriceDatabase()
        self.api_client = None

        # Переменные настроек
        self.telegram_enabled = tk.BooleanVar(value=False)
        self.seller_id_var = tk.StringVar(value="")

        # Для хранения данных офферов
        self.offers_data = {}
        
        # ✅ Храним цены конкурентов
        self.competitor_prices = {}
        
        # ✅ Выбранные офферы (чекбоксы)
        self.selected_offers = set()

        # Авто-процесс
        self.auto_process = None
        self.auto_running = False
        self.auto_changer = None

        # Переменная для поиска
        self.search_var = tk.StringVar()

        self.create_widgets()
        self.load_all_configs()

    def create_widgets(self):
        # Табы
        self.tabview = ctk.CTkTabview(self, width=1350, height=750)
        self.tabview.pack(padx=10, pady=10, fill="both", expand=True)

        # Создание вкладок
        self.tab_settings = self.tabview.add("⚙️ Настройки")
        self.tab_auto = self.tabview.add("🤖 Автоизменение + Офферы")
        self.tab_parsing = self.tabview.add("📊 Парсинг")
        self.tab_keys = self.tabview.add("🔑 Ключи")
        self.tab_stats = self.tabview.add("📈 Статистика")

        self.setup_settings_tab()
        self.setup_auto_offers_tab()
        self.setup_parsing_tab()
        self.setup_keys_tab()
        self.setup_stats_tab()

    def setup_settings_tab(self):
        """Вкладка настроек API"""
        frame = ctk.CTkFrame(self.tab_settings)
        frame.pack(fill="both", expand=True, padx=5, pady=5)

        scrollable = ctk.CTkScrollableFrame(frame, width=500, height=550)
        scrollable.pack(fill="both", expand=True, padx=5, pady=5)

        # G2A API Settings
        ctk.CTkLabel(scrollable, text="G2A API Настройки", font=("Arial", 11, "bold")).pack(pady=5)

        self.client_id_var = tk.StringVar()
        self.client_secret_var = tk.StringVar()
        self.client_email_var = tk.StringVar()

        ctk.CTkLabel(scrollable, text="G2A Client ID:", font=("Arial", 12)).pack(pady=5)
        self.client_id_entry = ctk.CTkEntry(scrollable, textvariable=self.client_id_var, width=400, height=26)
        self.client_id_entry.pack(pady=5)

        ctk.CTkLabel(scrollable, text="G2A Client Secret:", font=("Arial", 12)).pack(pady=5)
        self.client_secret_entry = ctk.CTkEntry(scrollable, textvariable=self.client_secret_var, width=400, height=26,
                                                show="*")
        self.client_secret_entry.pack(pady=5)

        ctk.CTkLabel(scrollable, text="G2A Account Email:", font=("Arial", 12)).pack(pady=5)
        self.client_email_entry = ctk.CTkEntry(scrollable, textvariable=self.client_email_var, width=400, height=26)
        self.client_email_entry.pack(pady=5)

        ctk.CTkLabel(scrollable, text="G2A Seller ID (автоматический):", font=("Arial", 12)).pack(pady=5)
        self.seller_id_entry = ctk.CTkEntry(scrollable, textvariable=self.seller_id_var, width=400, height=26, state="disabled")
        self.seller_id_entry.pack(pady=5)
        ctk.CTkLabel(scrollable, text="💡 ID получается автоматически при первой загрузке офферов", font=("Arial", 9), text_color="gray").pack(pady=3)

        # Разделитель
        ctk.CTkLabel(scrollable, text="─" * 60).pack(pady=20)

        # Telegram Settings
        ctk.CTkLabel(scrollable, text="Telegram Уведомления", font=("Arial", 11, "bold")).pack(pady=5)

        self.telegram_token_var = tk.StringVar()
        self.telegram_chat_var = tk.StringVar()

        ctk.CTkLabel(scrollable, text="Bot Token:", font=("Arial", 12)).pack(pady=5)
        self.telegram_token_entry = ctk.CTkEntry(scrollable, textvariable=self.telegram_token_var, width=400, height=26)
        self.telegram_token_entry.pack(pady=5)

        ctk.CTkLabel(scrollable, text="Chat ID:", font=("Arial", 12)).pack(pady=5)
        self.telegram_chat_entry = ctk.CTkEntry(scrollable, textvariable=self.telegram_chat_var, width=400, height=26)
        self.telegram_chat_entry.pack(pady=5)

        self.telegram_checkbox = ctk.CTkSwitch(
            scrollable,
            text="Включить Telegram уведомления",
            variable=self.telegram_enabled,
            font=("Arial", 10)
        )
        self.telegram_checkbox.pack(pady=5)

        # Кнопка сохранения
        ctk.CTkButton(
            scrollable,
            text="💾 Сохранить все настройки",
            command=self.save_all_settings,
            width=300,
            height=50,
            font=("Arial", 16, "bold"),
            fg_color="green",
            hover_color="darkgreen"
        ).pack(pady=10)

    def setup_auto_offers_tab(self):
        """
        ✅ Объединённая вкладка "Автоизменение + Офферы"
        """
        main_container = ctk.CTkFrame(self.tab_auto)
        main_container.pack(fill="both", expand=True, padx=5, pady=5)

        # ========== ВЕРХНЯЯ ПАНЕЛЬ: Глобальные настройки ==========
        top_panel = ctk.CTkFrame(main_container, height=150)
        top_panel.pack(fill="x", padx=5, pady=5)

        ctk.CTkLabel(top_panel, text="🤖 Глобальные настройки автоизменения", font=("Arial", 14, "bold")).pack(pady=5)

        controls_frame = ctk.CTkFrame(top_panel)
        controls_frame.pack(pady=5)

        # Статус
        self.auto_status_label = ctk.CTkLabel(
            controls_frame,
            text="🔴 Остановлено",
            font=("Arial", 13, "bold"),
            text_color="red"
        )
        self.auto_status_label.pack(side="left", padx=10)

        # Кнопки управления
        self.start_auto_btn = ctk.CTkButton(
            controls_frame,
            text="▶️ Запустить",
            command=self.start_auto_price_changing,
            width=150,
            height=40,
            fg_color="green",
            hover_color="darkgreen"
        )
        self.start_auto_btn.pack(side="left", padx=5)

        self.stop_auto_btn = ctk.CTkButton(
            controls_frame,
            text="⏹️ Остановить",
            command=self.stop_auto_price_changing,
            width=150,
            height=40,
            fg_color="red",
            hover_color="darkred",
            state="disabled"
        )
        self.stop_auto_btn.pack(side="left", padx=5)

        ctk.CTkButton(
            controls_frame,
            text="⚙️ Настроить",
            command=self.open_auto_settings_dialog,
            width=150,
            height=40
        ).pack(side="left", padx=5)

        # ========== СРЕДНЯЯ ЧАСТЬ: Таблица офферов ==========
        middle_container = ctk.CTkFrame(main_container)
        middle_container.pack(fill="both", expand=True, padx=5, pady=5)

        # Левая часть - таблица
        left_frame = ctk.CTkFrame(middle_container)
        left_frame.pack(side="left", fill="both", expand=True, padx=5)

        ctk.CTkLabel(left_frame, text="📋 Список офферов", font=("Arial", 12, "bold")).pack(pady=5)

        # Поиск и кнопки
        search_frame = ctk.CTkFrame(left_frame)
        search_frame.pack(pady=5, padx=5, fill="x")

        ctk.CTkLabel(search_frame, text="🔍 Поиск:", font=("Arial", 11)).pack(side="left", padx=5)
        self.search_var.trace("w", self.filter_offers)
        search_entry = ctk.CTkEntry(search_frame, textvariable=self.search_var, width=200, height=30)
        search_entry.pack(side="left", padx=5)

        # ✅ ИСПРАВЛЕНО: Простая кнопка без блокировки
        ctk.CTkButton(
            search_frame,
            text="🔄 Обновить",
            command=self.load_offers,
            width=120,
            height=35
        ).pack(side="left", padx=5)

        # ✅ ТАБЛИЦА С ЧЕКБОКСАМИ
        table_frame = ctk.CTkFrame(left_frame)
        table_frame.pack(fill="both", expand=True, padx=5, pady=5)

        scrollbar = ttk.Scrollbar(table_frame)
        scrollbar.pack(side="right", fill="y")

        # Колонки: ☑️ | Игра | Ваша цена | Конкурент | Порог | Авто
        self.offers_tree = ttk.Treeview(
            table_frame,
            columns=("Select", "Game", "YourPrice", "Competitor", "Threshold", "Auto", "Stock"),
            show="headings",
            height=20,
            yscrollcommand=scrollbar.set
        )
        scrollbar.config(command=self.offers_tree.yview)

        self.offers_tree.heading("Select", text="☑")
        self.offers_tree.heading("Game", text="Игра")
        self.offers_tree.heading("YourPrice", text="Ваша цена")
        self.offers_tree.heading("Competitor", text="Конкурент")
        self.offers_tree.heading("Threshold", text="Порог")
        self.offers_tree.heading("Auto", text="Авто")
        self.offers_tree.heading("Stock", text="Склад")

        self.offers_tree.column("Select", width=40)
        self.offers_tree.column("Game", width=300)
        self.offers_tree.column("YourPrice", width=100)
        self.offers_tree.column("Competitor", width=100)
        self.offers_tree.column("Threshold", width=100)
        self.offers_tree.column("Auto", width=80)
        self.offers_tree.column("Stock", width=80)

        self.offers_tree.pack(fill="both", expand=True)

        # Bind событий
        self.offers_tree.bind("<Button-1>", self.on_tree_click)
        self.offers_tree.bind("<<TreeviewSelect>>", self.on_offer_select)

        # Правая часть - управление
        right_frame = ctk.CTkFrame(middle_container, width=400)
        right_frame.pack(side="right", fill="both", padx=5)

        ctk.CTkLabel(right_frame, text="🎯 Управление оффером", font=("Arial", 12, "bold")).pack(pady=5)

        # Информация о выбранном
        self.selected_offer_label = ctk.CTkLabel(
            right_frame,
            text="Выберите оффер из списка",
            font=("Arial", 10),
            wraplength=350,
            justify="left"
        )
        self.selected_offer_label.pack(pady=10, padx=10)

        # Scrollable для кнопок
        scrollable_right = ctk.CTkScrollableFrame(right_frame, width=360, height=500)
        scrollable_right.pack(fill="both", expand=True, padx=5, pady=5)

        ctk.CTkLabel(scrollable_right, text="Точечные операции:", font=("Arial", 11, "bold")).pack(pady=5)

        ctk.CTkButton(
            scrollable_right,
            text="🔄 Обновить цену конкурента",
            command=self.update_competitor_price,
            width=250,
            height=45
        ).pack(pady=5)

        ctk.CTkButton(
            scrollable_right,
            text="🛡️ Установить минимальный порог",
            command=self.set_threshold_for_selected,
            width=250,
            height=45
        ).pack(pady=5)

        self.auto_toggle_btn = ctk.CTkButton(
            scrollable_right,
            text="🤖 Вкл/Выкл автоизменение",
            command=self.toggle_auto_for_offer,
            width=250,
            height=45
        )
        self.auto_toggle_btn.pack(pady=5)

        ctk.CTkButton(
            scrollable_right,
            text="💰 Изменить цену вручную",
            command=self.change_selected_offer_price,
            width=250,
            height=45
        ).pack(pady=5)

        ctk.CTkLabel(scrollable_right, text="─" * 30).pack(pady=10)
        ctk.CTkLabel(scrollable_right, text="Массовые операции:", font=("Arial", 11, "bold")).pack(pady=5)

        ctk.CTkButton(
            scrollable_right,
            text="☑️ Включить авто для выбранных",
            command=lambda: self.mass_toggle_auto(True),
            width=250,
            height=45,
            fg_color="green"
        ).pack(pady=5)

        ctk.CTkButton(
            scrollable_right,
            text="☐ Выключить авто для выбранных",
            command=lambda: self.mass_toggle_auto(False),
            width=250,
            height=45,
            fg_color="orange"
        ).pack(pady=5)

        ctk.CTkButton(
            scrollable_right,
            text="🛡️ Установить порог для выбранных",
            command=self.set_threshold_for_selected_mass,
            width=250,
            height=45
        ).pack(pady=5)

    def setup_parsing_tab(self):
        """Вкладка парсинга"""
        frame = ctk.CTkFrame(self.tab_parsing)
        frame.pack(fill="both", expand=True, padx=5, pady=5)

        ctk.CTkLabel(frame, text="Парсинг цен G2A", font=("Arial", 11, "bold")).pack(pady=20)

        btn_frame = ctk.CTkFrame(frame)
        btn_frame.pack(pady=20)

        ctk.CTkButton(
            btn_frame,
            text="📊 Обычный парсинг цен",
            command=lambda: self.run_parsing(auto_sell=False),
            width=280,
            height=70,
            font=("Arial", 15)
        ).pack(side="left", padx=10)

        ctk.CTkButton(
            btn_frame,
            text="🚀 Парсинг + автовыставление",
            command=lambda: self.run_parsing(auto_sell=True),
            width=280,
            height=70,
            font=("Arial", 15)
        ).pack(side="left", padx=10)

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ctk.CTkProgressBar(frame, variable=self.progress_var, width=500, height=16)
        self.progress_bar.pack(pady=20)
        self.progress_bar.set(0)

        self.log_text = ctk.CTkTextbox(frame, width=680, height=380, font=("Courier", 8))
        self.log_text.pack(pady=20)

    def setup_keys_tab(self):
        """Вкладка ключей"""
        frame = ctk.CTkFrame(self.tab_keys)
        frame.pack(fill="both", expand=True, padx=5, pady=5)

        ctk.CTkLabel(frame, text="Управление ключами", font=("Arial", 11, "bold")).pack(pady=20)

        btn_frame = ctk.CTkFrame(frame)
        btn_frame.pack(pady=10)

        ctk.CTkButton(
            btn_frame,
            text="📁 Добавить ключи из файла",
            command=self.add_keys_from_file,
            width=250,
            height=60
        ).pack(side="left", padx=10)

        ctk.CTkButton(
            btn_frame,
            text="📂 Добавить из папки",
            command=self.add_keys_from_folder,
            width=250,
            height=60
        ).pack(side="left", padx=10)

        ctk.CTkButton(
            btn_frame,
            text="📊 Обновить статистику",
            command=self.show_keys_stats,
            width=250,
            height=60
        ).pack(side="left", padx=10)

        self.stats_scrollable = ctk.CTkScrollableFrame(frame, width=750, height=520)
        self.stats_scrollable.pack(pady=20, fill="both", expand=True)

        self.stats_label = ctk.CTkLabel(
            self.stats_scrollable,
            text="Нажмите 'Обновить статистику' для загрузки...",
            font=("Courier", 9),
            justify="left",
            anchor="w"
        )
        self.stats_label.pack(pady=20, padx=20, fill="both")

    def setup_stats_tab(self):
        """Вкладка статистики"""
        frame = ctk.CTkFrame(self.tab_stats)
        frame.pack(fill="both", expand=True, padx=5, pady=5)

        ctk.CTkLabel(frame, text="Статистика изменений цен", font=("Arial", 11, "bold")).pack(pady=20)

        period_frame = ctk.CTkFrame(frame)
        period_frame.pack(pady=10)

        ctk.CTkButton(
            period_frame,
            text="За сегодня",
            command=lambda: self.load_price_stats("day"),
            width=160,
            height=45
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            period_frame,
            text="За 7 дней",
            command=lambda: self.load_price_stats("week"),
            width=160,
            height=45
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            period_frame,
            text="За 30 дней",
            command=lambda: self.load_price_stats("month"),
            width=160,
            height=45
        ).pack(side="left", padx=5)

        self.stats_text = ctk.CTkTextbox(frame, width=700, height=480, font=("Courier", 8))
        self.stats_text.pack(pady=20)

    # ==================== МЕТОДЫ ====================

    def load_all_configs(self):
        """Загрузка всех конфигураций при старте"""
        self.client_id_var.set(g2a_config.G2A_CLIENT_ID)
        self.client_secret_var.set(g2a_config.G2A_CLIENT_SECRET)
        self.client_email_var.set(g2a_config.G2A_CLIENT_EMAIL)
        self.telegram_token_var.set(g2a_config.TELEGRAM_BOT_TOKEN)
        self.telegram_chat_var.set(g2a_config.TELEGRAM_CHAT_ID)
        self.seller_id_var.set(g2a_config.G2A_SELLER_ID)
        print("✅ Настройки загружены")

    def save_all_settings(self):
        """Сохранение всех настроек"""
        client_id = self.client_id_var.get().strip()
        client_secret = self.client_secret_var.get().strip()
        client_email = self.client_email_var.get().strip()
        telegram_token = self.telegram_token_var.get().strip()
        telegram_chat = self.telegram_chat_var.get().strip()

        if not client_id or not client_secret or not client_email:
            messagebox.showerror("Ошибка", "Заполните все обязательные поля G2A")
            return

        config_data = {
            "G2A_CLIENT_ID": client_id,
            "G2A_CLIENT_SECRET": client_secret,
            "G2A_CLIENT_EMAIL": client_email,
            "G2A_SELLER_ID": self.seller_id_var.get(),
            "TELEGRAM_BOT_TOKEN": telegram_token,
            "TELEGRAM_CHAT_ID": telegram_chat,
            "TELEGRAM_ENABLED": self.telegram_enabled.get()
        }

        try:
            with open("g2a_config_saved.json", "w", encoding='utf-8') as f:
                json.dump(config_data, f, indent=4, ensure_ascii=False)

            g2a_config.reload_config()

            if telegram_token and telegram_chat:
                from telegram_notifier import notifier
                notifier.update_credentials(telegram_token, telegram_chat)

            messagebox.showinfo("Успех", "✅ Настройки сохранены!")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить: {e}")

    def load_offers(self):
        """✅ ИСПРАВЛЕНО: Взята рабочая логика из G2A_Rabochee"""
        
        def run():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                self.api_client = G2AApiClient()

                print("Получение токена G2A...")
                loop.run_until_complete(self.api_client.get_token())
                print("✅ Токен получен")

                print("Загрузка офферов...")
                result = loop.run_until_complete(self.api_client.get_offers())

                if result.get("success"):
                    # Извлекаем seller_id
                    if result.get("offers_cache"):
                        first_offer = next(iter(result["offers_cache"].values()), None)
                        if first_offer and first_offer.get("seller_id"):
                            seller_id = first_offer.get("seller_id")
                            self.seller_id_var.set(seller_id)
                            g2a_config.G2A_SELLER_ID = seller_id
                            print(f"✅ Seller ID установлен: {seller_id}")

                    self.offers_data = result.get("offers_cache", {})

                    # Обновляем таблицу в GUI потоке
                    self.after(0, self.refresh_offers_table)

                    print(f"✅ Загружено {len(self.offers_data)} офферов")
                    self.after(0, lambda: messagebox.showinfo("Готово", f"Загружено {len(self.offers_data)} офферов"))
                else:
                    error_msg = result.get("error", "Неизвестная ошибка")
                    print(f"❌ Ошибка: {error_msg}")
                    # ✅ ИСПРАВЛЕНО: Используем error_msg вместо e
                    def show_error():
                        messagebox.showerror("Ошибка", f"Не удалось загрузить офферы:\n{error_msg}")
                    self.after(0, show_error)

            except Exception as e:
                print(f"❌ Исключение: {e}")
                traceback.print_exc()
                # ✅ ИСПРАВЛЕНО: Используем именованную функцию
                error_message = str(e)
                def show_exception():
                    messagebox.showerror("Ошибка", f"Ошибка загрузки офферов:\n{error_message}")
                self.after(0, show_exception)
            finally:
                loop.close()

        threading.Thread(target=run, daemon=True).start()

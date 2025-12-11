# 🚀 ИНСТРУКЦИЯ ПО ОБНОВЛЕНИЮ G2A_GUI

## ✅ ЧТО БУДЕТ ИЗМЕНЕНО:

### 1️⃣ УДАЛЕНИЕ ВКЛАДКИ "🎮 ОФФЕРЫ"
В `create_widgets()` удалить строку:
```python
self.tab_offers = self.tabview.add("🎮 Офферы")
```

Удалить весь метод:
```python
def setup_offers_tab(self):
    # УДАЛИТЬ ВСЁ!
```

---

### 2️⃣ ПЕРЕИМЕНОВАНИЕ ВКЛАДКИ "АВТОИЗМЕНЕНИЕ"

В `create_widgets()` изменить:
```python
# БЫЛО:
self.tab_auto = self.tabview.add("🤖 Автоизменение")

# СТАЛО:
self.tab_auto = self.tabview.add("🤖 Офферы + Авто")
```

---

### 3️⃣ НОВАЯ СТРУКТУРА `setup_auto_tab()`

ЗАМЕНИТЬ ВЕСЬ метод `setup_auto_tab()` на:

```python
def setup_auto_tab(self):
    """
    ✅ НОВАЯ ВЕРСИЯ: Объединённая вкладка Офферы + Автоизменение
    """
    main_container = ctk.CTkFrame(self.tab_auto)
    main_container.pack(fill="both", expand=True, padx=10, pady=10)

    # ========== ЛЕВАЯ ЧАСТЬ: СПИСОК ОФФЕРОВ ==========
    left_frame = ctk.CTkFrame(main_container)
    left_frame.pack(side="left", fill="both", expand=True, padx=5)

    # Заголовок
    header_frame = ctk.CTkFrame(left_frame)
    header_frame.pack(fill="x", padx=10, pady=10)

    ctk.CTkLabel(
        header_frame,
        text="🎮 Список офферов (с автоизменением)",
        font=("Arial", 18, "bold")
    ).pack(side="left", padx=10)

    ctk.CTkButton(
        header_frame,
        text="🔄 Обновить",
        command=self.load_offers_with_prices,
        width=150,
        height=35,
        font=("Arial", 13, "bold")
    ).pack(side="right", padx=5)

    # Поиск
    search_frame = ctk.CTkFrame(left_frame)
    search_frame.pack(fill="x", padx=10, pady=5)

    ctk.CTkLabel(search_frame, text="🔍 Поиск:", font=("Arial", 12)).pack(side="left", padx=5)
    self.search_var.trace("w", self.filter_offers_auto_tab)
    search_entry = ctk.CTkEntry(search_frame, textvariable=self.search_var, width=300, height=35)
    search_entry.pack(side="left", padx=5)

    ctk.CTkButton(
        search_frame,
        text="❌ Очистить",
        command=lambda: self.search_var.set(""),
        width=100,
        height=35
    ).pack(side="left", padx=5)

    # Таблица офферов
    table_frame = ctk.CTkFrame(left_frame)
    table_frame.pack(fill="both", expand=True, padx=10, pady=10)

    scrollbar_y = ttk.Scrollbar(table_frame, orient="vertical")
    scrollbar_y.pack(side="right", fill="y")

    scrollbar_x = ttk.Scrollbar(table_frame, orient="horizontal")
    scrollbar_x.pack(side="bottom", fill="x")

    # ✅ НОВЫЕ КОЛОНКИ!
    self.auto_offers_tree = ttk.Treeview(
        table_frame,
        columns=("Game", "Price", "Competitor", "Floor", "Stock", "Auto", "Status"),
        show="tree headings",  # ✅ Показываем чекбоксы!
        height=25,
        selectmode="extended",  # ✅ Множественный выбор!
        yscrollcommand=scrollbar_y.set,
        xscrollcommand=scrollbar_x.set
    )
    scrollbar_y.config(command=self.auto_offers_tree.yview)
    scrollbar_x.config(command=self.auto_offers_tree.xview)

    # Настройка колонок
    self.auto_offers_tree.heading("#0", text="✅")
    self.auto_offers_tree.heading("Game", text="🎮 Игра")
    self.auto_offers_tree.heading("Price", text="💰 Цена")
    self.auto_offers_tree.heading("Competitor", text="🔴 Мин. конкурент")
    self.auto_offers_tree.heading("Floor", text="🛡️ Порог")
    self.auto_offers_tree.heading("Stock", text="📦 Stock")
    self.auto_offers_tree.heading("Auto", text="🤖 Авто")
    self.auto_offers_tree.heading("Status", text="✅ Статус")

    self.auto_offers_tree.column("#0", width=40, anchor="center")
    self.auto_offers_tree.column("Game", width=300)
    self.auto_offers_tree.column("Price", width=80, anchor="center")
    self.auto_offers_tree.column("Competitor", width=120, anchor="center")
    self.auto_offers_tree.column("Floor", width=100, anchor="center")
    self.auto_offers_tree.column("Stock", width=70, anchor="center")
    self.auto_offers_tree.column("Auto", width=80, anchor="center")
    self.auto_offers_tree.column("Status", width=100, anchor="center")

    self.auto_offers_tree.pack(fill="both", expand=True)

    # ========== ПРАВАЯ ЧАСТЬ: УПРАВЛЕНИЕ ==========
    right_frame = ctk.CTkFrame(main_container, width=500)
    right_frame.pack(side="right", fill="both", padx=5)

    scrollable_right = ctk.CTkScrollableFrame(right_frame, width=470, height=800)
    scrollable_right.pack(fill="both", expand=True, padx=5, pady=5)

    # --- Глобальные настройки ---
    ctk.CTkLabel(
        scrollable_right,
        text="⚙️ Глобальные настройки",
        font=("Arial", 16, "bold")
    ).pack(pady=15)

    # Главный переключатель
    self.auto_enabled_var = tk.BooleanVar(value=False)
    ctk.CTkSwitch(
        scrollable_right,
        text="🤖 Автоизменение (глобально)",
        variable=self.auto_enabled_var,
        font=("Arial", 13, "bold")
    ).pack(pady=10)

    # Интервал
    interval_frame = ctk.CTkFrame(scrollable_right)
    interval_frame.pack(pady=10, fill="x", padx=10)

    ctk.CTkLabel(interval_frame, text="⏱️ Интервал:", font=("Arial", 12)).pack()

    self.auto_interval_var = tk.IntVar(value=1800)
    self.interval_label = ctk.CTkLabel(interval_frame, text="30 мин", width=80)
    self.interval_label.pack(pady=5)

    interval_slider = ctk.CTkSlider(
        interval_frame,
        from_=300,
        to=7200,
        variable=self.auto_interval_var,
        width=300
    )
    interval_slider.pack(pady=5)

    def update_interval(value):
        minutes = int(float(value)) // 60
        self.interval_label.configure(text=f"{minutes} мин")

    interval_slider.configure(command=update_interval)

    # Снижение
    undercut_frame = ctk.CTkFrame(scrollable_right)
    undercut_frame.pack(pady=10, fill="x", padx=10)

    ctk.CTkLabel(undercut_frame, text="💰 Снижение от конкурента (EUR):", font=("Arial", 12)).pack()
    self.auto_undercut_var = tk.DoubleVar(value=0.01)
    ctk.CTkEntry(undercut_frame, textvariable=self.auto_undercut_var, width=150).pack(pady=5)

    # Мин/макс цена
    price_range_frame = ctk.CTkFrame(scrollable_right)
    price_range_frame.pack(pady=10, fill="x", padx=10)

    row1 = ctk.CTkFrame(price_range_frame)
    row1.pack(fill="x", pady=3)
    ctk.CTkLabel(row1, text="🛡️ Мин. цена (глобально):", font=("Arial", 11)).pack(side="left", padx=5)
    self.auto_min_price_var = tk.DoubleVar(value=0.1)
    ctk.CTkEntry(row1, textvariable=self.auto_min_price_var, width=100).pack(side="left", padx=5)

    row2 = ctk.CTkFrame(price_range_frame)
    row2.pack(fill="x", pady=3)
    ctk.CTkLabel(row2, text="📊 Макс. цена:", font=("Arial", 11)).pack(side="left", padx=5)
    self.auto_max_price_var = tk.DoubleVar(value=100.0)
    ctk.CTkEntry(row2, textvariable=self.auto_max_price_var, width=100).pack(side="left", padx=5)

    # Дневной лимит
    limit_frame = ctk.CTkFrame(scrollable_right)
    limit_frame.pack(pady=10, fill="x", padx=10)

    ctk.CTkLabel(limit_frame, text="🔢 Макс. изменений/день:", font=("Arial", 12)).pack()
    self.auto_daily_limit_var = tk.IntVar(value=20)
    ctk.CTkEntry(limit_frame, textvariable=self.auto_daily_limit_var, width=150).pack(pady=5)

    # Telegram
    self.auto_telegram_var = tk.BooleanVar(value=False)
    ctk.CTkSwitch(
        scrollable_right,
        text="📢 Telegram уведомления",
        variable=self.auto_telegram_var,
        font=("Arial", 12)
    ).pack(pady=10)

    # Кнопка сохранения
    ctk.CTkButton(
        scrollable_right,
        text="💾 Сохранить настройки",
        command=self.save_auto_settings,
        width=200,
        height=45,
        font=("Arial", 13, "bold"),
        fg_color="green",
        hover_color="darkgreen"
    ).pack(pady=15)

    ctk.CTkLabel(scrollable_right, text="─" * 40).pack(pady=10)

    # --- Управление автоизменением ---
    ctk.CTkLabel(
        scrollable_right,
        text="🎮 Управление автоизменением",
        font=("Arial", 15, "bold")
    ).pack(pady=10)

    self.auto_status_label = ctk.CTkLabel(
        scrollable_right,
        text="🔴 Остановлено",
        font=("Arial", 14, "bold"),
        text_color="red"
    )
    self.auto_status_label.pack(pady=5)

    self.start_auto_btn = ctk.CTkButton(
        scrollable_right,
        text="▶️ Запустить",
        command=self.start_auto_price_changing,
        width=200,
        height=50,
        font=("Arial", 14, "bold"),
        fg_color="green",
        hover_color="darkgreen"
    )
    self.start_auto_btn.pack(pady=5)

    self.stop_auto_btn = ctk.CTkButton(
        scrollable_right,
        text="⏹️ Остановить",
        command=self.stop_auto_price_changing,
        width=200,
        height=50,
        font=("Arial", 14, "bold"),
        fg_color="red",
        hover_color="darkred",
        state="disabled"
    )
    self.stop_auto_btn.pack(pady=5)

    ctk.CTkLabel(scrollable_right, text="─" * 40).pack(pady=10)

    # --- Точечное управление ---
    ctk.CTkLabel(
        scrollable_right,
        text="🎯 Точечное управление",
        font=("Arial", 14, "bold")
    ).pack(pady=10)

    ctk.CTkButton(
        scrollable_right,
        text="🛡️ Установить порог",
        command=self.set_individual_floor_price,
        width=220,
        height=45
    ).pack(pady=5)

    ctk.CTkButton(
        scrollable_right,
        text="💰 Изменить цену",
        command=self.change_selected_offer_price,
        width=220,
        height=45
    ).pack(pady=5)

    ctk.CTkButton(
        scrollable_right,
        text="📦 Изменить stock",
        command=self.change_selected_offer_stock,
        width=220,
        height=45
    ).pack(pady=5)

    ctk.CTkButton(
        scrollable_right,
        text="🔄 Проверить конкурента",
        command=self.check_competitor_for_selected,
        width=220,
        height=45
    ).pack(pady=5)

    ctk.CTkLabel(scrollable_right, text="─" * 40).pack(pady=10)

    # --- Массовое управление ---
    ctk.CTkLabel(
        scrollable_right,
        text="🔢 Массовое управление (Ctrl+Click)",
        font=("Arial", 14, "bold"),
        wraplength=200
    ).pack(pady=10)

    ctk.CTkButton(
        scrollable_right,
        text="✅ Включить авто",
        command=self.bulk_enable_auto,
        width=220,
        height=45,
        fg_color="green",
        hover_color="darkgreen"
    ).pack(pady=5)

    ctk.CTkButton(
        scrollable_right,
        text="❌ Выключить авто",
        command=self.bulk_disable_auto,
        width=220,
        height=45,
        fg_color="#CC0000",
        hover_color="#990000"
    ).pack(pady=5)

    ctk.CTkButton(
        scrollable_right,
        text="🛡️ Установить порог для всех",
        command=self.bulk_set_floor_price,
        width=220,
        height=45
    ).pack(pady=5)
```

---

## 🛠️ ДАЛЕЕ НУЖНО ДОБАВИТЬ НОВЫЕ МЕТОДЫ:

Я создам ОТДЕЛЬНЫЙ файл с новыми методами!
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Вкладка управления ключами
"""

import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QLineEdit, QComboBox,
    QGroupBox, QFileDialog, QMessageBox, QHeaderView
)
from PyQt6.QtCore import Qt, pyqtSignal
from database import Database


class KeysTab(QWidget):
    """Вкладка управления ключами"""
    
    keys_updated = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.init_ui()
        self.load_keys()
        
    def init_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Заголовок
        header = QLabel("🔑 Keys Management")
        header.setProperty("class", "header")
        layout.addWidget(header)
        
        # Группа добавления ключа
        add_group = QGroupBox("➕ Add New Key")
        add_layout = QVBoxLayout()
        
        # Поля ввода
        form_layout = QHBoxLayout()
        
        self.game_input = QLineEdit()
        self.game_input.setPlaceholderText("Game Name")
        form_layout.addWidget(QLabel("Game:"))
        form_layout.addWidget(self.game_input)
        
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("XXXXX-XXXXX-XXXXX")
        form_layout.addWidget(QLabel("Key:"))
        form_layout.addWidget(self.key_input)
        
        self.platform_combo = QComboBox()
        self.platform_combo.addItems(["Steam", "Epic Games", "Origin", "Uplay", "GOG", "Other"])
        form_layout.addWidget(QLabel("Platform:"))
        form_layout.addWidget(self.platform_combo)
        
        self.region_combo = QComboBox()
        self.region_combo.addItems(["Global", "EU", "US", "RU", "Asia", "Other"])
        form_layout.addWidget(QLabel("Region:"))
        form_layout.addWidget(self.region_combo)
        
        add_layout.addLayout(form_layout)
        
        # Кнопки
        buttons_layout = QHBoxLayout()
        
        add_btn = QPushButton("➕ Add Key")
        add_btn.clicked.connect(self.add_key)
        buttons_layout.addWidget(add_btn)
        
        import_btn = QPushButton("📁 Import from File")
        import_btn.clicked.connect(self.import_keys)
        buttons_layout.addWidget(import_btn)
        
        clear_btn = QPushButton("🗑️ Clear Form")
        clear_btn.clicked.connect(self.clear_form)
        buttons_layout.addWidget(clear_btn)
        
        buttons_layout.addStretch()
        add_layout.addLayout(buttons_layout)
        
        add_group.setLayout(add_layout)
        layout.addWidget(add_group)
        
        # Таблица ключей
        keys_group = QGroupBox("📋 Keys List")
        keys_layout = QVBoxLayout()
        
        # Поиск
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search by game name...")
        self.search_input.textChanged.connect(self.filter_keys)
        search_layout.addWidget(self.search_input)
        
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.load_keys)
        refresh_btn.setMaximumWidth(100)
        search_layout.addWidget(refresh_btn)
        
        keys_layout.addLayout(search_layout)
        
        # Таблица
        self.keys_table = QTableWidget()
        self.keys_table.setColumnCount(6)
        self.keys_table.setHorizontalHeaderLabels([
            "Game", "Key", "Platform", "Region", "Status", "Actions"
        ])
        self.keys_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.keys_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.keys_table.setAlternatingRowColors(True)
        self.keys_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        keys_layout.addWidget(self.keys_table)
        
        keys_group.setLayout(keys_layout)
        layout.addWidget(keys_group)
        
    def add_key(self):
        """Добавление ключа"""
        game_name = self.game_input.text().strip()
        key = self.key_input.text().strip()
        platform = self.platform_combo.currentText()
        region = self.region_combo.currentText()
        
        if not game_name or not key:
            QMessageBox.warning(self, "Warning", "Please fill in Game Name and Key fields!")
            return
        
        try:
            self.db.add_key(game_name, key, platform, region)
            QMessageBox.information(self, "Success", f"Key added successfully!\n{game_name} - {platform}")
            self.clear_form()
            self.load_keys()
            self.keys_updated.emit()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to add key:\n{str(e)}")
    
    def import_keys(self):
        """Импорт ключей из файла"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Keys File",
            "",
            "Text Files (*.txt);;All Files (*)"
        )
        
        if not file_path:
            return
        
        try:
            imported = 0
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    # Формат: Game Name | KEY | Platform | Region
                    parts = [p.strip() for p in line.split('|')]
                    if len(parts) >= 2:
                        game_name = parts[0]
                        key = parts[1]
                        platform = parts[2] if len(parts) > 2 else "Steam"
                        region = parts[3] if len(parts) > 3 else "Global"
                        
                        try:
                            self.db.add_key(game_name, key, platform, region)
                            imported += 1
                        except Exception as e:
                            print(f"Failed to import key: {e}")
            
            QMessageBox.information(
                self,
                "Import Complete",
                f"Successfully imported {imported} keys!"
            )
            self.load_keys()
            self.keys_updated.emit()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to import keys:\n{str(e)}")
    
    def clear_form(self):
        """Очистка формы"""
        self.game_input.clear()
        self.key_input.clear()
        self.platform_combo.setCurrentIndex(0)
        self.region_combo.setCurrentIndex(0)
    
    def load_keys(self):
        """Загрузка ключей в таблицу"""
        try:
            keys = self.db.get_all_keys()
            self.keys_table.setRowCount(len(keys))
            
            for row, key in enumerate(keys):
                self.keys_table.setItem(row, 0, QTableWidgetItem(key['game_name']))
                self.keys_table.setItem(row, 1, QTableWidgetItem(key['key_code']))
                self.keys_table.setItem(row, 2, QTableWidgetItem(key['platform']))
                self.keys_table.setItem(row, 3, QTableWidgetItem(key['region']))
                
                # Status
                status = "Available" if key['status'] == 'available' else "Sold"
                status_item = QTableWidgetItem(status)
                if key['status'] == 'available':
                    status_item.setForeground(Qt.GlobalColor.green)
                else:
                    status_item.setForeground(Qt.GlobalColor.red)
                self.keys_table.setItem(row, 4, status_item)
                
                # Actions button
                delete_btn = QPushButton("🗑️ Delete")
                delete_btn.setProperty("class", "danger")
                delete_btn.clicked.connect(lambda checked, k=key: self.delete_key(k))
                self.keys_table.setCellWidget(row, 5, delete_btn)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load keys:\n{str(e)}")
    
    def filter_keys(self):
        """Фильтрация ключей по поиску"""
        search_text = self.search_input.text().lower()
        
        for row in range(self.keys_table.rowCount()):
            game_name = self.keys_table.item(row, 0).text().lower()
            should_show = search_text in game_name
            self.keys_table.setRowHidden(row, not should_show)
    
    def delete_key(self, key):
        """Удаление ключа"""
        reply = QMessageBox.question(
            self,
            'Delete Key',
            f"Are you sure you want to delete this key?\n{key['game_name']} - {key['key_code']}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.db.delete_key(key['id'])
                QMessageBox.information(self, "Success", "Key deleted successfully!")
                self.load_keys()
                self.keys_updated.emit()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete key:\n{str(e)}")
    
    def refresh(self):
        """Обновление списка ключей"""
        self.load_keys()

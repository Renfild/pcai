#!/usr/bin/env python3
"""
Скрипт быстрой установки и запуска ИИ-ассистента для инженерного факультета ГрГУ
"""

import os
import sys
import subprocess
import platform
from pathlib import Path


def check_python_version():
    """Проверяет версию Python"""
    if sys.version_info < (3, 9):
        print(f"Ошибка: Требуется Python 3.9 или выше. У вас {sys.version}")
        return False
    return True


def install_requirements():
    """Устанавливает зависимости из requirements.txt"""
    print("Устанавливаю зависимости...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✓ Зависимости установлены")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Ошибка установки зависимостей: {e}")
        return False


def create_env_file():
    """Создает .env файл если его нет"""
    env_file = Path(".env")
    if not env_file.exists():
        print("Создаю .env файл...")
        example_env = Path(".env.example")
        if example_env.exists():
            env_file.write_text(example_env.read_text())
            print("✓ .env файл создан")
        else:
            print("⚠ .env.example не найден, пропускаю создание .env")
    else:
        print("✓ .env файл уже существует")


def create_directories():
    """Создает необходимые директории"""
    dirs_to_create = ["./uploads", "./db_storage"]
    for dir_path in dirs_to_create:
        Path(dir_path).mkdir(exist_ok=True)
    print("✓ Необходимые директории созданы")


def main():
    print("🚀 Установка ИИ-ассистента для инженерного факультета ГрГУ")
    print("=" * 60)
    
    # Проверяем версию Python
    if not check_python_version():
        sys.exit(1)
    
    # Создаем директории
    create_directories()
    
    # Создаем .env файл
    create_env_file()
    
    # Устанавливаем зависимости
    if not install_requirements():
        print("\n✗ Установка завершена с ошибками")
        sys.exit(1)
    
    print("\n✓ Установка завершена успешно!")
    print("\n📋 Для запуска приложения выполните:")
    print("   streamlit run src/app.py")
    print("\n🌐 Приложение будет доступно по адресу: http://localhost:8501")


if __name__ == "__main__":
    main()
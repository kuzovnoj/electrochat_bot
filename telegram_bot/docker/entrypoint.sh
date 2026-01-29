#!/bin/bash

# Ожидание запуска PostgreSQL (только для контейнера бота)
if [ "$1" = "bot" ]; then
    echo "Waiting for PostgreSQL to start..."
    while ! nc -z postgres 5432; do
        sleep 1
    done
    echo "PostgreSQL started"
fi

# Запуск приложения
if [ "$1" = "bot" ]; then
    echo "Starting Telegram Bot..."
    exec python main.py
elif [ "$1" = "debug" ]; then
    echo "Starting in debug mode..."
    exec python debug.py
else
    echo "Please specify mode: 'bot' or 'debug'"
    exit 1
fi
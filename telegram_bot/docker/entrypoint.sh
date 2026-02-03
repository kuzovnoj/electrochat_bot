#!/bin/bash

# Ожидание запуска PostgreSQL (простой вариант на чистом bash)
wait_for_postgres() {
    echo "Waiting for PostgreSQL to start..."
    
    # Простая задержка на 5 секунд
    sleep 5
    
    # Проверяем доступность порта с помощью встроенных средств bash
    local host="postgres"
    local port=5432
    local timeout=30
    local start_time=$(date +%s)
    
    while true; do
        # Используем bash встроенные средства для проверки порта
        (timeout 1 bash -c "cat < /dev/null > /dev/tcp/$host/$port") 2>/dev/null
        
        if [[ $? -eq 0 ]]; then
            echo "PostgreSQL started successfully"
            return 0
        fi
        
        local current_time=$(date +%s)
        local elapsed=$((current_time - start_time))
        
        if [[ $elapsed -ge $timeout ]]; then
            echo "Timeout waiting for PostgreSQL"
            return 1
        fi
        
        echo "Still waiting for PostgreSQL... ($elapsed/$timeout seconds)"
        sleep 2
    done
}

# Запуск приложения
if [ "$1" = "bot" ]; then
    wait_for_postgres
    if [ $? -ne 0 ]; then
        echo "Failed to connect to PostgreSQL. Exiting."
        exit 1
    fi
    
    echo "Starting Telegram Bot..."
    exec python main.py
    
elif [ "$1" = "debug" ]; then
    wait_for_postgres
    if [ $? -ne 0 ]; then
        echo "Failed to connect to PostgreSQL. Exiting."
        exit 1
    fi
    
    echo "Starting in debug mode..."
    exec python debug.py
    
else
    echo "Please specify mode: 'bot' or 'debug'"
    exit 1
fi
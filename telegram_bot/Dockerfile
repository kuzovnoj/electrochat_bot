FROM python:3.11-slim

WORKDIR /app

# Установка зависимостей системы (добавляем netcat-openbsd)
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Предпочитать IPv4 при dual-stack (меньше сбоев, если IPv6 до цели недоступен)
RUN printf '\n# elbot: prefer IPv4 for getaddrinfo\nprecedence ::ffff:0:0/96  100\n' >> /etc/gai.conf

# Копирование requirements.txt
COPY requirements.txt .

# Установка Python зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода
COPY . .

# Создание entrypoint скрипта
RUN chmod +x /app/docker/entrypoint.sh

# Запуск приложения
ENTRYPOINT ["/app/docker/entrypoint.sh"]
#!/bin/bash

# Проверка аргументов
if [ -z "$1" ]; then
    echo "Usage: $0 <service_name>"
    exit 1
fi

SERVICE_NAME=$1

# Получаем список контейнеров для указанного сервиса
CONTAINERS=$(docker ps --filter "name=$SERVICE_NAME" --format "{{.Names}}")

if [ -z "$CONTAINERS" ]; then
    echo "No running containers found for service: $SERVICE_NAME"
    exit 1
fi

# Если найден несколько контейнеров, используем первый
CONTAINER=$(echo "$CONTAINERS" | head -n 1)

docker exec -it $CONTAINER bash
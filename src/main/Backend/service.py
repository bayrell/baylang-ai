import sqlite3
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

executor = ThreadPoolExecutor(max_workers=1)


def get_current_datetime():
    """
    Получить дату по UTC
    """
    utc_now = datetime.now(timezone.utc)
    formatted_time = utc_now.strftime("%Y-%m-%d %H:%M:%S")
    return formatted_time


def get_connection():
    DB_PATH = "/data/db/baylang.db"
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode = WAL;")
    return connection


def sync_execute(query, params):
    """
    Синхронная функция для выполнения SQL запроса
    """
    connection = get_connection()
    cursor = connection.cursor()
    try:
        if params is None:
            params=[]
        cursor.execute(query, params)
        connection.commit()
    finally:
        connection.close()


def sync_execute_insert(query, params):
    """
    Синхронная функция для выполнения SQL запроса
    """
    connection = get_connection()
    cursor = connection.cursor()
    try:
        if params is None:
            params=[]
        cursor.execute(query, params)
        connection.commit()
        return cursor.lastrowid
    finally:
        connection.close()


def sync_execute_fetch(query, params, one_row):
    """
    Синхронная функция для выполнения SQL запроса
    """
    connection = get_connection()
    cursor = connection.cursor()
    try:
        if params is None:
            params=[]
        cursor.execute(query, params)
        if one_row:
            return cursor.fetchone()
        return cursor.fetchall()
    finally:
        connection.close()


async def execute(sql, params=None):
    """
    Асинхронная обертка для выполнения SQL запроса
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(executor, sync_execute, sql, params)


async def execute_insert(sql, params=None):
    """
    Асинхронная обертка для выполнения SQL запроса
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(executor, sync_execute_insert, sql, params)


async def execute_fetch(sql, params=None, one_row=False):
    """
    Асинхронная обертка для выполнения SQL запроса
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(executor, sync_execute_fetch, sql, params, one_row)


async def create_chat(name: str):
    """
    Функция для создания чата
    """
    gmtime_now = get_current_datetime()
    return await execute_insert(
        "INSERT INTO chats (name, gmtime_created, gmtime_updated) VALUES (?, ?, ?)",
        (name, gmtime_now, gmtime_now)
    )


async def delete_chat(id):
    """
    Функция удалить чат по id
    """
    await execute("delete from messages where chat_id=?", (id,))
    await execute("delete from chats where id=?", (id,))


async def get_chat_by_id(id):
    """
    Получить чат по id
    """
    return await execute_fetch("select * from chats where id=?", (id,), True)


async def get_chat_items():
    """
    Получить список всех чатов
    """
    
    items = await execute_fetch("select * from chats")
    if not items:
        return []
    
    index = {}
    items_id = []
    result = []
    for pos, item in enumerate(items):
        item_id = item["id"]
        index[item_id] = pos
        item = dict(item)
        item["messages"] = []
        items_id.append(item_id)
        result.append(item)
    
    # Получаем все сообщения для этих чатов
    query_messages = f"""
        SELECT * FROM messages
        WHERE chat_id IN ({','.join(['?'] * len(items_id))})
        ORDER BY chat_id, gmtime_created;
    """
    messages = await execute_fetch(query_messages, items_id)
    
    for message in messages:
        chat_id = message["chat_id"]
        chat_pos = index[chat_id] if chat_id in index else None
        if pos is not None:
            result[chat_pos]["messages"].append(message)
    
    return result


async def add_message(chat_id: int, sender: str, text: str):
    """
    Функция для добавления сообщения
    """
    gmtime_now = get_current_datetime()
    return await execute_insert(
        "INSERT INTO messages (chat_id, sender, text, gmtime_created, gmtime_updated) VALUES (?, ?, ?, ?, ?)",
        (chat_id, sender, text, gmtime_now, gmtime_now)
    )


async def get_message_by_id(id):
    """
    Получить чат по id
    """
    return await execute_fetch("select * from messages where id=?", (id,), True)


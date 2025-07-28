import asyncio, threading
import mysql.connector
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor()

class Database:
    
    def __init__(self):
        self.host = ""
        self.user = ""
        self.password = ""
        self.database = ""
        self.connection = threading.local()
    
    def escape_field(self, field):
    
        """
        Escape field
        """
        if field == "*":
            return field
        if field[0] != "`":
            return "`" + field + "`"
        return field

    def join_fields(self, fields):
        
        """
        Join fields
        """
        
        fields = list(map(self.escape_field, fields))
        return ",".join(fields)
    
    def connect(self):
        connection = mysql.connector.connect(
            host=self.host,
            user=self.user,
            password=self.password,
            database=self.database,
            autocommit=True,
        )
        cursor = connection.cursor()
        try:
            cursor.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED")
            cursor.execute("SET NAMES utf8mb4")
            cursor.execute("SET CHARACTER SET utf8mb4")
            connection.commit()
        finally:
            cursor.close()
        self.connection.value = connection
        return connection
    
    def get_connection_value(self):
        return self.connection.value if hasattr(self.connection, "value") else None
    
    def reconnect_if_needed(self):
        connection = self.get_connection_value()
        try:
            if not connection or not connection.is_connected():
                self.connect()
        except mysql.connector.InternalError as e:
            connection.disconnect()
            self.connect()
    
    def get_connection(self):
        self.reconnect_if_needed()
        return self.get_connection_value()
    
    def sync_execute(self, query, params=None):
        connection = self.get_connection()
        cursor = connection.cursor()
        try:
            cursor.execute(query, params)
            connection.commit()
        finally:
            cursor.close()
    
    def sync_executemany(self, query, params=None):
        connection = self.get_connection()
        cursor = connection.cursor()
        try:
            cursor.executemany(query, params)
            connection.commit()
        finally:
            cursor.close()
    
    def sync_execute_insert(self, query, params=None):
        connection = self.get_connection()
        cursor = connection.cursor()
        result = None
        try:
            cursor.execute(query, params)
            connection.commit()
            result = cursor.lastrowid
        finally:
            cursor.close()
        return result
    
    def sync_execute_fetch(self, query, params=None):
        connection = self.get_connection()
        cursor = connection.cursor(dictionary=True, buffered=True)
        result = None
        try:
            cursor.execute(query, params)
            result = cursor.fetchone()
            cursor.fetchall()
        finally:
            cursor.close()
        return result
    
    def sync_execute_fetchall(self, query, params=None):
        connection = self.get_connection()
        cursor = connection.cursor(dictionary=True, buffered=True)
        result = None
        try:
            cursor.execute(query, params)
            result = cursor.fetchall()
        finally:
            cursor.close()
        return result
    
    async def execute(self, sql, params=None):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(executor, self.sync_execute, sql, params)
    
    async def executemany(self, sql, params=None):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(executor, self.sync_executemany, sql, params)
    
    async def insert(self, sql, params=None):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(executor, self.sync_execute_insert, sql, params)
    
    async def fetch(self, sql, params=None):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(executor, self.sync_execute_fetch, sql, params)
    
    async def fetchall(self, sql, params=None):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(executor, self.sync_execute_fetchall, sql, params)


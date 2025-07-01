import asyncio, json, sqlite3, time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

executor = ThreadPoolExecutor(max_workers=1)


class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return json.JSONEncoder.default(self, obj)


class Database:
    
    def __init__(self, db_path):
        self.db_path = db_path
    
    def json_encode(self, obj, indent=2):
        return json.dumps(obj, indent=indent, cls=JSONEncoder, ensure_ascii=False)
    
    def get_current_datetime(self):
        """
        Получить дату по UTC
        """
        utc_now = datetime.now(timezone.utc)
        formatted_time = utc_now.strftime("%Y-%m-%d %H:%M:%S")
        return formatted_time
    
    def connect(self):
        pass
    
    def get_connection(self):
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode = WAL;")
        return connection
    
    def sync_execute(self, query, params=None):
        connection = self.get_connection()
        cursor = connection.cursor()
        try:
            if params == None:
                params = []
            cursor.execute(query, params)
            connection.commit()
        finally:
            connection.close()
    
    def sync_executemany(self, query, params=None):
        connection = self.get_connection()
        cursor = connection.cursor()
        try:
            if params == None:
                params = []
            cursor.executemany(query, params)
            connection.commit()
        finally:
            connection.close()
    
    def sync_execute_insert(self, query, params=None):
        connection = self.get_connection()
        cursor = connection.cursor()
        try:
            if params == None:
                params = []
            cursor.execute(query, params)
            connection.commit()
            return cursor.lastrowid
        finally:
            connection.close()
    
    def sync_execute_fetch(self, query, params=None):
        connection = self.get_connection()
        cursor = connection.cursor()
        try:
            if params == None:
                params = []
            cursor.execute(query, params)
            return cursor.fetchone()
        finally:
            connection.close()
    
    def sync_execute_fetchall(self, query, params=None):
        connection = self.get_connection()
        cursor = connection.cursor()
        try:
            if params == None:
                params = []
            cursor.execute(query, params)
            return cursor.fetchall()
        finally:
            connection.close()
    
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


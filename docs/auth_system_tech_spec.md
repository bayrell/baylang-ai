# Техническое задание: Система авторизации BayLang Cloud AGI

## 1. Обзор архитектуры

### 1.1 Принципы проектирования

Система авторизации построена на **трех слоях** с четким разделением ответственности:

```
┌─────────────────────────────────────────────────────────────┐
│                     API Layer (FastAPI)                      │
│  • HTTP эндпоинты, валидация запросов, JWT middleware       │
│  • Преобразование HTTP ↔ Domain модели                      │
├─────────────────────────────────────────────────────────────┤
│                  Service Layer                               │
│  • AuthService (наследуется от BaseService)                 │
│  • Высокоуровневая бизнес-логика                            │
│  • JWT токены, валидация                                     │
├─────────────────────────────────────────────────────────────┤
│                  Repository Layer                            │
│  • Абстракция над доступом к данным                         │
│  • Изоляция бизнес-логики от конкретной БД                  │
├─────────────────────────────────────────────────────────────┤
│                   Record Layer (Data)                        │
│  • Классы данных (UserRecord, SessionRecord)                │
│  • Методы from_db/to_db для сериализации                    │
├─────────────────────────────────────────────────────────────┤
│                   Database (SQLite / D1)                      │
│  • Локальная БД для разработки                              │
│  • Cloudflare D1 для production                             │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 Выбор технологий

| Компонент | Технология | Обоснование |
|-----------|------------|-------------|
| **Бэкенд** | FastAPI + Python 3 | Async поддержка, типизация, документация |
| **JWT** | PyJWT + bcrypt | Стандарт для авторизации, безопасное хеширование |
| **БД (dev)** | SQLite + aiosqlite | Async поддержка, файловый формат |
| **БД (prod)** | Cloudflare D1 | Serverless, интеграция с Workers |
| **Фронтенд** | Vue 3 + Options API | Архитектура проекта, реактивность |
| **State** | **Модели** (FormModel, ResultModel) | Архитектура проекта без Pinia |

---

## 2. Структура базы данных

### 2.1 Таблица users

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    display_name VARCHAR(100),
    is_active BOOLEAN DEFAULT 1,
    is_admin BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);
```

### 2.2 Таблица sessions

```sql
CREATE TABLE sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    token VARCHAR(500) UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_token ON sessions(token);
```

---

## 3. Record Layer — Классы данных

### 3.1 Базовый Record

```python
# src/core/database/record.py
from datetime import datetime
from typing import Optional, Any
import json

class Record:
    """Базовый класс для всех записей БД"""
    
    # Имя таблицы (переопределяется в дочерних классах)
    _table: str = ""
    
    # Поля таблицы (переопределяется в дочерних классах)
    _fields: list = []
    
    def __init__(self, **kwargs):
        self._data = {}
        for field in self._fields:
            setattr(self, field, kwargs.get(field))
            self._data[field] = kwargs.get(field)
    
    def to_dict(self) -> dict:
        """Преобразование в словарь"""
        return {k: v for k, v in self._data.items() if v is not None}
    
    def to_json(self) -> str:
        """Преобразование в JSON строку"""
        return json.dumps(self.to_dict(), default=str)
    
    @classmethod
    def from_db(cls, row: dict) -> 'Record':
        """Создание экземпляра из строки БД"""
        return cls(**row)
    
    def to_db(self) -> dict:
        """Преобразование для сохранения в БД"""
        return self.to_dict()
    
    def __repr__(self):
        return f"<{self.__class__.__name__}: {self.to_dict()}>"
```

### 3.2 UserRecord

```python
# src/core/database/records/user_record.py
from datetime import datetime
from typing import Optional
from core.database.record import Record
import bcrypt

class UserRecord(Record):
    """Запись пользователя в БД"""
    
    _table = "users"
    _fields = [
        "id", "username", "email", "password_hash",
        "display_name", "is_active", "is_admin",
        "created_at", "updated_at"
    ]
    
    # init не определяется здесь - он уже есть в базовом Record
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Хеширование пароля"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def verify_password(self, password: str) -> bool:
        """Проверка пароля"""
        return bcrypt.checkpw(
            password.encode('utf-8'),
            self.password_hash.encode('utf-8')
        )
    
    def to_public_dict(self) -> dict:
        """Публичные данные пользователя (без пароля)"""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "display_name": self.display_name,
            "is_active": self.is_active,
            "is_admin": self.is_admin,
            "created_at": self.created_at
        }
```

---

## 4. Repository Layer — Работа с данными

### 4.1 Базовый Repository

```python
# src/core/database/repository.py
from typing import Optional, List, Type, TypeVar
from core.database.record import Record
from core.database.database import Database

T = TypeVar('T', bound=Record)

class Repository:
    """Базовый репозиторий для CRUD операций"""
    
    def __init__(self, db: Database, record_class: Type[T]):
        self.db = db
        self.record_class = record_class
    
    async def find_by_id(self, id: int) -> Optional[T]:
        """Поиск по ID"""
        query = f"SELECT * FROM {self.record_class._table} WHERE id = ?"
        row = await self.db.fetch_one(query, (id,))
        if row:
            return self.record_class.from_db(row)
        return None
    
    async def find_all(self, limit: int = 100, offset: int = 0) -> List[T]:
        """Получение всех записей"""
        query = f"SELECT * FROM {self.record_class._table} LIMIT ? OFFSET ?"
        rows = await self.db.fetch_all(query, (limit, offset))
        return [self.record_class.from_db(row) for row in rows]
    
    async def create(self, record: T) -> T:
        """Создание новой записи"""
        data = record.to_db()
        fields = ", ".join(data.keys())
        placeholders = ", ".join(["?" for _ in data])
        
        query = f"INSERT INTO {self.record_class._table} ({fields}) VALUES ({placeholders})"
        cursor = await self.db.execute(query, list(data.values()))
        
        record.id = cursor.lastrowid
        return record
    
    async def update(self, record: T) -> T:
        """Обновление записи"""
        data = record.to_db()
        set_clause = ", ".join([f"{k} = ?" for k in data.keys()])
        
        query = f"UPDATE {self.record_class._table} SET {set_clause} WHERE id = ?"
        await self.db.execute(query, list(data.values()) + [record.id])
        
        return record
    
    async def delete(self, id: int) -> bool:
        """Удаление записи"""
        query = f"DELETE FROM {self.record_class._table} WHERE id = ?"
        cursor = await self.db.execute(query, (id,))
        return cursor.rowcount > 0
    
    async def count(self) -> int:
        """Подсчет количества записей"""
        query = f"SELECT COUNT(*) as count FROM {self.record_class._table}"
        row = await self.db.fetch_one(query)
        return row["count"] if row else 0
```

### 4.2 UserRepository

```python
# src/core/database/repositories/user_repository.py
from typing import Optional
from core.database.repository import Repository
from core.database.records.user_record import UserRecord

class UserRepository(Repository):
    """Репозиторий для работы с пользователями"""
    
    def __init__(self, db):
        super().__init__(db, UserRecord)
    
    async def find_by_email(self, email: str) -> Optional[UserRecord]:
        """Поиск пользователя по email"""
        query = "SELECT * FROM users WHERE email = ?"
        row = await self.db.fetch_one(query, (email,))
        if row:
            return UserRecord.from_db(row)
        return None
    
    async def find_by_username(self, username: str) -> Optional[UserRecord]:
        """Поиск пользователя по username"""
        query = "SELECT * FROM users WHERE username = ?"
        row = await self.db.fetch_one(query, (username,))
        if row:
            return UserRecord.from_db(row)
        return None
    
    async def create_user(self, username: str, email: str, password: str, 
                         display_name: str = None) -> UserRecord:
        """Создание нового пользователя"""
        password_hash = UserRecord.hash_password(password)
        
        user = UserRecord(
            username=username,
            email=email,
            password_hash=password_hash,
            display_name=display_name or username,
            is_active=True,
            is_admin=False
        )
        
        return await self.create(user)
    
    async def verify_user(self, email: str, password: str) -> Optional[UserRecord]:
        """Проверка учетных данных"""
        user = await self.find_by_email(email)
        if user and user.verify_password(password):
            return user
        return None
    
    async def update_password(self, user_id: int, new_password: str) -> bool:
        """Обновление пароля"""
        password_hash = UserRecord.hash_password(new_password)
        query = "UPDATE users SET password_hash = ? WHERE id = ?"
        cursor = await self.db.execute(query, (password_hash, user_id))
        return cursor.rowcount > 0
```

---

## 5. Database Layer — Абстракция БД

### 5.1 Интерфейс Database

```python
# src/core/database/database.py
from typing import Optional, List, Any
from abc import ABC, abstractmethod

class Database(ABC):
    """Абстрактный класс для работы с БД"""
    
    @abstractmethod
    async def connect(self):
        """Подключение к БД"""
        pass
    
    @abstractmethod
    async def disconnect(self):
        """Отключение от БД"""
        pass
    
    @abstractmethod
    async def execute(self, query: str, params: tuple = ()) -> Any:
        """Выполнение запроса"""
        pass
    
    @abstractmethod
    async def fetch_one(self, query: str, params: tuple = ()) -> Optional[dict]:
        """Получение одной строки"""
        pass
    
    @abstractmethod
    async def fetch_all(self, query: str, params: tuple = ()) -> List[dict]:
        """Получение всех строк"""
        pass
    
    @abstractmethod
    async def execute_migration(self, sql: str):
        """Выполнение миграции"""
        pass
```

### 5.2 SQLite Database

```python
# src/core/database/sqlite_database.py
import aiosqlite
from typing import Optional, List, Any
from core.database.database import Database

class SQLiteDatabase(Database):
    """Реализация для SQLite"""
    
    def __init__(self, db_path: str = "data.db"):
        self.db_path = db_path
        self.connection: Optional[aiosqlite.Connection] = None
    
    async def connect(self):
        """Подключение к SQLite"""
        self.connection = await aiosqlite.connect(self.db_path)
        self.connection.row_factory = aiosqlite.Row
        # Включаем поддержку внешних ключей
        await self.connection.execute("PRAGMA foreign_keys = ON")
    
    async def disconnect(self):
        """Отключение от SQLite"""
        if self.connection:
            await self.connection.close()
    
    async def execute(self, query: str, params: tuple = ()) -> Any:
        """Выполнение запроса"""
        cursor = await self.connection.execute(query, params)
        await self.connection.commit()
        return cursor
    
    async def fetch_one(self, query: str, params: tuple = ()) -> Optional[dict]:
        """Получение одной строки"""
        cursor = await self.connection.execute(query, params)
        row = await cursor.fetchone()
        if row:
            return dict(row)
        return None
    
    async def fetch_all(self, query: str, params: tuple = ()) -> List[dict]:
        """Получение всех строк"""
        cursor = await self.connection.execute(query, params)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    
    async def execute_migration(self, sql: str):
        """Выполнение миграции"""
        await self.connection.executescript(sql)
        await self.connection.commit()
```

### 5.3 Cloudflare D1 Database

```python
# src/core/database/d1_database.py
from typing import Optional, List, Any
from core.database.database import Database

class D1Database(Database):
    """Реализация для Cloudflare D1"""
    
    def __init__(self, d1_binding):
        """
        d1_binding - привязка D1 из Cloudflare Workers
        self.env.D1_DB
        """
        self.d1 = d1_binding
    
    async def connect(self):
        """D1 не требует явного подключения"""
        pass
    
    async def disconnect(self):
        """D1 не требует явного отключения"""
        pass
    
    async def execute(self, query: str, params: tuple = ()) -> Any:
        """Выполнение запроса через D1 API"""
        # D1 использует differently API
        result = await self.d1.prepare(query).bind(*params).run()
        return result
    
    async def fetch_one(self, query: str, params: tuple = ()) -> Optional[dict]:
        """Получение одной строки"""
        result = await self.d1.prepare(query).bind(*params).first()
        return result
    
    async def fetch_all(self, query: str, params: tuple = ()) -> List[dict]:
        """Получение всех строк"""
        result = await self.d1.prepare(query).bind(*params).all()
        return result["results"] if result else []
    
    async def execute_migration(self, sql: str):
        """Выполнение миграции (разбиваем на отдельные запросы)"""
        # D1 не поддерживает executescript, разбиваем SQL
        queries = sql.split(";")
        for query in queries:
            query = query.strip()
            if query:
                await self.d1.prepare(query).run()
```

---

## 6. Service Layer — Сервисы

### 6.1 Базовый ApiService


/**
 * Ответ API
 */
class ApiResponse {
  constructor(success, data = null, error = null) {
    this.success = success;
    this.data = data;
    this.error = error;
  }

  isSuccess() {
    return this.success;
  }

  toDict() {
    return {
      success: this.success,
      data: this.data,
      error: this.error,
    };
  }
}

/**
 * Базовый сервис для работы с API
 */
class ApiService {
  constructor(baseUrl = "") {
    this.baseUrl = baseUrl;
    this.token = null;
  }

  /**
   * Установка JWT токена
   */
  setToken(token) {
    this.token = token;
  }

  /**
   * Получение заголовков для запросов
   */
  _getHeaders() {
    const headers = {
      "Content-Type": "application/json",
    };
    if (this.token) {
      headers["Authorization"] = `Bearer ${this.token}`;
    }
    return headers;
  }

  /**
   * Базовый метод для HTTP запросов
   */
  async _request(method, endpoint, data = null) {
    const url = `${this.baseUrl}${endpoint}`;
    const headers = this._getHeaders();

    try {
      const options = {
        method,
        headers,
      };

      if (data && (method === "POST" || method === "PUT")) {
        options.body = JSON.stringify(data);
      }

      const response = await fetch(url, options);
      return await this._handleResponse(response);
    } catch (e) {
      return new ApiResponse(false, null, e.message);
    }
  }

  /**
   * Обработка ответа от сервера
   */
  async _handleResponse(response) {
    try {
      const data = await response.json();

      if (response.status >= 200 && response.status < 300) {
        return new ApiResponse(true, data);
      } else {
        const errorMsg = data.detail || "Unknown error";
        return new ApiResponse(false, null, errorMsg);
      }
    } catch (e) {
      return new ApiResponse(false, null, e.message);
    }
  }

  /**
   * GET запрос
   */
  async get(endpoint) {
    return this._request("GET", endpoint);
  }

  /**
   * POST запрос
   */
  async post(endpoint, data = null) {
    return this._request("POST", endpoint, data);
  }

  /**
   * PUT запрос
   */
  async put(endpoint, data = null) {
    return this._request("PUT", endpoint, data);
  }

  /**
   * DELETE запрос
   */
  async delete(endpoint) {
    return this._request("DELETE", endpoint);
  }
}

export { ApiResponse, ApiService };


### 6.2 AuthService


/**
 * Сервис авторизации
 */
class AuthService extends ApiService {
  constructor(baseUrl = "") {
    super(baseUrl);
  }

  /**
   * Регистрация нового пользователя
   */
  async register(username, email, password, displayName = null) {
    const data = {
      username,
      email,
      password,
    };
    if (displayName) {
      data.display_name = displayName;
    }

    return this.post("/api/auth/register", data);
  }

  /**
   * Вход в систему
   */
  async login(email, password) {
    const data = {
      email,
      password,
    };

    const response = await this.post("/api/auth/login", data);

    return response;
  }

  /**
   * Получение профиля текущего пользователя
   */
  async getProfile() {
    return this.get("/api/auth/me");
  }

  /**
   * Обновление профиля
   */
  async updateProfile(displayName = null, email = null) {
    const data = {};
    if (displayName !== null && displayName !== undefined) {
      data.display_name = displayName;
    }
    if (email !== null && email !== undefined) {
      data.email = email;
    }

    return this.put("/api/auth/profile", data);
  }

  /**
   * Смена пароля
   */
  async changePassword(currentPassword, newPassword) {
    const data = {
      current_password: currentPassword,
      new_password: newPassword,
    };

    return this.post("/api/auth/change-password", data);
  }

  /**
   * Выход из системы (клиентская сторона)
   */
  async logout() {
    this.token = null;
    return new ApiResponse(true, { message: "Logged out" });
  }
}

export { AuthService };

---

## 7. API Layer — FastAPI роуты

### 7.1 Request/Response модели (в router)

```python
# src/core/auth/router.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

# Request модели (перенесены сюда)
class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6)
    display_name: Optional[str] = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class UpdateProfileRequest(BaseModel):
    display_name: Optional[str] = None
    email: Optional[EmailStr] = None

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=6)

# Response модели (перенесены сюда)
class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    display_name: Optional[str]
    is_active: bool
    is_admin: bool
    created_at: datetime

class AuthResponse(BaseModel):
    user: UserResponse
    token: str
    expires_at: datetime

class ErrorResponse(BaseModel):
    detail: str
```

### 7.2 JWT Сервис

```python
# src/core/auth/jwt_service.py
from datetime import datetime, timedelta
from typing import Optional
import jwt
import os

class JWTService:
    """Сервис для работы с JWT токенами"""
    
    def __init__(self):
        self.secret_key = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 60 * 24  # 24 часа
    
    def create_access_token(self, user_id: int, email: str) -> dict:
        """Создание JWT токена"""
        expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        payload = {
            "sub": user_id,
            "email": email,
            "exp": expire,
            "iat": datetime.utcnow()
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        
        return {
            "token": token,
            "expires_at": expire
        }
    
    def verify_token(self, token: str) -> Optional[dict]:
        """Проверка JWT токена"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    def decode_token(self, token: str) -> Optional[dict]:
        """Декодирование JWT токена"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except Exception:
            return None
```

### 7.3 Auth API роуты

```python
# src/core/auth/router.py (продолжение)
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from datetime import datetime

from core.auth.jwt_service import JWTService
from core.database.repositories.user_repository import UserRepository

router = APIRouter(prefix="/api/auth", tags=["auth"])
security = HTTPBearer()

# Сервисы (получаются через DI контейнер)
jwt_service = JWTService()

def get_user_repository():
    """Получение репозитория пользователей через контейнер"""
    # В реальном приложении это будет через Depends
    from core.app import get_container
    container = get_container()
    return container.get("user_repository")

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Получение текущего пользователя из JWT"""
    token = credentials.credentials
    payload = jwt_service.verify_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    return payload

@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest):
    """Регистрация нового пользователя"""
    user_repo = get_user_repository()
    
    # Проверяем существование пользователя
    existing_user = await user_repo.find_by_email(request.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    existing_user = await user_repo.find_by_username(request.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )
    
    # Создаем пользователя
    user = await user_repo.create_user(
        username=request.username,
        email=request.email,
        password=request.password,
        display_name=request.display_name
    )
    
    # Создаем JWT токен
    token_data = jwt_service.create_access_token(user.id, user.email)
    
    return AuthResponse(
        user=UserResponse(**user.to_public_dict()),
        token=token_data["token"],
        expires_at=token_data["expires_at"]
    )

@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest):
    """Вход в систему"""
    user_repo = get_user_repository()
    
    # Проверяем учетные данные
    user = await user_repo.verify_user(request.email, request.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled"
        )
    
    # Создаем JWT токен
    token_data = jwt_service.create_access_token(user.id, user.email)
    
    return AuthResponse(
        user=UserResponse(**user.to_public_dict()),
        token=token_data["token"],
        expires_at=token_data["expires_at"]
    )

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    """Получение текущего пользователя"""
    user_repo = get_user_repository()
    user = await user_repo.find_by_id(current_user["sub"])
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse(**user.to_public_dict())

@router.put("/profile", response_model=UserResponse)
async def update_profile(
    request: UpdateProfileRequest,
    current_user: dict = Depends(get_current_user)
):
    """Обновление профиля"""
    user_repo = get_user_repository()
    user = await user_repo.find_by_id(current_user["sub"])
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Обновляем поля
    if request.display_name is not None:
        user.display_name = request.display_name
    if request.email is not None:
        # Проверяем уникальность email
        existing = await user_repo.find_by_email(request.email)
        if existing and existing.id != user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already in use"
            )
        user.email = request.email
    
    user.updated_at = datetime.utcnow()
    await user_repo.update(user)
    
    return UserResponse(**user.to_public_dict())

@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user)
):
    """Смена пароля"""
    user_repo = get_user_repository()
    user = await user_repo.find_by_id(current_user["sub"])
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Проверяем текущий пароль
    if not user.verify_password(request.current_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Обновляем пароль
    await user_repo.update_password(user.id, request.new_password)
    
    return {"message": "Password updated successfully"}
```

### 7.4 Регистрация роутов

```python
# src/core/routes.py (обновленный)
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse
from core.app import get_container, get_config
from core.config import Config

router = APIRouter()
container = get_container()
template = container.get("template")

index_page = template.from_string("""<!DOCTYPE html>
<body>
  <div class="app_container"></div>
  <link rel="stylesheet" href="main.css" />
  <script src="main.js"></script>
</body>""")

@router.get("/", response_class=HTMLResponse)
def action_index():
    return index_page.render()

@router.get("/env")
async def env(config: Config = Depends(get_config)):
    value = config.get("DEBUG")
    message = f"Here is an example of getting an environment variable: {value}"
    return {"message": message}

# Подключаем auth роуты
from core.auth.router import router as auth_router
router.include_router(auth_router)
```

---

## 8. Frontend — Vue 3 с Моделями

### 8.1 Структура компонентов

```
src/
├── core/
│   ├── pages/
│   │   ├── Layout.vue          # Основной layout
│   │   ├── LayoutModel.js      # Модель layout
│   │   ├── authPage/
│   │   │   ├── AuthPage.vue    # Компонент страницы входа
│   │   │   └── AuthPageModel.js # Модель страницы входа
│   │   └── registerPage/
│   │       ├── RegisterPage.vue # Компонент страницы регистрации
│   │       └── RegisterPageModel.js # Модель страницы регистрации
│   ├── models/
│   │   ├── FormModel.js        # Базовая модель формы
│   │   └── ResultModel.js      # Базовая модель результата
│   └── services/
│       ├── ApiService.js       # Базовый API сервис
│       └── AuthService.js      # Сервис авторизации
```

### 8.2 Базовые модели

#### FormModel

```javascript
// src/core/models/FormModel.js
export class FormModel {
    constructor() {
        this.items = {}; // Данные формы
        this.errors = {}; // Ошибки валидации
        this.loading = false;
    }
    
    // Установка значения поля
    setField(name, value) {
        this.items[name] = value;
        // Очищаем ошибку при изменении поля
        if (this.errors[name]) {
            delete this.errors[name];
        }
    }
    
    // Получение значения поля
    getField(name) {
        return this.items[name] || '';
    }
    
    // Установка ошибки
    setError(name, message) {
        this.errors[name] = message;
    }
    
    // Получение ошибки
    getError(name) {
        return this.errors[name] || null;
    }
    
    // Проверка наличия ошибок
    hasErrors() {
        return Object.keys(this.errors).length > 0;
    }
    
    // Очистка формы
    clear() {
        this.items = {};
        this.errors = {};
        this.loading = false;
    }
    
    // Установка данных формы
    setData(data) {
        this.items = { ...data };
    }
    
    // Получение всех данных
    getData() {
        return { ...this.items };
    }
    
    // Валидация (переопределяется в дочерних классах)
    validate() {
        return true;
    }
}
```

#### ResultModel

```javascript
// src/core/models/ResultModel.js
export class ResultModel {
    constructor() {
        this.data = null; // Данные результата
        this.error = null; // Сообщение об ошибке
        this.loading = false; // Состояние загрузки
        this.waitMessage = ''; // Сообщение ожидания
    }
    
    // Установка сообщения ожидания
    setWaitMessage(message) {
        this.waitMessage = message;
        this.loading = true;
        this.error = null;
    }
    
    // Установка результата
    setResponse(data) {
        this.data = data;
        this.loading = false;
        this.waitMessage = '';
        this.error = null;
    }
    
    // Установка ошибки
    setError(message) {
        this.error = message;
        this.loading = false;
        this.waitMessage = '';
    }
    
    // Очистка результата
    clear() {
        this.data = null;
        this.error = null;
        this.loading = false;
        this.waitMessage = '';
    }
    
    // Проверка успешности
    isSuccess() {
        return this.data !== null && this.error === null;
    }
    
    // Проверка загрузки
    isLoading() {
        return this.loading;
    }
}
```

### 8.3 LayoutModel с Auth/Register моделями

```javascript
// src/core/pages/LayoutModel.js
import { reactive } from 'vue';
import { AuthPageModel } from './authPage/AuthPageModel';
import { RegisterPageModel } from './registerPage/RegisterPageModel';

export class LayoutModel {
    constructor() {
        // Текущая страница
        this.currentPage = null;
        this.currentPageName = '';
        
        // Модели страниц
        this.authModel = reactive(new AuthPageModel());
        this.registerModel = reactive(new RegisterPageModel());
        
        // Данные пользователя
        this.user = null;
        this.token = localStorage.getItem('token') || null;
        this.isAuthenticated = false;
        
        // Инициализация
        this.init();
    }
    
    init() {
        // Восстанавливаем состояние из localStorage
        const user = localStorage.getItem('user');
        if (user && this.token) {
            this.user = JSON.parse(user);
            this.isAuthenticated = true;
        }
    }
    
    // Переключение страницы
    setPage(pageName) {
        this.currentPageName = pageName;
        
        switch (pageName) {
            case 'auth':
                this.currentPage = this.authModel;
                break;
            case 'register':
                this.currentPage = this.registerModel;
                break;
            default:
                this.currentPage = null;
        }
    }
    
    // Получение текущей страницы
    getCurrentPage() {
        return this.currentPage;
    }
    
    // Авторизация
    setAuth(user, token) {
        this.user = user;
        this.token = token;
        this.isAuthenticated = true;
        
        localStorage.setItem('token', token);
        localStorage.setItem('user', JSON.stringify(user));
    }
    
    // Выход
    logout() {
        this.user = null;
        this.token = null;
        this.isAuthenticated = false;
        
        localStorage.removeItem('token');
        localStorage.removeItem('user');
    }
    
    // Получение текущего пользователя
    getUser() {
        return this.user;
    }
    
    // Проверка авторизации
    isLoggedIn() {
        return this.isAuthenticated && this.token;
    }
}
```

### 8.4 AuthPage Model

```javascript
// src/core/pages/authPage/AuthPageModel.js
import { FormModel } from '@/core/models/FormModel';
import { ResultModel } from '@/core/models/ResultModel';
import { AuthService } from '@/core/services/AuthService';

export class AuthPageModel {
    constructor() {
        this.form = new FormModel();
        this.result = new ResultModel();
        this.authService = new AuthService();
        
        // Инициализация полей формы
        this.form.setData({
            email: '',
            password: ''
        });
    }
    
    // Получение компонента страницы
    getPage() {
        return () => import('./AuthPage.vue');
    }
    
    // Получение заголовка страницы
    getPageTitle() {
        return "Вход в систему";
    }
    
    // Установка значений формы
    setEmail(email) {
        this.form.setField('email', email);
    }
    
    setPassword(password) {
        this.form.setField('password', password);
    }
    
    // Валидация формы
    validate() {
        let isValid = true;
        this.form.errors = {};
        
        const email = this.form.getField('email');
        if (!email) {
            this.form.setError('email', 'Email обязателен');
            isValid = false;
        } else if (!this.isValidEmail(email)) {
            this.form.setError('email', 'Некорректный email');
            isValid = false;
        }
        
        const password = this.form.getField('password');
        if (!password) {
            this.form.setError('password', 'Пароль обязателен');
            isValid = false;
        }
        
        return isValid;
    }
    
    isValidEmail(email) {
        const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return re.test(email);
    }
    
    // Авторизация
    async login() {
        if (!this.validate()) {
            return;
        }
        
        this.result.setWaitMessage('Выполняется вход...');
        this.form.loading = true;
        
        try {
            const email = this.form.getField('email');
            const password = this.form.getField('password');
            
            const response = await this.authService.login(email, password);
            
            if (response.is_success()) {
                this.result.setResponse(response.data);
                
                // Сохраняем токен и пользователя
                const { user, token } = response.data;
                
                // Обновляем LayoutModel
                // (в реальном приложении это будет через events или DI)
                localStorage.setItem('token', token);
                localStorage.setItem('user', JSON.stringify(user));
                
                return response.data;
            } else {
                this.result.setError(response.error || 'Ошибка авторизации');
            }
        } catch (error) {
            this.result.setError('Ошибка соединения с сервером');
        } finally {
            this.form.loading = false;
        }
    }
    
    // Очистка формы
    clear() {
        this.form.clear();
        this.result.clear();
    }
}
```

### 8.5 RegisterPage Model

```javascript
// src/core/pages/registerPage/RegisterPageModel.js
import { FormModel } from '@/core/models/FormModel';
import { ResultModel } from '@/core/models/ResultModel';
import { AuthService } from '@/core/services/AuthService';

export class RegisterPageModel {
    constructor() {
        this.form = new FormModel();
        this.result = new ResultModel();
        this.authService = new AuthService();
        
        // Инициализация полей формы
        this.form.setData({
            username: '',
            email: '',
            display_name: '',
            password: '',
            confirmPassword: ''
        });
    }
    
    // Получение компонента страницы
    getPage() {
        return () => import('./RegisterPage.vue');
    }
    
    // Получение заголовка страницы
    getPageTitle() {
        return "Регистрация";
    }
    
    // Установка значений формы
    setUsername(username) {
        this.form.setField('username', username);
    }
    
    setEmail(email) {
        this.form.setField('email', email);
    }
    
    setDisplayName(displayName) {
        this.form.setField('display_name', displayName);
    }
    
    setPassword(password) {
        this.form.setField('password', password);
    }
    
    setConfirmPassword(confirmPassword) {
        this.form.setField('confirmPassword', confirmPassword);
    }
    
    // Валидация формы
    validate() {
        let isValid = true;
        this.form.errors = {};
        
        const username = this.form.getField('username');
        if (!username) {
            this.form.setError('username', 'Имя пользователя обязательно');
            isValid = false;
        } else if (username.length < 3) {
            this.form.setError('username', 'Минимум 3 символа');
            isValid = false;
        }
        
        const email = this.form.getField('email');
        if (!email) {
            this.form.setError('email', 'Email обязателен');
            isValid = false;
        } else if (!this.isValidEmail(email)) {
            this.form.setError('email', 'Некорректный email');
            isValid = false;
        }
        
        const password = this.form.getField('password');
        if (!password) {
            this.form.setError('password', 'Пароль обязателен');
            isValid = false;
        } else if (password.length < 6) {
            this.form.setError('password', 'Минимум 6 символов');
            isValid = false;
        }
        
        const confirmPassword = this.form.getField('confirmPassword');
        if (password !== confirmPassword) {
            this.form.setError('confirmPassword', 'Пароли не совпадают');
            isValid = false;
        }
        
        return isValid;
    }
    
    isValidEmail(email) {
        const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return re.test(email);
    }
    
    // Регистрация
    async register() {
        if (!this.validate()) {
            return;
        }
        
        this.result.setWaitMessage('Выполняется регистрация...');
        this.form.loading = true;
        
        try {
            const username = this.form.getField('username');
            const email = this.form.getField('email');
            const password = this.form.getField('password');
            const displayName = this.form.getField('display_name');
            
            const response = await this.authService.register(
                username, 
                email, 
                password, 
                displayName || null
            );
            
            if (response.is_success()) {
                this.result.setResponse(response.data);
                
                // Сохраняем токен и пользователя
                const { user, token } = response.data;
                localStorage.setItem('token', token);
                localStorage.setItem('user', JSON.stringify(user));
                
                return response.data;
            } else {
                this.result.setError(response.error || 'Ошибка регистрации');
            }
        } catch (error) {
            this.result.setError('Ошибка соединения с сервером');
        } finally {
            this.form.loading = false;
        }
    }
    
    // Очистка формы
    clear() {
        this.form.clear();
        this.result.clear();
    }
}
```

### 8.6 Компонент AuthPage

```vue
<!-- src/core/pages/authPage/AuthPage.vue -->
<style scoped>
.auth_page {
    max-width: 400px;
    margin: 50px auto;
    padding: 30px;
    background: #fff;
    border-radius: 12px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
}

.auth_page h2 {
    text-align: center;
    margin-bottom: 30px;
    color: #333;
}

.form_group {
    margin-bottom: 20px;
}

.form_group label {
    display: block;
    margin-bottom: 8px;
    font-weight: 500;
    color: #555;
}

.form_group input {
    width: 100%;
    padding: 12px;
    border: 1px solid #ddd;
    border-radius: 8px;
    font-size: 16px;
    transition: border-color 0.3s;
}

.form_group input:focus {
    outline: none;
    border-color: #667eea;
}

.error_message {
    color: #e74c3c;
    font-size: 14px;
    margin-top: 5px;
}

.login_button {
    width: 100%;
    padding: 14px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border: none;
    border-radius: 8px;
    font-size: 16px;
    font-weight: 600;
    cursor: pointer;
    transition: transform 0.2s, box-shadow 0.2s;
}

.login_button:hover:not(:disabled) {
    transform: translateY(-2px);
    box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
}

.login_button:disabled {
    opacity: 0.7;
    cursor: not-allowed;
}

.register_link {
    text-align: center;
    margin-top: 20px;
    color: #666;
}

.register_link a {
    color: #667eea;
    text-decoration: none;
    font-weight: 500;
}

.register_link a:hover {
    text-decoration: underline;
}
</style>

<template>
    <div class="auth_page">
        <h2>{{ model.getPageTitle() }}</h2>
        
        <form @submit.prevent="handleLogin">
            <div class="form_group">
                <label for="email">Email</label>
                <input 
                    type="email" 
                    id="email" 
                    :value="model.form.getField('email')"
                    @input="model.setEmail($event.target.value)"
                    placeholder="your@email.com"
                    required
                />
                <div v-if="model.form.getError('email')" class="error_message">
                    {{ model.form.getError('email') }}
                </div>
            </div>
            
            <div class="form_group">
                <label for="password">Пароль</label>
                <input 
                    type="password" 
                    id="password" 
                    :value="model.form.getField('password')"
                    @input="model.setPassword($event.target.value)"
                    placeholder="Введите пароль"
                    required
                />
                <div v-if="model.form.getError('password')" class="error_message">
                    {{ model.form.getError('password') }}
                </div>
            </div>
            
            <div v-if="model.result.error" class="error_message">
                {{ model.result.error }}
            </div>
            
            <button 
                type="submit" 
                class="login_button"
                :disabled="model.form.loading"
            >
                {{ model.form.loading ? 'Вход...' : 'Войти' }}
            </button>
        </form>
        
        <div class="register_link">
            Нет аккаунта? <a href="#" @click.prevent="goToRegister">Зарегистрироваться</a>
        </div>
    </div>
</template>

<script>
export default {
    name: 'AuthPage',
    
    computed: {
        layout() {
            return this.$layout;
        },
        
        model() {
            return this.layout.authModel;
        }
    },
    
    methods: {
        async handleLogin() {
            const result = await this.model.login();
            
            if (result) {
                // Перенаправление после успешного входа
                this.$router.push('/chat');
            }
        },
        
        goToRegister() {
            this.layout.setPage('register');
            this.$router.push('/register');
        }
    }
}
</script>
```

### 8.7 Компонент RegisterPage

```vue
<!-- src/core/pages/registerPage/RegisterPage.vue -->
<style scoped>
.register_page {
    max-width: 400px;
    margin: 50px auto;
    padding: 30px;
    background: #fff;
    border-radius: 12px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
}

.register_page h2 {
    text-align: center;
    margin-bottom: 30px;
    color: #333;
}

.form_group {
    margin-bottom: 20px;
}

.form_group label {
    display: block;
    margin-bottom: 8px;
    font-weight: 500;
    color: #555;
}

.form_group input {
    width: 100%;
    padding: 12px;
    border: 1px solid #ddd;
    border-radius: 8px;
    font-size: 16px;
    transition: border-color 0.3s;
}

.form_group input:focus {
    outline: none;
    border-color: #667eea;
}

.form_group .hint {
    font-size: 12px;
    color: #888;
    margin-top: 5px;
}

.error_message {
    color: #e74c3c;
    font-size: 14px;
    margin-top: 5px;
}

.register_button {
    width: 100%;
    padding: 14px;
    background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
    color: white;
    border: none;
    border-radius: 8px;
    font-size: 16px;
    font-weight: 600;
    cursor: pointer;
    transition: transform 0.2s, box-shadow 0.2s;
}

.register_button:hover:not(:disabled) {
    transform: translateY(-2px);
    box-shadow: 0 4px 15px rgba(17, 153, 142, 0.4);
}

.register_button:disabled {
    opacity: 0.7;
    cursor: not-allowed;
}

.login_link {
    text-align: center;
    margin-top: 20px;
    color: #666;
}

.login_link a {
    color: #667eea;
    text-decoration: none;
    font-weight: 500;
}

.login_link a:hover {
    text-decoration: underline;
}
</style>

<template>
    <div class="register_page">
        <h2>{{ model.getPageTitle() }}</h2>
        
        <form @submit.prevent="handleRegister">
            <div class="form_group">
                <label for="username">Имя пользователя</label>
                <input 
                    type="text" 
                    id="username" 
                    :value="model.form.getField('username')"
                    @input="model.setUsername($event.target.value)"
                    placeholder="username"
                    required
                    minlength="3"
                />
                <div class="hint">Минимум 3 символа</div>
                <div v-if="model.form.getError('username')" class="error_message">
                    {{ model.form.getError('username') }}
                </div>
            </div>
            
            <div class="form_group">
                <label for="email">Email</label>
                <input 
                    type="email" 
                    id="email" 
                    :value="model.form.getField('email')"
                    @input="model.setEmail($event.target.value)"
                    placeholder="your@email.com"
                    required
                />
                <div v-if="model.form.getError('email')" class="error_message">
                    {{ model.form.getError('email') }}
                </div>
            </div>
            
            <div class="form_group">
                <label for="display_name">Отображаемое имя</label>
                <input 
                    type="text" 
                    id="display_name" 
                    :value="model.form.getField('display_name')"
                    @input="model.setDisplayName($event.target.value)"
                    placeholder="Ваше имя"
                />
                <div class="hint">Необязательно</div>
            </div>
            
            <div class="form_group">
                <label for="password">Пароль</label>
                <input 
                    type="password" 
                    id="password" 
                    :value="model.form.getField('password')"
                    @input="model.setPassword($event.target.value)"
                    placeholder="Минимум 6 символов"
                    required
                    minlength="6"
                />
                <div v-if="model.form.getError('password')" class="error_message">
                    {{ model.form.getError('password') }}
                </div>
            </div>
            
            <div class="form_group">
                <label for="confirmPassword">Подтвердите пароль</label>
                <input 
                    type="password" 
                    id="confirmPassword" 
                    :value="model.form.getField('confirmPassword')"
                    @input="model.setConfirmPassword($event.target.value)"
                    placeholder="Повторите пароль"
                    required
                />
                <div v-if="model.form.getError('confirmPassword')" class="error_message">
                    {{ model.form.getError('confirmPassword') }}
                </div>
            </div>
            
            <div v-if="model.result.error" class="error_message">
                {{ model.result.error }}
            </div>
            
            <button 
                type="submit" 
                class="register_button"
                :disabled="model.form.loading"
            >
                {{ model.form.loading ? 'Регистрация...' : 'Зарегистрироваться' }}
            </button>
        </form>
        
        <div class="login_link">
            Уже есть аккаунт? <a href="#" @click.prevent="goToLogin">Войти</a>
        </div>
    </div>
</template>

<script>
export default {
    name: 'RegisterPage',
    
    computed: {
        layout() {
            return this.$layout;
        },
        
        model() {
            return this.layout.registerModel;
        }
    },
    
    methods: {
        async handleRegister() {
            const result = await this.model.register();
            
            if (result) {
                // Перенаправление после успешной регистрации
                this.$router.push('/chat');
            }
        },
        
        goToLogin() {
            this.layout.setPage('auth');
            this.$router.push('/login');
        }
    }
}
</script>
```

---

## 9. Интеграция с DI Container

### 9.1 Регистрация зависимостей

```python
# src/core/app.py (обновленный)
import jinja2
from fastapi import FastAPI
from core.container import Container
from core.config import Config, CloudflareConfig
from core.database.sqlite_database import SQLiteDatabase
from core.database.d1_database import D1Database

def register_container():
    container = Container()
    container.singleton("app", lambda container: FastAPI())
    container.singleton("template", lambda container: jinja2.Environment())
    container.singleton("config", lambda container: Config())
    
    return container

def register_repository(container):
    """Регистрация репозиториев"""
    from core.database.repositories.user_repository import UserRepository
    
    # Получаем БД из контейнера
    db = container.get("database")
    
    # Регистрируем репозиторий пользователей
    container.singleton("user_repository", lambda container: UserRepository(db))

def get_user_repository():
    """Получение репозитория пользователей через контейнер"""
    from core.app import get_container
    container = get_container()
    return container.get("user_repository")

container = register_container()
app = container.get("app")

def get_container():
    return container

def get_app():
    return app

def get_config():
    return container.get("config")

def register_routes():
    from core.routes import router
    app.include_router(router)

def register_frontend():
    app.mount("/", directory="dist")

def create_app():
    # Регистрируем SQLite БД для разработки
    db = SQLiteDatabase("data.db")
    container.singleton("database", lambda container: db)
    
    # Регистрируем репозитории
    register_repository(container)
    
    # Регистрируем роуты
    register_routes()
    
    return app

def create_cloudflare(env):
    # Регистрируем D1 БД для production
    db = D1Database(env.D1_DB)
    container.singleton("database", lambda container: db)
    
    # Регистрируем репозитории
    register_repository(container)
    
    # Обновляем конфигурацию
    container.singleton("config", lambda container: CloudflareConfig(env))
    
    # Регистрируем роуты
    register_routes()
    
    return app
```

---

## 10. Миграции

### 10.1 Сервис миграций

```python
# src/core/database/migrations/migration_service.py
import os
import importlib
from typing import List, Type
from core.database.migrations.migration import Migration

class MigrationService:
    """Сервис для управления миграциями"""
    
    def __init__(self, db):
        self.db = db
        self.migrations: List[Type[Migration]] = []
        self._load_migrations()
    
    def _load_migrations(self):
        """Автоматическая загрузка миграций из директории"""
        migrations_dir = os.path.dirname(__file__)
        
        for filename in os.listdir(migrations_dir):
            if filename.startswith("0") and filename.endswith(".py"):
                module_name = filename[:-3]  # Убираем .py
                module = importlib.import_module(
                    f"core.database.migrations.{module_name}"
                )
                
                # Находим все классы миграций в модуле
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (isinstance(attr, type) and 
                        issubclass(attr, Migration) and 
                        attr != Migration):
                        self.migrations.append(attr)
        
        # Сортируем по имени
        self.migrations.sort(key=lambda m: m(self.db).get_name())
    
    async def migrate(self):
        """Применение всех миграций"""
        # Создаем таблицу для отслеживания миграций
        await self.db.execute_migration("""
            CREATE TABLE IF NOT EXISTS migrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(255) UNIQUE NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Получаем список примененных миграций
        applied = await self.db.fetch_all(
            "SELECT name FROM migrations"
        )
        applied_names = [row["name"] for row in applied]
        
        # Применяем новые миграции
        for migration_class in self.migrations:
            migration = migration_class(self.db)
            name = migration.get_name()
            
            if name not in applied_names:
                print(f"Applying migration: {name}")
                await migration.up()
                
                # Записываем в таблицу миграций
                await self.db.execute(
                    "INSERT INTO migrations (name) VALUES (?)",
                    (name,)
                )
        
        print("All migrations applied successfully!")
```

---

## 11. Итог

### 11.1 Архитектурные преимущества

Использование паттернов **API**, **Service**, **Repository** и **Record** обеспечивает:

1. **Разделение ответственности**: Каждый слой отвечает за свою задачу
2. **Тестируемость**: Легко писать unit-тесты для каждого слоя
3. **Расширяемость**: Можно добавить новую БД без изменения бизнес-логики
4. **Поддерживаемость**: Изменения в одном слое не ломают другие
5. **Архитектура моделей**: Состояние хранится в моделях, а не в Pinia

### 11.2 Основные изменения

✅ **Pinia заменена на модели**: FormModel, ResultModel, LayoutModel  
✅ **Record методы**: from_db/to_db вместо from_row/to_dict  
✅ **UserRecord без init**: Используется init из базового Record  
✅ **DatabaseFactory удален**: Прямая регистрация singleton в create_app/create_cloudflare  
✅ **Request/Response в router**: Перенесены в auth/router.py  
✅ **Service Layer**: ApiService + AuthService  
✅ **Структура pages**: authPage, registerPage с моделями  
✅ **DI контейнер**: register_repository, get_user_repository  

### 11.3 Готовые компоненты

- ✅ Record классы (UserRecord с from_db/to_db)
- ✅ Repository классы (UserRepository)
- ✅ Database абстракция (SQLite, D1)
- ✅ Service Layer (ApiService, AuthService)
- ✅ API эндпоинты (register, login, profile)
- ✅ JWT аутентификация
- ✅ Миграции БД
- ✅ Модели (FormModel, ResultModel)
- ✅ LayoutModel с auth/register моделями
- ✅ Vue компоненты (AuthPage, RegisterPage)

### 11.4 Следующие шаги

1. Добавить тесты для всех компонентов
2. Реализовать middleware для проверки JWT
3. Добавить rate limiting для API
4. Реализовать refresh tokens
5. Добавить двухфакторную аутентификацию (опционально)

---

**Последнее обновление:** 25 сентября 2026 года  
**Статус:** Готово к реализации  
**Ответственный:** Лея
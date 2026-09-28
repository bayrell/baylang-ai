"""
Миграция для создания таблиц users и sessions.
Создает таблицы при первом запуске приложения.
"""
from core.database.migrations.migration import Migration


class Migration_Users(Migration):
    """Миграция для создания таблицы users"""

    def get_name(self):
        return "init_users_table"

    async def up(self):
        await self.db.execute_migration("""
            CREATE TABLE IF NOT EXISTS users (
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

            CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
            CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
        """)

        # Создаем пользователя admin по умолчанию
        import bcrypt
        salt = bcrypt.gensalt()
        password_hash = bcrypt.hashpw(b"admin", salt).decode('utf-8')

        await self.db.execute(
            "INSERT OR IGNORE INTO users (username, email, password_hash, display_name, is_active, is_admin) VALUES (?, ?, ?, ?, ?, ?)",
            ("admin", "admin@baylang.com", password_hash, "Admin", 1, 1)
        )

    async def down(self):
        await self.db.execute_migration("DROP TABLE IF EXISTS users;")


class Migration_Sessions(Migration):
    """Миграция для создания таблицы sessions"""

    def get_name(self):
        return "init_sessions_table"

    async def up(self):
        await self.db.execute_migration("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token VARCHAR(500) UNIQUE NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
            CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token);
        """)

    async def down(self):
        await self.db.execute_migration("DROP TABLE IF EXISTS sessions;")
Техническое задание на систему авторизации:
- Авторизация пользователей через JWT токен
- JWT секрет храниться в env используется SHA
- Создать базу данных sqlite, а для cloudflare использовать D1. Должно быть два разных singleton для рарботы с базой данных.
- Отдельно сделать сервис для миграций с базой данных. Каждая миграция это класс:

class Migration_Users(Migration):
    
    def get_name(self):
        return "init_users_table"
    
    async def up(self):
        await self.db.execute("-- Create users table")
        await self.db.execute(sql)
    
    async def down(self):
        await self.db.execute("-- Drop users table")
        await self.db.execute("drop table users")

По умолчанию создается пользователь admin. с паролем admin. В одном файле может быть несколько классов миграций.

Также требуется создать на Vue форму авторизации. И страницу профиль, где можно поменять имя, email и пароль. Для смены пароля требуется ввести предыдущий пароль.

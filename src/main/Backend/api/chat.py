import asyncio, time
from starlette.responses import JSONResponse
from starlette.requests import Request
from starlette.websockets import WebSocket, WebSocketDisconnect


class ChatProvider:
    
    def __init__(self, app):
        self.app = app
        self.database = app.get("database")
    
    
    async def create(self, name: str):
        """
        Функция для создания чата
        """
        gmtime_now = self.database.get_current_datetime()
        return await self.database.insert(
            "INSERT INTO chats (name, gmtime_created, gmtime_updated) VALUES (?, ?, ?)",
            (name, gmtime_now, gmtime_now)
        )
    
    async def rename(self, id, chat_title):
        
        """
        Фунция переименовывает чат
        """
        
        await self.database.execute(
            "UPDATE chats SET name=? WHERE id=?",
            (chat_title, id)
        )
    
    
    async def delete(self, id):
        """
        Функция удалить чат по id
        """
        await self.database.execute("delete from messages where chat_id=?", (id,))
        await self.database.execute("delete from chats where id=?", (id,))
    
    
    async def get_by_id(self, id):
        """
        Получить чат по id
        """
        return await self.database.execute_fetch("select * from chats where id=?", (id,), True)
    
    
    async def get_items_by_query(self, query, params=None):
        
        """
        Получить список всех чатов
        """
        
        items = await self.database.fetchall(query, params)
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
            ORDER BY id, gmtime_created;
        """
        messages = await self.database.fetchall(query_messages, items_id)
        
        for message in messages:
            chat_id = message["chat_id"]
            chat_pos = index[chat_id] if chat_id in index else None
            if pos is not None:
                result[chat_pos]["messages"].append(dict(message))
        
        return result
    
    
    async def get_items(self):
        
        """
        Получить список чатов
        """
        
        return await self.get_items_by_query("select * from chats order by id desc")
    
    
    async def get_last_messages(self, chat_id, limit=-1):
        
        """
        Получить последние сообщения чата
        """
        
        query = f"""
            SELECT * FROM messages
            WHERE chat_id = ?
            ORDER BY id desc
        """
        args = [chat_id]
        
        if limit >= 0:
            query += "LIMIT ?"
            args.append(limit)
        
        history = await self.database.fetchall(query, args)
        history = list(map(dict, history))
        history.reverse()
        return history
    
    
    async def add_message(self, chat_id: int, sender: str, text: str):
        """
        Функция для добавления сообщения
        """
        gmtime_now = self.database.get_current_datetime()
        return await self.database.insert(
            "INSERT INTO messages (chat_id, sender, text, gmtime_created, gmtime_updated) VALUES (?, ?, ?, ?, ?)",
            (chat_id, sender, text, gmtime_now, gmtime_now)
        )

    
    async def update_message(self, message_id: int, text: str):
        """
        Функция обновления сообщения
        """
        gmtime_now = self.database.get_current_datetime()
        return await self.database.execute(
            "UPDATE messages SET text=?, gmtime_updated=? WHERE id=?",
            (text, gmtime_now, message_id)
        )
    
    
    async def get_message_by_id(self, id):
        """
        Получить чат по id
        """
        item = dict(await self.database.fetch("select * from messages where id=?", (id,)))
        return item
    


class ChatApi:
    
    def __init__(self, app):
        self.app = app
        self.db = app.get("database")
        self.chat_provider = self.app.get("chat_provider")
        self.starlette = app.get("starlette")
        self.starlette.add_route("/app.chat/load", self.load, methods=["POST"])
        self.starlette.add_route("/app.chat/create", self.create, methods=["POST"])
        self.starlette.add_route("/app.chat/send", self.send, methods=["POST"])
        self.starlette.add_route("/app.chat/rename", self.rename, methods=["POST"])
        self.starlette.add_route("/app.chat/delete", self.delete, methods=["POST"])
        self.starlette.add_websocket_route("/app.chat/socket", self.socket)
    
    
    async def load(self, request: Request):
        
        items = await self.chat_provider.get_items()
        
        return JSONResponse({
            "code": 1,
            "message": "Ok",
            "data": {
                "items": items
            }
        })
    
    
    async def create(self, request: Request):
    
        # Get form data
        post_data = await request.form()
        post_data = dict(post_data)
        
        # Get model name and message
        model_name = post_data.get("data[item][model]")
        message = post_data.get("data[item][message]")
        if model_name is None or message is None:
            return {
                "code": -1,
                "message": "Fields error",
                "data": {},
            }
        
        chat_name = "Chat " + str(round(time.time()))
        chat_id = await self.chat_provider.create(chat_name)
        
        # Add messages
        chat_message_id = await self.chat_provider.add_message(chat_id, "human", message)
        answer_message_id = await self.chat_provider.add_message(chat_id, "assistant", "")
        
        # Get chat
        chat_items = await self.chat_provider.get_items_by_query(
            "select * from chats where id=?", [chat_id]
        )
        
        # Send message to LLM
        ai = self.app.get("ai")
        asyncio.create_task(ai.send_message(chat_id, chat_message_id, answer_message_id, message))
        
        return JSONResponse({
            "code": 1,
            "message": "Ok",
            "data": {
                "chat": chat_items[0],
            },
        })
    
    
    async def send(self, request: Request):
    
        # Get form data
        post_data = await request.form()
        post_data = dict(post_data)
        chat_id = post_data.get("data[chat_id]")
        message = post_data.get("data[text]")
        
        # Add message
        chat_message_id = await self.chat_provider.add_message(chat_id, "human", message)
        
        # Add answer
        answer_message_id = await self.chat_provider.add_message(chat_id, "assistant", "")
        answer_message_item = await self.chat_provider.get_message_by_id(answer_message_id)
        
        # Send message to LLM
        ai = self.app.get("ai")
        asyncio.create_task(ai.send_message(chat_id, chat_message_id, answer_message_id, message))
        
        return JSONResponse({
            "code": 1,
            "message": "Ok",
            "data": {
                "chat_id": chat_id,
                "answer": answer_message_item,
            },
        })
    
    
    async def rename(self, request: Request):
    
        # Get form data
        post_data = await request.form()
        post_data = dict(post_data)
        chat_id = post_data.get("data[chat_id]")
        chat_title = post_data.get("data[title]")
        
        # Rename title
        await self.chat_provider.rename(chat_id, chat_title)
        
        return JSONResponse({
            "code": 1,
            "message": "Ok",
        })
    
    
    async def delete(self, request: Request):
    
        # Get form data
        post_data = await request.form()
        post_data = dict(post_data)
        chat_id = post_data.get("data[chat_id]")
        
        # Delete chat
        await self.chat_provider.delete(chat_id)
        
        # Return result
        return JSONResponse({
            "code": 1,
            "message": "Ok",
            "data": {
            },
        })
    
    
    async def socket(self, websocket: WebSocket):
        
        client_provider = self.app.get("client_provider")
        
        await websocket.accept()
        client_provider.add(websocket)
        
        try:
            while True:
                await websocket.receive_text()
        
        except WebSocketDisconnect:
            client_provider.remove(websocket)
        
        except Exception as e:
            self.app.exception(f"WebSocket error: {e}")
    
import asyncio, time
from helper import json_encode, json_response
from model import Repository, Model, Chat, Message, create_block
from pydantic import BaseModel
from starlette.requests import Request
from starlette.websockets import WebSocket, WebSocketDisconnect


class ChatApi:
    
    def __init__(self, app):
        self.app = app
        self.db = app.get("database")
        self.client_provider = self.app.get("client_provider")
        self.starlette = app.get("starlette")
        self.starlette.add_route("/api/chat/load", self.load, methods=["POST"])
        self.starlette.add_route("/api/chat/send", self.send, methods=["POST"])
        self.starlette.add_route("/api/chat/rename", self.rename, methods=["POST"])
        self.starlette.add_route("/api/chat/delete", self.delete, methods=["POST"])
        self.starlette.add_websocket_route("/api/chat/socket", self.socket)
    
    
    async def load(self, request: Request):
        
        """
        Load current chats
        """
        
        # Create repository
        repository = Repository()
        
        # Get chat items
        chat_items = await Chat.load_all(self.database)
        repository.add_chat(chat_items)
        
        # Get messages
        chat_messages = await Message.get_by_chat_id(self.database, chat=chat_items)
        repository.add_messages(chat_messages)
        
        # Get result
        chat_items = [item.model_dump() for item in chat_items]
        for chat in chat_items:
            messages = repository.get_messages_by_chat_id(chat.id)
            item["messages"] = [message.model_dump() for message in messages]
        
        # Return result
        return json_response({
            "code": 1,
            "message": "Ok",
            "data": {
                "items": chat_items
            }
        })
    
    
    async def send(self, request: Request):
        
        """
        Send new message
        """
        
        class DTO(BaseModel):
            uid: str
            content: list[AbstractBlock]
            
            @validator("content", pre=True, each_item=True, check_fields=False)
            def parse_content(cls, item):
                return create_block(item)
        
        # Get form data
        post_data = await request.form()
        post_data = DTO(**dict(post_data))
        
        # Receive new message	
        self.app.log("Send " + post_data.uid)
        
        # Check chat_id
        if chat_id is None or chat_id == "":
            self.app.log("Error: chat_id is None")
            return self.helper.json_response({
                "code": -1,
                "message": "chat_id is None",
            })
        
        # Find chat by id
        chat = await Chat.get_by_id(self.database, chat_id)
        if chat is None:
            
            # Create chat
            chat = Chat(
                name = "Chat " + str(chat_id)
            )
            await chat.save(self.database)
            
            # Send create chat event
            await self.client_provider.send_broadcast_message(
                "create_chat",
                {
                    "chat_id": chat.id,
                    "chat_uid": post_data.uid,
                    "chat_name": post_data.name,
                }
            )
        
        # Create human message
        message_human = Message(
            sender = Message.SENDER_HUMAIN,
            chat_id = chat_id,
            content = post_data.content
        )
        
        # Create AI message
        message_ai = Message(
            sender = Message.SENDER_AI,
            chat_id = chat_id,
        )
        
        # Save messages to database
        await message_human.save(self.database)
        await message_ai.save(self.database)
        
        # Send message to LLM
        ai = self.app.get("ai")
        asyncio.create_task(ai.send_message(
            chat=chat,
            message_human=message_human,
            message_ai=message_ai
        ))
        
        # Response
        return json_response({
            "code": 1,
            "message": "Ok",
            "data": {
                "chat_id": chat.id,
                "answer": message_ai.model_dump(),
            },
        })
    
    
    async def rename(self, request: Request):
        
        """
        Rename chat
        """
        
        class DTO(BaseModel):
            chat_id: int
            title: str
        
        # Get form data
        post_data = await request.form()
        post_data = DTO(**dict(post_data))
        
        # Rename title
        await Chat.rename(self.database, post_data.chat_id, post_data.title)
        
        # Returns response
        return json_response({
            "code": 1,
            "message": "Ok",
        })
    
    
    async def delete(self, request: Request):
        
        """
        Delete chat
        """
        
        class DTO(BaseModel):
            chat_id: int
        
        # Get form data
        post_data = await request.form()
        post_data = DTO(**dict(post_data))
        
        # Delete chat
        await Chat.delete(self.database, post_data.chat_id)
        
        # Return result
        return json_response({
            "code": 1,
            "message": "Ok",
            "data": {
            },
        })
    
    
    async def socket(self, websocket: WebSocket):
        
        """
        WebSocket
        """
        
        client_provider = self.app.get("client_provider")
        
        # Accept connection
        await websocket.accept()
        client_provider.add(websocket)
        
        # Listen socket
        try:
            
            # Client connected message
            self.app.log("Client connected")
            
            # Send Hello
            helper = self.app.get("helper")
            await websocket.send_text(helper.json_encode({
                "event": "hello"
            }))
            
            # Receive message
            while True:
                await websocket.receive_text()
        
        except WebSocketDisconnect:
            
            # Client disconnected message
            self.app.log("Client disconnected")
            client_provider.remove(websocket)
        
        except Exception as e:
            self.app.exception(f"WebSocket error: {e}")
    
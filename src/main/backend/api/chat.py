import asyncio, time
from helper import json_encode, json_response, convert_request
from model import Repository, Model, Chat, Message, AbstractBlock, AbstractBlockList
from pydantic import BaseModel, validator
from starlette.requests import Request
from starlette.websockets import WebSocket, WebSocketDisconnect


class ChatApi:
    
    def __init__(self, app):
        self.app = app
        self.database = app.get("database")
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
            messages = repository.get_messages_by_chat_id(chat.get("id"))
            chat["id"] = chat["uid"]; del chat["uid"]
            chat["messages"] = [message.model_dump() for message in messages]
        
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
            id: str
            name: str = ""
            content: AbstractBlockList
        
        # Get form data
        response, post_data = await convert_request(request, DTO)
        if response:
            return response
        
        # Receive new message	
        self.app.log("Send " + post_data.id)
        
        # Check chat uid
        if post_data.id is None or post_data.id == "":
            self.app.log("Error: chat_id is None")
            return json_response({
                "code": -1,
                "message": "chat_id is None",
            })
        
        # Find chat by id
        chat = await Chat.get_by_uid(self.database, post_data.id)
        if chat is None:
            
            if post_data.name == "":
                return json_response({
                    "code": -1,
                    "message": "chat_name is None",
                })
            
            # Create chat
            chat = Chat(
                name = post_data.name,
                uid = post_data.id,
            )
            await chat.save(self.database)
            
            # Send create chat event
            await self.client_provider.send_broadcast_message(
                "create_chat",
                {
                    "id": chat.uid,
                    "name": post_data.name,
                    "content": [block.model_dump() for block in post_data.content],
                }
            )
        
        # Send message to LLM
        ai = self.app.get("ai")
        _, message_ai = await ai.send_question(chat, post_data.content, create_async_task=True)
        
        # Response
        return json_response({
            "code": 1,
            "message": "Ok",
            "data": {
                "chat_id": chat.uid,
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
        response, post_data = await convert_request(request, DTO)
        if response:
            return response
        
        # Rename title
        chat = await Chat.get_by_uid(self.database, post_data.chat_id)
        if chat:
            await Chat.rename(self.database, chat.id, post_data.title)
        
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
        response, post_data = await convert_request(request, DTO)
        if response:
            return response
        
        # Delete chat
        chat = await Chat.get_by_uid(self.database, post_data.chat_id)
        if chat:
            await Chat.delete(self.database, chat.id)
        
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
            # Send Hello
            helper = self.app.get("helper")
            await websocket.send_text(helper.json_encode({
                "event": "hello"
            }))
            
            # Receive message
            while True:
                await websocket.receive_text()
        
        except WebSocketDisconnect:
            client_provider.remove(websocket)
        
        except Exception as e:
            self.app.exception(f"WebSocket error: {e}")
    
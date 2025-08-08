import asyncio
from starlette.websockets import WebSocketDisconnect
from helper import json_encode

class Client:
    
    def __init__(self, app):
        self.app = app
        self.database = app.get("database")
        self.helper = app.get("helper")
        
        # Подключенные клиенты
        self.connected_clients = set()
        self.lock = asyncio.Lock()
    
    
    async def add(self, websocket):
        async with self.lock:
            self.connected_clients.add(websocket)
    
    
    async def remove(self, websocket):
        async with self.lock:
            self.connected_clients.discard(websocket)
    
    
    async def send_broadcast_message(self, event: str, message: dict):
    
        """
        Отправить сообщение всем клиентам
        """
        
        connected_clients = []
        disconnected_clients = []
        
        async with self.lock:
            connected_clients = list(self.connected_clients)
        
        for websocket in connected_clients:
            try:
                await websocket.send_text(json_encode({
                    "event": event,
                    "message": message,
                }))
            except WebSocketDisconnect:
                await self.remove(websocket)

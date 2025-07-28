from starlette.websockets import WebSocketDisconnect
from helper import json_encode

class Client:
    
    def __init__(self, app):
        self.app = app
        self.database = app.get("database")
        self.helper = app.get("helper")
        
        # Подключенные клиенты
        self.connected_clients = set()
    
    
    def add(self, websocket):
        self.connected_clients.add(websocket)
    
    
    def remove(self, websocket):
        self.connected_clients.remove(websocket)
    
    
    async def send_broadcast_message(self, event: str, message: dict):
    
        """
        Отправить сообщение всем клиентам
        """
        
        disconnected_clients = []
        for websocket in self.connected_clients:
            try:
                await websocket.send_text(json_encode({
                    "event": event,
                    "message": message,
                }))
            except WebSocketDisconnect:
                self.disconnected_clients.add(websocket)
        
        for websocket in disconnected_clients:
            self.connected_clients.remove(websocket)
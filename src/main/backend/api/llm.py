import asyncio, time
from helper import json_encode, json_response, convert_request, Form
from model import LLM, OpenAI, OpenAIContent_Annotation, is_alphanum_rule
from pydantic import BaseModel, validator
from pydantic.functional_validators import AfterValidator
from starlette.requests import Request
from starlette.websockets import WebSocket, WebSocketDisconnect
from typing import Annotated, Literal, Union

class LLM_Api:
    
    def __init__(self, app):
        self.app = app
        self.database = app.get("database")
        self.starlette = app.get("starlette")
        self.starlette.add_route("/api/settings/llm", self.index, methods=["POST"])
        self.starlette.add_route("/api/settings/llm/save", self.save, methods=["POST"])
        self.starlette.add_route("/api/settings/llm/delete", self.delete, methods=["POST"])
    
    
    async def index(self, request: Request):
        
        # Build query
        table_name = LLM.table_name()
        query = f"""
            SELECT *
            FROM {table_name}
        """
        params = []
        
        # Fetch from database
        items = await self.database.fetchall(query, params)
        items = [LLM.from_database(item) for item in items]
        items = [item.model_dump() for item in items]
        
        # Return result
        return json_response({
            "code": 1,
            "message": "Ok",
            "data": {
                "items": items
            }
        })
    
    
    async def save(self, request: Request):
        
        """
        Save item
        """
        
        class Item(BaseModel):
            type: Literal["openai"]
            name: Annotated[str, AfterValidator(is_alphanum_rule)]
            content: Union[OpenAIContent_Annotation, None] = None
        
        class DTO(BaseModel):
            id: int = 0
            item: Item
        
        # Validate form
        form = await Form.parse_request(request, DTO)
        if not form.is_correct:
            return form.get_response()
        
        # Create item
        if form.data.id > 0:
            item = await LLM.get_by_id(self.database, form.data.id)
            item.name = form.data.item.name
            item.content = form.data.item.content
        else:
            item = OpenAI(**form.data.item.model_dump())
        
        if item is None:
            return json_response({
                "code": -1,
                "message": "Item not found",
            })
        
        # Save item
        await item.save(self.database)
        
        # Return result
        return json_response({
            "code": 1,
            "message": "Ok",
            "data": {
                "id": item.id,
            }
        })
    
    
    async def delete(self, request: Request):
        
        """
        Delete item
        """
        
        class DTO(BaseModel):
            id: int = 0
        
        # Validate form
        form = await Form.parse_request(request, DTO)
        if not form.is_correct:
            return form.get_response()
        
        # Find item
        item = await LLM.get_by_id(self.database, form.data.id)
        if item is None:
            return json_response({
                "code": -1,
                "message": "Item not found",
            })
        
        await LLM.delete(self.database, form.data.id)
        
        # Return result
        return json_response({
            "code": 1,
            "message": "Ok",
            "data": {
                "id": item.id,
            }
        })
        
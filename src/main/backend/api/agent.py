import asyncio, time
from helper import Form, json_response, is_name_rule
from model import Agent
from pydantic import BaseModel
from pydantic.functional_validators import AfterValidator
from starlette.requests import Request
from typing import Annotated, Literal, Union


class AgentApi:
    
    def __init__(self, app):
        self.app = app
        self.database = app.get("database")
        self.starlette = app.get("starlette")
        self.starlette.add_route("/api/settings/agent", self.index, methods=["POST"])
        self.starlette.add_route("/api/settings/agent/save", self.save, methods=["POST"])
        self.starlette.add_route("/api/settings/agent/delete", self.delete, methods=["POST"])
    
    
    async def index(self, request: Request):
        
        # Build query
        table_name = Agent.table_name()
        query = f"""
            SELECT *
            FROM {table_name}
        """
        params = []
        
        # Fetch from database
        items = await self.database.fetchall(query, params)
        items = [Agent.from_database(item) for item in items]
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
            role: str
            llm_id: int
            prompt: str
            name: Annotated[str, AfterValidator(is_name_rule)]
        
        class DTO(BaseModel):
            id: int = 0
            item: Item
        
        # Validate form
        form = await Form.parse_request(request, DTO)
        if not form.is_correct:
            return form.get_response()
        
        # Create item
        if form.data.id > 0:
            item = await Agent.get_by_id(self.database, form.data.id)
            item.role = form.data.item.role
            item.llm_id = form.data.item.llm_id
            item.prompt = form.data.item.prompt
            item.name = form.data.item.name
        else:
            item = Agent(**form.data.item.model_dump())
        
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
        item = await Agent.get_by_id(self.database, form.data.id)
        if item is None:
            return json_response({
                "code": -1,
                "message": "Item not found",
            })
        
        await Agent.delete(self.database, form.data.id)
        
        # Return result
        return json_response({
            "code": 1,
            "message": "Ok",
            "data": {
                "id": item.id,
            }
        })
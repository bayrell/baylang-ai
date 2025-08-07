from __future__ import annotations
import json
from helper import Index, DateTimeType, \
    json_encode, json_decode, get_current_datetime, get_datetime_from_utc
from langchain.agents.output_parsers.tools import ToolAgentAction
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage
from langchain_core.messages.ai import UsageMetadata
from pydantic import BaseModel, Field, ConfigDict, validator
from pydantic.functional_validators import BeforeValidator
from typing import Annotated, ClassVar, Literal, List, Optional, Union


class Repository:
    
    def __init__(self):
        self.chat_items = []
        self.chat_index = Index()
        self.messages = []
        self.message_index = Index()
        self.message_index_chat_id = Index(key="chat_id")
    
    def add_chat(self, items):
        self.chat_items.extend(items)
        self.chat_index.extend(items)
    
    def add_messages(self, items):
        self.messages.extend(items)
        self.message_index.extend(items)
        self.message_index_chat_id.extend(items)
    
    def get_chat_by_id(self, chat_id):
        return self.chat_index.get(chat_id)
    
    def get_message_by_id(self, message_id):
        return self.chat_index.get(message_id)
    
    def get_messages_by_chat_id(self, chat_id):
        return self.message_index_chat_id.getall(chat_id)
    

class Model(BaseModel):
    
    model_config = ConfigDict(validate_assignment=True)
    _updated: set = set()
    _old_pk: dict = {}
    
    @classmethod
    def table_name(cls):
        return ""
    
    @classmethod
    def autoincrement(cls):
        return False
    
    @classmethod
    def primary_key(cls):
        return []
    
    @classmethod
    def has_updated_datetime(cls):
        return False
    
    @classmethod
    def add_foreign_items(cls, items, key, foreign, foreign_key):
        
        """
        Add foreign_item to each item[key]
        """
        
        index = Index(items)
        for foreign_item in foreign:
            item = index.get(foreign_item[foreign_key])
            item[key].append(foreign_item)
    
    
    @classmethod
    def get_primary_list_from_data(cls, data):
        if isinstance(data, list):
            return data
        
        if isinstance(data, dict):
            pk = cls.primary_key()
            item = [data[key] if key in data else None for key in pk]
            return item
        
        return [data]
    
    
    @classmethod
    async def get_by_id(cls, database, id, fields=["*"]):
        
        """
        Get chat by id
        """
        
        # Get where
        pk = cls.primary_key()
        where = [database.escape_field(key) + "=%s" for key in pk]
        args = cls.get_primary_list_from_data(id)
        
        # Query to database
        table_name = cls.table_name()
        item = await database.fetch(f"""
            select {database.join_fields(fields)} from {table_name} where {",".join(where)}
        """, args)
        
        return cls.from_database(item)
    
    
    @classmethod
    async def load_all(cls, database, fields=["*"]):
        
        """
        Load all items
        """
        
        table_name = cls.table_name()
        items = await database.fetchall(f"""
            SELECT {database.join_fields(fields)}
            FROM {table_name}
        """)
        items = [cls.from_database(item) for item in items]
        return items
    
    
    @classmethod
    async def delete(cls, database, id):
        
        """
        Delete chat by id
        """
        
        # Get where
        pk = cls.primary_key()
        where = [database.escape_field(key) + "=%s" for key in pk]
        args = cls.get_primary_list_from_data(id)
        
        # Query to database
        table_name = cls.table_name()
        await database.execute(f"delete from {table_name} where " + ",".join(where), args)
    
    
    async def create(self, database):
        
        """
        Create object
        """
        
        # Add updated datetime
        gmtime_now = get_current_datetime()
        if self.has_updated_datetime():
            if self.gmtime_created is None:
                self.gmtime_created = gmtime_now
            if self.gmtime_updated is None:
                self.gmtime_updated = gmtime_now
        
        # Convert item
        item = self.to_database(self)
        table_name = self.table_name()
        
        # Remove primary key
        if self.autoincrement():
            pk = self.primary_key()
            for key in pk:
                if key in item:
                    del item[key]
        
        keys = item.keys()
        fields = [database.escape_field(key) for key in keys]
        values = ["%s"] * len(keys)
        args = [item[key] for key in keys]
        query = f"""
            INSERT INTO {table_name} ({",".join(fields)})
            VALUES ({",".join(values)})
            """
        
        result = await database.insert(query, args)
        
        if self.autoincrement():
            pk = self.primary_key()
            if len(pk) == 1:
                key = pk[0]
                if not key in item:
                    setattr(self, key, result)
        
        self._updated = set()
        self._old_pk = self.get_primary_key()
    
    
    async def update(self, database):
        
        """
        Update to database
        """
        
        # Add updated datetime
        gmtime_now = get_current_datetime()
        if self.has_updated_datetime():
            if self.gmtime_updated is None:
                self.gmtime_updated = gmtime_now
        
        # Convert item
        item = self.to_database(self)
        table_name = self.table_name()
        
        # Get updated fields
        updated = self.updated()
        values = [database.escape_field(key) + "=%s" for key in updated]
        
        pk_keys = self._old_pk.keys()
        pk_values = [database.escape_field(key) + "=%s" for key in pk_keys]
        
        args = [item[key] if key in item else None for key in updated]
        args.extend([self._old_pk[key] for key in pk_keys])
        query = f"""
            UPDATE {table_name}
            SET {",".join(values)}
            WHERE {",".join(pk_values)}
            """
        
        await database.execute(query, args)
        
        self._updated = set()
        self._old_pk = self.get_primary_key()
        
    
    async def save(self, database):
        
        """
        Save to database
        """
        
        if self.is_create():
            await self.create(database)
        
        else:
            await self.update(database)

    
    def get_primary_key(self, data=None):
        
        """
        Returns primary key
        """
        
        if data is None:
            data = self
        
        pk = self.primary_key()
        item = {}
        for key in pk:
            item[key] = data[key] if key in data else None
        return item
    
    
    def is_create(self):
        
        """
        Returns true if model should be create
        """
        
        pk = self.primary_key()
        id = self._old_pk.get(pk[0])
        return id is None or id == 0
    
    def is_update(self):
        
        """
        Returns true if model should be update
        """
        
        pk = self.primary_key()
        id = self._old_pk.get(pk[0])
        return id > 0
    
    def updated(self):
        
        """
        Returns updated fields
        """
        
        return list(self._updated)
    
    
    def __init__(self, **data):
        BaseModel.__init__(self, **data)
        self._old_pk = self.get_primary_key(data)
    
    
    def __contains__(self, key):
        return key in self.__annotations__
    
    
    def __getitem__(self, key):
        return getattr(self, key)
    
    
    def __setattr__(self, key, value):
        if key in self.model_fields:
            self._updated.add(key)
        return super().__setattr__(key, value)
    

class Chat(Model):
    id: int = 0
    uid: str = ""
    name: str = ""
    gmtime_created: DateTimeType = None
    gmtime_updated: DateTimeType = None
    
    @classmethod
    def autoincrement(cls):
        return True
    
    @classmethod
    def has_updated_datetime(cls):
        return True
    
    @classmethod
    def primary_key(cls):
        return ["id"]
    
    @classmethod
    def table_name(cls):
        return "chats"
    
    @classmethod
    def from_database(cls, item, create_instance=True):
        if not create_instance or item is None:
            return item
        return Chat(**item)
    
    @classmethod
    def to_database(cls, item):
        return item.model_dump()
    
    
    @classmethod
    async def load_all(cls, database, fields=["*"]):
        
        """
        Load all items
        """
        
        table_name = cls.table_name()
        items = await database.fetchall(f"""
            SELECT {database.join_fields(fields)}
            FROM {table_name} ORDER BY `id` DESC
        """)
        items = [cls.from_database(item) for item in items]
        return items
    
    
    @classmethod
    async def get_by_uid(cls, database, uid: str, fields=["*"]):
        
        """
        Get chat by uid
        """
        
        item = await database.fetch(f"""
            SELECT {database.join_fields(fields)}
            FROM chats
            WHERE uid=%s
        """, [uid])
        
        return cls.from_database(item)
    
    
    @classmethod
    async def rename(cls, database, id, name):
        
        """
        Rename chat
        """
        
        await database.execute(
            "UPDATE chats SET name=%s WHERE id=%s",
            [name, id]
        )
    
    
    @classmethod
    async def delete(cls, database, id):
        
        """
        Delete chat by id
        """
        
        await database.execute("delete from messages where chat_id=%s", [id])
        await database.execute("delete from chats where id=%s", [id])
        
    

class Tool(Model):
    name: str = ""
    args: dict = {}


class AbstractBlock(Model):
    block: str = ""
    content: str = ""
    
    def is_empty(self):
        return self.content == ""
    
    def add_char(self, char):
        self.content += char
    
    def get_text(self):
        return self.content
    
    def trim(self):
        pass


class BlockText(AbstractBlock):
    block: Literal["text"] = "text"


class BlockCode(AbstractBlock):
    block: Literal["code"] = "code"
    language: str = ""
    
    def detect_language(self):
        lines = self.content.split("\n")
        self.language = lines[0][3:]
    
    def is_block_end(self):
        return len(self.content) >= 6 and self.content[-3:] == "```"
    
    def get_text(self):
        return "```" + self.language + "\n" + self.content + "\n" + "```"
    
    def trim(self):
        lines = self.content.split()
        if len(lines) > 1:
            if lines[0][0:3] == "```":
                lines = lines[1:]
        if len(lines) > 1:
            if lines[-1][0:3] == "```":
                lines = lines[0:-1]
        self.content = "\n".join(lines)


class BlockTool(AbstractBlock):
    block: Literal["tool"] = "tool"
    name: str = ""
    args: list = []
    tool: Tool = None


def create_block(item):
    if isinstance(item, AbstractBlock):
        return item
    block_type = item["block"]
    if block_type == "text":
        return BlockText(**item)
    if block_type == "code":
        return BlockCode(**item)
    if block_type == "tool":
        return BlockTool(**item)
    return AbstractBlock(**item)


def convert_block_list(value):
    if isinstance(value, list):
        value = [create_block(item) for item in value]
        return value
    return None

AbstractBlockList = Annotated[List[AbstractBlock], BeforeValidator(convert_block_list)]

class Message(Model):
    
    SENDER_AI: ClassVar[str] = "ai"
    SENDER_HUMAIN: ClassVar[str] = "human"
    id: int = 0
    chat_id: int = None
    sender: Literal["ai", "human"] = None
    content: AbstractBlockList = []
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    gmtime_created: DateTimeType = None
    gmtime_updated: DateTimeType = None
    
    @classmethod
    def autoincrement(cls):
        return True
    
    @classmethod
    def has_updated_datetime(cls):
        return True
    
    @classmethod
    def primary_key(cls):
        return ["id"]
    
    @classmethod
    def table_name(cls):
        return "messages"
    
    @classmethod
    def from_database(cls, item, chat: Index = None, create_instance=True):
        if item is None:
            return None
        item = item.copy()
        item["content"] = json_decode(item["content"])
        if not create_instance:
            return item
        return Message(**item)
    
    
    @classmethod
    def to_database(cls, item):
        item = item.model_dump()
        item["content"] = json_encode(item["content"], indent=None)
        return item
    
    
    @classmethod
    async def get_by_chat_id(cls, database, chat_id=None, chat=None, fields=["*"], limit=-1):
        
        """
        Get messages by chat_id
        """
        
        if chat is not None:
            if not isinstance(chat, list):
                chat = [chat]
        
        if chat_id is None:
            if chat is not None:
                chat_id = [item.id for item in chat]
        
        if chat_id is None:
            return []
        
        query = f"""
            SELECT {database.join_fields(fields)} FROM messages
            WHERE chat_id in ({','.join(['%s'] * len(chat_id))})
            ORDER BY id asc
        """
        
        args = chat_id
        if limit >= 0:
            query += "LIMIT %s"
            args.append(limit)
        
        items = await database.fetchall(query, args)
        items = [cls.from_database(item) for item in items]
        return items
    
    
    def add_usage(self, usage_metadata: UsageMetadata):
        
        """
        Add usage
        """
        
        def get_usage(usage_metadata: UsageMetadata, key: str):
            return usage_metadata[key] if key in usage_metadata else 0
        
        self.input_tokens += get_usage(usage_metadata, "input_tokens")
        self.output_tokens += get_usage(usage_metadata, "output_tokens")
        self.total_tokens += get_usage(usage_metadata, "total_tokens")
    
    
    def get_text(self):
        
        """
        Returns message content
        """
        
        items = [item.get_text() for item in self.content]
        content = "\n\n".join(items)
        return content
    
    
    def get_message(self):
        
        """
        Returns message
        """
        
        # Get message content
        content = self.get_text()
        
        # Create message
        if self.sender == Message.SENDER_HUMAIN:
            return HumanMessage(content)
        return AIMessage(content)
    
    
    def get_last_block(self):
        
        """
        Returns last block
        """
        
        if len(self.content) == 0:
            return None
        return self.content[-1]
    
    
    def replace_last_block(self, block):
        
        """
        Replace last block
        """
        
        self.content[-1] = block
    
    
    def add_text_block(self, **kwargs):
        
        """
        Add text block
        """
        
        block = BlockText(**kwargs)
        self.content.append(block)
        return block
    
    
    def add_new_line(self):
        
        """
        Add new line
        """
        
        last_block = self.get_last_block()
        
        # if last block is text
        if isinstance(last_block, BlockText):
            
            # Change last block to code
            if last_block.content[0:3] == "```":
                block = BlockCode(content=last_block.content)
                block.add_char("\n")
                block.detect_language()
                self.replace_last_block(block)
                return
        
        # If last block is code
        if isinstance(last_block, BlockCode):
            if not last_block.is_block_end():
                last_block.add_char("\n")
                return
        
        # Add new line
        if not last_block.is_empty():
            return self.add_text_block()
        
        return last_block
    
    
    def add_chunk(self, chunk: AIMessageChunk):
        
        """
        Add chunk
        """
        
        content = str(chunk.content)
        if content == "":
            return
        
        # Get last block
        last_block = self.get_last_block()
        if last_block is None or isinstance(last_block, BlockTool):
            last_block = self.add_text_block()
        
        for char in content:
            if char == "\n":
                last_block = self.add_new_line()
            else:
                last_block.add_char(char)
    
    
    def add_tool(self, action: ToolAgentAction):
        
        """
        Add tool
        """
        
        # Get last block
        last_block = self.get_last_block()
        
        # Create new block
        block = BlockTool(
            content = action.log,
            tool = Tool(
                name = action.tool,
                args = action.tool_input,
            )
        )
        
        # Add new block
        if last_block is None or not last_block.is_empty() or \
            isinstance(last_block, BlockTool):
                self.content.append(block)
        else:
            self.replace_last_block(block)
        

class LLM(Model):
    
    id: int = 0
    type: str = ""
    name: str = ""
    content: Union[dict, None] = None
    gmtime_created: DateTimeType = None
    gmtime_updated: DateTimeType = None
    
    @classmethod
    def autoincrement(cls):
        return True
    
    @classmethod
    def has_updated_datetime(cls):
        return True
    
    @classmethod
    def primary_key(cls):
        return ["id"]
    
    @classmethod
    def table_name(cls):
        return "llm"
    
    @classmethod
    def from_database(cls, item, create_instance=True):
        if item is None:
            return None
        item = item.copy()
        item["content"] = json_decode(item["content"])
        if not create_instance:
            return item
        llm_type = item.get("type")
        if llm_type == "openai":
            return OpenAI(**item)
        return LLM(**item)
    
    @classmethod
    def to_database(cls, item):
        item = item.model_dump()
        item["content"] = json_encode(item["content"], indent=None)
        return item

class OpenAIContent(BaseModel):
    url: str = ""
    key: str = ""
    model: str = ""

OpenAIContent_Annotation = Annotated[
    OpenAIContent,
    BeforeValidator(
        lambda value: value if value is None or isinstance(value, OpenAIContent) \
            else OpenAIContent(**value)
    )
]

class OpenAI(LLM):
    type: Literal["openai"] = "openai"
    content: Union[OpenAIContent_Annotation, None] = None


class Agent(Model):
    
    id: int = 0
    role: str = ""
    name: str = ""
    gmtime_created: DateTimeType = None
    gmtime_updated: DateTimeType = None
    
    @classmethod
    def autoincrement(cls):
        return True
    
    @classmethod
    def has_updated_datetime(cls):
        return True
    
    @classmethod
    def primary_key(cls):
        return ["id"]
    
    @classmethod
    def table_name(cls):
        return "agent"
    
    @classmethod
    def from_database(cls, item, create_instance=True):
        if item is None:
            return None
        item = item.copy()
        if not create_instance:
            return item
        return Agent(**item)
    
    @classmethod
    def to_database(cls, item):
        item = item.model_dump()
        return item
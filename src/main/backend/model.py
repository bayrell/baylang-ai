from __future__ import annotations
import json
from urllib.parse import urljoin
from helper import Index, DateTimeType, fetch_json, json_encode, json_decode
from langchain.agents.output_parsers.tools import ToolAgentAction
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage
from langchain_core.messages.ai import UsageMetadata
from langchain_ollama import ChatOllama
from orm import Model
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
        lines = self.content.split("\n")
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
    agent_name: str = ""
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
        if llm_type == "ollama":
            return OllamaAI(**item)
        return LLM(**item)
    
    @classmethod
    def to_database(cls, item):
        item = item.model_dump()
        item["content"] = json_encode(item["content"], indent=None)
        return item
    
    def factory(self):
        
        """
        Create LLM instance
        """
        
        return None
    
    
    async def reload_models(self):
        
        """
        Reload LLM models
        """
        
        pass
    
    
    def get_models(self):
        
        """
        Returns LLM models
        """
        
        return []


class OpenAIContent(BaseModel):
    url: str = ""
    key: str = ""
    model: str = ""
    models: List[str] = []
    temperature: float = 0.5

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


class OllamaAIContent(BaseModel):
    url: str = ""
    model: str = ""
    models: List[str] = []
    temperature: float = 0.5

OllamaAIContent_Annotation = Annotated[
    OllamaAIContent,
    BeforeValidator(
        lambda value: value if value is None or isinstance(value, OllamaAIContent) \
            else OllamaAIContent(**value)
    )
]

class OllamaAI(LLM):
    type: Literal["ollama"] = "ollama"
    content: Union[OllamaAIContent_Annotation, None] = None
    
    def factory(self):
        
        """
        Create LLM instance
        """
        
        return ChatOllama(
            base_url=self.content.url,
            model=self.content.model,
            temperature=self.content.temperature,
        )
    
    
    async def reload_models(self):
        
        """
        Reload LLM models
        """
        
        result = await fetch_json(urljoin(self.content.url, "/api/tags"))
        result = [item["name"] for item in result["models"]]
        result.sort()
        
        # Save models
        self.content.models = result
    
    
    def get_models(self):
        
        """
        Returns LLM models
        """
        
        return self.content.models


class Agent(Model):
    
    id: int = 0
    role: str = ""
    name: str = ""
    prompt: str = ""
    model: str = ""
    llm: LLM = None
    llm_id: Union[int, None] = None
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
    
    async def bind_llm(self, database):
        if self.llm is None and self.llm_id > 0:
            self.llm = await LLM.get_by_id(database, self.llm_id)
    
    def factory(self):
        
        """
        Create LLM instance
        """
        
        return self.llm.factory()

from __future__ import annotations
import json
from datetime import datetime
from helper import Index, json_encode, json_decode, get_current_datetime
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage
from pydantic import BaseModel, Field, validator
from typing import ClassVar, Literal, Union


class Model(BaseModel):
    def __getitem__(self, key):
        return getattr(self, key)
    
    @classmethod
    def add_foreign_items(cls, key="", items=[], foreign=[], foreign_key=""):
        index = Index(items)
        for foreign_item in foreign:
            pk = foreign_item[foreign_key]
            item = index.get(pk)
            item[key].append(foreign_item)


class Chat(Model):
    id: int = 0
    uid: str = ""
    name: str = ""
    messages: list[Message] = []
    gmtime_created: datetime = None
    gmtime_updated: datetime = None
    
    @classmethod
    def from_database(cls, item):
        return Chat(**item)
    
    
    @classmethod
    def to_database(cls, item):
        return item.model_dump()
    
    
    @classmethod
    async def get_by_id(cls, database, id, fields=["*"]):
        
        """
        Get chat by id
        """
        
        item = await database.fetch(f"""
            select {database.join_fields(fields)} from chats where id=%s
        """, [id])
        return cls.from_database(item)
    
    
    @classmethod
    async def load_all(cls, database, fields=["*"]):
        
        """
        Load all items
        """
        
        items = await get_items_by_query(f"""
            select {database.join_fields(fields)} from chats order by id desc
        """)
        items = [cls.from_database(item) for item in items]
        return items
    
    
    @classmethod
    async def create(cls, database, name: str, uid=""):
        
        """
        Create chat
        """
        
        gmtime_now = get_current_datetime()
        chat_id = await database.insert(
            """INSERT INTO chats
                (name, uid, gmtime_created, gmtime_updated)
                VALUES (%s, %s, %s)
            """,
            (name, uid, gmtime_now, gmtime_now)
        )
        chat = Chat(
            id = chat_id,
            name = name,
            uid = uid,
        )
        return chat
    
    
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
    
    
    async def save(self):
        
        """
        Save to database
        """
        
        item = self.__class__.to_database(self)
        gmtime_now = self.helper.get_current_datetime()
        
        if self.id == 0:
            self.id = await self.database.insert(
                f"""
                INSERT INTO chats (uid, name, gmtime_created, gmtime_updated)
                VALUES (%s, %s, %s, %s, %s)
                """,
                [item["uid"], item["name"], gmtime_now, gmtime_now]
            )
        
        else:
            item["gmtime_updated"] = gmtime_now
            await self.database.execute(
                """
                UPDATE chats
                SET `name`=%s, `gmtime_updated`=%s,
                WHERE `id`=%s
                """,
                [
                    item["name"],
                    item["gmtime_updated"],
                    item["id"]
                ]
            )
        
    

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


class BlockTool(AbstractBlock):
    block: Literal["tool"] = "tool"
    name: str = ""
    args: list = []
    tool: Tool = None


def create_block(item: dict):
    block_type = item["block"]
    if block_type == "text":
        return BlockText(**item)
    if block_type == "code":
        return BlockCode(**item)
    if block_type == "tool":
        return BlockTool(**item)
    return AbstractBlock(**item)


class Message(Model):
    
    SENDER_AI: ClassVar[str] = "ai"
    SENDER_HUMAIN: ClassVar[str] = "human"
    id: int = 0
    chat_id: int = None
    chat: Chat = None
    sender: Literal["ai", "human"] = None
    content: list[AbstractBlock] = []
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    gmtime_created: datetime = None
    gmtime_updated: datetime = None
    
    @validator("content", pre=True, each_item=True, check_fields=False)
    def parse_content(cls, item):
        return create_block(item)
    
    
    @classmethod
    def from_database(cls, item, chat: Index = None):
        item = item.copy()
        item["content"] = json_decode(item["content"])
        if chat is not None:
            item["chat"] = chat.get(item.get("chat_id"))
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
            chat_index = Index(chat)
        
        if chat_id is None:
            if chat is not None:
                chat_id = [item.id for item in chat]
        
        if chat_id is None:
            return []
        
        query = f"""
            SELECT {database.join_fields(fields)} FROM messages
            WHERE chat_id in ({','.join(['%s'] * len(chat_id))})
            ORDER BY id desc
        """
        
        args = chat_id
        if limit >= 0:
            query += "LIMIT %s"
            args.append(limit)
        
        items = await database.fetchall(query, args)
        items = [cls.from_database(item, chat=chat_index) for item in items]
        return items
    
    
    async def save(self, database):
        
        """
        Save to database
        """
        
        item = self.__class__.to_database(self)
        gmtime_now = self.helper.get_current_datetime()
        
        if self.id == 0:
            self.id = await self.database.insert(
                f"""
                INSERT INTO messages (chat_id, sender, content, gmtime_created, gmtime_updated)
                VALUES (%s, %s, %s, %s, %s)
                """,
                [item["chat_id"], item["sender"], item["content"], gmtime_now, gmtime_now]
            )
        
        else:
            item["gmtime_updated"] = gmtime_now
            await self.database.execute(
                """
                UPDATE messages
                SET `content`=%s,
                    `input_tokens`=%s,
                    `output_tokens`=%s,
                    `total_tokens`=%s,
                    `gmtime_updated`=%s
                WHERE `id`=%s
                """,
                [
                    item["content"],
                    item["input_tokens"],
                    item["output_tokens"],
                    item["total_tokens"],
                    item["gmtime_updated"],
                    item["id"],
                ]
            )
    
    
    def get_message(self):
        
        """
        Returns message
        """
        
        # Get message content
        items = [item.get_text() for item in self.content]
        content = " ".join(items)
        
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
    
    
    def change_last_block(self, block):
        
        """
        Change last block
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
                self.change_last_block(block)
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
        if last_block is None:
            last_block = self.add_text_block()
        
        for char in content:
            if char == "\n":
                last_block = self.add_new_line()
            else:
                last_block.add_char(char)
    
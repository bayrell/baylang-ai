import asyncio, torch, random, sys, os
import numpy as np
from langchain.agents.format_scratchpad.tools import format_to_tool_messages
from langchain.agents.output_parsers.tools import ToolAgentAction
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, SystemMessage
from langchain_core.messages.ai import UsageMetadata, add_ai_message_chunks
from langchain_core.tools import tool
from langchain_ollama import ChatOllama
from model import Chat, Message, AbstractBlock
from mcp.server.fastmcp import FastMCP
from starlette.routing import Mount


class Question:
    
    def __init__(self, content="", history=None):
        self.answer = ""
        self.answer_next = 0
        self.chat = None
        self.content = content
        self.message_ai = None
        self.message_human = None
        self.context = []
        self.history = []
        self.response_step = []
    
    
    def add_chunk_message(self, chunk: AIMessageChunk):
        
        """
        Add chunk message
        """
        
        self.message_ai.add_chunk(chunk)
        
    
    def add_tool_message(self, action: ToolAgentAction):
        
        """
        Add run tool message
        """
        
        self.message_ai.add_tool(action)
        
    
    def get_history(self):
        
        """
        Get history as list
        """
        
        history = []
        for item in self.history:
            if item.id == self.message_ai.id or \
                item.id == self.message_human.id:
                    continue
            message = item.get_message()
            if isinstance(message, HumanMessage):
                history.append("Human:\n" + message.content)
            elif isinstance(message, AIMessage):
                history.append("AI:\n" + message.content)
        return history
    
    
    def get_system_prompt(self):
        
        """
        Returns system prompt
        """
        
        text = ["Ты консультант для программистов. Отвечай на русском языке в деловом стиле. Если задача требует вычислений или инструментов, используй доступные функции."]
        history = self.get_history()
        if len(history) > 0:
            history = "\n\n".join(history)
            text.append("История:\n\n" + history)
        return "------------------\n".join(text)
    
    
    async def get_prompt(self):
        
        """
        Returns question prompt
        """
        
        prompt = [
            SystemMessage(content=self.get_system_prompt()),
            HumanMessage(content=" ".join([self.content, "Отвечай на русском языке"]))
        ]
        prompt.extend(format_to_tool_messages(self.response_step))
        return prompt
    

class Agent:
    
    def __init__(self, app, llm):
        self.app = app
        self.llm = llm
        self.database = app.get("database")
        self.client_provider = app.get("client_provider")
        
        # Bind tools
        self.tools = app.get("tools")
        if self.tools:
            self.llm = self.tools.bind(self.llm)
    
    
    async def send_callback(self, kind, data=None):
        
        if self.callback == None:
            return
        
        await self.callback(self, kind, data)
    
    
    async def send_question(self, question):
        
        """
        Отправить вопрос в LLM
        """
        
        chunks = []
        tool_calls = []
        
        # Start question
        await self.on_start(question)
        
        # Get prompt
        prompt = await question.get_prompt()
        self.app.log(prompt)
        
        # Send question to LLM
        response = self.llm.astream(prompt, stream=True)
        async for chunk in response:
            
            # Add tool
            if hasattr(chunk, "tool_calls") and chunk.tool_calls:
                tool_calls.extend(chunk.tool_calls)
            
            # Add chunk
            chunks.append(chunk)
            question.add_chunk_message(chunk)
            
            # Send chunk
            await self.on_chunk(question, chunk)
        
        # Merge chunks
        chunk = None
        if len(chunks) > 0:
            chunk = chunks[0]
        if len(chunks) > 1:
            chunk = add_ai_message_chunks(chunk, *chunks[1:])
        
        # Build mesage
        message = AIMessage(
            content=chunk.content,
            tool_calls=tool_calls,
            additional_kwargs=chunk.additional_kwargs if chunk is not None else {},
            response_metadata=chunk.response_metadata if chunk is not None else {},
            usage_metadata=chunk.usage_metadata if chunk is not None else None,
        )
        question.message_ai.add_usage(message.usage_metadata)
        
        # Trim messages block
        for block in question.message_ai.content:
            block.trim()
        
        # Send message
        await self.on_message(question, message)
        return message
    
    
    def get_tools(self, message):
        
        """
        Получает список tools на основе сообщения
        """
        
        items = []
        for item in message.tool_calls:
            log = "Run " + item["name"] + " with args " + str(item["args"])
            action = ToolAgentAction(
                tool=item["name"],
                tool_input=item["args"],
                log=log,
                message_log=[message],
                tool_call_id=item["id"],
            )
            items.append(action)
        
        return items
    
    
    async def run_tools(self, question, message):
        
        """
        Выполнить функции
        """
        
        response = []
        actions = self.get_tools(message)
        for action in actions:
            tool = self.tools.find(action)
            observation = None
            
            if tool:
                self.app.log("Run tool " + action.log)
                
                # Add tool to question
                question.add_tool_message(action)
                await self.on_tool(question, action, tool)
                
                # Run tool
                observation = tool.run(action.tool_input)
                self.app.log("Answer " + str(observation))
            
            response.append((action, observation))
        
        return response
    
    
    async def send(self, question):
        
        """
        Отправить вопрос в LLM с учетом tools
        """
        
        step = 1
        while True:
            
            self.app.log("Step " + str(step))
            message = await self.send_question(question)
            if len(message.tool_calls) == 0:
                break
            
            result = await self.run_tools(question, message)
            question.response_step.extend(result)
            step = step + 1
    
    
    async def on_start(self, question):
        await self.client_provider.send_broadcast_message(
            "start_chat",
            {
                "id": question.message_ai.id,
                "chat_id": question.chat.uid,
            }
        )
    
    
    async def on_tool(self, question, action, tool):
        await self.database_update(question, True)
    
    async def on_chunk(self, question, chunk):
        text_chunk = chunk.content
        if text_chunk == "":
            return
        await self.database_update(question)
        self.app.print(text_chunk, end="", flush=True)
    
    async def on_message(self, question, message):
        await self.database_update(question, True)
        self.app.print("\n", end="", flush=True)
    
    async def database_update(self, question, force_update=False):
        
        """
        Update message in database
        """
        
        if force_update or len(question.answer) > question.answer_next:
            question.answer_next += random.randint(10, 30)
            await question.message_ai.save(self.database)
        
        # Send to client
        await self.client_provider.send_broadcast_message(
            "update_chat",
            {
                "id": question.message_ai.id,
                "chat_id": question.chat.uid,
                "sender": "ai",
                "content": [block.model_dump() for block in question.message_ai.content],
            }
        )

# Определим функции
def add_tool(a: int, b: int) -> int:
    """Складывает два числа 'a' и 'b'"""
    return a + b

def multiply_tool(a: int, b: int) -> int:
    """Перемножает два числа 'a' и 'b'"""
    return a * b

def magic_function(a: int) -> int:
    """Applies a magic function to an input."""
    return a + 5


class Tools:
    
    def __init__(self, app):
        self.app = app
        self.items = [
            tool(add_tool),
            tool(multiply_tool),
            tool(magic_function),
        ]
    
    def bind(self, llm):
        return llm.bind_tools(self.items)
    
    def find(self, action):
        for tool in self.items:
            if tool.name == action.tool:
                return tool


class McpServer:
    
    def __init__(self, app):
        self.app = app
        self.mcp = FastMCP("BayLang AI")
        self.starlette = app.get("starlette")
        self.starlette.mount("/api/chat", self.mcp.sse_app())
        self.app.log("Create MCP Server")
    
    def update_tools(self):
        tools = self.app.get("tools")
        for item in tools.items:
            self.mcp.add_tool(item.func)
    
    async def start(self):
        self.update_tools()
    

class AI:
    
    
    def __init__(self, app):
        
        """
        Constructor
        """
        
        self.app = app
        self.database = app.get("database")
        self.database_path = "/app/var/database"
        self.device = "cpu"
        self.tools = app.get("tools")
        self.chat_provider = self.app.get("chat_provider")
        self.client_provider = self.app.get("client_provider")
    
    
    def init_llm(self):
        
        """
        Connect to LLM
        """
        
        self.llm_answer = ChatOllama(
            base_url="http://database_ollama:11434",
            model="qwen2.5:3b",
            temperature=0.5,
        )
        self.agent = Agent(self.app, self.llm_answer)
    
    
    async def send_question(self, chat: Chat, content: list[AbstractBlock], create_async_task=False):
        
        """
        Send question to LLM and save in database
        """
        
        # Create human message
        message_human = Message(
            sender = Message.SENDER_HUMAIN,
            chat_id = chat.id,
            content = content
        )
        
        # Create AI message
        message_ai = Message(
            sender = Message.SENDER_AI,
            chat_id = chat.id,
        )
        
        # Save messages to database
        await message_human.save(self.database)
        await message_ai.save(self.database)
        
        task = self.send_message(
            chat=chat,
            message_human=message_human,
            message_ai=message_ai
        )
        
        if create_async_task:
            asyncio.create_task(task)
        else:
            await task
        
        return [message_human, message_ai]
    
    
    async def send_message(self, chat, message_human, message_ai):
   
        """
        Генерация ответа LLM и рассылка всем клиентам по WebSocket.
        """
        
        self.app.log("")
        self.app.log("Receive message: " + message_human.get_text())
        
        # Start chat
        await self.client_provider.send_broadcast_message(
            "start_chat",
            {
                "id": message_ai.id,
                "chat_id": chat.uid,
            }
        )
        
        # Wait 100ms
        await asyncio.sleep(0.1)
        
        try:
            question = Question(message_human.get_text())
            question.chat = chat
            question.message_human = message_human
            question.message_ai = message_ai
            
            # Получить историю сообщений
            question.history = await Message.get_by_chat_id(
                self.database,
                fields=["id", "sender", "content"],
                chat=chat, limit=10
            )
            
            # Отправить запрос в LLM
            await self.agent.send(question)
            
            # Send end
            self.app.log("Ok")
            await self.client_provider.send_broadcast_message(
                "end_chat",
                {
                    "id": message_ai.id,
                    "chat_id": chat.uid,
                }
            )
            
        except Exception as e:
            self.app.exception(e)
            await self.client_provider.send_broadcast_message(
                "error_chat",
                {
                    "id": message_ai.id,
                    "chat_id": chat.uid,
                    "error": str(e),
                }
            )
import asyncio, torch, random, sys, os
import numpy as np
from langchain.agents.format_scratchpad.tools import format_to_tool_messages
from langchain.agents.output_parsers.tools import ToolAgentAction
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from langchain_ollama import ChatOllama
from mcp.server.fastmcp import FastMCP
from starlette.routing import Mount


class Question:
    
    def __init__(self, content, history=None):
        self.answer = ""
        self.answer_next = 0
        self.content = content
        self.data = {}
        self.chunks = []
        self.context = []
        self.history = []
        self.response_step = []
    
    
    def get_history(self):
        
        """
        Получить историю ввиде массива
        """
        
        history = []
        for item in self.history:
            if isinstance(item, HumanMessage):
                history.append("Human:\n" + item.content)
            elif isinstance(item, AIMessage):
                history.append("AI:\n" + item.content)
        return history
    
    
    def get_system_prompt(self):
        
        """
        Возвратить системный промпт
        """
        
        text = ["Ты консультант для программистов. Отвечай на русском языке в деловом стиле. Если задача требует вычислений или инструментов, используй доступные функции."]
        history = self.get_history()
        if len(history) > 0:
            history = "\n\n".join(history)
            text.append("История:\n\n" + history)
        return "------------------\n".join(text)
    
    
    async def get_prompt(self):
        
        """
        Получить промпт на основе вопроса
        """
        
        prompt = [
            SystemMessage(content=self.get_system_prompt()),
            HumanMessage(content=" ".join([self.content, "Отвечай на русском языке"]))
        ]
        prompt.extend(format_to_tool_messages(self.response_step))
        return prompt
    

class Agent:
    
    def __init__(self, app, llm, callback):
        self.app = app
        self.llm = llm
        self.callback = callback
        
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
        
        # Очистить ответ
        question.chunks = []
        await self.send_callback("start", {
            "question": question,
        })
        
        # Получить промт
        prompt = await question.get_prompt()
        self.app.log(prompt)
        
        # Отправим вопрос LLM
        response = self.llm.astream(prompt, stream=True)
        async for chunk in response:
            await self.send_callback("chunk", {
                "question": question,
                "chunk": chunk,
            })
            question.chunks.append(chunk)
        
        # Get tools
        tool_calls = []
        for chunk in question.chunks:
            if hasattr(chunk, "tool_calls") and chunk.tool_calls:
                tool_calls.extend(chunk.tool_calls)
        
        # Get content
        full_content = "".join(chunk.content for chunk in question.chunks)
        
        # Build mesage
        message = AIMessage(content=full_content, tool_calls=tool_calls)
        await self.send_callback("message", {
            "question": question,
            "message": message,
        })
        
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
    
    
    async def run_tools(self, question, items):
        
        """
        Выполнить функции
        """
        
        response = []
        for action in items:
            tool = self.tools.find(action)
            observation = None
            
            if tool:
                self.app.log("Run tool " + action.log)
                await self.send_callback("tool", {
                    "action": action,
                    "question": question,
                    "tool": tool,
                })
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
            
            tools = self.get_tools(message)
            result = await self.run_tools(question, tools)
            question.response_step.extend(result)
            step = step + 1


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
        self.mcp.settings.mount_path = "/api/chat"
        self.starlette = app.get("starlette")
        self.starlette.mount("/", self.mcp.sse_app())
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
        self.agent = Agent(self.app, self.llm_answer, self.callback)
    
    
    async def callback(self, request, kind, data):
        
        """
        Send message callback
        """
        
        force_update = False
        question = data["question"]
        answer_message_id = question.data["answer_message_id"]
        chat_id = question.data["chat_id"]
        
        if kind == "start":
            await self.client_provider.send_broadcast_message({
                "event": "start_chat",
                "message":
                {
                    "id": answer_message_id,
                    "chat_id": chat_id,
                }
            })
            return
        
        if kind == "message":
            
            force_update = True
            self.app.print("\n", end="", flush=True)
        
        if kind == "tool":
            
            force_update = True
            if question.answer != "":
                question.answer += "\n"
            question.answer += data["action"].log + "\n"
        
        if kind == "chunk":
            
            # Get text chunk
            text_chunk = data["chunk"].content
            if text_chunk == "":
                return
            
            self.app.print(text_chunk, end="", flush=True)
            
            # Answer
            question.answer += text_chunk
        
        # Обновление истории
        if force_update or len(question.answer) > question.answer_next:
            question.answer_next += random.randint(10, 30)
            await self.chat_provider.update_message(answer_message_id, question.answer)
        
        # Рассылаем всем клиентам
        await self.client_provider.send_broadcast_message({
            "event": "update_chat",
            "message":
            {
                "id": answer_message_id,
                "chat_id": chat_id,
                "sender": "assistant",
                "text": question.answer,
            }
        })
    
    
    async def send_message(self, chat_id, chat_message_id, answer_message_id, message):
   
        """
        Генерация ответа LLM и рассылка всем клиентам по WebSocket.
        """
        
        self.app.log("")
        self.app.log("Receive message: " + message)
        
        # Start chat
        await self.client_provider.send_broadcast_message({
            "event": "start_chat",
            "message":
            {
                "id": answer_message_id,
                "chat_id": chat_id,
            }
        })
        
        # Wait 100ms
        await asyncio.sleep(0.1)
        
        try:
            question = Question(message)
            question.data = {
                "chat_id": chat_id,
                "chat_message_id": chat_message_id,
                "answer_message_id": answer_message_id,
            }
            
            # Получить историю сообщений
            history = await self.chat_provider.get_last_messages(chat_id, 10)
            
            # История сообщений
            question.history = []
            for item in history:
                item_id = item["id"]
                text = item["text"]
                if text == "" or \
                    item_id == chat_message_id or \
                    item_id == answer_message_id:
                        continue
                if item["sender"] == "human":
                    question.history.append(HumanMessage(text))
                else:
                    question.history.append(AIMessage(text))
            
            # Отправить запрос в LLM
            await self.agent.send(question)
            
            # Send end
            self.app.log("Ok")
            await self.client_provider.send_broadcast_message({
                "event": "end_chat",
                "message":
                {
                    "id": answer_message_id,
                    "chat_id": chat_id,
                }
            })
            
        except Exception as e:
            self.app.exception(e)
            await self.client_provider.send_broadcast_message({
                "event": "error_chat",
                "message":
                {
                    "id": answer_message_id,
                    "chat_id": chat_id,
                    "error": str(e),
                }
            })
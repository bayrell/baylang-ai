import asyncio, torch, random, sys, os
import numpy as np
from langchain.agents.format_scratchpad.tools import format_to_tool_messages
from langchain.agents.output_parsers.tools import ToolAgentAction
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, SystemMessage
from langchain_core.messages.ai import UsageMetadata, add_usage, add_ai_message_chunks
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from langchain_ollama import ChatOllama
from mcp.server.fastmcp import FastMCP
from starlette.routing import Mount


class Question:
    
    def __init__(self, content="", history=None):
        self.answer = ""
        self.answer_next = 0
        self.content = content
        self.current_block = ""
        self.data = {}
        self.context = []
        self.history = []
        self.messages = []
        self.lines = []
        self.usage_metadata = UsageMetadata()
        self.response_step = []
    
    
    def get_current_line(self):
        if len(self.lines) == 0:
            return None
        return self.lines[-1]
    
    
    def add_new_line(self, block="text", content=""):
        
        """
        Add new line
        """
        
        line = {
            "block": block,
            "content": content,
        }
        self.lines.append(line)
        return line
    
    
    def set_line_content(self, block=None, content=None, tool=None):
        
        """
        Set current line content
        """
        
        line = self.get_current_line()
        if block is not None:
            line["block"] = block
        if content is not None:
            line["content"] = content
        if tool is not None:
            line["tool"] = tool
    
    
    def create_new_line(self):
        
        """
        Create new line and detect block
        """
        
        # Get current line
        current_line = self.get_current_line()
        if current_line is None:
            self.add_new_line()
            return
        
        # Detect block of current line
        if current_line["block"] == "text":
            if current_line["content"][0:3] == "```":
                current_line["block"] = "code"
        else:
            if current_line["content"][-3:] == "```":
                self.add_new_line()
                return
        
        # Add new line
        if current_line["block"] == "code":
            if not "language" in current_line:
                lines = current_line["content"][0:3].split("\n")
                current_line["language"] = lines[0][3:]
            current_line["content"] += "\n"
        elif current_line["content"] != "":
            self.add_new_line()
    
    
    def add_chunk_message(self, chunk: AIMessageChunk):
        
        """
        Add chunk message
        """
        
        content = str(chunk.content)
        if content == "":
            return
        
        # Create current line
        if len(self.lines) == 0:
            self.add_new_line()
        
        # Add content
        self.answer += content
        
        # Add lines
        current_line = self.get_current_line()
        for char in content:
            if char == "\n":
                self.create_new_line()
                current_line = self.get_current_line()
            else:
                current_line["content"] += char
        
    
    def add_tool_message(self, action: ToolAgentAction):
        
        """
        Add run tool message
        """
        
        # Add new line
        self.create_new_line()
        self.set_line_content(
            block="tool",
            content=action.log,
            tool={
                "name": action.tool,
                "args": action.tool_input
            }
        )
        self.add_new_line()
        
        # Add answer
        if self.answer != "":
            self.answer += "\n"
        self.answer += action.log + "\n"
        
    
    def get_history(self):
        
        """
        Get history as list
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
    
    def get_content(self):
        if len(self.lines) == 0:
            return []
        if self.lines[-1]["content"] == "":
            return self.lines[:-1]
        return self.lines
    
    def get_usage(self, key):
        return self.usage_metadata[key] if key in self.usage_metadata else 0
    
    def get_usage_metadata(self):
        return {
            "input_tokens": self.get_usage("input_tokens"),
            "output_tokens": self.get_usage("output_tokens"),
            "total_tokens": self.get_usage("total_tokens"),
        }
    

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
        
        chunks = []
        tool_calls = []
        
        # Start question
        await self.send_callback("start", {
            "question": question,
        })
        
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
            await self.send_callback("chunk", {
                "question": question,
                "chunk": chunk,
            })
        
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
        question.usage_metadata = add_usage(question.usage_metadata, message.usage_metadata)
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
                question.add_tool_message(action)
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
            
            result = await self.run_tools(question, message)
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
            await self.client_provider.send_broadcast_message(
                "start_chat",
                {
                    "id": answer_message_id,
                    "chat_id": chat_id,
                }
            )
            return
        
        if kind == "message":
            
            force_update = True
            self.app.print("\n", end="", flush=True)
        
        if kind == "tool":
            force_update = True
        
        if kind == "chunk":
            
            # Get text chunk
            text_chunk = data["chunk"].content
            if text_chunk == "":
                return
            
            self.app.print(text_chunk, end="", flush=True)
        
        # Обновление истории
        if force_update or len(question.answer) > question.answer_next:
            question.answer_next += random.randint(10, 30)
            await self.chat_provider.update_message(answer_message_id, question)
        
        # Рассылаем всем клиентам
        await self.client_provider.send_broadcast_message(
            "update_chat",
            {
                "id": answer_message_id,
                "chat_id": chat_id,
                "sender": "assistant",
                "content": question.get_content(),
            }
        )
    
    
    async def send_message(self, chat_id, chat_message_id, answer_message_id, message):
   
        """
        Генерация ответа LLM и рассылка всем клиентам по WebSocket.
        """
        
        self.app.log("")
        self.app.log("Receive message: " + message)
        
        # Start chat
        await self.client_provider.send_broadcast_message(
            "start_chat",
            {
                "id": answer_message_id,
                "chat_id": chat_id,
            }
        )
        
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
                content = item["content"]
                content = [block["content"] for block in content]
                content = " ".join(content)
                if content == "" or \
                    item_id == chat_message_id or \
                    item_id == answer_message_id:
                        continue
                if item["sender"] == "human":
                    question.history.append(HumanMessage(content))
                else:
                    question.history.append(AIMessage(content))
            
            # Отправить запрос в LLM
            await self.agent.send(question)
            
            # Send end
            self.app.log("Ok")
            await self.client_provider.send_broadcast_message(
                "end_chat",
                {
                    "id": answer_message_id,
                    "chat_id": chat_id,
                }
            )
            
        except Exception as e:
            self.app.exception(e)
            await self.client_provider.send_broadcast_message(
                "error_chat",
                {
                    "id": answer_message_id,
                    "chat_id": chat_id,
                    "error": str(e),
                }
            )
import asyncio, random
from langchain_core.messages import AIMessage
from langchain_core.messages.ai import add_ai_message_chunks
from model import Agent, Chat, Message, AbstractBlock
from .question import Question


class AgentHelper:
    
    def __init__(self, app, llm, question):
        self.app = app
        self.llm = llm
        self.question = question
        self.database = app.get("database")
        self.client_provider = app.get("client_provider")
        
        # Bind tools
        self.tools = None
        #self.tools = app.get("tools")
        #if self.tools:
        #    self.llm = self.tools.bind(self.llm)
    
    
    async def send_callback(self, kind, data=None):
        
        if self.callback == None:
            return
        
        await self.callback(self, kind, data)
    
    
    async def send_question(self):
        
        """
        Отправить вопрос в LLM
        """
        
        chunks = []
        tool_calls = []
        
        # Start question
        await self.on_start()
        
        # Get prompt
        prompt = self.question.get_prompt()
        self.app.log(prompt)
        
        # Send question to LLM
        response = self.llm.astream(prompt, stream=True)
        async for chunk in response:
            
            # Add tool
            if hasattr(chunk, "tool_calls") and chunk.tool_calls:
                tool_calls.extend(chunk.tool_calls)
            
            # Add chunk
            chunks.append(chunk)
            self.question.add_chunk_message(chunk)
            
            # Send chunk
            await self.on_chunk(chunk)
        
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
        self.question.message_ai.add_usage(message.usage_metadata)
        
        # Trim messages block
        for block in self.question.message_ai.content:
            block.trim()
        
        # Send message
        await self.on_message(message)
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
    
    
    async def run_tools(self, message):
        
        """
        Выполнить функции
        """
        
        response = []
        if self.tools is None:
            return response
        
        actions = self.get_tools(message)
        for action in actions:
            tool = self.tools.find(action)
            observation = None
            
            if tool:
                self.app.log("Run tool " + action.log)
                
                # Add tool to question
                self.question.add_tool_message(action)
                await self.on_tool(action, tool)
                
                # Run tool
                observation = tool.run(action.tool_input)
                self.app.log("Answer " + str(observation))
            
            response.append((action, observation))
        
        return response
    
    
    async def send(self):
        
        """
        Отправить вопрос в LLM с учетом tools
        """
        
        step = 1
        while True:
            
            self.app.log("Step " + str(step))
            message = await self.send_question()
            if len(message.tool_calls) == 0:
                break
            
            result = await self.run_tools(message)
            self.question.response_step.extend(result)
            step = step + 1
    
    
    async def on_start(self):
        await self.client_provider.send_broadcast_message(
            "start_chat",
            {
                "id": self.question.message_ai.id,
                "chat_id": self.question.chat.uid,
            }
        )
    
    async def on_tool(self, action, tool):
        await self.database_update(True)
    
    async def on_chunk(self, chunk):
        text_chunk = chunk.content
        if text_chunk == "":
            return
        await self.database_update()
        self.app.print(text_chunk, end="", flush=True)
    
    async def on_message(self, message):
        await self.database_update(True)
        self.app.print("\n", end="", flush=True)
    
    async def database_update(self, force_update=False):
        
        """
        Update message in database
        """
        
        answer = self.question.message_ai.get_text()
        if force_update or len(answer) > self.question.answer_next:
            self.question.answer_next += random.randint(10, 30)
            await self.question.message_ai.save(self.database)
        
        # Send to client
        await self.client_provider.send_broadcast_message(
            "update_chat",
            {
                "id": self.question.message_ai.id,
                "chat_id": self.question.chat.uid,
                "sender": "ai",
                "content": [block.model_dump() for block in self.question.message_ai.content],
            }
        )


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
        self.question = None
        self.message_ai = None
        self.message_human = None
        self.chat = None
        self.content = []
    
    
    def set_agent(self, agent: Agent):
        
        """
        Set agent
        """
        
        self.agent = agent
    
    
    def set_chat(self, chat: Chat):
        
        """
        Set chat
        """
        
        self.chat = chat
    
    
    def set_content(self, content: list[AbstractBlock]):
        
        """
        Set content
        """
        
        self.content = content
    
    
    async def load(self):
        
        """
        Load data
        """
        
        # Create messages
        self.create_messages()
        
        # Create question
        self.create_question()
        
        # Save messages to database
        await self.message_human.save(self.database)
        await self.message_ai.save(self.database)
        
        # Load history
        await self.load_history()
        
        # Bind agent LLM
        await self.agent.bind_llm(self.database)
        
    
    async def create_send_task(self):
        
        """
        Send content to LLM and save in database
        """
        
        # Create task
        task = self.send_message()
        asyncio.create_task(task)
    
    
    def create_messages(self):
        
        # Create human message
        self.message_human = Message(
            sender = Message.SENDER_HUMAIN,
            chat_id = self.chat.id,
            content = self.content
        )
        
        # Create AI message
        self.message_ai = Message(
            agent_name = self.agent.name if self.agent is not None else "",
            sender = Message.SENDER_AI,
            chat_id = self.chat.id,
        )
    
    
    def create_question(self):
        
        """
        Create question
        """
        
        self.question = Question(self.message_human.get_text())
        self.question.agent = self.agent
        self.question.chat = self.chat
        self.question.message_human = self.message_human
        self.question.message_ai = self.message_ai
    
    
    async def load_history(self, limit=10):
    
        # Получить историю сообщений
        self.question.history = await Message.get_by_chat_id(
            self.database,
            fields=["id", "sender", "content"],
            chat=self.chat, limit=limit
        )
    
    
    async def send_message(self):
   
        """
        Генерация ответа LLM и рассылка всем клиентам по WebSocket.
        """
        
        self.app.log("")
        self.app.log("Receive message: " + self.message_human.get_text())
        
        # Start chat
        await self.client_provider.send_broadcast_message(
            "start_chat",
            {
                "id": self.message_ai.id,
                "chat_id": self.chat.uid,
            }
        )
        
        # Wait 100ms
        await asyncio.sleep(0.1)
        
        try:
            # Отправить запрос в LLM
            self.helper = AgentHelper(self.app, self.agent.factory(), self.question)
            await self.helper.send()
            
            # Save messages to database
            await self.message_human.save(self.database)
            await self.message_ai.save(self.database)
            
            # Send end
            self.app.log("Ok")
            await self.client_provider.send_broadcast_message(
                "end_chat",
                {
                    "id": self.message_ai.id,
                    "chat_id": self.chat.uid,
                }
            )
            
        except Exception as e:
            self.app.exception(e)
            await self.client_provider.send_broadcast_message(
                "error_chat",
                {
                    "id": self.message_ai.id,
                    "chat_id": self.chat.uid,
                    "error": str(e),
                }
            )
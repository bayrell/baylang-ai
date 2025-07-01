import asyncio, torch, sys, os
import numpy as np
from langchain_ollama import ChatOllama


class AI:
    
    
    def __init__(self, app):
        
        """
        Constructor
        """
        
        self.app = app
        self.database = app.get("database")
        self.database_path = "/app/var/database"
        self.device = "cpu"
        self.embeddings_model = None
        self.embeddings_model_name = None
        self.vector_store = None
    
    
    def init_llm(self):
        
        # Connect to LLM
        self.llm_answer = ChatOllama(
            base_url="http://database_ollama:11434",
            model="qwen2.5:1.5b",
            temperature=0.5,
        )
    
    
    async def get_prompt(self, question):
        
        """
        Получить промт на основе вопроса
        """
        
        # Создаем промт
        context = ""
        system_message = f"Ты консультант для программистов. Отвечай на русском языке в деловом стиле. Используй следующую информацию для ответа:\n\n{context}"
        prompt = [
            ("system", system_message),
            ("human", " ".join([question, "Отвечай на русском языке"]))
        ]
        
        return prompt
    
    
    async def send_question(self, chat_id, question):
        
        """
        Send question to LLM
        """
        
        # Получить промт
        prompt = await self.get_prompt(question)
        print(prompt)
        
        # Отправим вопрос LLM
        for chunk in self.llm_answer.stream(prompt, stream=True):
            yield chunk
        
    
    async def send_message(self, chat_id, message_id, message):
   
        """
        Генерация ответа LLM и рассылка всем клиентам по WebSocket.
        """
        
        chat_provider = self.app.get("chat_provider")
        client_provider = self.app.get("client_provider")
        
        print("")
        print("Receive message: " + message)
        
        # Wait 100ms
        await asyncio.sleep(0.1)
        
        try:
            answer = ""
            async for chunk in self.send_question(chat_id, message):
                
                # Get text chunk
                text_chunk = chunk.content
                print(text_chunk, end="", flush=True)
                
                # Answer
                answer += text_chunk
                
                # Рассылаем всем клиентам
                await client_provider.send_broadcast_message({
                    "event": "send_message",
                    "message":
                    {
                        "id": message_id,
                        "chat_id": chat_id,
                        "sender": "assistant",
                        "text": answer,
                    }
                })
                
                # Обновление истории
                await chat_provider.update_message(message_id, answer)
                
        except Exception as e:
            print(e)
            await client_provider.send_broadcast_message({
                "event": "error",
                "message": str(e)
            })
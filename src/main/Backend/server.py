import asyncio, time
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from langchain_ollama import ChatOllama
from service import add_message, create_chat, delete_chat, \
    get_chat_by_id, get_chat_items_by_query, get_prompt, json_encode, \
    get_chat_items, get_message_by_id, update_chat_message

app = FastAPI()

# Разрешаем CORS для фронта
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключенные клиенты
connected_clients = set()

# Подключение к LLM
llm = ChatOllama(
    base_url="http://database_ollama:11434",
    model="qwen2.5-coder:1.5b",
    #model="qwen2.5-coder:3b",
    temperature=0.5,
)

async def send_broadcast_message(message):
    
    """
    Отправить сообщение всем клиентам
    """
    
    disconnected_clients = []
    for websocket in connected_clients:
        try:
            await websocket.send_text(json_encode(message))
        except WebSocketDisconnect:
            disconnected_clients.add(websocket)
    
    for websocket in disconnected_clients:
        connected_clients.remove(websocket)


async def send_message_llm(chat_id, message_id, message):
   
    """
    Генерация ответа LLM и рассылка всем клиентам по WebSocket.
    """
    
    print("Receive message " + message)
    
    # Wait 100ms
    await asyncio.sleep(0.1)
    
    # Получить промт
    system_message = "Ты консультант для программистов. Отвечай на русском языке"
    prompt = await get_prompt(chat_id, system_message, message)
    print(prompt)
    
    try:
        answer = ""
        for chunk in llm.stream(prompt, stream=True):
            
            # Get text chunk
            text_chunk = chunk.content
            print(text_chunk, end="", flush=True)
            
            # Answer
            answer += text_chunk
            
            # Рассылаем всем клиентам
            await send_broadcast_message({
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
            await update_chat_message(message_id, answer)
            
    except Exception as e:
        await send_broadcast_message({
            "event": "error",
            "message": str(e)
        })


@app.get("/")
@app.head("/")
async def action_index():
    return {"message": "Hello, World!"}


@app.post("/app.chat/load")
async def action_load(request: Request):
    
    items = await get_chat_items()
    
    return {
        "code": 1,
        "message": "Ok",
        "data": {
            "items": items
        }
    }


@app.post("/app.chat/create")
async def action_create(request: Request):
    
    # Get form data
    post_data = await request.form()
    post_data = dict(post_data)
    
    # Get model name and message
    model_name = post_data.get("data[item][model]")
    message = post_data.get("data[item][message]")
    if model_name is None or message is None:
        return {
            "code": -1,
            "message": "Fields error",
            "data": {},
        }
    
    chat_name = "Chat " + str(round(time.time()))
    chat_id = await create_chat(chat_name)
    
    # Add messages
    chat_message_id = await add_message(chat_id, "human", message)
    answer_message_id = await add_message(chat_id, "assistant", "")
    
    # Get chat
    chat_items = await get_chat_items_by_query("select * from chats where id=?", [chat_id])
    
    # Send message to LLM
    asyncio.create_task(send_message_llm(chat_id, answer_message_id, message))
    
    return {
        "code": 1,
        "message": "Ok",
        "data": {
            "chat": chat_items[0],
        },
    }


@app.post("/app.chat/send")
async def action_send(request: Request):
    
    # Get form data
    post_data = await request.form()
    post_data = dict(post_data)
    chat_id = post_data.get("data[chat_id]")
    message = post_data.get("data[text]")
    
    # Add message
    await add_message(chat_id, "human", message)
    
    # Add answer
    answer_message_id = await add_message(chat_id, "assistant", "")
    answer_message_item = await get_message_by_id(answer_message_id)
    
    # Send message to LLM
    asyncio.create_task(send_message_llm(chat_id, answer_message_id, message))
    
    return {
        "code": 1,
        "message": "Ok",
        "data": {
            "chat_id": chat_id,
            "answer": answer_message_item,
        },
    }


@app.post("/app.chat/delete")
async def action_delete(request: Request):
    
    # Get form data
    post_data = await request.form()
    post_data = dict(post_data)
    chat_id = post_data.get("data[chat_id]")
    
    # Delete chat
    await delete_chat(chat_id)
    
    # Return result
    return {
        "code": 1,
        "message": "Ok",
        "data": {
        },
    }


@app.websocket("/socket")
async def chat_endpoint(websocket: WebSocket):
    
    await websocket.accept()
    connected_clients.add(websocket)
    
    try:
        while True:
            await websocket.receive_text()
    
    except WebSocketDisconnect:
        connected_clients.remove(websocket)
    
    except Exception as e:
        print(f"WebSocket error: {e}")
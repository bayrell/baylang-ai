import time
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from service import add_message, create_chat, delete_chat, \
    get_chat_by_id, get_chat_items, get_message_by_id

app = FastAPI()

# Разрешаем CORS для фронта
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
@app.head("/")
def action_index():
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
    chat_item = await get_chat_by_id(chat_id)
    chat_message_id = await add_message(chat_id, "human", message)
    chat_message_item = await get_message_by_id(chat_message_id)
    
    return {
        "code": 1,
        "message": "Ok",
        "data": {
            "chat": chat_item,
            "message": chat_message_item,
        },
    }


@app.post("/app.chat/delete")
async def action_delete(request: Request):
    
    # Get form data
    post_data = await request.form()
    post_data = dict(post_data)
    chat_id = post_data.get("data[pk][id]")
    
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
    try:
        while True:
            user_message = await websocket.receive_text()
            await websocket.send_text(user_message)
    
    except WebSocketDisconnect:
        print("Disconnected")
    
    except Exception as e:
        print(f"WebSocket error: {e}")
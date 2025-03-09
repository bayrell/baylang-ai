from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

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
def root():
    return {"message": "Hello, World!"}


@app.websocket("/socket")
async def chat_endpoint(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_text("Hello, World!")

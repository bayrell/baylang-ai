from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

@app.get("/")
@app.head("/")
def root():
    return {"message": "Hello, World!"}

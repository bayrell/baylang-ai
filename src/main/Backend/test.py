import asyncio
import websockets

async def test_websocket():
    uri = "ws://chat.baylang.docker0/api/chat/socket"
    print(uri)
    async with websockets.connect(uri) as websocket:
        await websocket.send("Hello WebSocket!")
        response = await websocket.recv()
        print(f"Ответ от сервера: {response}")

asyncio.run(test_websocket())

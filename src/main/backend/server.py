import asyncio
from app import App

# Create application
app = App()
asyncio.create_task(app.start())

# Get web
web = app.get("web")
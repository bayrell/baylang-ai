import asyncio, os, sys
from app import App

# Add path
sys.path.append(os.getcwd())

# Create application
app = App()
app.init()
asyncio.create_task(app.start())

# Get web
web = app.get("web")
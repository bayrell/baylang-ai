import os
from uvicorn.logging import logging
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route, Mount
from ai import AI, Tools, McpServer
from database import Database
from client import Client
from api.chat import ChatApi, ChatProvider


class Container:
    def __init__(self):
        self.services = {}
        self.providers = {}
    
    def register(self, name, callback):
        self.services[name] = {
            "callback": callback,
            "singleton": False,
        }
    
    def singleton(self, name, callback):
        self.services[name] = {
            "callback": callback,
            "singleton": True,
        }
    
    def get(self, name):
        if name in self.providers:
            return self.providers[name]
        
        instance = None
        
        if name in self.services:
            res = self.services[name]
            instance = res["callback"]()
            if res["singleton"]:
                self.providers[name] = instance
        
        return instance
    
    def init(self):
        for name, item in self.services.items():
            if item["singleton"]:
                self.get(name)
    
    async def start(self):
        for name, item in self.services.items():
            if item["singleton"]:
                provider = self.get(name)
                if hasattr(provider, "start"):
                    await provider.start()
    
    def print(self, message, end="\n", flush=True):
        print(message, end=end, flush=flush)
    
    def log(self, message):
        logger = self.get("logger")
        logger.info(message)
    
    def exception(self, message):
        logger = self.get("logger")
        logger.exception(message)


class Web:
    def __init__(self, app):
        self.starlette = app.get("starlette")
        self.starlette.add_route("/", self.index_page, methods=["GET"])
    
    async def __call__(self, scope, receive, send):
        return await self.starlette(scope, receive, send)
    
    async def index_page(self, request):
        return JSONResponse({"message": "Hello, World!"})


class App(Container):
    def __init__(self):
        
        Container.__init__(self)
        
        # Register singleton
        self.singleton("starlette", lambda: Starlette())
        
        # Register AI
        def register_ai():
            ai = AI(self)
            ai.init_llm()
            return ai
        self.singleton("ai", register_ai)
        
        # Register database
        self.singleton("database", lambda: Database("/data/db/baylang.db"))
        
        # Register logger
        self.singleton("logger", lambda: logging.getLogger("uvicorn"))
        
        # Register providers
        self.singleton("chat_api", lambda: ChatApi(self))
        self.singleton("chat_provider", lambda: ChatProvider(self))
        self.singleton("client_provider", lambda: Client(self))
        self.singleton("mcp", lambda: McpServer(self))
        self.singleton("tools", lambda: Tools(self))
        self.singleton("web", lambda: Web(self))
        
        # Init providers
        self.init()
    
    
    def print_routes(self):
        
        """
        Print starlette routes
        """
        
        def list_routes(routes, prefix=""):
            urls = []
            for route in routes:
                if isinstance(route, Route):
                    urls.append(f"{prefix}{route.path}")
                elif isinstance(route, Mount):
                    urls.extend(list_routes(route.routes, prefix + route.path))
            return urls
        
        for url in list_routes(self.get("starlette").routes):
            print(url)
        
    
    async def run(self):
        
        # Start providers
        await self.start()
        
        db = self.get("database")
        logger = self.get("logger")
        try:
            db.connect()
            logger.info("Database connected")
        except Exception as e:
            logger.exception(f"Fatal error: {str(e)}")

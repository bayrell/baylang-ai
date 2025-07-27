import os
from uvicorn.logging import logging
from starlette.applications import Starlette
from starlette.staticfiles import StaticFiles
from starlette.responses import FileResponse
from starlette.routing import Route, Mount
from ai import AI, Tools, McpServer
from database import Database
from client import Client
from helper import Helper
from api.chat import ChatApi

logging.getLogger("mysql.connector").setLevel(logging.WARNING)
#logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

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
        self.app = app
        self.starlette = app.get("starlette")
        self.starlette.add_exception_handler(404, self.not_found_page)
        self.starlette.add_route("/", self.index_page, methods=["GET"])
        self.starlette.add_route("/chat", self.index_page, methods=["GET"])
        self.starlette.add_route("/robots.txt", self.static("public/robots.txt"), methods=["GET"])
        self.starlette.mount("/assets", StaticFiles(directory=self.app.public_path("assets")))
        self.starlette.mount("/dist", StaticFiles(directory=self.app.public_path("dist")))
    
    async def __call__(self, scope, receive, send):
        return await self.starlette(scope, receive, send)
    
    def static(self, file_name):
        async def response(request):
            return FileResponse(self.app.path(file_name))
        return response
    
    async def not_found_page(self, request, exception):
        return FileResponse(self.app.path("main/frontend/index.html"), status_code=404)
    
    async def index_page(self, request):
        return FileResponse(self.app.path("main/frontend/index.html"))


class App(Container):
    def __init__(self):
        
        Container.__init__(self)
        
        # Base app path
        self.base_path = "/app"
        
        # Register singleton
        self.singleton("starlette", lambda: Starlette())
        
        # Register AI
        def register_ai():
            ai = AI(self)
            ai.init_llm()
            return ai
        self.singleton("ai", register_ai)
        
        # Register database
        def create_database():
            database = Database()
            database.host = os.getenv("MYSQL_HOST")
            database.user = os.getenv("MYSQL_USERNAME")
            database.password = os.getenv("MYSQL_PASSWORD")
            database.database = os.getenv("MYSQL_DATABASE")
            return database
        self.singleton("database", create_database)
        
        # Register logger
        self.singleton("logger", lambda: logging.getLogger("uvicorn"))
        
        # Register providers
        self.singleton("chat_api", lambda: ChatApi(self))
        self.singleton("client_provider", lambda: Client(self))
        self.singleton("helper", lambda: Helper())
        self.singleton("mcp", lambda: McpServer(self))
        self.singleton("tools", lambda: Tools(self))
        self.singleton("web", lambda: Web(self))
    
    def path(self, *args):
        args = [self.base_path] + list(args)
        return os.path.join(*args)
    
    def public_path(self, *args):
        args = ["public"] + list(args)
        return self.path(*args)
    
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

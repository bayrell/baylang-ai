from mcp.server.fastmcp import FastMCP
from starlette.routing import Mount
from .question import Builder, Question
from .agent import AgentRole, AI

__all__ = ("Builder", "Question", "AgentRole", "AI")


# Определим функции
def add_tool(a: int, b: int) -> int:
    """Складывает два числа 'a' и 'b'"""
    return a + b

def multiply_tool(a: int, b: int) -> int:
    """Перемножает два числа 'a' и 'b'"""
    return a * b

def magic_function(a: int) -> int:
    """Applies a magic function to an input."""
    return a + 5


class Tools:
    
    def __init__(self, app):
        self.app = app
        self.items = [
            tool(add_tool),
            tool(multiply_tool),
            tool(magic_function),
        ]
    
    def bind(self, llm):
        return llm.bind_tools(self.items)
    
    def find(self, action):
        for tool in self.items:
            if tool.name == action.tool:
                return tool


class McpServer:
    
    def __init__(self, app):
        self.app = app
        self.mcp = FastMCP("BayLang AI")
        self.starlette = app.get("starlette")
        self.starlette.mount("/api/chat", self.mcp.sse_app())
        self.app.log("Create MCP Server")
    
    def update_tools(self):
        tools = self.app.get("tools")
        for item in tools.items:
            self.mcp.add_tool(item.func)
    
    async def start(self):
        self.update_tools()
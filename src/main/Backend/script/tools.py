import sys, os
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from langchain_ollama import ChatOllama


# Определим функции
@tool
def add_tool(a, b):
    """Складывает два числа 'a' и 'b'"""
    return a + b

@tool
def multiply_tool(a, b):
    """Перемножает два числа 'a' и 'b'"""
    return a * b

@tool
def magic_function(input):
    """Applies a magic function to an input."""
    return input + 2


llm = ChatOllama(
    base_url="http://database_ollama:11434",
    model="qwen2.5:1.5b",
    temperature=0.5,
)

tools = [add_tool, multiply_tool, magic_function]
tool_calling_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", "Ты консультант для программистов. Отвечай на русском языке в деловом стиле"),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ]
)
agent = create_tool_calling_agent(llm, tools, prompt=tool_calling_prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools)

query = "Выполни magic_function(7)"
prompt = {"input": query}
print(agent_executor.invoke(prompt))
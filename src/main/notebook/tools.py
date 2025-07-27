import asyncio, sys, os
from langchain.agents.format_scratchpad.tools import format_to_tool_messages
from langchain.agents.output_parsers.tools import ToolAgentAction, ToolsAgentOutputParser
from langchain_core.runnables import Runnable, RunnablePassthrough
from langchain_core.messages import AIMessage
from langchain_core.tools import tool
from langchain_core.tools.structured import StructuredTool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_ollama import ChatOllama

# Set env
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

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

class AI:
    
    def __init__(self):
        self.tools = [
            tool(add_tool),
            tool(multiply_tool),
            tool(magic_function),
        ]
    
    def get_llm(self, name):
        llm_answer = ChatOllama(
            base_url="http://database_ollama:11434",
            model=name,
            temperature=0.5,
            streaming=True,
        )
        llm_with_tools = llm_answer.bind_tools(self.tools)
        return llm_with_tools

    def find_tool(self, action):
        for tool in self.tools:
            if tool.name == action.tool:
                return tool
    
    def run_tools(self, items):
        
        response = []
        for action in items:
            tool = self.find_tool(action)
            observation = None
            
            if tool:
                print("Run tool " + action.log)
                observation = tool.run(action.tool_input)
                print("Answer " + str(observation))
            
            response.append((action, observation))
        
        return response

    def send_question(self, llm, prompt_value):
        chunks = []
        response = llm.stream(prompt_value)
        for chunk in response:
            print(chunk.content, end="", flush=True)
            chunks.append(chunk)
        
        # Get tools
        tool_calls = []
        for chunk in chunks:
            if hasattr(chunk, "tool_calls") and chunk.tool_calls:
                tool_calls.extend(chunk.tool_calls)
        
        # Get content
        full_content = "".join(chunk.content for chunk in chunks)
        
        # Build mesage
        message = AIMessage(content=full_content, tool_calls=tool_calls)
        return message
    
    def get_tools_answer(self, answer):
        items = []
        for item in answer.tool_calls:
            log = item["name"] + " with args " + str(item["args"])
            action = ToolAgentAction(
                tool=item["name"],
                tool_input=item["args"],
                log=log,
                message_log=[answer],
                tool_call_id=item["id"],
            )
            items.append(action)
        return items
    
    def send_message(self, llm, query):
        
        step = 1
        response_step = []
        tool_calling_prompt = ChatPromptTemplate.from_messages(
            [
                ("system", "Ты консультант для программистов. Отвечай на русском языке в деловом стиле. Если задача требует вычислений или инструментов, используй доступные функции."),
                ("human", "{input}"),
                ("placeholder", "{agent_scratchpad}"),
            ]
        )
        while True:
            prompt = {
                "input": query,
                "intermediate_steps": response_step,
                "agent_scratchpad": format_to_tool_messages(response_step)
            }
            prompt_value = tool_calling_prompt.invoke(prompt)
            
            print ("Step " + str(step))
            answer = self.send_question(llm, prompt_value)
            if len(answer.tool_calls) == 0:
                break
            
            tools = self.get_tools_answer(answer)
            response_step.extend(self.run_tools(tools))
            step = step + 1
        
        return answer

# Query
#query = "Выполни волшебную функцию над числом 5. Ответ:"
query = "Сначала вычисли 5 + 7, а затем выполни волшебную функцию над результатом сложения. Ответ:"
#query = "Выполни волшебную функцию над числом 5, а затем результат передай еще раз в волшебную функцию. Ответ:"

# Get answer
ai = AI()
model = ai.get_llm("qwen2.5:3b")
answer = ai.send_message(model, query)
print("\nOk")
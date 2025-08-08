import re, html
from langchain.agents.format_scratchpad.tools import format_to_tool_messages
from langchain.agents.output_parsers.tools import ToolAgentAction
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, SystemMessage


class Builder:
    
    def __init__(self, prompt):
        self.prompt = prompt
        self.messages = {
            "ai": AIMessage,
            "assistant": AIMessage,
            "system": SystemMessage,
            "user": HumanMessage,
        }
    
    def get_result(self, variables=None):
        
        if variables is None:
            variables = {}
        
        prompt = self.prompt
        for key, value in variables.items():
            pattern = re.compile(re.escape(f"%{key}%"), re.IGNORECASE)
            prompt = pattern.sub(value, prompt)
        
        matches = re.findall(r"<(\w+)>(.*?)</\1>", prompt, re.DOTALL)
        messages = []
        for tag, content in matches:
            tag_lower = tag.lower()
            content = content.strip()
            content = html.unescape(content)
            
            if tag_lower not in self.messages:
                continue
            
            class_name = self.messages[tag_lower]
            messages.append(class_name(content=content))
        
        return messages


class BuilderXML:
    
    def __init__(self, prompt):
        self.prompt = prompt
        self.messages = {
            "ai": AIMessage,
            "assistant": AIMessage,
            "system": SystemMessage,
            "user": HumanMessage,
        }
    
    def get_result(self, variables=None):
        
        import xml.etree.ElementTree as ET
        
        if variables is None:
            variables = {}
        
        prompt = self.prompt
        for key, value in variables.items():
            pattern = re.compile(re.escape(f"%{key}%"), re.IGNORECASE)
            prompt = pattern.sub(value, prompt)
        
        prompt = "<root>" + prompt + "</root>"
        try:
            root = ET.fromstring(prompt)
        except ET.ParseError as e:
            return []
        
        messages = []
        for elem in root:
            tag_lower = elem.tag.lower()
            content = elem.text or ""
            content = content.strip()
            content = html.unescape(content)
            
            if tag_lower not in self.messages:
                continue
            
            class_name = self.messages[tag_lower]
            messages.append(class_name(content=content))
        
        return messages


class Question:
    
    def __init__(self, content="", history=None):
        self.answer_next = 0
        self.agent = None
        self.chat = None
        self.content = content
        self.message_ai = None
        self.message_human = None
        self.context = []
        self.history = []
        self.response_step = []
    
    
    def add_chunk_message(self, chunk: AIMessageChunk):
        
        """
        Add chunk message
        """
        
        self.message_ai.add_chunk(chunk)
        self.message_ai.set_updated("content")
        
    
    def add_tool_message(self, action: ToolAgentAction):
        
        """
        Add run tool message
        """
        
        self.message_ai.add_tool(action)
        self.message_ai.set_updated("content")
        
    
    def get_history(self):
        
        """
        Get history as list
        """
        
        history = []
        for item in self.history:
            if item.id == self.message_ai.id or \
                item.id == self.message_human.id:
                    continue
            message = item.get_message()
            if isinstance(message, HumanMessage):
                history.append("Human:\n" + message.content)
            elif isinstance(message, AIMessage):
                history.append("AI:\n" + message.content)
        return history
    
    
    def get_prompt(self):
        
        """
        Returns question prompt
        """
        
        history = self.get_history()
        builder = Builder(self.agent.prompt)
        prompt = builder.get_result({
            "history": "\n\n".join(history),
            "query": self.content,
        })
        prompt.extend(format_to_tool_messages(self.response_step))
        return prompt
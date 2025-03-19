import sys, os
import numpy as np
import faiss
import torch
from service import *
from langchain.docstore.document import Document
from langchain_community.docstore.in_memory import InMemoryDocstore
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_ollama import ChatOllama
from tqdm import tqdm


class MarkdownParser:
    
    def __init__(self):
        self.blocks = []
        self.lines = []
        self.levels = {}
        self.current_level = 0
    
    def get_header_content(self, level):
        lines = []
        for i in range(1, level + 1):
            if i in self.levels:
                lines.append(self.levels[i])
        return lines
    
    def add_block(self, block):
        if "\n".join(block) == "":
            return
        lines = self.get_header_content(self.current_level - 1)
        content = "\n".join(lines + block)
        self.blocks.append({
            "level": self.current_level,
            "content": content.strip()
        })
    
    def get_header_level(self, line):
        if line is None:
            return 0
        i = 0
        line_sz = len(line)
        while i < line_sz and line[i] == "#":
            i = i + 1
        return i
    
    def save_level(self, lines):
        if len(lines) == 0:
            self.levels[self.current_level] = ""
        elif self.current_level == 1:
            self.levels[self.current_level] = lines[0]
        else:
            self.levels[self.current_level] = lines[0]
    
    def process_header(self, current_line, lines):
        self.add_block(lines)
        self.save_level(lines)
        self.current_level = self.get_header_level(current_line)
    
    def parse(self, text):
        self.lines = text.split("\n")
        
        block_code = False
        current_lines = []
        for line in self.lines:
            
            if line[0:3] == "```":
                block_code = not block_code
            
            if len(line) > 0 and line[0] == "#" and not block_code:
                self.process_header(line, current_lines)
                current_lines = []
            
            current_lines.append(line)
        
        self.add_block(current_lines)


class DocumentLoader:
    
    def __init__(self):
        
        self.ai = None
        self.docs_path = "/app/docs"
        self.documents = []
        self.chunks = []
    
    
    def get_documents(self):
        
        """
        Returns documents list
        """
        
        self.documents = []
        for root, subdirs, files in os.walk(self.docs_path):
            for file in files:
                if file.endswith(".md"):
                    file_name = os.path.join(root, file)
                    with open(file_name, "r", encoding="utf-8") as f:
                        self.documents.append({
                            "path": file_name,
                            "content": f.read(),
                        })
    
    
    def parse_documents(self):
        
        """
        Parse documents by blocks
        """
        
        self.chunks = []
        
        for document in self.documents:
            parser = MarkdownParser()
            parser.parse(document["content"])
            for index, block in enumerate(parser.blocks):
                lines = block["content"].split("\n")
                if len(lines) > 3:
                    block_id = document["path"] + "?id=" + str(index)
                    self.chunks.append({
                        "id": block_id,
                        "index": index,
                        "level": block["level"],
                        "path": document["path"],
                        "content": block["content"],
                    })
    
    
    def create_index(self):
    
        """
        Create index
        """
        
        documents = []
        for chunk in tqdm(self.chunks):
            
            # Add document
            documents.append(
                Document(
                    page_content=chunk["content"],
                    metadata={
                        "id": chunk["id"],
                        "path": chunk["path"],
                        "index": chunk["index"],
                    }
                )
            )
            
            if len(documents) > 10:
                self.ai.add_documents(documents)
                
                ids = []
                documents = []
        
        if len(documents) > 0:
            self.ai.add_documents(documents)


class AI:
    
    
    def __init__(self):
        
        """
        Constructor
        """
        
        self.database_path = "/app/var/database"
        self.device = "cpu"
        self.embeddings_model = None
        self.embeddings_model_name = None
        self.vector_store = None
    
    
    def create_store(self):
        
        # Returns embedding
        self.embeddings_model = HuggingFaceEmbeddings(
            model_name=self.embeddings_model_name,
            model_kwargs={"device": self.device}
        )
        
        # Create index
        index = faiss.IndexFlatL2(len(self.embeddings_model.embed_query("hello world")))
        #index = faiss.IndexFlatIP(len(self.embeddings_model.embed_query("hello world")))
        
        # Returns store
        self.vector_store = FAISS(
            embedding_function=self.embeddings_model,
            index=index,
            docstore=InMemoryDocstore(),
            index_to_docstore_id={}
        )
    
    
    def load_store(self):
        
        # Read model name
        with open(os.path.join(self.database_path, "model.txt"), "r", encoding="utf-8") as f:
            self.embeddings_model_name = f.read()

        # Returns embedding
        self.embeddings_model = HuggingFaceEmbeddings(
            model_name=self.embeddings_model_name,
            model_kwargs={"device": self.device}
        )
        
        # Returns store
        self.vector_store = FAISS.load_local(
            self.database_path,
            embeddings=self.embeddings_model,
            allow_dangerous_deserialization=True
        )
    
    
    def save_store(self):
    
        """
        Save document store
        """
        
        if os.path.exists(self.database_path):
            os.system("rm -rf " + self.database_path)
        self.vector_store.save_local(self.database_path)
        
        with open(os.path.join(self.database_path, "model.txt"), "w", encoding="utf-8") as f:
            f.write(self.embeddings_model_name)
    
    
    def init_llm(self):
        
        # Connect to LLM
        self.llm_answer = ChatOllama(
            base_url="http://database_ollama:11434",
            model="qwen2.5:1.5b",
            temperature=0.5,
        )
        self.llm_question = ChatOllama(
            base_url="http://database_ollama:11434",
            model="qwen2.5:1.5b",
            temperature=0.1,
        )
    
    
    def compute_embeddings(self, documents):
        
        """
        Compute embeddings
        """
        
        embeddings = self.embeddings_model.embed_documents(documents)
        embeddings = np.array(embeddings).astype(np.float32)
        faiss.normalize_L2(embeddings.reshape(1, -1))
        return embeddings
    
    
    def add_documents(self, documents):
        
        """
        Add documents to vectorstore
        """
        
        ids = [doc.metadata["id"] for doc in documents]
        self.vector_store.add_documents(documents=documents, ids=ids)
        
        """
        content = [doc.page_content for doc in documents]
        metadata = [doc.metadata for doc in documents]
        embeddings = self.compute_embeddings(content)
        add = getattr(self.vector_store, "_" + self.vector_store.__class__.__name__ + "__add")
        add(content, embeddings, metadata, ids)
        """
    
    
    def find_documents(self, questions, k=3):
        
        """
        Find documents by questions
        """
        
        embeddings = self.compute_embeddings(questions)
        mean_embedding = embeddings.mean(axis=0)
        docs = self.vector_store.similarity_search_by_vector(mean_embedding.tolist(), k)
        return embeddings, docs


    def print_documents(self, docs):
        
        """
        Print docs
        """
        
        for i, doc in enumerate(docs):
            print(f"Result {i+1}:")
            print(f"ID: {doc.metadata['id']}")
            print(f"Content: {doc.page_content}")
            #print(f"Distance: {distance}")
            if i + 1 < len(docs):
                print("-" * 50)


    def get_llm_question(self, question, history, debug=False):
        
        """
        Returns new question
        """
        
        prompt = [
            ("system",
                "Ты помощник, который делает вопросы самодостаточными, добавляя контекст из истории диалога"
            ),
            ("human",
                f"История диалога:\n\n" + "\n".join(history) + "\n\n" +
                f"Переформулируй вопрос, на основе истории диалога, " +
                    f"чтобы он был понятен без контекста: {question}. Вопрос:"
            ),
        ]
        
        answer = self.llm_question.invoke(prompt).content
        
        if debug:
            print(str(prompt) + "\n")
            print("Новый вопрос: " + answer + "\n")
        
        return answer


    async def get_prompt(self, history, question, debug=False):
        
        """
        Получить промт на основе вопроса и истории
        """
        
        # Получить список вопросов
        questions = []
        for item in history:
            if item["sender"] == "human":
                questions.append(item["text"])
        
        # Переформулировка вопроса
        new_question = question
        if len(questions) > 1:
            new_question = self.get_llm_question(question, questions, debug=debug)
        
        # Ищем релевантные документы
        _, docs = self.find_documents([new_question], k=1)
        context = "\n\n".join([doc.page_content for doc in docs])
        
        #if debug:
        #    print("Context:\n" + context)
        
        # Создаем промт
        system_message = f"Ты консультант для программистов. Отвечай на русском языке в деловом стиле. Используй следующую информацию для ответа:\n\n{context}"
        prompt = [
            ("system", system_message),
            ("human", " ".join([new_question, "Отвечай на русском языке"]))
        ]
        
        # Добавляем историю сообщений
        #last_messages = 2 * 3
        #for item in messages[-last_messages:]:
        #    if item["text"] != "" and item["sender"] == "human":
        #        prompt += [(item["sender"], item["text"])]
        
        # Добавляем чтобы ответил на русском языке
        #item = prompt[-1]
        #prompt[-1] = (item[0], " ".join([item[1], "Отвечай на русском языке"]))
        
        return prompt


    async def send_question(self, chat_id, question, debug=False):
        
        """
        Send question to LLM
        """
        
        # Получаем все сообщения чата
        query = f"""
            SELECT * FROM messages
            WHERE chat_id = ?
            ORDER BY id, gmtime_created;
        """
        history = await execute_fetch(query, [chat_id])
        history = history[-10:]
        
        # Получить промт
        prompt = await self.get_prompt(history, question, debug=debug)
        if debug:
            print(prompt)
        
        # Отправим вопрос LLM
        for chunk in self.llm_answer.stream(prompt, stream=True):
            yield chunk
        

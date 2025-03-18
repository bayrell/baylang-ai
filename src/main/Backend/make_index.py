import sys, os
import faiss
import torch
from langchain.docstore.document import Document
from langchain_community.docstore.in_memory import InMemoryDocstore
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
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
        if self.current_level == 1:
            self.levels[self.current_level] = "\n".join(lines[0:5])
        else:
            self.levels[self.current_level] = "\n".join(lines[0:3])
    
    def process_header(self, current_line, lines):
        self.add_block(lines)
        self.save_level(lines)
        self.current_level = self.get_header_level(current_line)
    
    def parse(self, text):
        self.lines = text.split("\n")
        
        current_lines = []
        for line in self.lines:
            
            if len(line) > 0 and line[0] == "#":
                self.process_header(line, current_lines)
                current_lines = []
            
            current_lines.append(line)
        
        self.add_block(current_lines)


# Set folder path
os.environ["HF_HOME"] = "/app/var/cache"
os.chdir("/app")

# Set constant
DATABASE_PATH = "/app/var/database"
DOCS_PATH = "/app/docs"
EMBEDDINGS_MODEL_NAME="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


def get_embedding():
    
    """
    Create embedding
    """
    
    embeddings_model = HuggingFaceEmbeddings(
        model_name=EMBEDDINGS_MODEL_NAME,
        model_kwargs={"device": "cpu"}
    )
    vector_store = FAISS(
        embedding_function=embeddings_model,
        index=faiss.IndexFlatL2(len(embeddings_model.embed_query("hello world"))),
        docstore=InMemoryDocstore(),
        index_to_docstore_id={}
    )
    return embeddings_model, vector_store


def get_documents():
    
    """
    Returns documents list
    """
    
    documents = []
    for root, subdirs, files in os.walk(DOCS_PATH):
        for file in files:
            if file.endswith(".md"):
                file_name = os.path.join(root, file)
                with open(file_name, "r", encoding="utf-8") as f:
                    documents.append({
                        "path": file_name,
                        "content": f.read(),
                    })
    
    return documents


def parse_documents(documents):
    
    """
    Parse documents by blocks
    """
    
    blocks = []
    
    for document in documents:
        parser = MarkdownParser()
        parser.parse(document["content"])
        for index, block in enumerate(parser.blocks):
            lines = block["content"].split("\n")
            if len(lines) > 3:
                block_id = document["path"] + "?id=" + str(index)
                blocks.append({
                    "id": block_id,
                    "index": index,
                    "level": block["level"],
                    "path": document["path"],
                    "content": block["content"],
                })
    
    return blocks


def create_index(vector_store, blocks):
    
    """
    Create index
    """
    
    ids = []
    documents = []
    
    for block in tqdm(blocks):
        
        # Add id
        ids.append(block["id"])
        
        # Add document
        documents.append(
            Document(
                page_content=block["content"],
                metadata={
                    "id": block["id"],
                    "path": block["path"],
                    "index": block["index"],
                }
            )
        )
    
    # Add documents to vectorstore
    vector_store.add_documents(documents=documents, ids=ids)


def save_index(vector_store):
    
    """
    Save document store
    """
    
    if os.path.exists(DATABASE_PATH):
        os.system("rm -rf " + DATABASE_PATH)
    vector_store.save_local(DATABASE_PATH)
    
    with open(os.path.join(DATABASE_PATH, "model.txt"), "w", encoding="utf-8") as f:
        f.write(EMBEDDINGS_MODEL_NAME)
    

# Read documents
documents = get_documents()
blocks = parse_documents(documents)

# Create index
_, vector_store = get_embedding()
create_index(vector_store, blocks)
save_index(vector_store)

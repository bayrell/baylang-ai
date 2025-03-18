import sys, os
import numpy as np
import faiss
import torch
from service import *
from langchain_community.docstore.in_memory import InMemoryDocstore
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_ollama import ChatOllama


# Constant
DATABASE_PATH = "/app/var/database"
DEVICE = "cpu"


# Read model name
with open(os.path.join(DATABASE_PATH, "model.txt"), "r", encoding="utf-8") as f:
    EMBEDDINGS_MODEL_NAME = f.read()


# Returns embedding
embeddings_model = HuggingFaceEmbeddings(
    model_name=EMBEDDINGS_MODEL_NAME,
    model_kwargs={"device": DEVICE}
)
vector_store = FAISS.load_local(
    DATABASE_PATH,
    embeddings=embeddings_model,
    allow_dangerous_deserialization=True
)


def get_llm():
    
    """
    Connect to LLM
    """
    
    llm = ChatOllama(
        base_url="http://database_ollama:11434",
        #model="deepseek-r1:1.5b",
        model="qwen2.5:3b",
        temperature=0.5,
    )
    
    return llm


def find_docs(questions):
    
    """
    Find documents by questions
    """
    
    embeddings = np.array(embeddings_model.embed_documents(questions))
    mean_embedding = embeddings.mean(axis=0).tolist()
    docs = vector_store.similarity_search_by_vector(mean_embedding, k=3)
    return embeddings, docs


def print_docs(docs):
    for i, doc in enumerate(docs):
        print(f"Result {i+1}:")
        print(f"ID: {doc.metadata['id']}")
        print(f"Content: {doc.page_content}")
        #print(f"Distance: {distance}")
        print("-" * 50)


async def get_prompt(chat_id, question):

    """
    Получить промт на основе вопроса и истории
    """
    
    # Получаем все сообщения чата
    query = f"""
        SELECT * FROM messages
        WHERE chat_id = ?
        ORDER BY id, gmtime_created;
    """
    messages = await execute_fetch(query, [chat_id])
    messages = messages[-10:]
    
    # Получить список вопросов
    questions = []
    for item in messages:
        if item["sender"] == "human":
            questions.append(item["text"])
    
    # Ищем релевантные документы
    _, docs = find_docs(questions)
    context = "\n\n".join([doc.page_content for doc in docs])
    
    print("Context:")
    for doc in docs:
        print("")
        print(doc.page_content)
    
    # Создаем промт
    system_message = f"Ты консультант для программистов. Отвечай на русском языке в деловом стиле. Используй следующую информацию для ответа:\n\n{context}"
    prompt = [
        ("system", system_message),
        ("human", " ".join([question, "Отвечай на русском языке"]))
    ]
    
    # Добавляем историю сообщений
    #last_messages = 2 * 3
    #for item in messages[-last_messages:]:
    #    if item["text"] != "" and item["sender"] == "human":
    #        prompt += [(item["sender"], item["text"])]
    
    # Добавляем чтобы ответил на русском языке
    item = prompt[-1]
    prompt[-1] = (item[0], " ".join([item[1], "Отвечай на русском языке"]))
    
    return prompt


async def send_question(llm, chat_id, question):
    
    # Получить промт
    prompt = await get_prompt(chat_id, question)
    print(prompt)
    
    # Отправим вопрос LLM
    for chunk in llm.stream(prompt, stream=True):
        yield chunk
    

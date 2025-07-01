import sys, os
from ai import *


# Set folder path
os.environ["HF_HOME"] = "/app/var/cache"
os.chdir("/app")

# Create ai
ai = AI()
ai.embeddings_model_name = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
ai.create_store()

# Create loader
loader = DocumentLoader()
loader.ai = ai

# Read documents
loader.get_documents()
loader.parse_documents()
loader.create_index()

# Save store
ai.save_store()

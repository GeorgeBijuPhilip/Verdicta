import chromadb
import pandas as pd
import uuid
from sentence_transformers import SentenceTransformer
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def initialize_database():
    try:
        # Initialize ChromaDB
        client = chromadb.PersistentClient(path="./chroma_db")
        collection = client.get_or_create_collection(name="legal_docs")
        logger.info("ChromaDB initialized successfully.")

        # Load Sentence Transformer Model for embeddings
        model_embedding = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info("Sentence Transformer model loaded successfully.")

        # Load and process Excel data
        file_path = "/Users/athulkrishnagopakumar/Downloads/law_dataset.xlsx"
        df = pd.read_excel(file_path)

        texts_xlsx = df["Questions"].astype(str) + " " + df["Answers"].astype(str)
        ids_xlsx = [str(uuid.uuid4()) for _ in range(len(texts_xlsx))]

        embeddings_xlsx = model_embedding.encode(texts_xlsx.tolist()).tolist()
        collection.add(
            ids=ids_xlsx, 
            embeddings=embeddings_xlsx, 
            metadatas=[{"text": t} for t in texts_xlsx]
        )

        logger.info("Additional Excel dataset embedded and stored in ChromaDB successfully!")
        return client, collection

    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise

if __name__ == "__main__":
    initialize_database()

from flask import Flask, request, jsonify, session
from flask_cors import CORS
import chromadb
import pypdf
from sentence_transformers import SentenceTransformer
import logging
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
import os
import ollama

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
app.secret_key = os.urandom(24)  # Secret key for session handling

# Initialize ChromaDB
try:
    client = chromadb.PersistentClient(path="./chroma_db")
    collection = client.get_or_create_collection(name="legal_docs")
    logger.info("ChromaDB initialized successfully.")
except Exception as e:
    logger.error(f"Error initializing ChromaDB: {e}")

# Load Sentence Transformer Model for embeddings
try:
    model_embedding = SentenceTransformer("all-MiniLM-L6-v2")
    logger.info("Sentence Transformer model loaded successfully.")
except Exception as e:
    logger.error(f"Error loading Sentence Transformer model: {e}")

# Load LLaMA 3 Model via Ollama
try:
    ollama.pull("llama3")
    logger.info("LLaMA 3 model loaded successfully.")
except Exception as e:
    logger.error(f"Error loading LLaMA 3 model: {e}")

# Extract Text from PDF
def extract_text_from_pdf(file):
    try:
        pdf_reader = pypdf.PdfReader(file)
        text = "\n".join([page.extract_text() for page in pdf_reader.pages if page.extract_text()])
        logger.info("Text extracted from PDF successfully.")
        return text.strip()
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {e}")
        return None

# Store PDF text in session memory
@app.route("/upload", methods=["POST"])
def upload_pdf():
    if "file" not in request.files:
        logger.error("No file uploaded.")
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    if file.filename == "":
        logger.error("No selected file.")
        return jsonify({"error": "No selected file"}), 400

    try:
        text = extract_text_from_pdf(file)
        if not text:
            return jsonify({"error": "Failed to extract text from the file."}), 400

        # Store in session memory
        session["pdf_text"] = text
        logger.info("PDF content stored in session.")

        return jsonify({"message": "PDF uploaded and processed successfully.", "text": text}), 200

    except Exception as e:
        logger.error(f"Error processing file: {e}")
        return jsonify({"error": f"Error processing file: {str(e)}"}), 500

# Generate Response from LLaMA 3
def generate_llama_response(prompt):
    try:
        response = ollama.chat(
            model="llama3",
            messages=[{"role": "user", "content": prompt}]
        )
        return response["message"]["content"]
    except Exception as e:
        logger.error(f"Error generating response from LLaMA 3: {e}")
        return "I couldn't process your request. Please try again."

@app.route("/query", methods=["POST"])
def query():
    data = request.json
    user_question = data.get("question", "").strip()

    if not user_question:
        logger.error("No question provided.")
        return jsonify({"error": "A question is required."}), 400

    # Retrieve stored PDF text from session
    pdf_text = session.get("pdf_text", "")

    try:
        # Retrieve relevant legal documents
        results = collection.query(query_texts=[user_question], n_results=3)
        retrieved_texts = [doc["text"] for doc in results["metadatas"][0] if "text" in doc] if "metadatas" in results and results["metadatas"] else []
        doc_context = "\n".join(retrieved_texts) if retrieved_texts else "No additional documents found."

        # Format legal query with PDF text and context
        prompt = (
            f"User Question: {user_question}\n\n"
            f"PDF Context:\n{pdf_text[:1000]}...\n\n"
            f"Relevant Sections:\n{doc_context}\n\n"
            f"Answer based on the provided legal documents and context."
        )

        # Get response from LLaMA 3
        answer = generate_llama_response(prompt)
        logger.info("Response generated successfully.")
        return jsonify({"answer": answer}), 200

    except Exception as e:
        logger.error(f"Error generating response: {e}")
        return jsonify({"error": f"Error generating response: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(port=8080, debug=True)
from flask import Flask, request, jsonify, session, Response
from flask_cors import CORS
import chromadb
import pypdf
from sentence_transformers import SentenceTransformer
import logging
import os
import ollama
import re
import uuid
from unidecode import unidecode
from pdf2image import convert_from_bytes
import pytesseract
import pandas as pd
import openpyxl

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  
app.secret_key = os.urandom(24)  # Secret key for session handling
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # Create upload folder if it doesn't exist

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
try:
    file_path = "/Users/athulkrishnagopakumar/Downloads/law_dataset.xlsx"
    df = pd.read_excel(file_path) # Load your new dataset

    texts_xlsx = df["Questions"].astype(str) + " " + df["Answers"].astype(str)
    ids_xlsx = [str(uuid.uuid4()) for _ in range(len(texts_xlsx))]

    embeddings_xlsx = model_embedding.encode(texts_xlsx.tolist()).tolist()
    collection.add(ids=ids_xlsx, embeddings=embeddings_xlsx, metadatas=[{"text": t} for t in texts_xlsx])

    logger.info("Additional Excel dataset embedded and stored in ChromaDB successfully!")
    data = collection.get()
    print(f"Stored document IDs: {data.get('ids', [])}")
except Exception as e:
    logger.error(f"Error processing additional Excel dataset: {e}")
# Load LLaMA 3 Model via Ollama
try:
    ollama.pull("llama3")
    logger.info("LLaMA 3 model loaded successfully.")
except Exception as e:
    logger.error(f"Error loading LLaMA 3 model: {e}")

# Text Cleaning Function
def clean_ocr_text(text):
    text = unidecode(text)
    text = re.sub(r'Pennit', 'Permit', text)
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^a-zA-Z0-9\s.,:/()-]', '', text)
    return text.strip()

# Extract Text from PDF
def extract_text_from_pdf(file):
    try:
        pdf_reader = pypdf.PdfReader(file)
        text = "\n".join([page.extract_text() for page in pdf_reader.pages if page.extract_text()])
        if not text:  # If pypdf fails, try OCR
            images = convert_from_bytes(file.read())
            text = "\n".join([pytesseract.image_to_string(img) for img in images])
        return clean_ocr_text(text)
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {e}")
        return None

# Store PDF text in a temporary file instead of session
@app.route("/upload", methods=["POST"])
def upload_pdf():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    try:
        text = extract_text_from_pdf(file)
        if not text:
            return jsonify({"error": "Failed to extract text from the file."}), 400

        file_id = str(uuid.uuid4())
        file_path = os.path.join(UPLOAD_FOLDER, f"{file_id}.txt")

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(text)

        session["pdf_file_path"] = file_path
        session.setdefault("chat_history", [])

        return jsonify({"message": f"File '{file.filename}' uploaded successfully.", "file_id": file_id}), 200
    except Exception as e:
        logger.error(f"Error processing file: {e}")
        return jsonify({"error": f"Error processing file: {str(e)}"}), 500

# Stream LLaMA Response to User
def stream_llama_response(prompt):
    try:
        stream = ollama.chat(
            model="llama3",
            messages=[{"role": "user", "content": prompt}],
            stream=True
        )
        for part in stream:
            yield part["message"]["content"]
    except Exception as e:
        logger.error(f"Error streaming response: {e}")
        yield "I couldn't process your request. Please try again."

@app.route("/query", methods=["POST"])
def query():
    data = request.json
    user_question = data.get("question", "").strip()

    if not user_question:
        return jsonify({"error": "A question is required."}), 400

    chat_history = session.get("chat_history", [])
    pdf_file_path = session.get("pdf_file_path")
    pdf_text = ""

    if pdf_file_path and os.path.exists(pdf_file_path):
        with open(pdf_file_path, "r", encoding="utf-8") as f:
            pdf_text = f.read()

    casual_responses = {
        "hello": "Hey there! How can I assist you today?",
        "hi": "Hi! Need help with something?",
        "how are you": "I'm just a chatbot, but I'm here to help! What do you need?",
        "what's up": "Not much, just ready to assist! What’s on your mind?",
        "who are you": "I'm an AI legal assistant, here to help with legal questions and documents!",
    }

    if user_question.lower() in casual_responses and not pdf_text:
        return jsonify({"answer": casual_responses[user_question.lower()]}), 200

    try:
        results = collection.query(query_texts=[user_question], n_results=5)
        retrieved_texts = [doc["text"] for doc in results["metadatas"][0] if "text" in doc] if "metadatas" in results and results["metadatas"] else []
        doc_context = "\n".join(retrieved_texts) if retrieved_texts else "No additional documents found."

        chat_history.append({"role": "user", "content": user_question})
        session["chat_history"] = chat_history

        if pdf_text:
            prompt = (
                f"You are Verdicta, an AI assistant that provides clear and well-structured legal insights. "
        f"You help users understand complex legal documents and answer their queries in a professional but approachable tone.\n\n"
        f"### User Question:\n{user_question}\n\n"
        f"### Additional Instructions:\n{user_question}\n\n"
        f"### The first line is always a query from the user you have to answer using the extracted text and remember the extracted text and also only answer according to indian law\n\n"
        f"### Uploaded Legal Document Content:\n{pdf_text[:1500]}...\n\n"
        f"### Relevant Legal References:\n{doc_context}\n\n"
        f"### Response Format:\n"
        f"**1. Summary of the Legal Issue**\n"
        f"**2. Key Legal Provisions & Their Meaning**\n"
        f"**3. Steps the User Can Take**\n"
        f"**4. Additional Resources for Further Help**\n\n"
        f"Write in a professional yet conversational style, like ChatGPT would."
            )
        else:
            prompt = f"You are Verdicta, a helpful AI assistant. Answer the following question in a clear and concise manner and do not hallucinate also the first line will be a prompt so answer according to that prompt:\n\n{user_question}"

        return Response(stream_llama_response(prompt), content_type='text/event-stream; charset=utf-8')
    except Exception as e:
        logger.error(f"Error generating response: {e}")
        return jsonify({"error": f"Error generating response: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(port=8080, debug=True)

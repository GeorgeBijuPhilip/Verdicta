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
import requests

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  
app.secret_key = os.urandom(24)  # Secret key for session handling
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # Create upload folder if it doesn't exist
chat_history = []  # Stores the last few interactions
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
HISTORY_FILE = "chat_history.txt"
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
def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            return f.read().split("\n")[-5:]  # Load last 5 messages
    return []

def save_history(user_input, bot_response):
    with open(HISTORY_FILE, "a") as f:
        f.write(f"User: {user_input}\nAI: {bot_response}\n")

def generate_response(user_input):
    chat_history = load_history()
    prompt = "\n".join(chat_history) + f"\nUser: {user_input}\nAI:"

    response = requests.post("http://127.0.0.1:11434/api/generate", json={
        "model": "llama3",
        "prompt": prompt,
        "max_tokens": 1024
    })

    bot_response = response.json().get("response", "I'm sorry, I didn't understand.")

    save_history(user_input, bot_response)
    
    return bot_response
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

def store_chat_history(session_id, user_question, full_response):
    try:
        doc_entry = {"question": user_question, "answer": full_response}
        doc_id = str(uuid.uuid4())  # Ensure unique ID for each entry
        collection.add(
            ids=[doc_id],
            metadatas=[doc_entry],  # Ensure this is a list
            documents=[full_response]  # Ensure this is a list
        )
        logger.info(f"Stored chat history: {doc_entry}")
    except Exception as e:
        logger.error(f"Error storing chat history: {e}")


def retrieve_chat_history(session_id, query):
    """Retrieves past chat history relevant to the new query"""
    try:
        results = collection.query(
            query_texts=[query],
            n_results=5
        )
        past_messages = [doc["text"] for doc in results["metadatas"][0] if isinstance(doc, dict) and "text" in doc]
        return "\n".join(past_messages) if past_messages else ""
    except Exception as e:
        logger.error(f"Error retrieving chat history: {e}")
        return ""

@app.route("/query", methods=["POST"])
def query():
    global chat_history
    data = request.get_json()
    user_question = data.get("question", "").strip()
    session_id = data.get("session_id", str(uuid.uuid4()))

    if not user_question:
        return jsonify({"error": "A question is required."}), 400

    # ✅ Casual responses early exit
    casual_responses = {
        "hello": "Hey there! How can I assist you today?",
        "good morning": "Good morning! How can I help you today?",
        "good evening": "Good evening! What can I do for you?",
        "thank you": "You're welcome! Let me know if there's anything else I can assist with.",
        "bye": "Goodbye! Have a great day!",
        "hey": "Hey there! How can I assist you today?",
        "hi": "Hi! Need help with something?",
        "how are you": "I'm just a chatbot, but I'm here to help! What do you need?",
        "what's up": "Not much, just ready to assist! What’s on your mind?",
        "who are you": "I'm an AI legal assistant, here to help with legal questions and documents!",
    }

    if user_question.lower() in casual_responses:
        return jsonify({"answer": casual_responses[user_question.lower()]}), 200

    # ✅ Load or initialize chat history
    if "chat_history" not in session:
        session["chat_history"] = []

    chat_history = session["chat_history"][-5:]  # Keep last 5 messages for context
    if "remember" in user_question.lower():
        key_value = user_question.replace("remember", "").strip().split(" is ")
        if len(key_value) == 2:
            key, value = key_value
            chat_history.append({"role": "memory", "content": f"{key.strip()} is {value.strip()}"})
            session["chat_history"] = chat_history[-10:]  # Update session
            return jsonify({"answer": f"Got it! I'll remember that {key.strip()} is {value.strip()}."})

# ✅ Retrieve stored info
    for msg in chat_history:
        if msg["role"] == "memory" and any(word in user_question.lower() for word in msg["content"].split(" is ")[0].lower().split()):
            key, value = msg["content"].split(" is ")
            return jsonify({"answer": f"{key.capitalize()} is {value}!"})

    if "what do you remember" in user_question.lower():
        memories = [msg["content"] for msg in chat_history if msg["role"] == "memory"]
        if memories:
            return jsonify({"answer": f"Here's what I remember: {', '.join(memories)}."})
        return jsonify({"answer": "I don't remember anything yet. Tell me something to remember!"})
    pdf_file_path = session.get("pdf_file_path")
    pdf_text = ""
    if pdf_file_path and os.path.exists(pdf_file_path):
        with open(pdf_file_path, "r", encoding="utf-8") as f:
            pdf_text = f.read()

    try:
        # ✅ Retrieve from RAG
        results = collection.query(
            query_texts=[user_question], n_results=3, include=["documents"], where={"category": "legal"}
        )
        retrieved_texts = [
            doc for doc in results.get("documents", [[]])[0] if isinstance(doc, str)
        ]
        doc_context = "\n".join(retrieved_texts) if retrieved_texts else ""

        # ✅ Maintain chat history structure properly
        chat_history.append({"role": "user", "content": user_question})

        # ✅ Construct better prompt including chat history
        formatted_chat_history = "\n".join(
            f"{msg['role'].capitalize()}: {msg['content']}" for msg in chat_history
        )

        prompt = (
            "You are an AI legal assistant. Answer professionally while keeping a conversational tone.\n\n"
            f"### Previous Conversation:\n{formatted_chat_history}\n\n"
            f"### User Question:\n{user_question}\n\n"
        )

        if pdf_text:
            prompt += f"### Uploaded Legal Document Content:\n{pdf_text[:1500]}...\n\n"
        
        if doc_context:
            prompt += f"### Relevant Legal References:\n{doc_context}\n\n"
        else:
            prompt += "No relevant documents were found. Provide a general legal response.\n\n"

        prompt += (
            "### First Line is always going to be a query, write a response according to the first line\n"
            "### Response Guidelines:\n"
            "- If the query involves sensitive topics (e.g., domestic violence, criminal law, family disputes), provide "
            "general legal guidance rather than specific legal advice.\n"
            "- Offer information on legal rights, resources, and support services.\n"
            "- Suggest seeking professional legal assistance if needed.\n"
            "- Always maintain an informative, supportive, and professional tone.\n\n"
            "**Response Format:**\n"
            "**1. Summary of the Legal Issue**\n"
            "**2. Legal Rights & Options Available**\n"
            "**3. Steps the User Can Take**\n"
            "**4. Additional Resources for Further Help**\n\n"
            "Write in a professional yet conversational style."
        )
        prompt+= (
            "You are a helpful chatbot that remembers user inputs during a conversation.\n\n " 
            "If the user shares personal details like their name, preferences, or facts about themselves, store them and recall them when relevant. \n\n" 
            "If the user asks about something they previously mentioned, retrieve the stored information and respond accordingly.\n\n"  
            "If you don’t remember something, politely ask the user to repeat it.\n\n " 
        )

        response_stream = stream_llama_response(prompt)
        full_response = "".join(part for part in response_stream)

        # ✅ Store assistant response in chat history
        chat_history.append({"role": "assistant", "content": full_response})
        session["chat_history"] = chat_history[-5:]  # Save last 5 exchanges

        return Response(stream_llama_response(prompt), content_type='text/event-stream; charset=utf-8')

    except Exception as e:
        logger.error(f"Error generating response: {e}")
        return jsonify({"error": f"Error generating response: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(port=8080, debug=True)

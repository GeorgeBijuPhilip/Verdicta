# Standard library imports
import os
import re
import uuid
import logging
import datetime
from typing import Optional, Dict, List

# Third-party imports
from flask import Flask, request, jsonify, session, Response
from flask_cors import CORS
from dotenv import load_dotenv
import chromadb
import pypdf
from sentence_transformers import SentenceTransformer
from unidecode import unidecode
from pdf2image import convert_from_bytes
import pytesseract
import pandas as pd
import requests
from groq import Groq
import ollama

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Flask app configuration
app = Flask(__name__)
CORS(app)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024
app.secret_key = os.urandom(24)

# Constants
UPLOAD_FOLDER = "uploads"
HISTORY_FILE = "chat_history.txt"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize services
try:
    client = chromadb.PersistentClient(path="./chroma_db")
    collection = client.get_or_create_collection(name="legal_docs")
    model_embedding = SentenceTransformer("all-MiniLM-L6-v2")
    ollama.pull("llama3")
    logger.info("Services initialized successfully.")
except Exception as e:
    logger.error(f"Error initializing services: {e}")

# Utility functions
def clean_ocr_text(text: str) -> str:
    text = unidecode(text)
    text = re.sub(r'Pennit', 'Permit', text)
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[^a-zA-Z0-9\s.,:/()-]', '', text)
    return text.strip()

def extract_text_from_pdf(file) -> Optional[str]:
    try:
        pdf_reader = pypdf.PdfReader(file)
        text = "\n".join([page.extract_text() for page in pdf_reader.pages if page.extract_text()])
        if not text:
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

def should_use_local_model(prompt: str) -> bool:
    """Determine if we should use local LLaMA model based on context"""
    file_related_indicators = [
        "Uploaded Legal Document Content" in prompt,
        "pdf_text" in prompt.lower(),
        "extracted text" in prompt.lower(),
        "document analysis" in prompt.lower(),
        "### Document Context:" in prompt,  # Added to catch file uploads explicitly
        "File uploaded:" in prompt
    ]
    return any(file_related_indicators)

def stream_llama_response(prompt: str) -> str:
    try:
        if should_use_local_model(prompt):
            logger.info("Using local LLaMA model for file processing")
            response = requests.post(
                "http://127.0.0.1:11434/api/generate",
                json={
                    "model": "llama3",
                    "prompt": (
                        "You are an AI legal assistant. Provide direct, declarative responses without "
                        "asking questions back. Be professional yet conversational, and focus on "
                        "providing clear, actionable information.\n\n"
                        f"{prompt}"
                    ),
                    "stream": False,
                    "max_tokens": 2048,
                    "temperature": 0.7
                }
            )
            if response.status_code == 200:
                return response.json().get("response", "Error processing with local model")
            else:
                logger.error(f"Error with local LLaMA: {response.text}")
                return "Error processing with local model"
        
        else:
            logger.info("Using Groq API for general query")
            client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
            chat_completion = client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an AI legal assistant. Provide direct, declarative responses "
                            "without asking questions back. Be professional yet conversational, and "
                            "focus on providing clear, actionable information."
                        )
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                model="llama-3.3-70b-versatile",
            )
            return chat_completion.choices[0].message.content

    except Exception as e:
        logger.error(f"Error in stream_llama_response: {e}")
        return f"Error processing request: {str(e)}"

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

# Add these new functions for chat history management
def save_chat_message(session_id: str, role: str, content: str) -> bool:
    try:
        message_id = str(uuid.uuid4())
        metadata = {
            "session_id": session_id,
            "role": role,
            "timestamp": str(datetime.datetime.now()),
            "content": content
        }
        
        # Store in ChromaDB
        collection.add(
            ids=[message_id],
            documents=[content],
            metadatas=[metadata]
        )
        logger.info(f"Saved chat message: {metadata}")
        return True
    except Exception as e:
        logger.error(f"Error saving chat message: {e}")
        return False

def get_chat_history(session_id, limit=10):
    try:
        # Query ChromaDB for messages from this session
        results = collection.query(
            query_texts=[f"session:{session_id}"],
            where={"session_id": session_id},
            n_results=limit
        )
        
        # Sort messages by timestamp
        messages = []
        for metadata in results.get("metadatas", []):
            if metadata:
                messages.append({
                    "role": metadata["role"],
                    "content": metadata["content"],
                    "timestamp": metadata["timestamp"]
                })
        
        return sorted(messages, key=lambda x: x["timestamp"])
    except Exception as e:
        logger.error(f"Error retrieving chat history: {e}")
        return []

def format_response(text: str) -> str:
    """Format the response text to be more readable and professional"""
    try:
        # Clean the text
        text = text.strip()
        
        # Handle numbered lists - ensure proper spacing and formatting
        text = re.sub(r'(\d+\.)\s*', r'\n\1 ', text)
        
        # Handle bullet points
        text = re.sub(r'([•\*])\s*', r'\n• ', text)
        
        # Add proper spacing after greetings
        text = re.sub(r'(Hello|Hi|Hey|Namaste)([^,.!?\n]*[,.!?])', r'\1\2\n\n', text)
        
        # Add paragraph breaks after sentences that end sections
        text = re.sub(r'([.!?])\s+(?=[A-Z])', r'\1\n\n', text)
        
        # Clean up excessive newlines
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Ensure lists are properly spaced
        text = re.sub(r'\n((?:\d+\.|\•)[^\n]+)(?:\n(?!\d+\.|\•|$))', r'\n\1\n\n', text)
        
        # Final cleanup
        text = text.strip()
        paragraphs = text.split('\n\n')
        formatted_paragraphs = [p.strip() for p in paragraphs if p.strip()]
        
        return '\n\n'.join(formatted_paragraphs)
        
    except Exception as e:
        logger.error(f"Error formatting response: {e}")
        return text

# Route handlers
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

        # Make it explicit that we're using local model for file processing
        prompt = (
            "You are an AI legal assistant processing an uploaded document. "
            "Answer professionally while keeping a conversational tone.\n\n"
            f"### File uploaded: {file.filename}\n"
            f"### Document Context:\n{text[:1500]}...\n\n"
            "Please analyze this legal document and provide a comprehensive summary."
        )
        
        # This will automatically use local LLaMA due to should_use_local_model check
        response = stream_llama_response(prompt)

        # Split the text into lines and get the first line as the query
        lines = text.split('\n')
        query = lines[0].strip()
        remaining_text = '\n'.join(lines[1:])

        file_id = str(uuid.uuid4())
        file_path = os.path.join(UPLOAD_FOLDER, f"{file_id}.txt")

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(remaining_text)

        session["pdf_file_path"] = file_path
        session.setdefault("chat_history", [])

        return jsonify({
            "message": f"File '{file.filename}' uploaded successfully.",
            "file_id": file_id,
            "query": query,
            "response": response
        }), 200

    except Exception as e:
        logger.error(f"Error processing file: {e}")
        return jsonify({"error": f"Error processing file: {str(e)}"}), 500

@app.route("/query", methods=["POST"])
def query():
    data = request.get_json()
    user_question = data.get("question", "").strip()
    session_id = data.get("session_id", str(uuid.uuid4()))

    if not user_question:
        return jsonify({"error": "A question is required."}), 400

    try:
        save_chat_message(session_id, "user", user_question)
        chat_history = get_chat_history(session_id)
        
        formatted_history = "\n".join([
            f"{msg['role'].capitalize()}: {msg['content']}" 
            for msg in chat_history[-5:]
        ])

        prompt = (
            "You are an AI legal assistant. Answer professionally while keeping a conversational tone.\n\n"
            f"### Chat History:\n{formatted_history}\n\n"
            f"### Current Question:\n{user_question}\n\n"
        )

        # Get response
        response = stream_llama_response(prompt)
        formatted_response = format_response(response)
        
        # Save assistant's response
        save_chat_message(session_id, "assistant", response)
        
        return jsonify({
            "response": formatted_response,
            "success": True
        }), 200

    except Exception as e:
        logger.error(f"Error processing query: {e}")
        return jsonify({
            "error": str(e),
            "success": False
        }), 500

@app.route("/chat_history/<session_id>", methods=["GET"])
def get_session_history(session_id):
    try:
        history = get_chat_history(session_id)
        return jsonify({"history": history}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(port=8080, debug=True)

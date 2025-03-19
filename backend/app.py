from flask import Flask, request, jsonify, session
from flask_cors import CORS
import chromadb
import tiktoken
import pypdf
from sentence_transformers import SentenceTransformer
import logging
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
import groq
import os
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

# Load Fine-Tuned GPT-2 Model
MODEL_PATH = "C:/Users/DELL/OneDrive/Desktop/chat1/backend/legal-finetuned-gpt2"

try:
    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
    model = AutoModelForCausalLM.from_pretrained(MODEL_PATH)
    logger.info("Fine-tuned GPT-2 model loaded successfully.")
except Exception as e:
    logger.error(f"Error loading fine-tuned model: {e}")

# Initialize Groq client
GROQ_API_KEY = "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"
try:
    groq_client = groq.Client(api_key=GROQ_API_KEY)
    logger.info("Groq client initialized successfully.")
except Exception as e:
    logger.error(f"Error initializing Groq client: {e}")

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

# Generate Response from Fine-Tuned Model (Legal Queries)
def generate_local_response(prompt):
    try:
        inputs = tokenizer(prompt, return_tensors="pt")

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_length=150,
                num_return_sequences=1,   
                temperature=0.7,          
                top_p=0.9,                
                top_k=50,                 
                repetition_penalty=1.2     
            )
        
        response = tokenizer.decode(outputs[0], skip_special_tokens=True).strip()

        # If model generates an error-like response, return None
        if not response or "error" in response.lower() or "sorry" in response.lower():
            return None

        return response
    except Exception as e:
        logger.error(f"Error generating response: {e}")
        return None

# Generate Response from Groq API
def generate_groq_response(prompt):
    try:
        response = groq_client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error getting response from Groq: {e}")
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
        # If the question is casual, use Groq API only
        if not any(keyword in user_question.lower() for keyword in ["law", "section", "punishment", "legal", "act", "penalty", "offense", "crime"]):
            answer = generate_groq_response(user_question)
        else:
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

            # Get response from Fine-Tuned GPT-2
            fine_tuned_response = generate_local_response(prompt)

            # If fine-tuned model fails, show only Groq response
            if fine_tuned_response is None:
                answer = generate_groq_response(prompt)
            else:
                # Combine responses if both are available
                groq_response = generate_groq_response(prompt)
                answer = f"{fine_tuned_response} (Additional Groq Response: {groq_response})"

        logger.info("Response generated successfully.")
        return jsonify({"answer": answer}), 200

    except Exception as e:
        logger.error(f"Error generating response: {e}")
        return jsonify({"error": f"Error generating response: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(port=8080, debug=True)

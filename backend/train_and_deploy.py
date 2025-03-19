import re
import json
import logging
from pypdf import PdfReader
from transformers import AutoTokenizer, AutoModelForCausalLM, Trainer, TrainingArguments
from datasets import Dataset, DatasetDict
from flask import Flask, request, jsonify
from flask_cors import CORS
from sklearn.model_selection import train_test_split

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Step 1: Extract text from the PDF
def extract_text_from_pdf(pdf_path):
    logging.info("Extracting text from PDF...")
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        if page.extract_text():
            text += page.extract_text() + "\n"
    return text.strip()

# Step 2: Preprocess the text
def preprocess_text(text):
    logging.info("Preprocessing text...")
    text = re.sub(r"Page \d+ of \d+", "", text)  # Remove headers/footers
    sections = re.split(r"CHAPTER\s+\w+", text, flags=re.IGNORECASE)  # Split by "CHAPTER" headings
    sections = [section.strip() for section in sections if section.strip()]
    return sections

# Step 3: Create prompt-completion pairs
def create_prompt_completion_pairs(sections):
    logging.info("Creating prompt-completion pairs...")
    pairs = []
    for section in sections:
        paragraphs = re.split(r"\n\s*\n", section)  # Split by paragraphs
        for i in range(len(paragraphs) - 1):
            prompt = paragraphs[i].strip()
            completion = paragraphs[i + 1].strip()
            if prompt and completion:
                pairs.append({"prompt": prompt, "completion": completion})
    return pairs

# Step 4: Fine-tune the model
def fine_tune_model(dataset_path, output_dir):
    logging.info("Fine-tuning the model...")
    
    # Load dataset
    dataset = [json.loads(line) for line in open(dataset_path, "r", encoding="utf-8")]
    train_data, val_data = train_test_split(dataset, test_size=0.1, random_state=42)
    dataset = DatasetDict({"train": Dataset.from_list(train_data), "validation": Dataset.from_list(val_data)})

    # Load pre-trained GPT-2 model and tokenizer
    model_name = "gpt2"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(model_name)

    # Set padding token
    tokenizer.pad_token = tokenizer.eos_token

    # 🔹 Explicitly set loss_type to prevent warnings
    model.config.loss_type = "ForCausalLMLoss"

    # Tokenize dataset
    def tokenize_function(examples):
        model_inputs = tokenizer(
            examples["prompt"], 
            examples["completion"], 
            truncation=True, 
            padding="max_length", 
            max_length=512
        )
        model_inputs["labels"] = model_inputs["input_ids"].copy()  # Fix loss computation issue
        return model_inputs

    tokenized_dataset = dataset.map(tokenize_function, batched=True)

    # 🔹 Fix evaluation_strategy -> eval_strategy
    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=3,
        per_device_train_batch_size=2,
        save_steps=1000,
        save_total_limit=2,
        logging_dir="./logs",
        logging_steps=500,
        eval_strategy="steps",  # ✅ Fixed
        eval_steps=500,
        learning_rate=5e-5,
        weight_decay=0.01,
        fp16=True,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized_dataset["train"],
        eval_dataset=tokenized_dataset["validation"],
    )

    trainer.train()
    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)
    logging.info("Model fine-tuning completed and saved.")

# Step 5: Deploy the fine-tuned model
def deploy_model(model_dir):
    app = Flask(__name__)
    CORS(app)  # Enable CORS

    # Load the fine-tuned model
    model = AutoModelForCausalLM.from_pretrained(model_dir)
    tokenizer = AutoTokenizer.from_pretrained(model_dir)

    # Generate responses
    def generate_response(prompt):
        inputs = tokenizer(prompt, return_tensors="pt")
        outputs = model.generate(**inputs, max_length=150)
        return tokenizer.decode(outputs[0], skip_special_tokens=True)

    @app.route("/query", methods=["POST"])
    def query():
        data = request.json
        user_question = data.get("question", "")
        file_content = data.get("fileContent", "")

        if not user_question and not file_content:
            return jsonify({"error": "Question or file content is required"}), 400

        try:
            prompt = f"User Question: {user_question}\n\nFile Content: {file_content}\n\nAnswer:"
            answer = generate_response(prompt)
            return jsonify({"answer": answer}), 200

        except Exception as e:
            logging.error(f"Error generating response: {str(e)}")
            return jsonify({"error": f"Error generating response: {str(e)}"}), 500

    logging.info("Starting Flask server...")
    app.run(port=8080, debug=True)

# Main function
def main():
    pdf_path = "C:/Users/DELL/Downloads/THE-INDIAN-PENAL-CODE-1860.pdf"
    output_dir = "C:/Users/DELL/OneDrive/Desktop/chat1/backend/legal-finetuned-gpt2"

    # Step 1: Extract text
    text = extract_text_from_pdf(pdf_path)

    # Step 2: Preprocess text
    sections = preprocess_text(text)

    # Step 3: Create prompt-completion pairs
    pairs = create_prompt_completion_pairs(sections)

    # Save pairs to a JSONL file
    dataset_path = "legal_dataset.jsonl"
    with open(dataset_path, "w", encoding="utf-8") as f:
        for pair in pairs:
            f.write(json.dumps(pair) + "\n")

    # Step 4: Fine-tune the model
    fine_tune_model(dataset_path, output_dir)

    # Step 5: Deploy the model
    deploy_model(output_dir)

if __name__ == "__main__":
    main()

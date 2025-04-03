import requests
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from nltk.translate.bleu_score import sentence_bleu
from rouge import Rouge  # Changed import
import nltk
import json
from sentence_transformers import SentenceTransformer
import logging
from tqdm import tqdm
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ModelTester:
    def __init__(self, api_url="http://localhost:8080", max_retries=3):
        self.api_url = api_url
        self.model_embedding = SentenceTransformer("all-MiniLM-L6-v2")
        self.rouge = Rouge()  # Changed scorer initialization
        nltk.download('punkt', quiet=True)
        
        # Setup requests session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def calculate_metrics(self, predicted_answer, actual_answer):
        try:
            # ROUGE scores
            rouge_scores = self.rouge.get_scores(predicted_answer, actual_answer)[0]
            
            # BLEU score
            reference = [actual_answer.split()]
            candidate = predicted_answer.split()
            bleu_score = sentence_bleu(reference, candidate)
            
            # Semantic similarity
            actual_embedding = self.model_embedding.encode([actual_answer])[0]
            predicted_embedding = self.model_embedding.encode([predicted_answer])[0]
            similarity = cosine_similarity([actual_embedding], [predicted_embedding])[0][0]
            
            return {
                'bleu_score': float(bleu_score),
                'semantic_similarity': float(similarity),
                'rouge1_f1': float(rouge_scores['rouge-1']['f']),
                'rouge2_f1': float(rouge_scores['rouge-2']['f']),
                'rougeL_f1': float(rouge_scores['rouge-l']['f'])
            }
        except Exception as e:
            logger.error(f"Error calculating metrics: {e}")
            return None

    def test_model(self, test_data_path):
        """
        Test model using a CSV/Excel file containing test cases
        Format: | question | expected_answer |
        """
        try:
            # Check if server is running
            try:
                response = self.session.get(self.api_url)
                if response.status_code != 200:
                    print(f"Server returned status code {response.status_code}")
                    return None
            except requests.exceptions.ConnectionError:
                print("Error: Flask server is not running. Please start the Flask app first.")
                print("Run 'python app.py' in a separate terminal window.")
                return None

            # Load test dataset
            if test_data_path.endswith('.csv'):
                df = pd.read_csv(test_data_path)
            else:
                df = pd.read_excel(test_data_path)

            results = []
            total_metrics = {
                'bleu_score': 0,
                'semantic_similarity': 0,
                'rouge1_f1': 0,
                'rouge2_f1': 0,
                'rougeL_f1': 0
            }

            # Process each test case
            successful_tests = 0
            for _, row in tqdm(df.iterrows(), total=len(df), desc="Testing cases"):
                question = row['question']
                actual_answer = row['expected_answer']

                try:
                    # Add headers and timeout
                    response = self.session.post(
                        f"{self.api_url}/query",
                        json={
                            "question": question,
                            "session_id": "test_session"
                        },
                        headers={
                            'Content-Type': 'application/json',
                            'Accept': 'application/json'
                        },
                        timeout=30
                    )
                    
                    if response.status_code == 200:
                        response_data = response.json()
                        if response_data.get('success', False):
                            predicted_answer = response_data.get('answer', '')
                            
                            # Calculate metrics
                            metrics = self.calculate_metrics(predicted_answer, actual_answer)
                            if metrics:
                                for key in total_metrics:
                                    total_metrics[key] += metrics[key]

                                results.append({
                                    'question': question,
                                    'actual_answer': actual_answer,
                                    'predicted_answer': predicted_answer,
                                    'metrics': metrics
                                })
                                successful_tests += 1
                        else:
                            logger.error(f"Query failed: {response_data.get('error', 'Unknown error')}")
                    else:
                        logger.error(f"Query failed with status code: {response.status_code}")

                except Exception as e:
                    logger.error(f"Error processing question '{question}': {e}")
                    continue

            # Only calculate averages if we have successful tests
            if successful_tests > 0:
                avg_metrics = {
                    key: total_metrics[key] / successful_tests 
                    for key in total_metrics
                }

                # Save results
                with open('model_test_results.json', 'w') as f:
                    json.dump({
                        'individual_results': results,
                        'average_metrics': avg_metrics,
                        'total_tests': len(df),
                        'successful_tests': successful_tests
                    }, f, indent=2)

                print(f"\nTest Results Summary:")
                print(f"Total test cases: {len(df)}")
                print(f"Successful tests: {successful_tests}")
                print("\nAverage Metrics:")
                for metric, value in avg_metrics.items():
                    print(f"{metric}: {value:.4f}")

                return avg_metrics
            else:
                print("\nNo successful tests completed. Please check the server connection.")
                return None

        except Exception as e:
            logger.error(f"Error in test_model: {e}")
            return None

if __name__ == "__main__":
    # Create test cases using pandas
    test_cases = {
        'question': [
            "What are the essential elements of a valid contract?",
            "Explain the concept of negligence in law.",
            "What is the difference between civil and criminal law?",
            "What is meant by intellectual property rights?",
            "Define habeas corpus and its importance.",
            "What is tort law?",
            "Explain the concept of strict liability.",
            "What is the role of a power of attorney?",
            "What constitutes defamation?",
            "Explain what is meant by consideration in contract law."
        ],
        'expected_answer': [
            "The essential elements of a valid contract are: offer, acceptance, consideration, intention to create legal relations, and capacity to contract.",
            "Negligence is a legal concept where a person fails to exercise reasonable care, causing harm to another. It requires proving duty of care, breach, causation, and damages.",
            "Civil law deals with private disputes between parties seeking compensation, while criminal law involves offenses against society prosecuted by the state.",
            "Intellectual property rights protect creations of the mind, including patents, copyrights, trademarks, and trade secrets.",
            "Habeas corpus is a fundamental legal right requiring authorities to prove the legal basis for a person's detention, protecting against unlawful imprisonment.",
            "Tort law deals with civil wrongs that cause harm or injury, allowing victims to seek compensation for damages.",
            "Strict liability holds a party legally responsible regardless of fault or intent, commonly applied in product liability and dangerous activities.",
            "A power of attorney is a legal document giving someone authority to act on another's behalf in specified legal or financial matters.",
            "Defamation is a false statement presented as fact that causes harm to someone's reputation, including libel (written) and slander (spoken).",
            "Consideration in contract law is something of value exchanged between parties, making a promise legally binding."
        ]
    }
    
    # Create DataFrame and save to Excel
    df = pd.DataFrame(test_cases)
    test_file_path = "legal_test_cases.xlsx"
    df.to_excel(test_file_path, index=False)
    print(f"Created test cases file: {test_file_path}")
    
    # Run the tests
    tester = ModelTester()
    results = tester.test_model(test_file_path)
    
    if results:
        print("\nDetailed metrics saved to model_test_results.json")

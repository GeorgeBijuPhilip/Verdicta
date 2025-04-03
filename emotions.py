from typing import Dict, List, Tuple
import re
from sklearn.metrics import f1_score
import numpy as np

class EmotionAnalyzer:
    def __init__(self):
        # Basic emotions with their associated keywords
        self.emotion_keywords = {
            'joy': ['happy', 'joy', 'delighted', 'glad', 'pleased', 'excited', 'wonderful'],
            'sadness': ['sad', 'unhappy', 'depressed', 'gloomy', 'miserable', 'disappointed'],
            'anger': ['angry', 'furious', 'rage', 'annoyed', 'irritated', 'frustrated'],
            'fear': ['afraid', 'scared', 'terrified', 'worried', 'anxious', 'nervous'],
            'surprise': ['surprised', 'amazed', 'astonished', 'shocked', 'unexpected'],
            'disgust': ['disgusted', 'repulsed', 'awful', 'horrible', 'gross']
        }

    def analyze_text(self, text: str) -> Dict[str, float]:
        text = text.lower()
        scores = {emotion: 0.0 for emotion in self.emotion_keywords.keys()}
        words = re.findall(r'\w+', text)

        for word in words:
            for emotion, keywords in self.emotion_keywords.items():
                if word in keywords:
                    scores[emotion] += 1.0

        # Normalize scores
        total = sum(scores.values())
        if total > 0:
            scores = {k: v/total for k, v in scores.items()}

        return scores

    def get_dominant_emotion(self, text: str) -> str:
        scores = self.analyze_text(text)
        return max(scores.items(), key=lambda x: x[1])[0] if scores else 'neutral'

    def evaluate_f1_score(self, test_data: List[Tuple[str, str]]) -> Dict[str, float]:
        """
        Calculate F1 score for emotion classification
        test_data: List of tuples containing (text, true_emotion)
        Returns: Dict with F1 scores for each emotion and macro average
        """
        y_true = []
        y_pred = []
        
        for text, true_emotion in test_data:
            predicted_emotion = self.get_dominant_emotion(text)
            y_true.append(true_emotion)
            y_pred.append(predicted_emotion)
        
        # Convert emotions to numerical labels
        emotions = list(self.emotion_keywords.keys())
        y_true_encoded = [emotions.index(e) for e in y_true]
        y_pred_encoded = [emotions.index(e) for e in y_pred]
        
        # Calculate F1 score for each emotion
        f1_scores = {}
        f1_per_class = f1_score(y_true_encoded, y_pred_encoded, 
                               average=None, 
                               labels=range(len(emotions)))
        
        for emotion, score in zip(emotions, f1_per_class):
            f1_scores[emotion] = score
            
        # Add macro average
        f1_scores['macro_avg'] = f1_score(y_true_encoded, y_pred_encoded, 
                                        average='macro')
        
        return f1_scores

    def test_model(self):
        """
        Test the emotion analyzer with some example data
        """
        test_data = [
            ("I am so happy today!", "joy"),
            ("This makes me really angry", "anger"),
            ("I'm feeling quite sad", "sadness"),
            ("That's disgusting", "disgust"),
            ("I'm really scared", "fear"),
            ("Wow, that's amazing!", "surprise")
        ]
        
        f1_scores = self.evaluate_f1_score(test_data)
        
        print("\nF1 Scores:")
        for emotion, score in f1_scores.items():
            print(f"{emotion}: {score:.3f}")

# Example usage:
if __name__ == "__main__":
    analyzer = EmotionAnalyzer()
    analyzer.test_model()

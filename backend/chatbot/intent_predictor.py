import pickle
import os
from sentence_transformers import SentenceTransformer

# Load embedding model
embedder = SentenceTransformer("all-MiniLM-L6-v2")

# Get path of the current folder
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Path to trained classifier
model_path = os.path.join(BASE_DIR, "intent_model.pkl")

# Load trained classifier
with open(model_path, "rb") as f:
    classifier = pickle.load(f)


def predict_intent(text):

    embedding = embedder.encode([text])

    probs = classifier.predict_proba(embedding)[0]
    max_prob = max(probs)

    intent = classifier.classes_[probs.argmax()]

    if max_prob < 0.60:
        return "unknown"

    return intent
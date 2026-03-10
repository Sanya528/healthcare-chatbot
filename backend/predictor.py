import os
import pickle
import pandas as pd
import torch
import torch.nn.functional as F
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MODEL_PATH = os.path.join(BASE_DIR, "clinicalbert_classifier")
MATRIX_PATH = os.path.join(BASE_DIR, "weighted_disease_symptom_matrix.csv")
ENCODER_PATH = os.path.join(MODEL_PATH, "disease_label_encoder.pkl")
SYNONYM_PATH = os.path.join(BASE_DIR, "synonym.csv")

# Load disease-symptom matrix
df = pd.read_csv(MATRIX_PATH, index_col=0)

# Load synonym dataset
syn_df = pd.read_csv(SYNONYM_PATH)

# Build synonym dictionary
synonym_map = {}

for _, row in syn_df.iterrows():
    canonical = str(row["Symptom"]).lower().strip()
    synonym = str(row["Synonym"]).lower().strip()
    synonym_map[synonym] = canonical


def normalize_symptoms(text):
    """
    Replace symptom synonyms with canonical names
    """
    if not text:
        return ""

    text = text.lower()

    for syn, canonical in synonym_map.items():
        pattern = r"\b" + re.escape(syn) + r"\b"
        text = re.sub(pattern, canonical, text)

    return text


# Load label encoder
with open(ENCODER_PATH, "rb") as f:
    label_encoder = pickle.load(f)

label_list = list(label_encoder.classes_)

# Load trained ClinicalBERT model
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, local_files_only=True)
model = AutoModelForSequenceClassification.from_pretrained(MODEL_PATH, local_files_only=True)
model.eval()


def predict_disease(text):
    """
    Predict disease using ClinicalBERT model
    """

    text = normalize_symptoms(text)

    inputs = tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        padding=True,
        max_length=128
    )

    with torch.no_grad():
        outputs = model(**inputs)

    probs = F.softmax(outputs.logits, dim=1)[0].numpy()

    predictions = dict(zip(label_list, probs))
    sorted_preds = sorted(predictions.items(), key=lambda x: x[1], reverse=True)

    top_disease = sorted_preds[0][0]
    confidence = float(sorted_preds[0][1])

    top3 = [
        {"disease": disease, "confidence": float(conf)}
        for disease, conf in sorted_preds[:3]
    ]

    return top_disease, confidence, top3


def extract_supporting_symptoms(text):
    
    text = normalize_symptoms(text)
    text = text.lower()

    matched = []

    for symptom in df.columns:

        pattern = r"\b" + re.escape(symptom.lower()) + r"\b"

        if re.search(pattern, text):
            matched.append(symptom)

    return matched
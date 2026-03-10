from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import traceback
import uuid
import numpy as np
import re
from werkzeug.security import generate_password_hash, check_password_hash

import predictor
from predictor import predict_disease, extract_supporting_symptoms
from database import get_db, init_db, close_db
from chatbot.intent_predictor import predict_intent

app = Flask(__name__)
CORS(app)

LOW_CONFIDENCE_THRESHOLD = 50
STOP_CONFIDENCE = 65
MAX_QUESTIONS = 12

init_db()
app.teardown_appcontext(close_db)

disease_info = pd.read_csv("disease.csv")
disease_info["disease"] = (
    disease_info["disease"]
    .str.strip()
    .str.lower()
    .str.replace("_", " ")
    .str.replace(r"\s*\(.*?\)", "", regex=True)
    .str.strip()
)


def _normalize_disease_name(name: str) -> str:
    """Canonical form used for all disease lookups."""
    return re.sub(r"\s*\(.*?\)", "", name.strip().lower().replace("_", " ")).strip()

def get_department(disease_name: str) -> str:
    row = disease_info[disease_info["disease"] == _normalize_disease_name(disease_name)]
    if row.empty:
        return "GENERAL MEDICINE"
    department = row.iloc[0].get("department", "GENERAL MEDICINE")
    return "GENERAL MEDICINE" if pd.isna(department) else str(department).upper()


def get_disease_metadata(disease_name: str):
    row = disease_info[disease_info["disease"] == _normalize_disease_name(disease_name)]
    if row.empty:
        return "Description not available.", "Precautions not available."

    row = row.iloc[0]
    description = row.get("description", "") or "Description not available."

    precaution_cols = [c for c in disease_info.columns if "precaution" in c.lower()]
    precautions = [
        str(row.get(c)) for c in precaution_cols
        if pd.notna(row.get(c)) and str(row.get(c)).strip()
    ]
    precaution_text = (
        "\n• " + "\n• ".join(precautions) if precautions else "Precautions not available."
    )
    return description, precaution_text


def filter_diseases_by_demographics(diseases: list, age: int, user_gender: str) -> list:
    user_gender = str(user_gender).strip().lower()
    valid = []

    for disease in diseases:
        row = disease_info[disease_info["disease"] == _normalize_disease_name(disease)]

        if row.empty:
            valid.append(disease)
            continue

        row = row.iloc[0]
        min_age = row.get("min_age", 0)
        max_age = row.get("max_age", 120)

        age_valid = True
        if pd.notna(min_age) and pd.notna(max_age):
            age_valid = min_age <= age <= max_age

        disease_gender = str(row.get("sex_type", "both")).strip().lower()
        gender_valid = (disease_gender == "both") or (user_gender == disease_gender)

        if age_valid and gender_valid:
            valid.append(disease)

    return valid

def _build_final_response(
    final_disease: str,
    confidence_percent: float,
    confirmed: list,
    disease_confidences: list,
    force_stop: bool,
) -> str:
    description, precautions = get_disease_metadata(final_disease)
    department   = get_department(final_disease)
    symptom_list = ", ".join(confirmed).strip(", ") or "none recorded"

    alternatives_text = ""
    alternatives = disease_confidences[1:3]
    if alternatives:
        alternatives_text = "\nOther possible conditions:\n"
        for d, c in alternatives:
            alternatives_text += f"• {d.title()} ({round(c * 100, 1)}%)\n"

    return (
        f"Based on the symptoms you reported: {symptom_list},\n\n"
        f"The most likely condition is {final_disease.title()} "
        f"with a confidence of {confidence_percent}%.\n\n"
        f"{alternatives_text}\n"
        f"Recommended department: {department.title()}\n\n"
        f"Description:\n{description}\n\n"
        f"Precautions:\n{precautions}"
    )


def _calculate_entropy(weights: list) -> float:
    total = sum(weights)
    if total == 0:
        return 0.0
    probs = [w / total for w in weights if w > 0]
    return -sum(p * np.log2(p) for p in probs)


def choose_best_symptom(top_candidates: list, confirmed: list, denied: list):
    candidate_symptoms = set()
    for disease in top_candidates:
        ds = predictor.df.loc[disease]
        candidate_symptoms.update(ds[ds > 0].index.tolist())

    candidate_symptoms = [
        s for s in candidate_symptoms
        if s not in confirmed and s not in denied
    ]

    best_symptom = None
    max_gain = -1

    for symptom in candidate_symptoms:
        weights      = [predictor.df.loc[d, symptom] for d in top_candidates]
        entropy_before = _calculate_entropy(weights)
        yes_weights  = [w for w in weights if w > 0]
        no_weights   = [w for w in weights if w == 0]
        entropy_yes  = _calculate_entropy(yes_weights) if yes_weights else 0
        entropy_no   = _calculate_entropy(no_weights)  if no_weights  else 0
        gain = entropy_before - (entropy_yes + entropy_no) / 2
        if gain > max_gain:
            max_gain = gain
            best_symptom = symptom

    return best_symptom

conversations = {}


def _new_conversation(initial_text: str) -> dict:
    return {
        "confirmed":      [],
        "denied":         [],
        "top_candidates": [],
        "last_asked":     None,
        "prob_map":       {},
        "initial_text":   initial_text,
    }

YES_TOKENS = {"yes", "yeah", "yep", "y"}
NO_TOKENS  = {"no",  "nope", "nah", "n"}


@app.route("/admin/users", methods=["GET"])
def get_all_users():
    try:
        db = get_db()
        users = db.execute(
            "SELECT id, name, email, age, gender FROM users WHERE name != 'admin'"
        ).fetchall()
        return jsonify({"users": [dict(u) for u in users]})
    except Exception:
        traceback.print_exc()
        return jsonify({"error": "Failed to fetch users"}), 500


@app.route("/register", methods=["POST"])
def register():
    data = request.get_json() or {}

    name     = (data.get("name")     or "").strip().lower()
    email    = (data.get("email")    or "").strip().lower()
    password = (data.get("password") or "").strip()
    gender   = (data.get("gender")   or "").strip().lower()

    try:
        age = int(data.get("age"))
    except (TypeError, ValueError):
        return jsonify({"error": "Valid age is required"}), 400

    if not name:
        return jsonify({"error": "Name is required"}), 400
    if not email:
        return jsonify({"error": "Email is required"}), 400
    if not password:
        return jsonify({"error": "Password is required"}), 400
    if gender not in ("male", "female", "other"):
        return jsonify({"error": "Gender must be male, female, or other"}), 400

    db = get_db()
    if db.execute("SELECT id FROM users WHERE name = ?", (name,)).fetchone():
        return jsonify({"error": "User already exists"}), 400

    db.execute(
        "INSERT INTO users (name, email, password_hash, age, gender) VALUES (?, ?, ?, ?, ?)",
        (name, email, generate_password_hash(password), age, gender),
    )
    db.commit()
    return jsonify({"message": "User registered successfully"}), 201


@app.route("/login", methods=["POST"])
def login():
    data     = request.get_json() or {}
    name     = (data.get("name",     "") or "").strip().lower()
    password = (data.get("password", "") or "").strip()

    db   = get_db()
    user = db.execute("SELECT * FROM users WHERE name = ?", (name,)).fetchone()

    if user is None or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Invalid name or password"}), 401

    return jsonify({
        "message": "Login successful",
        "user_id": user["id"],
        "name":    user["name"],
        "age":     user["age"],
        "gender":  user["gender"],
    }), 200


@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json() or {}

        # --- Parse all request fields up front ---
        user_message    = (data.get("message", "") or "").strip().lower()
        user_message    = predictor.normalize_symptoms(user_message)
        conversation_id = data.get("conversation_id")
        user_id         = data.get("user_id")

        # --- Early guards (before any DB call) ---
        if not user_message:
            return jsonify({"response": "Please describe your symptoms."})

        if not user_id:
            return jsonify({"response": "Session expired. Please log in again."}), 401

        # --- Intent classification ---
        if user_message in YES_TOKENS | NO_TOKENS:
            intent = "symptom_answer"
        else:
            intent = predict_intent(user_message)

        # Presence of known symptoms overrides intent
        if extract_supporting_symptoms(user_message):
            intent = "symptom_input"

        # --- Handle non-symptom intents (no DB needed) ---
        if intent == "greeting":
            return jsonify({
                "response": "Hello! I'm your AI healthcare assistant. Please describe your symptoms.",
                "conversation_id": conversation_id,
            })

        if intent == "goodbye":
            return jsonify({
                "response": "Take care! If symptoms persist, please consult a doctor.",
                "conversation_id": conversation_id,
            })

        if intent == "medical_advice":
            return jsonify({
                "response": (
                    "If your symptoms persist or worsen, it is recommended "
                    "to consult a doctor for proper medical evaluation."
                ),
                "conversation_id": conversation_id,
            })

        # Unknown intent with no symptoms — ask user to clarify
        if intent == "unknown":
            return jsonify({
                "response": (
                    "I'm not sure what you mean. "
                    "Please describe your symptoms — for example: "
                    "'I have a fever, headache, and sore throat'."
                ),
                "conversation_id": conversation_id,
            })

        # --- Resolve user from DB ---
        db   = get_db()
        user = db.execute(
            "SELECT age, gender FROM users WHERE id = ?", (user_id,)
        ).fetchone()

        if user is None:
            return jsonify({"response": "User not found. Please log in again."}), 401

        user_age    = user["age"]
        user_gender = user["gender"]

        # --- Resolve or create conversation (single unified block) ---
        if not conversation_id or conversation_id not in conversations:
            conversation_id = str(uuid.uuid4())
            conversations[conversation_id] = _new_conversation(user_message)

        convo = conversations[conversation_id]

        # --- Process user response ---
        if user_message in YES_TOKENS:
            if convo["last_asked"]:
                convo["confirmed"].append(convo["last_asked"])
                convo["last_asked"] = None

        elif user_message in NO_TOKENS:
            if convo["last_asked"]:
                convo["denied"].append(convo["last_asked"])
                convo["last_asked"] = None

        else:
            # New symptom text — initialise candidates on first pass
            if not convo["top_candidates"]:
                _, _, top3 = predict_disease(convo["initial_text"])
                predicted  = [d["disease"] for d in top3]
                filtered   = filter_diseases_by_demographics(predicted, user_age, user_gender)

                if not filtered:
                    del conversations[conversation_id]
                    return jsonify({
                        "response": (
                            "The detected conditions do not match your demographic profile. "
                            "Please provide more symptoms."
                        ),
                        "conversation_id": None,
                    })

                convo["top_candidates"] = filtered
                convo["prob_map"]       = {d["disease"]: d["confidence"] for d in top3}

            # Extract and accumulate newly mentioned symptoms
            for s in extract_supporting_symptoms(user_message):
                if s not in convo["confirmed"]:
                    convo["confirmed"].append(s)

            # Guard: require at least one confirmed symptom before predicting
            if not convo["confirmed"]:
                del conversations[conversation_id]
                return jsonify({
                    "response": (
                        "I wasn't able to identify any specific symptoms from your message. "
                        "Please describe what you are feeling — for example: "
                        "'I have a headache, fever, and sore throat'."
                    ),
                    "conversation_id": None,
                })

        if not convo["top_candidates"]:
            return jsonify({
                "response": "Unable to determine a condition. Please provide more symptoms.",
                "conversation_id": conversation_id,
            })

        # --- Score and rank candidates ---
        def compute_confidence(disease_name: str) -> float:
            model_conf     = convo["prob_map"].get(disease_name, 0)
            dw             = predictor.df.loc[disease_name]
            total_weight   = dw.sum()
            matched_weight = sum(dw.get(s, 0) for s in convo["confirmed"])
            coverage       = max(0.0, min(1.0, matched_weight / total_weight if total_weight > 0 else 0))
            boost          = min(0.2, len(convo["confirmed"]) * 0.03)
            return min(1.0, 0.6 * model_conf + 0.4 * coverage + boost)

        disease_confidences = sorted(
            [(d, compute_confidence(d)) for d in convo["top_candidates"]],
            key=lambda x: x[1],
            reverse=True,
        )

        final_disease      = disease_confidences[0][0]
        final_confidence   = disease_confidences[0][1]
        confidence_percent = round(final_confidence * 100, 1)
        total_questions    = len(convo["confirmed"]) + len(convo["denied"])

        # --- Demographic check on final disease ---
        if not filter_diseases_by_demographics([final_disease], user_age, user_gender):
            del conversations[conversation_id]
            return jsonify({
                "response": (
                    "The predicted condition does not match your demographic profile. "
                    "This condition typically occurs in the opposite gender. "
                    "Please consult a doctor for proper diagnosis."
                ),
                "conversation_id": conversation_id,
            })

        # --- Decide: stop or ask next question ---
        force_stop  = total_questions >= MAX_QUESTIONS
        should_stop = confidence_percent >= STOP_CONFIDENCE or force_stop

        if should_stop:
            del conversations[conversation_id]
            # If confidence is too low, don't show a prediction — just advise the doctor
            if confidence_percent < LOW_CONFIDENCE_THRESHOLD:
                return jsonify({
                    "response": (
                        "I wasn't able to identify your condition with enough confidence based on the symptoms provided.\n"
                        "Please consult a doctor for a proper diagnosis or provide more symptoms."
                    ),
                    "conversation_id": conversation_id,
                })
            response_text = _build_final_response(
                final_disease, confidence_percent,
                convo["confirmed"], disease_confidences, force_stop,
            )
            return jsonify({"response": response_text, "conversation_id": conversation_id})

        # --- Choose best follow-up question ---
        best_symptom = choose_best_symptom(
            convo["top_candidates"], convo["confirmed"], convo["denied"]
        )

        if not best_symptom:
            # No distinguishing questions left
            del conversations[conversation_id]
            if confidence_percent < LOW_CONFIDENCE_THRESHOLD:
                return jsonify({
                    "response": (
                        "I wasn't able to identify your condition with enough confidence "
                        "based on the symptoms provided.\n\n"
                        "Please consult a doctor for a proper diagnosis."
                    ),
                    "conversation_id": conversation_id,
                })
            response_text = _build_final_response(
                final_disease, confidence_percent,
                convo["confirmed"], disease_confidences, force_stop=False,
            )
            return jsonify({"response": response_text, "conversation_id": conversation_id})

        convo["last_asked"] = best_symptom
        return jsonify({
            "response": f"Do you also have symptom: {best_symptom}?",
            "conversation_id": conversation_id,
        })

    except Exception:
        traceback.print_exc()
        return jsonify({"response": "Internal server error."}), 500


@app.route("/")
def home():
    return "Backend is running", 200


if __name__ == "__main__":
    app.run(debug=True)
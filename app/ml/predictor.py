from pathlib import Path

import numpy as np
import pandas as pd
from joblib import load


# ============================================================
# Configuration
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

MODEL_PATH = (
    PROJECT_ROOT
    / "models"
    / "disease_prediction_model.pkl"
)

CONFIDENCE_THRESHOLD = 0.60


# ============================================================
# Load Trained Model
# ============================================================

_model = None


def load_model():
    """
    Load the trained disease prediction pipeline.
    """

    global _model

    if _model is None:

        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Model file not found: {MODEL_PATH}"
            )

        _model = load(MODEL_PATH)

    return _model


# ============================================================
# Prepare Input
# ============================================================

def prepare_input(symptoms):
    """
    Convert a symptom dictionary into a model-compatible
    pandas DataFrame.

    Expected input:
        {
            "Symptom_1": "itching",
            "Symptom_2": "skin_rash",
            ...
            "Symptom_17": ""
        }
    """

    if not isinstance(symptoms, dict):
        raise TypeError(
            "Symptoms must be provided as a dictionary."
        )

    input_data = {}

    for i in range(1, 18):

        column = f"Symptom_{i}"

        value = symptoms.get(
            column,
            "__MISSING__"
        )

        if value is None or str(value).strip() == "":
            value = "__MISSING__"

        input_data[column] = str(value)

    # Calculate symptom count
    symptom_count = sum(
        1
        for i in range(1, 18)
        if input_data[f"Symptom_{i}"] != "__MISSING__"
    )

    input_data["Symptom_Count"] = symptom_count

    return pd.DataFrame([input_data])


# ============================================================
# Predict Disease
# ============================================================

def predict_disease(symptoms):
    """
    Predict the most likely disease.

    Returns:
        {
            "disease": ...,
            "confidence": ...,
            "is_confident": ...,
            "threshold": ...,
            "top_3": [...]
        }
    """

    model = load_model()

    input_data = prepare_input(symptoms)

    probabilities = model.predict_proba(
        input_data
    )[0]

    classes = np.asarray(
        model.named_steps["model"].classes_
    )

    top_indices = np.argsort(
        probabilities
    )[::-1][:3]

    predicted_index = top_indices[0]

    predicted_disease = classes[
        predicted_index
    ]

    confidence = float(
        probabilities[predicted_index]
    )

    top_3 = []

    for rank, index in enumerate(
        top_indices,
        start=1
    ):

        top_3.append({
            "rank": rank,
            "disease": str(classes[index]),
            "probability": round(
                float(probabilities[index]),
                4
            )
        })

    is_confident = (
        confidence >= CONFIDENCE_THRESHOLD
    )

    return {
        "disease": str(predicted_disease),
        "confidence": round(
            confidence,
            4
        ),
        "is_confident": is_confident,
        "threshold": CONFIDENCE_THRESHOLD,
        "top_3": top_3
    }


# ============================================================
# Top-3 Predictions
# ============================================================

def get_top_3_predictions(symptoms):
    """
    Return the three highest-probability disease predictions.
    """

    result = predict_disease(
        symptoms
    )

    return result["top_3"]


# ============================================================
# Confidence Evaluation
# ============================================================

def check_confidence(confidence):
    """
    Check whether a prediction satisfies the project
    confidence threshold.
    """

    confidence = float(
        confidence
    )

    return {
        "confidence": confidence,
        "threshold": CONFIDENCE_THRESHOLD,
        "is_confident": (
            confidence >= CONFIDENCE_THRESHOLD
        )
    }


# ============================================================
# Test Module
# ============================================================

if __name__ == "__main__":

    print("=" * 60)
    print("PREDICTOR MODULE TEST")
    print("=" * 60)

    model = load_model()

    print(
        f"Model loaded successfully: "
        f"{type(model).__name__}"
    )

    print(
        f"Model path: "
        f"{MODEL_PATH}"
    )

    print(
        f"Confidence threshold: "
        f"{CONFIDENCE_THRESHOLD:.0%}"
    )

    print(
        "\n✓ predictor.py is working correctly."
    )
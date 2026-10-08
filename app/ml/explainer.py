from pathlib import Path

import numpy as np
import pandas as pd
import shap
from joblib import load

from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import (
    RandomForestClassifier,
    GradientBoostingClassifier
)


# ============================================================
# Configuration
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

MODEL_PATH = (
    PROJECT_ROOT
    / "models"
    / "disease_prediction_model.pkl"
)

SHAP_BACKGROUND_SIZE = 50


# ============================================================
# Load Trained Model
# ============================================================

_model = None
_explainer = None
_background_data = None


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
    Convert symptoms into the same input format used by
    the trained model.
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

    symptom_count = sum(
        1
        for i in range(1, 18)
        if input_data[f"Symptom_{i}"] != "__MISSING__"
    )

    input_data["Symptom_Count"] = symptom_count

    return pd.DataFrame([input_data])


# ============================================================
# Get Preprocessor and Model
# ============================================================

def get_preprocessor():

    model = load_model()

    return model.named_steps[
        "preprocessor"
    ]


def get_classifier():

    model = load_model()

    return model.named_steps[
        "model"
    ]


# ============================================================
# Transform Input
# ============================================================

def transform_input(symptoms):

    input_data = prepare_input(
        symptoms
    )

    preprocessor = get_preprocessor()

    transformed = preprocessor.transform(
        input_data
    )

    if hasattr(
        transformed,
        "toarray"
    ):
        transformed = transformed.toarray()

    return transformed


# ============================================================
# Feature Names
# ============================================================

def get_feature_names():

    preprocessor = get_preprocessor()

    return np.asarray(
        preprocessor.get_feature_names_out()
    )


# ============================================================
# Create Background Data
# ============================================================

def create_background_data():

    global _background_data

    if _background_data is not None:
        return _background_data

    model = load_model()

    # Use the training data stored by the model's SMOTENC step
    # when available.
    smote = model.named_steps.get(
        "smote"
    )

    if smote is not None and hasattr(
        smote,
        "sampling_strategy_"
    ):
        pass

    raise RuntimeError(
        "Background data must be provided from the "
        "Week 4 SHAP analysis workflow."
    )


# ============================================================
# Create SHAP Explainer
# ============================================================

def create_explainer(
    background_data
):

    global _explainer
    global _background_data

    model = get_classifier()

    _background_data = background_data

    if isinstance(
        model,
        (
            DecisionTreeClassifier,
            RandomForestClassifier,
            GradientBoostingClassifier
        )
    ):

        _explainer = shap.TreeExplainer(
            model,
            data=background_data,
            feature_perturbation="interventional"
        )

    elif isinstance(
        model,
        LogisticRegression
    ):

        _explainer = shap.LinearExplainer(
            model,
            background_data
        )

    else:

        def predict_proba(
            transformed_data
        ):
            return model.predict_proba(
                transformed_data
            )

        _explainer = shap.Explainer(
            predict_proba,
            background_data,
            algorithm="permutation"
        )

    return _explainer


# ============================================================
# Calculate SHAP Values
# ============================================================

def calculate_shap_values(
    symptoms,
    background_data
):

    explainer = create_explainer(
        background_data
    )

    transformed_input = transform_input(
        symptoms
    )

    shap_result = explainer(
        transformed_input
    )

    return shap_result


# ============================================================
# Get Feature Contributions
# ============================================================

def get_feature_contributions(
    symptoms,
    background_data,
    class_index=0
):

    shap_result = calculate_shap_values(
        symptoms,
        background_data
    )

    shap_values = np.asarray(
        shap_result.values
    )

    if shap_values.ndim == 3:

        values = shap_values[
            0,
            :,
            class_index
        ]

    else:

        values = shap_values[
            0
        ]

    feature_names = (
        get_feature_names()
    )

    contributions = pd.DataFrame({
        "Feature": feature_names,
        "SHAP_Value": values
    })

    contributions = (
        contributions
        .sort_values(
            "SHAP_Value",
            ascending=False
        )
        .reset_index(drop=True)
    )

    return contributions


# ============================================================
# Top Positive Contributions
# ============================================================

def get_top_positive_contributions(
    symptoms,
    background_data,
    class_index=0,
    top_n=10
):

    contributions = (
        get_feature_contributions(
            symptoms,
            background_data,
            class_index
        )
    )

    return (
        contributions
        .head(top_n)
    )


# ============================================================
# Top Negative Contributions
# ============================================================

def get_top_negative_contributions(
    symptoms,
    background_data,
    class_index=0,
    top_n=10
):

    contributions = (
        get_feature_contributions(
            symptoms,
            background_data,
            class_index
        )
    )

    return (
        contributions
        .sort_values(
            "SHAP_Value"
        )
        .head(top_n)
    )


# ============================================================
# Module Test
# ============================================================

if __name__ == "__main__":

    print("=" * 60)
    print("EXPLAINER MODULE TEST")
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
        f"Feature count: "
        f"{len(get_feature_names())}"
    )

    print(
        "\n✓ explainer.py basic loading test passed."
    )
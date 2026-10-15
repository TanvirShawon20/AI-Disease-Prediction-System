from app.ml.predictor import predict_disease


def test_real_model_predicts_from_symptoms():
    symptoms = {
        "Symptom_1": "itching",
        "Symptom_2": "skin_rash",
    }

    result = predict_disease(symptoms)

    assert isinstance(result["disease"], str)
    assert result["disease"]
    assert 0 <= result["confidence"] <= 1
    assert isinstance(result["is_confident"], bool)
    assert len(result["top_3"]) == 3

    for item in result["top_3"]:
        assert "disease" in item
        assert 0 <= item["probability"] <= 1

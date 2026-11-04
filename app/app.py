import json
import math
import os
import pickle

import psycopg2
from flask import Flask, jsonify, request


app = Flask(__name__)

MODEL_PATH = os.getenv("MODEL_PATH", "model/model.pkl")

with open(MODEL_PATH, "rb") as file:
    artifact = pickle.load(file)

model = artifact["model"]
feature_names = artifact["feature_names"]
model_version = artifact["model_version"]
classes = artifact["classes"]


def get_db():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "10.10.10.2"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "ml_predictions"),
        user=os.getenv("DB_USER", "ml_app"),
        password=os.getenv("DB_PASSWORD"),
        sslmode=os.getenv("DB_SSLMODE", "require"),
        connect_timeout=5,
    )


@app.route("/health", methods=["GET"])
def health():
    return jsonify(
        {
            "status": "ok",
            "dataset": "Palmer Penguins",
            "model_version": model_version,
            "classes": classes,
            "feature_names": feature_names,
        }
    )


@app.route("/predict", methods=["POST"])
def predict():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "Request body must be a JSON object"}), 400

    features = data.get("features")

    if not isinstance(features, list):
        return jsonify({"error": "Field 'features' must be a list"}), 400

    if len(features) != len(feature_names):
        return jsonify(
            {
                "error": f"Expected {len(feature_names)} features",
                "feature_names": feature_names,
            }
        ), 400

    try:
        numeric_features = [float(value) for value in features]
    except (TypeError, ValueError):
        return jsonify({"error": "All features must be numeric"}), 400

    if not all(math.isfinite(value) for value in numeric_features):
        return jsonify({"error": "Features must contain finite numbers"}), 400

    species = str(model.predict([numeric_features])[0])
    probabilities = model.predict_proba([numeric_features])[0]
    probability = float(max(probabilities))

    input_data = {
        "features": dict(zip(feature_names, numeric_features))
    }

    result = {
        "species": species,
        "probability": round(probability, 6),
        "model_version": model_version,
    }

    connection = None

    try:
        connection = get_db()

        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO predictions
                    (input_data, prediction, model_version)
                VALUES (%s, %s, %s)
                RETURNING id
                """,
                (
                    json.dumps(input_data),
                    json.dumps(result),
                    model_version,
                ),
            )
            prediction_id = cursor.fetchone()[0]

        connection.commit()

    except psycopg2.Error as error:
        if connection is not None:
            connection.rollback()

        return jsonify(
            {
                "error": "Database operation failed",
                "details": str(error).strip(),
            }
        ), 503

    finally:
        if connection is not None:
            connection.close()

    result["prediction_id"] = prediction_id
    return jsonify(result)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

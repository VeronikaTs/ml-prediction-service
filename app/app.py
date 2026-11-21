import json
import math
import os
import pickle
import time
import urllib.error
import urllib.request

from flask import Flask, Response, jsonify, request
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)


app = Flask(__name__)

MODEL_PATH = os.getenv("MODEL_PATH", "model/model.pkl")

with open(MODEL_PATH, "rb") as file:
    artifact = pickle.load(file)

model = artifact["model"]
feature_names = artifact["feature_names"]
model_version = artifact["model_version"]
classes = artifact["classes"]

PREDICTIONS_TOTAL = Counter(
    "ml_predictions_total",
    "Total number of predictions",
    ["model_version", "predicted_class"],
)
PREDICTION_LATENCY = Histogram(
    "ml_prediction_latency_seconds",
    "Prediction latency in seconds",
)
LOGGER_ERRORS_TOTAL = Counter(
    "ml_logger_errors_total",
    "Total number of logger service errors",
)
MODEL_INFO = Gauge(
    "ml_model_info",
    "Information about the loaded model",
    ["version"],
)
MODEL_INFO.labels(version=model_version).set(1)


LOGGER_URL = os.getenv(
    "LOGGER_URL",
    "http://logger-service:5001/log",
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
    started_at = time.perf_counter()
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

    PREDICTION_LATENCY.observe(time.perf_counter() - started_at)
    PREDICTIONS_TOTAL.labels(
        model_version=model_version,
        predicted_class=species,
    ).inc()

    input_data = {
        "features": dict(zip(feature_names, numeric_features))
    }

    result = {
        "species": species,
        "probability": round(probability, 6),
        "model_version": model_version,
    }

    payload = json.dumps(
        {
            "input_data": input_data,
            "prediction": result,
            "model_version": model_version,
        }
    ).encode("utf-8")

    try:
        logger_request = urllib.request.Request(
            LOGGER_URL,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(
            logger_request,
            timeout=5,
        ) as logger_response:
            logger_result = json.loads(
                logger_response.read().decode("utf-8")
            )

        prediction_id = logger_result.get("prediction_id")
        if prediction_id is not None:
            result["prediction_id"] = prediction_id

    except (urllib.error.URLError, TimeoutError, ValueError) as error:
        LOGGER_ERRORS_TOTAL.inc()
        app.logger.error("Logger service error: %s", error)

    return jsonify(result)


@app.route("/metrics", methods=["GET"])
def metrics():
    return Response(generate_latest(), content_type=CONTENT_TYPE_LATEST)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

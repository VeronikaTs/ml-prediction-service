import json
import os

import psycopg2
from flask import Flask, Response, jsonify, request
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    generate_latest,
)


app = Flask(__name__)

LOG_REQUESTS_TOTAL = Counter(
    "logger_requests_total",
    "Total number of log requests",
    ["status"],
)
DB_WRITE_ERRORS_TOTAL = Counter(
    "logger_db_errors_total",
    "Total number of database write errors",
)


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
    return jsonify({"status": "ok", "service": "logger"})


@app.route("/log", methods=["POST"])
def log_prediction():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        LOG_REQUESTS_TOTAL.labels(status="bad_request").inc()
        return jsonify({"error": "Request body must be a JSON object"}), 400

    input_data = data.get("input_data")
    prediction = data.get("prediction")
    model_version = data.get("model_version")

    if not input_data or not prediction or not model_version:
        LOG_REQUESTS_TOTAL.labels(status="bad_request").inc()
        return jsonify(
            {
                "error": (
                    "input_data, prediction and model_version are required"
                )
            }
        ), 400

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
                    json.dumps(prediction),
                    model_version,
                ),
            )
            prediction_id = cursor.fetchone()[0]

        connection.commit()
        LOG_REQUESTS_TOTAL.labels(status="success").inc()

        return jsonify(
            {
                "status": "logged",
                "prediction_id": prediction_id,
            }
        ), 201

    except psycopg2.Error as error:
        DB_WRITE_ERRORS_TOTAL.inc()
        LOG_REQUESTS_TOTAL.labels(status="error").inc()

        if connection is not None:
            connection.rollback()

        app.logger.error("Database operation failed: %s", error)
        return jsonify({"error": "Database operation failed"}), 503

    finally:
        if connection is not None:
            connection.close()


@app.route("/metrics", methods=["GET"])
def metrics():
    return Response(generate_latest(), content_type=CONTENT_TYPE_LATEST)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)

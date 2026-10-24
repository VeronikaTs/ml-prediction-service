from pathlib import Path
import csv
import pickle

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split


RANDOM_STATE = 42
MODEL_VERSION = "penguins-rf-v1"

FEATURE_NAMES = [
    "bill_length_mm",
    "bill_depth_mm",
    "flipper_length_mm",
    "body_mass_g",
]

model_dir = Path(__file__).resolve().parent
dataset_path = model_dir / "penguins.csv"
model_path = model_dir / "model.pkl"

X = []
y = []

# Читаем CSV и пропускаем строки с отсутствующими измерениями.
with dataset_path.open("r", encoding="utf-8", newline="") as file:
    reader = csv.DictReader(file)

    for row in reader:
        values = [row[name].strip() for name in FEATURE_NAMES]
        species = row["species"].strip()

        if not species or any(value == "" for value in values):
            continue

        X.append([float(value) for value in values])
        y.append(species)

X = np.asarray(X, dtype=float)
y = np.asarray(y)

# 80% данных используются для обучения, 20% — для проверки.
X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    random_state=RANDOM_STATE,
    stratify=y,
)

# Random Forest строит ансамбль из 200 деревьев решений.
model = RandomForestClassifier(
    n_estimators=200,
    random_state=RANDOM_STATE,
)

model.fit(X_train, y_train)

predictions = model.predict(X_test)
accuracy = accuracy_score(y_test, predictions)

# Вместе с моделью сохраняем порядок признаков и версию.
artifact = {
    "model": model,
    "feature_names": FEATURE_NAMES,
    "model_version": MODEL_VERSION,
    "classes": model.classes_.tolist(),
}

with model_path.open("wb") as file:
    pickle.dump(artifact, file)

print("Dataset: Palmer Penguins")
print(f"Valid samples: {len(X)}")
print(f"Features: {len(FEATURE_NAMES)}")
print(f"Classes: {', '.join(model.classes_)}")
print(f"Accuracy: {accuracy:.4f}")
print(f"Model version: {MODEL_VERSION}")
print(f"Model saved to: {model_path}")

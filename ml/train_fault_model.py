from __future__ import annotations

from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder

ROOT_DIR = Path(__file__).resolve().parents[1]
DATASET_PATH = ROOT_DIR / "ml" / "datasets" / "pv_dataset.csv"
MODEL_DIR = ROOT_DIR / "api" / "app" / "services" / "models"
MODEL_PATH = MODEL_DIR / "fault_model.joblib"
LABEL_ENCODER_PATH = MODEL_DIR / "label_encoder.joblib"

FEATURE_COLUMNS = [
    "voltage_v",
    "current_a",
    "power_w",
    "panel_temperature_c",
    "light_lux",
]
TARGET_COLUMN = "fault_type"


def main() -> None:
    if not DATASET_PATH.is_file():
        raise FileNotFoundError(f"Fault dataset not found: {DATASET_PATH}")

    dataset = pd.read_csv(DATASET_PATH)
    required_columns = {*FEATURE_COLUMNS, TARGET_COLUMN}
    missing_columns = required_columns.difference(dataset.columns)
    if missing_columns:
        raise ValueError(
            "Dataset is missing required columns: "
            + ", ".join(sorted(missing_columns))
        )

    dataset = dataset.dropna(subset=[TARGET_COLUMN])
    features = dataset[FEATURE_COLUMNS].apply(pd.to_numeric, errors="coerce")
    target = dataset[TARGET_COLUMN].astype(str)

    label_encoder = LabelEncoder()
    encoded_target = label_encoder.fit_transform(target)
    if len(label_encoder.classes_) < 2:
        raise ValueError("Fault training requires at least two fault_type classes")

    x_train, x_test, y_train, y_test = train_test_split(
        features,
        encoded_target,
        test_size=0.2,
        random_state=42,
        stratify=encoded_target,
    )
    model = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            (
                "classifier",
                RandomForestClassifier(n_estimators=100, random_state=42),
            ),
        ]
    )
    model.fit(x_train, y_train)

    predictions = model.predict(x_test)
    labels = range(len(label_encoder.classes_))
    print(f"Accuracy: {accuracy_score(y_test, predictions):.4f}")
    print(
        "Classification report:\n"
        + classification_report(
            y_test,
            predictions,
            labels=list(labels),
            target_names=label_encoder.classes_,
            zero_division=0,
        )
    )
    print(
        "Confusion matrix:\n"
        + str(confusion_matrix(y_test, predictions, labels=list(labels)))
    )

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    joblib.dump(label_encoder, LABEL_ENCODER_PATH)
    print(f"Saved fault model to {MODEL_PATH}")
    print(f"Saved label encoder to {LABEL_ENCODER_PATH}")


if __name__ == "__main__":
    main()

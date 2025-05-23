"""
Train ML model on HR feedback dataset for candidate analysis.
- Loads data from /api/feedback/dataset/csv
- Trains RandomForestClassifier to predict is_successful
- Saves model to model.pkl
"""
import pandas as pd
import requests
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, roc_auc_score, f1_score
import os

API_URL = "http://localhost:8000/api/feedback/dataset/csv"
MODEL_PATH = os.path.join(os.path.dirname(__file__), "model.pkl")

# 1. Load data
def load_data():
    response = requests.get(API_URL)
    response.raise_for_status()
    from io import StringIO
    df = pd.read_csv(StringIO(response.text))
    return df

# 2. Feature engineering (MVP: используем только score и hr_rating)
def prepare_features(df):
    df = df.dropna(subset=["is_successful"])  # только размеченные примеры
    df["is_successful"] = df["is_successful"].astype(int)
    X = df[["score", "hr_rating"]].fillna(0)
    y = df["is_successful"]
    return X, y

# 3. Train model
def train_model(X, y):
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42)
    clf = RandomForestClassifier(n_estimators=100, random_state=42)
    clf.fit(X_train, y_train)
    y_pred = clf.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)
    try:
        auc = roc_auc_score(y_test, clf.predict_proba(X_test)[:,1])
    except Exception:
        auc = None
    return clf, {"accuracy": acc, "f1": f1, "roc_auc": auc}

# 4. Save model
def save_model(model):
    joblib.dump(model, MODEL_PATH)

if __name__ == "__main__":
    df = load_data()
    X, y = prepare_features(df)
    model, metrics = train_model(X, y)
    save_model(model)
    print("Model trained and saved to", MODEL_PATH)
    print("Metrics:", metrics)

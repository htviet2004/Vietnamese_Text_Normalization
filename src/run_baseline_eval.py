from __future__ import annotations

from pathlib import Path

import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer, HashingVectorizer, TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import MultinomialNB
from sklearn.svm import LinearSVC


def evaluate(name: str, X_train, X_test, y_train, y_test):
    rows = []
    models = [
        ("NaiveBayes", MultinomialNB()),
        ("LogisticRegression", LogisticRegression(max_iter=1200)),
        ("LinearSVM", LinearSVC()),
    ]
    for model_name, model in models:
        model.fit(X_train, y_train)
        pred = model.predict(X_test)
        rows.append(
            {
                "representation": name,
                "model": model_name,
                "accuracy": float(accuracy_score(y_test, pred)),
                "precision_weighted": float(precision_score(y_test, pred, average="weighted", zero_division=0)),
                "recall_weighted": float(recall_score(y_test, pred, average="weighted", zero_division=0)),
                "f1_weighted": float(f1_score(y_test, pred, average="weighted", zero_division=0)),
            }
        )
    return rows


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent
    input_csv = project_root / "outputs" / "cleaned_dataset_fixed.csv"
    output_csv = project_root / "outputs" / "baseline_results.csv"

    if not input_csv.exists():
        raise FileNotFoundError(f"Missing input dataset: {input_csv}")

    df = pd.read_csv(input_csv, encoding="utf-8-sig")
    if "clean_text" not in df.columns or "source" not in df.columns:
        raise ValueError("Dataset must contain clean_text and source columns")

    df = df.dropna(subset=["clean_text", "source"]).copy()
    df["clean_text"] = df["clean_text"].astype(str)
    df = df[df["clean_text"].str.strip() != ""]

    X = df["clean_text"].tolist()
    y = df["source"].astype(str).to_numpy()

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    rows = []

    one_hot = CountVectorizer(max_features=3000, binary=True)
    rows.extend(evaluate("OneHot", one_hot.fit_transform(X_train), one_hot.transform(X_test), y_train, y_test))

    count = CountVectorizer(max_features=6000)
    rows.extend(evaluate("CountVectorizer", count.fit_transform(X_train), count.transform(X_test), y_train, y_test))

    ngrams = CountVectorizer(max_features=12000, ngram_range=(1, 2))
    rows.extend(evaluate("Ngrams_1_2", ngrams.fit_transform(X_train), ngrams.transform(X_test), y_train, y_test))

    hashing = HashingVectorizer(n_features=2**14, alternate_sign=False, norm=None)
    rows.extend(evaluate("Hashing", hashing.transform(X_train), hashing.transform(X_test), y_train, y_test))

    tfidf = TfidfVectorizer(max_features=12000, ngram_range=(1, 2))
    rows.extend(evaluate("TFIDF", tfidf.fit_transform(X_train), tfidf.transform(X_test), y_train, y_test))

    result = pd.DataFrame(rows).sort_values(by=["f1_weighted", "accuracy"], ascending=False)
    result.to_csv(output_csv, index=False, encoding="utf-8-sig")

    print("Saved:", output_csv)
    print(result.head(10).to_string(index=False))


if __name__ == "__main__":
    main()

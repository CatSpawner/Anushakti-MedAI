from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.pipeline import Pipeline


@dataclass
class Predictor:
    dept_model: Pipeline
    pri_model: Pipeline
    sev_model: Pipeline

    def predict(self, X):
        dept = self.dept_model.predict(X)
        pri = self.pri_model.predict(X)
        sev = self.sev_model.predict(X)
        sev_int = [max(1, min(10, int(round(s)))) for s in sev]
        return list(zip(dept, pri, sev_int))


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--csv", required=True)
    p.add_argument("--out", default="hospital_ai_system/ml_artifacts/triage_model.joblib")
    args = p.parse_args()

    df = pd.read_csv(args.csv)

    X = df["symptoms_text"].astype(str).tolist()
    y_dept = df["expected_department"].astype(str).tolist()
    y_pri = df["expected_priority"].astype(str).tolist()
    y_sev = df["expected_severity"].astype(int).tolist()

    dept_model = Pipeline([("tfidf", TfidfVectorizer(ngram_range=(1, 2))), ("clf", LogisticRegression(max_iter=2500))])
    pri_model = Pipeline([("tfidf", TfidfVectorizer(ngram_range=(1, 2))), ("clf", LogisticRegression(max_iter=2500))])
    sev_model = Pipeline([("tfidf", TfidfVectorizer(ngram_range=(1, 2))), ("reg", Ridge())])

    dept_model.fit(X, y_dept)
    pri_model.fit(X, y_pri)
    sev_model.fit(X, y_sev)

    predictor = Predictor(dept_model=dept_model, pri_model=pri_model, sev_model=sev_model)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"predictor": predictor}, out)
    print(f"Saved: {out}")


if __name__ == "__main__":
    main()
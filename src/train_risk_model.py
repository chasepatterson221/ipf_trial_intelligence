"""
Train a logistic regression model to predict trial termination risk,
then score all currently-active trials and write results to trial_risk_scores.
"""

import pandas as pd
import psycopg2
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report, roc_auc_score

DB_CONFIG = {
    "host": "localhost",
    "dbname": "ipf_trial_intelligence",
    "user": "ipf_user",
    "password": "ipf_pass",
    "port": 5432,
}

RESOLVED_STATUSES = ("COMPLETED", "TERMINATED", "WITHDRAWN")
ACTIVE_STATUSES = ("RECRUITING", "ACTIVE_NOT_RECRUITING", "NOT_YET_RECRUITING",
                    "ENROLLING_BY_INVITATION", "UNKNOWN")

FEATURE_QUERY = """
    SELECT
        t.nct_id,
        t.overall_status,
        t.phase,
        t.enrollment_count,
        s.sponsor_class,
        s.publicly_traded,
        i.mechanism_class,
        (t.primary_completion_date - t.start_date) AS planned_duration_days
    FROM trials t
    LEFT JOIN sponsors s ON t.sponsor_id = s.sponsor_id
    LEFT JOIN (
        -- one row per trial: pick a single mechanism_class per trial
        -- (a trial can have multiple interventions; take the first non-null)
        SELECT DISTINCT ON (nct_id) nct_id, mechanism_class
        FROM interventions
        WHERE mechanism_class IS NOT NULL
        ORDER BY nct_id, intervention_id
    ) i ON t.nct_id = i.nct_id
    WHERE t.phase IN ('EARLY_PHASE1', 'PHASE1', 'PHASE2', 'PHASE3', 'PHASE4')
"""


def load_data(conn):
    df = pd.read_sql(FEATURE_QUERY, conn)
    return df


def prepare_features(df):
    """Fill missing values honestly rather than dropping rows we don't have to."""
    df = df.copy()
    df["enrollment_count"] = df["enrollment_count"].fillna(df["enrollment_count"].median())
    df["planned_duration_days"] = df["planned_duration_days"].fillna(df["planned_duration_days"].median())
    df["sponsor_class"] = df["sponsor_class"].fillna("UNKNOWN")
    df["mechanism_class"] = df["mechanism_class"].fillna("investigational_unclassified")
    df["publicly_traded"] = df["publicly_traded"].fillna(False)
    return df


def build_pipeline():
    categorical_features = ["phase", "sponsor_class", "mechanism_class"]
    numeric_features = ["enrollment_count", "planned_duration_days", "publicly_traded"]

    preprocessor = ColumnTransformer(transformers=[
        ("cat", OneHotEncoder(handle_unknown="ignore"), categorical_features),
        ("num", StandardScaler(), numeric_features),
    ])

    pipeline = Pipeline(steps=[
        ("preprocess", preprocessor),
        ("classifier", LogisticRegression(max_iter=1000, class_weight="balanced")),
    ])
    return pipeline


def main():
    conn = psycopg2.connect(**DB_CONFIG)
    df = load_data(conn)
    df = prepare_features(df)

    print(f"Total trials with defined phase: {len(df)}")

    # --- Training set: resolved trials only ---
    train_df = df[df["overall_status"].isin(RESOLVED_STATUSES)].copy()
    train_df["terminated"] = (train_df["overall_status"] != "COMPLETED").astype(int)

    print(f"Training set size: {len(train_df)} (terminated/withdrawn: {train_df['terminated'].sum()}, completed: {(train_df['terminated']==0).sum()})")

    feature_cols = ["phase", "sponsor_class", "mechanism_class",
                     "enrollment_count", "planned_duration_days", "publicly_traded"]

    X = train_df[feature_cols]
    y = train_df["terminated"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    pipeline = build_pipeline()
    pipeline.fit(X_train, y_train)

    y_pred = pipeline.predict(X_test)
    y_proba = pipeline.predict_proba(X_test)[:, 1]

    print("\n--- Model evaluation on held-out test set ---")
    print(classification_report(y_test, y_pred, target_names=["Not Terminated", "Terminated"]))
    print(f"ROC AUC: {roc_auc_score(y_test, y_proba):.3f}")

    # --- Score active trials ---
    active_df = df[df["overall_status"].isin(ACTIVE_STATUSES)].copy()
    print(f"\nScoring {len(active_df)} currently-active trials...")

    X_active = active_df[feature_cols]
    active_df["termination_risk_score"] = pipeline.predict_proba(X_active)[:, 1]

    # --- Write scores back to Postgres ---
    cur = conn.cursor()
    inserted = 0
    for _, row in active_df.iterrows():
        cur.execute("""
            INSERT INTO trial_risk_scores (nct_id, termination_risk_score, model_version)
            VALUES (%s, %s, %s)
            ON CONFLICT (nct_id) DO UPDATE
            SET termination_risk_score = EXCLUDED.termination_risk_score,
                model_version = EXCLUDED.model_version,
                scored_at = NOW()
        """, (row["nct_id"], float(row["termination_risk_score"]), "logreg_v1"))
        inserted += 1
    conn.commit()

    cur.close()
    conn.close()

    print(f"\nDone. Wrote {inserted} risk scores to trial_risk_scores.")

        # --- Feature importance (logistic regression coefficients) ---
    feature_names = pipeline.named_steps["preprocess"].get_feature_names_out()
    coefficients = pipeline.named_steps["classifier"].coef_[0]
    importance_df = pd.DataFrame({
        "feature": feature_names,
        "coefficient": coefficients
    }).sort_values("coefficient", key=abs, ascending=False)

    print("\n--- Top 10 features by influence on termination risk ---")
    print(importance_df.head(10).to_string(index=False))


if __name__ == "__main__":
    main()
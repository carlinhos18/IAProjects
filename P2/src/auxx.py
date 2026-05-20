import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import joblib
import os

from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score


# =========================
# CREATE OUTPUT FOLDER
# =========================

os.makedirs("../results/plots", exist_ok=True)


# =========================
# LOAD DATA
# =========================

X_train, X_test, y_train, y_test = joblib.load("../models/split_data.pkl")


# =========================
# GRIDS
# =========================

rf_grid = {
    "n_estimators": [100, 200],
    "max_depth": [8, 12],
}

gb_grid = {
    "n_estimators": [100, 200],
    "learning_rate": [0.03, 0.1],
}

lr_grid = {
    "C": [1.0, 5.0],
}


# =========================
# EVAL FUNCTION
# =========================

def evaluate_model(model):
    model.fit(X_train, y_train)
    preds = model.predict(X_test)

    return {
        "accuracy": accuracy_score(y_test, preds),
        "f1": f1_score(y_test, preds)
    }


# =========================
# RANDOM FOREST
# =========================

rf_results = []

for n in rf_grid["n_estimators"]:
    for d in rf_grid["max_depth"]:

        model = RandomForestClassifier(
            n_estimators=n,
            max_depth=d,
            class_weight="balanced",
            random_state=42
        )

        metrics = evaluate_model(model)

        rf_results.append({
            "model": "RandomForest",
            "n_estimators": n,
            "max_depth": d,
            **metrics
        })

rf_df = pd.DataFrame(rf_results)


# =========================
# GRADIENT BOOST
# =========================

gb_results = []

for n in gb_grid["n_estimators"]:
    for lr in gb_grid["learning_rate"]:

        model = GradientBoostingClassifier(
            n_estimators=n,
            learning_rate=lr,
            subsample=0.8,
            random_state=42
        )

        metrics = evaluate_model(model)

        gb_results.append({
            "model": "GradientBoost",
            "n_estimators": n,
            "learning_rate": lr,
            **metrics
        })

gb_df = pd.DataFrame(gb_results)


# =========================
# LOGISTIC REGRESSION
# =========================

lr_results = []

for c in lr_grid["C"]:

    model = LogisticRegression(
        C=c,
        max_iter=1500,
        solver="liblinear",
        class_weight="balanced"
    )

    metrics = evaluate_model(model)

    lr_results.append({
        "model": "LogisticRegression",
        "C": c,
        **metrics
    })

lr_df = pd.DataFrame(lr_results)


# =========================
# COMBINE RESULTS
# =========================

all_results = pd.concat([rf_df, gb_df, lr_df], ignore_index=True)

print("\nTOP MODELS:")
print(all_results.sort_values("f1", ascending=False))


# =========================
# BEST MODELS
# =========================

best_rf = rf_df.sort_values("f1", ascending=False).iloc[0]
best_gb = gb_df.sort_values("f1", ascending=False).iloc[0]
best_lr = lr_df.sort_values("f1", ascending=False).iloc[0]


final_comparison = pd.DataFrame([
    {"model": "RandomForest", "f1": best_rf["f1"], "accuracy": best_rf["accuracy"]},
    {"model": "GradientBoost", "f1": best_gb["f1"], "accuracy": best_gb["accuracy"]},
    {"model": "LogisticRegression", "f1": best_lr["f1"], "accuracy": best_lr["accuracy"]}
])


# =========================
# EXPORT 1: BEST MODEL COMPARISON
# =========================

plt.figure(figsize=(8,5))
plt.bar(final_comparison["model"], final_comparison["f1"])
plt.title("Best Model Comparison (F1 Score)")
plt.ylabel("F1 Score")
plt.tight_layout()
plt.savefig("../results/plots/best_models_comparison.png")
plt.close()


# =========================
# EXPORT 2: RANDOM FOREST PARAM EFFECT
# =========================

plt.figure(figsize=(8,5))

for n in rf_grid["n_estimators"]:
    subset = rf_df[rf_df["n_estimators"] == n]
    plt.plot(subset["max_depth"], subset["f1"], marker="o", label=f"n={n}")

plt.title("Random Forest: max_depth vs F1")
plt.xlabel("max_depth")
plt.ylabel("F1 Score")
plt.legend()
plt.tight_layout()
plt.savefig("../results/plots/rf_max_depth_vs_f1.png")
plt.close()


# =========================
# EXPORT 3: HEATMAP STYLE VIEW (RF)
# =========================

pivot = rf_df.pivot_table(
    values="f1",
    index="max_depth",
    columns="n_estimators"
)

plt.figure(figsize=(6,5))
plt.imshow(pivot, aspect="auto")
plt.title("Random Forest F1 Heatmap")
plt.xlabel("n_estimators")
plt.ylabel("max_depth")
plt.colorbar()
plt.tight_layout()
plt.savefig("../results/plots/rf_heatmap.png")
plt.close()


# =========================
# EXPORT 4: GB PARAM EFFECT
# =========================

plt.figure(figsize=(8,5))

for lr in gb_grid["learning_rate"]:
    subset = gb_df[gb_df["learning_rate"] == lr]
    plt.plot(subset["n_estimators"], subset["f1"], marker="o", label=f"lr={lr}")

plt.title("Gradient Boost: n_estimators vs F1")
plt.xlabel("n_estimators")
plt.ylabel("F1 Score")
plt.legend()
plt.tight_layout()
plt.savefig("../results/plots/gb_n_estimators_vs_f1.png")
plt.close()

plt.figure(figsize=(7,5))

plt.plot(lr_df["C"], lr_df["f1"], marker="o", color="blue")

plt.xscale("log")
plt.title("Logistic Regression - F1 vs C")
plt.xlabel("C")
plt.ylabel("F1 Score")
plt.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig("../results/plots/logistic_regression_f1_only.png")
plt.close()
# =========================
# DONE
# =========================

print("\n✅ ALL GRAPHS SAVED TO ../results/plots/")
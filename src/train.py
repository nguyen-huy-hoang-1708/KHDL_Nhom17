"""
BƯỚC 4 - MÔ HÌNH HOÁ & ĐÁNH GIÁ
Bài toán 1 (Hồi quy):  dự báo PM2.5 trung bình của ngày mai.
Bài toán 2 (Phân loại): dự báo ngày mai có vượt QCVN (PM2.5 > 50 µg/m³) hay không.

Chia dữ liệu THEO THỜI GIAN (không xáo trộn) để tránh rò rỉ thông tin tương lai:
  train: trước 2025-07-01   |   test: từ 2025-07-01
Siêu tham số chọn bằng TimeSeriesSplit (5 fold) trên tập train.
"""
import json
from pathlib import Path

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.ensemble import (HistGradientBoostingClassifier, HistGradientBoostingRegressor,
                              RandomForestClassifier, RandomForestRegressor)
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import (ConfusionMatrixDisplay, accuracy_score, f1_score, mean_absolute_error,
                             mean_squared_error, precision_score, r2_score, recall_score,
                             roc_auc_score, RocCurveDisplay)
from sklearn.model_selection import GridSearchCV, TimeSeriesSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
FIG, MODELS = ROOT / "figures", ROOT / "models"
SPLIT_DATE = "2025-07-01"
SEED = 42
sns.set_theme(style="whitegrid")
plt.rcParams["figure.dpi"] = 120

TARGETS = ["target_pm25_next", "target_polluted_next"]
DROP = TARGETS + ["season"]


def load():
    d = pd.read_csv(ROOT / "data/processed/daily_features.csv", parse_dates=["date"], index_col="date")
    features = [c for c in d.columns if c not in DROP]
    train, test = d[d.index < SPLIT_DATE], d[d.index >= SPLIT_DATE]
    return d, train, test, features


def tune(model, grid, X, y, scoring):
    if not grid:
        return model.fit(X, y), {}
    gs = GridSearchCV(model, grid, cv=TimeSeriesSplit(5), scoring=scoring, n_jobs=-1)
    gs.fit(X, y)
    return gs.best_estimator_, gs.best_params_


def regression(train, test, features):
    Xtr, ytr = train[features], train["target_pm25_next"]
    Xte, yte = test[features], test["target_pm25_next"]
    models = {
        "Ridge Regression": (make_pipeline(StandardScaler(), Ridge()),
                             {"ridge__alpha": [0.1, 1, 10, 100]}),
        "Random Forest": (RandomForestRegressor(random_state=SEED, n_jobs=-1),
                          {"n_estimators": [300], "max_depth": [6, 10, None], "min_samples_leaf": [1, 5]}),
        "Gradient Boosting": (HistGradientBoostingRegressor(random_state=SEED),
                              {"learning_rate": [0.03, 0.1], "max_depth": [3, 6], "max_iter": [200, 400]}),
    }
    rows, preds, fitted = [], {}, {}
    # Baseline "persistence": ngày mai = hôm nay
    preds["Baseline (ngày mai = hôm nay)"] = test["pm2_5"].values
    for name, (m, grid) in models.items():
        best, params = tune(m, grid, Xtr, ytr, "neg_mean_absolute_error")
        preds[name], fitted[name] = best.predict(Xte), best
        print(f"  {name}: {params}")
    for name, p in preds.items():
        rows.append({"Mô hình": name, "MAE": mean_absolute_error(yte, p),
                     "RMSE": np.sqrt(mean_squared_error(yte, p)), "R2": r2_score(yte, p)})
    res = pd.DataFrame(rows).round(3)

    best_name = res.iloc[1:].sort_values("MAE").iloc[0]["Mô hình"]
    best = fitted[best_name]
    joblib.dump({"model": best, "features": features}, MODELS / "regressor.joblib")

    # Biểu đồ dự báo vs thực tế
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(yte.index, yte.values, color="k", lw=1, label="Thực tế")
    ax.plot(yte.index, preds[best_name], color="#e67e22", lw=1.2, label=f"Dự báo ({best_name})")
    ax.axhline(50, ls="--", color="grey", lw=1)
    ax.set(title="Dự báo PM2.5 ngày hôm sau trên tập kiểm tra", ylabel="µg/m³")
    ax.legend()
    plt.tight_layout(); plt.savefig(FIG / "08_forecast_vs_actual.png"); plt.close()

    fig, ax = plt.subplots(figsize=(5, 5))
    ax.scatter(yte, preds[best_name], s=10, alpha=.6)
    lim = [0, max(yte.max(), preds[best_name].max()) * 1.05]
    ax.plot(lim, lim, "r--")
    ax.set(xlim=lim, ylim=lim, xlabel="Thực tế", ylabel="Dự báo", title=f"{best_name}: thực tế vs dự báo")
    plt.tight_layout(); plt.savefig(FIG / "09_scatter_pred.png"); plt.close()

    # Độ quan trọng đặc trưng (permutation importance trên tập test)
    pi = permutation_importance(best, Xte, yte, n_repeats=10, random_state=SEED,
                                scoring="neg_mean_absolute_error")
    imp = pd.Series(pi.importances_mean, index=features).sort_values(ascending=False).head(15)
    fig, ax = plt.subplots(figsize=(7, 5))
    imp[::-1].plot.barh(ax=ax, color="#16a085")
    ax.set(title=f"Top 15 đặc trưng quan trọng ({best_name})", xlabel="Mức tăng MAE khi xáo trộn")
    plt.tight_layout(); plt.savefig(FIG / "10_feature_importance.png"); plt.close()
    return res, best_name, imp


def classification(train, test, features):
    Xtr, ytr = train[features], train["target_polluted_next"].astype(int)
    Xte, yte = test[features], test["target_polluted_next"].astype(int)
    models = {
        "Logistic Regression": (make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, class_weight="balanced")),
                                {"logisticregression__C": [0.01, 0.1, 1, 10]}),
        "Random Forest": (RandomForestClassifier(random_state=SEED, n_jobs=-1, class_weight="balanced"),
                          {"n_estimators": [300], "max_depth": [6, 10, None], "min_samples_leaf": [1, 5]}),
        "Gradient Boosting": (HistGradientBoostingClassifier(random_state=SEED, class_weight="balanced"),
                              {"learning_rate": [0.03, 0.1], "max_depth": [3, 6], "max_iter": [200, 400]}),
    }
    rows, fitted = [], {}
    base = (test["pm2_5"] > 50).astype(int)
    rows.append({"Mô hình": "Baseline (ngày mai = hôm nay)", "Accuracy": accuracy_score(yte, base),
                 "Precision": precision_score(yte, base), "Recall": recall_score(yte, base),
                 "F1": f1_score(yte, base), "ROC-AUC": np.nan})
    for name, (m, grid) in models.items():
        best, params = tune(m, grid, Xtr, ytr, "f1")
        fitted[name] = best
        p, prob = best.predict(Xte), best.predict_proba(Xte)[:, 1]
        print(f"  {name}: {params}")
        rows.append({"Mô hình": name, "Accuracy": accuracy_score(yte, p), "Precision": precision_score(yte, p),
                     "Recall": recall_score(yte, p), "F1": f1_score(yte, p), "ROC-AUC": roc_auc_score(yte, prob)})
    res = pd.DataFrame(rows).round(3)
    best_name = res.iloc[1:].sort_values("F1").iloc[-1]["Mô hình"]
    joblib.dump({"model": fitted[best_name], "features": features}, MODELS / "classifier.joblib")

    fig, ax = plt.subplots(1, 2, figsize=(11, 4.5))
    ConfusionMatrixDisplay.from_estimator(fitted[best_name], Xte, yte, ax=ax[0], cmap="Blues",
                                          display_labels=["Đạt chuẩn", "Ô nhiễm"])
    ax[0].set_title(f"Ma trận nhầm lẫn – {best_name}")
    for name, m in fitted.items():
        RocCurveDisplay.from_estimator(m, Xte, yte, ax=ax[1], name=name)
    ax[1].plot([0, 1], [0, 1], "k--", lw=.8)
    ax[1].set_title("Đường cong ROC")
    plt.tight_layout(); plt.savefig(FIG / "11_classification.png"); plt.close()
    return res, best_name


def main():
    MODELS.mkdir(exist_ok=True)
    d, train, test, features = load()
    print(f"Train: {len(train)} ngày | Test: {len(test)} ngày | {len(features)} đặc trưng")
    print("Hồi quy...")
    reg, reg_best, imp = regression(train, test, features)
    print(reg.to_string(index=False))
    print("Phân loại...")
    clf, clf_best = classification(train, test, features)
    print(clf.to_string(index=False))
    reg.to_csv(ROOT / "report/results_regression.csv", index=False)
    clf.to_csv(ROOT / "report/results_classification.csv", index=False)
    json.dump({"n_train": len(train), "n_test": len(test), "split_date": SPLIT_DATE,
               "features": features, "best_regressor": reg_best, "best_classifier": clf_best,
               "top_features": imp.round(3).to_dict()},
              open(ROOT / "report/results_summary.json", "w"), ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()

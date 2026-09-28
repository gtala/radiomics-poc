"""
Entrenamiento y validación del modelo benigno / maligno (docs/plan-modelo.md, Etapa 4).

- Validación cruzada anidada agrupada por paciente: 5 folds externos (evaluación)
  y 5 internos (hiperparámetros). Cada nódulo se evalúa una vez, con un modelo
  que nunca vio a su paciente.
- Selección de features dentro del pipeline (sin fuga de información).
- Comparaciones: solo diámetro máximo 3D, y radiómica sin features de forma.

Salida:
    models/modelo_nodulo.joblib
    reports/validacion.md, reports/roc.png, reports/features.png

Uso:
    python -m scripts.train
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import joblib
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import radiomics  # noqa: E402
import sklearn  # noqa: E402
from sklearn.base import clone  # noqa: E402
from sklearn.calibration import calibration_curve  # noqa: E402
from sklearn.ensemble import RandomForestClassifier  # noqa: E402
from sklearn.feature_selection import SelectKBest, VarianceThreshold, f_classif  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402
from sklearn.metrics import brier_score_loss, confusion_matrix, roc_auc_score, roc_curve  # noqa: E402
from sklearn.model_selection import GridSearchCV, StratifiedGroupKFold  # noqa: E402
from sklearn.pipeline import Pipeline  # noqa: E402
from sklearn.preprocessing import StandardScaler  # noqa: E402

from app.nodule_model import MODEL_PATH, CorrelationFilter  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FEATURES = ROOT / "outputs" / "features.parquet"
REPORTS = ROOT / "reports"
SEED = 42
META = [
    "patient_id", "series_uid", "nodule_idx", "label", "malignancy_median",
    "n_readers", "diameter_mm", "slice_thickness", "error",
]
SIZE_FEATURE = "original_shape_Maximum3DDiameter"
INTERPRETABLE_MARGIN = 0.01
KEY_DESCRIPTORS = [
    "original_shape_Maximum3DDiameter",
    "original_shape_MeshVolume",
    "original_shape_Sphericity",
    "original_shape_Elongation",
    "original_shape_SurfaceVolumeRatio",
    "original_firstorder_Mean",
    "original_firstorder_Entropy",
    "original_glcm_Idm",
]


def reference_stats(X: pd.DataFrame, labels: pd.Series, features: list[str]) -> dict:
    """Mediana y rango intercuartil por clase, para explicar cada caso."""
    stats = {}
    for f in dict.fromkeys(features):
        stats[f] = {
            label: {
                "mediana": float(X.loc[labels == label, f].median()),
                "p25": float(X.loc[labels == label, f].quantile(0.25)),
                "p75": float(X.loc[labels == label, f].quantile(0.75)),
            }
            for label in ("benigno", "maligno")
        }
    return stats


def candidates() -> dict[str, tuple[Pipeline, dict]]:
    base = [
        ("var", VarianceThreshold()),
        ("corr", CorrelationFilter(0.9)),
        ("scale", StandardScaler()),
    ]
    lasso = Pipeline(base + [(
        "clf",
        LogisticRegression(
            penalty="l1", solver="liblinear", class_weight="balanced",
            max_iter=5000, random_state=SEED,
        ),
    )])
    forest = Pipeline(base + [
        ("kbest", SelectKBest(f_classif)),
        ("clf", RandomForestClassifier(
            n_estimators=500, class_weight="balanced", random_state=SEED, n_jobs=-1,
        )),
    ])
    return {
        "Regresión logística (LASSO)": (lasso, {"clf__C": [0.01, 0.03, 0.1, 0.3, 1.0, 3.0]}),
        "Random forest": (forest, {"kbest__k": [10, 20, 40], "clf__max_depth": [3, 5, None]}),
    }


def size_baseline() -> Pipeline:
    return Pipeline([
        ("scale", StandardScaler()),
        ("clf", LogisticRegression(class_weight="balanced", random_state=SEED)),
    ])


def metrics(y, prob, threshold: float = 0.5) -> dict[str, float]:
    tn, fp, fn, tp = confusion_matrix(y, prob >= threshold).ravel()
    return {
        "auc": roc_auc_score(y, prob),
        "sensibilidad": tp / (tp + fn),
        "especificidad": tn / (tn + fp),
        "brier": brier_score_loss(y, prob),
    }


def nested_oof(pipe, grid, X, y, groups) -> tuple[np.ndarray, list[float]]:
    """Probabilidades fuera de fold con validación cruzada anidada por paciente."""
    outer = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=SEED)
    prob = np.zeros(len(y))
    fold_aucs = []
    for tr, te in outer.split(X, y, groups):
        if grid:
            inner = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=SEED)
            model = GridSearchCV(pipe, grid, scoring="roc_auc", cv=inner, n_jobs=-1)
            model.fit(X.iloc[tr], y[tr], groups=groups[tr])
        else:
            model = clone(pipe).fit(X.iloc[tr], y[tr])
        prob[te] = model.predict_proba(X.iloc[te])[:, 1]
        fold_aucs.append(roc_auc_score(y[te], prob[te]))
    return prob, fold_aucs


def main() -> None:
    df = pd.read_parquet(FEATURES)
    df = df[df["error"] == ""].reset_index(drop=True)
    y = (df["label"] == "maligno").astype(int).to_numpy()
    groups = df["patient_id"].to_numpy()
    X = df.drop(columns=META)
    feature_names = list(X.columns)
    no_shape = [c for c in feature_names if "_shape_" not in c]
    print(f"{len(y)} nódulos / {len(set(groups))} pacientes · validación cruzada anidada 5x5 por paciente")

    results = {}
    for name, (pipe, grid) in candidates().items():
        prob, folds = nested_oof(pipe, grid, X, y, groups)
        results[name] = {"pipe": pipe, "grid": grid, "prob": prob, "folds": folds,
                         "test": metrics(y, prob)}

    lasso_pipe, lasso_grid = candidates()["Regresión logística (LASSO)"]
    prob, folds = nested_oof(lasso_pipe, lasso_grid, X[no_shape], y, groups)
    comparisons = {"Sin forma ni tamaño (textura + intensidad, LASSO)": {"prob": prob, "folds": folds,
                                                                        "test": metrics(y, prob)}}
    prob, folds = nested_oof(size_baseline(), None, X[[SIZE_FEATURE]], y, groups)
    comparisons["Solo diámetro (base)"] = {"prob": prob, "folds": folds, "test": metrics(y, prob)}

    for name, r in {**results, **comparisons}.items():
        print(f"{name}: AUC={r['test']['auc']:.3f} (folds {np.mean(r['folds']):.3f} ± {np.std(r['folds']):.3f}) · "
              f"sens={r['test']['sensibilidad']:.2f} esp={r['test']['especificidad']:.2f} brier={r['test']['brier']:.3f}")

    interpretable = "Regresión logística (LASSO)"
    top_auc = max(r["test"]["auc"] for r in results.values())
    best_name = (
        interpretable
        if results[interpretable]["test"]["auc"] >= top_auc - INTERPRETABLE_MARGIN
        else max(results, key=lambda n: results[n]["test"]["auc"])
    )
    best = results[best_name]
    search = GridSearchCV(
        best["pipe"], best["grid"], scoring="roc_auc",
        cv=StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=SEED), n_jobs=-1,
    ).fit(X, y, groups=groups)
    final = search.best_estimator_
    base_test = comparisons["Solo diámetro (base)"]["test"]

    selected = list(final[:-1].get_feature_names_out(feature_names))
    clf = final[-1]
    if hasattr(clf, "coef_"):
        weights = pd.Series(clf.coef_[0], index=selected)
        weights = weights[weights != 0]
    else:
        weights = pd.Series(clf.feature_importances_, index=selected)
    weights = weights.reindex(weights.abs().sort_values(ascending=False).index)

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    bundle = {
        "pipeline": final,
        "model_name": best_name,
        "feature_names": feature_names,
        "label_definition": "LIDC-IDRI: mediana de malignidad 4-5 = maligno, 1-2 = benigno (3 excluido)",
        "metrics": {
            **{f"{k}_cv": float(v) for k, v in best["test"].items()},
            "auc_base_diametro": float(base_test["auc"]),
            "hiperparametros": search.best_params_,
        },
        "reference_stats": reference_stats(X, df["label"], list(weights.index) + KEY_DESCRIPTORS),
        "key_descriptors": KEY_DESCRIPTORS,
        "n_train_nodules": int(len(y)),
        "n_train_patients": int(len(set(groups))),
        "pyradiomics_version": radiomics.__version__,
        "sklearn_version": sklearn.__version__,
        "trained_at": dt.datetime.now().isoformat(timespec="seconds"),
    }
    joblib.dump(bundle, MODEL_PATH)

    write_report(results, comparisons, y, best_name, weights, len(y), len(set(groups)))
    print(f"\nModelo elegido: {best_name} · guardado en {MODEL_PATH.relative_to(ROOT)}")
    print(f"Reporte: {(REPORTS / 'validacion.md').relative_to(ROOT)}")


def write_report(results, comparisons, y, best_name, weights, n, n_pat):
    REPORTS.mkdir(parents=True, exist_ok=True)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5))
    for name, r in {**results, **comparisons}.items():
        fpr, tpr, _ = roc_curve(y, r["prob"])
        style = "--" if name in comparisons else "-"
        ax1.plot(fpr, tpr, style, label=f"{name} (AUC {r['test']['auc']:.2f})")
    ax1.plot([0, 1], [0, 1], ":", color="lightgray")
    ax1.set(xlabel="1 − especificidad", ylabel="Sensibilidad",
            title="Curva ROC (validación cruzada anidada)")
    ax1.legend(loc="lower right", fontsize=7)
    frac, mean = calibration_curve(y, results[best_name]["prob"], n_bins=5, strategy="quantile")
    ax2.plot(mean, frac, "o-", label=best_name)
    ax2.plot([0, 1], [0, 1], ":", color="lightgray")
    ax2.set(xlabel="Probabilidad predicha", ylabel="Proporción observada de malignos", title="Calibración")
    ax2.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(REPORTS / "roc.png", dpi=130)
    plt.close(fig)

    top = weights.head(15)[::-1]
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.barh([t.replace("original_", "").replace("wavelet-", "w-") for t in top.index], top.values,
            color=["#c0392b" if v > 0 else "#2e86c1" for v in top.values])
    ax.set(title="Features principales del modelo", xlabel="Peso (rojo: aumenta malignidad)")
    fig.tight_layout()
    fig.savefig(REPORTS / "features.png", dpi=130)
    plt.close(fig)

    rows = [
        f"| {name} | {r['test']['auc']:.3f} | {np.mean(r['folds']):.3f} ± {np.std(r['folds']):.3f} "
        f"| {r['test']['sensibilidad']:.2f} | {r['test']['especificidad']:.2f} | {r['test']['brier']:.3f} |"
        for name, r in {**results, **comparisons}.items()
    ]
    feats = "\n".join(f"| `{k}` | {v:+.3f} |" for k, v in weights.head(15).items())
    (REPORTS / "validacion.md").write_text(f"""# Validación — modelo benigno / maligno

Generado: {dt.datetime.now():%Y-%m-%d %H:%M}

## Datos

- LIDC-IDRI: **{n} nódulos** de **{n_pat} pacientes**.
- Etiqueta: mediana del puntaje de malignidad de los radiólogos (4–5 maligno, 1–2 benigno, 3 excluido).
- Validación cruzada anidada agrupada por paciente (5 folds externos × 5 internos): cada nódulo
  se evalúa una vez con un modelo que nunca vio a su paciente.

## Resultados

| Modelo | AUC global | AUC por fold (media ± DE) | Sensibilidad | Especificidad | Brier |
|---|---|---|---|---|---|
{chr(10).join(rows)}

Umbral de 0,5 para sensibilidad y especificidad. Brier: error de las probabilidades (menor es mejor).

![ROC y calibración](roc.png)

## Modelo elegido: {best_name}

Se prefiere la regresión logística si su AUC está a menos de {INTERPRETABLE_MARGIN} del mejor
modelo (permite explicar el aporte de cada feature por caso). Reentrenado con todos los nódulos.
Features usadas: **{len(weights)}** de 1.218.

| Feature | Peso |
|---|---|
{feats}

![Features principales](features.png)

## Limitaciones

- La etiqueta es opinión radiológica, no anatomía patológica.
- En LIDC-IDRI el puntaje de malignidad está muy asociado al tamaño; por eso se compara contra un modelo que usa solo el diámetro.
- Conjunto chico ({n} nódulos): las métricas tienen incertidumbre amplia.
- Datos de un único dataset público: requiere validación externa antes de cualquier uso con datos propios.
- Uso académico: no es una herramienta diagnóstica.
""")


if __name__ == "__main__":
    main()

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.tree import DecisionTreeRegressor, plot_tree, export_text
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error

INPUT_FILE = "../data/features.csv"
OUTPUT_DIR = "../outputs/decision_tree"
os.makedirs(OUTPUT_DIR, exist_ok=True)

TARGET = "LSOA GVA Estimates (millions)"
AREA_NAME_COL = "LSOA21NM"
RANDOM_STATE = 123

MODEL_SCOPE = "all"

# Load data
df = pd.read_csv(INPUT_FILE)
print("Original data shape:", df.shape)

df = df.dropna(subset=[TARGET]).copy()
df["log_gva"] = np.log1p(df[TARGET])

df["area_group"] = np.where(
    df[AREA_NAME_COL].str.contains("Swindon", case=False, na=False),
    "Swindon",
    "Non-Swindon"
)

if MODEL_SCOPE == "swindon":
    df_model = df[df["area_group"] == "Swindon"].copy()
elif MODEL_SCOPE == "non_swindon":
    df_model = df[df["area_group"] == "Non-Swindon"].copy()
else:
    df_model = df.copy()

print("Model scope:", MODEL_SCOPE)
print("Model data shape:", df_model.shape)

# Feature selection
num_cols = df_model.select_dtypes(include=np.number).columns.tolist()
drop_cols = [
    TARGET,
    "log_gva",
    "cluster",
    "non_swindon_cluster",
    "PC1",
    "PC2"
]
feature_cols = [col for col in num_cols if col not in drop_cols]
X = df_model[feature_cols].copy()
y = df_model["log_gva"].copy()
all_missing_cols = X.columns[X.isnull().all()].tolist()
X = X.drop(columns=all_missing_cols)
X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.25,
    random_state=RANDOM_STATE
)

# Decision tree with grid search over depth params
pipeline = Pipeline([
    ("imputer", SimpleImputer(strategy="median")),
    ("tree", DecisionTreeRegressor(random_state=RANDOM_STATE))
])
param_grid = {
    "tree__max_depth": [2, 3, 4, 5],
    "tree__min_samples_leaf": [10, 20, 30, 50],
    "tree__min_samples_split": [20, 40, 60]
}
grid = GridSearchCV(
    pipeline,
    param_grid=param_grid,
    cv=5,
    scoring="r2",
    n_jobs=-1
)
grid.fit(X_train, y_train)
best_model = grid.best_estimator_
tree_model = best_model.named_steps["tree"]
print("\nBest parameters:")
print(grid.best_params_)

# Evaluate on log scale and back on the original GVA scale
y_pred_log = best_model.predict(X_test)
r2 = r2_score(y_test, y_pred_log)
rmse_log = np.sqrt(mean_squared_error(y_test, y_pred_log))
mae_log = mean_absolute_error(y_test, y_pred_log)
y_test_gva = np.expm1(y_test)
y_pred_gva = np.expm1(y_pred_log)
mae_gva = mean_absolute_error(y_test_gva, y_pred_gva)
metrics = pd.DataFrame({
    "Metric": ["R2_log", "RMSE_log", "MAE_log", "MAE_GVA_millions"],
    "Value": [r2, rmse_log, mae_log, mae_gva]
})
print("\nModel performance:")
print(metrics)
metrics.to_csv(os.path.join(OUTPUT_DIR, "decision_tree_metrics.csv"), index=False)

# Feature importance
importance_df = pd.DataFrame({
    "Feature": X.columns,
    "Importance": tree_model.feature_importances_
}).sort_values("Importance", ascending=False)

importance_df.to_csv(
    os.path.join(OUTPUT_DIR, "decision_tree_feature_importance.csv"),
    index=False
)
print("\nTop 15 important features:")
print(importance_df.head(15))

plt.figure(figsize=(10, 6))
importance_df.head(15).sort_values("Importance").plot(
    kind="barh",
    x="Feature",
    y="Importance",
    legend=False
)
plt.title("Decision Tree Feature Importance")
plt.xlabel("Importance")
plt.tight_layout()
plt.savefig(
    os.path.join(OUTPUT_DIR, "decision_tree_feature_importance.png"),
    dpi=150,
    bbox_inches="tight"
)
plt.close()

# Tree plot
plt.figure(figsize=(24, 12))
plot_tree(
    tree_model,
    feature_names=X.columns,
    filled=True,
    rounded=True,
    fontsize=8,
    max_depth=3
)
plt.title("Decision Tree for log(GVA)")
plt.tight_layout()
plt.savefig(
    os.path.join(OUTPUT_DIR, "decision_tree_plot.png"),
    dpi=200,
    bbox_inches="tight"
)
plt.close()

# Text rules export
tree_rules = export_text(
    tree_model,
    feature_names=list(X.columns),
    max_depth=4
)
with open(os.path.join(OUTPUT_DIR, "decision_tree_rules.txt"), "w", encoding="utf-8") as f:
    f.write(tree_rules)
print("\nDecision tree rules:")
print(tree_rules)

# Predictions export
predictions = df_model.loc[X_test.index, [AREA_NAME_COL, "area_group", TARGET]].copy()
predictions["actual_log_gva"] = y_test
predictions["predicted_log_gva"] = y_pred_log
predictions["predicted_gva"] = y_pred_gva
predictions.to_csv(os.path.join(OUTPUT_DIR, "decision_tree_predictions.csv"), index=False)
print("\nDone.")
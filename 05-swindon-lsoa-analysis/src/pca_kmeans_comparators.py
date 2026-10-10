import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.impute import SimpleImputer
from sklearn.cluster import KMeans

INPUT_FILE = "../data/features.csv"
OUTPUT_DIR = "../outputs/pca_kmeans_comparators"
FIGURE_DIR = os.path.join(OUTPUT_DIR, "figures")

TARGET = "LSOA GVA Estimates (millions)"
AREA_NAME_COL = "LSOA21NM"

N_CLUSTERS = 4
RANDOM_STATE = 123

INCLUDE_TARGET_IN_CLUSTERING = False

sns.set_theme(style="whitegrid")
pd.set_option("display.max_columns", None)

os.makedirs(FIGURE_DIR, exist_ok=True)

def savefig(name: str) -> None:
    """Save current matplotlib figure and close it."""
    plt.tight_layout()
    plt.savefig(os.path.join(FIGURE_DIR, name), dpi=150, bbox_inches="tight")
    plt.close()

# Load data
df = pd.read_csv(INPUT_FILE)

if AREA_NAME_COL not in df.columns:
    raise ValueError(f"Column '{AREA_NAME_COL}' was not found in the dataset.")
if TARGET not in df.columns:
    raise ValueError(f"Target column '{TARGET}' was not found in the dataset.")

# Keep only Non-Swindon rows
non_swindon_df = df[
    ~df[AREA_NAME_COL].str.contains("Swindon", case=False, na=False)
].copy()
if non_swindon_df.empty:
    raise ValueError("No Non-Swindon rows were found. Please check the LSOA name column.")

# Pick numeric features, dropping cluster columns from a previous run
num_cols = non_swindon_df.select_dtypes(include=np.number).columns.tolist()
cols_to_drop = [col for col in ["cluster", "non_swindon_cluster"] if col in num_cols]
if not INCLUDE_TARGET_IN_CLUSTERING:
    target_like_cols = [
        col for col in num_cols
        if ("GVA" in col) or (col.lower() in ["log_gva"])
    ]
    cols_to_drop.extend(target_like_cols)
cols_to_drop = list(dict.fromkeys(cols_to_drop))
feature_cols = [col for col in num_cols if col not in cols_to_drop]

# Preprocessing, drop empty columns, impute, scale
X = non_swindon_df[feature_cols].copy()
all_missing_cols = X.columns[X.isnull().all()].tolist()
X = X.drop(columns=all_missing_cols)
imputer = SimpleImputer(strategy="median")
X_imputed = pd.DataFrame(
    imputer.fit_transform(X),
    columns=X.columns,
    index=X.index
)
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X_imputed)

# PCA
pca = PCA(n_components=2, random_state=RANDOM_STATE)
X_pca = pca.fit_transform(X_scaled)
pca_df = pd.DataFrame(X_pca, columns=["PC1", "PC2"], index=non_swindon_df.index)
non_swindon_df["PC1"] = pca_df["PC1"]
non_swindon_df["PC2"] = pca_df["PC2"]
explained_variance = pd.DataFrame({
    "Component": ["PC1", "PC2"],
    "Explained Variance Ratio": pca.explained_variance_ratio_
})

explained_variance.to_csv(
    os.path.join(OUTPUT_DIR, "non_swindon_pca_explained_variance.csv"),
    index=False
)

pca_loadings = pd.DataFrame(
    pca.components_.T,
    index=X_imputed.columns,
    columns=["PC1_loading", "PC2_loading"]
)
pca_loadings.to_csv(os.path.join(OUTPUT_DIR, "non_swindon_pca_loadings.csv"))

plt.figure(figsize=(8, 6))
plt.scatter(non_swindon_df["PC1"], non_swindon_df["PC2"], alpha=0.6)
plt.title("Non-Swindon PCA Projection")
plt.xlabel("PC1")
plt.ylabel("PC2")
savefig("non_swindon_pca_projection.png")

# Elbow method to sanity-check cluster count
sse = []
for k in range(2, 11):
    km = KMeans(n_clusters=k, random_state=RANDOM_STATE, n_init=10)
    km.fit(X_scaled)
    sse.append(km.inertia_)
elbow_df = pd.DataFrame({"k": list(range(2, 11)), "SSE": sse})
elbow_df.to_csv(os.path.join(OUTPUT_DIR, "non_swindon_elbow_method.csv"), index=False)
plt.figure(figsize=(7, 5))
plt.plot(elbow_df["k"], elbow_df["SSE"], marker="o")
plt.xlabel("Number of clusters")
plt.ylabel("SSE")
plt.title("Non-Swindon Elbow Method")
savefig("non_swindon_elbow_method.png")

# K-means clustering
kmeans = KMeans(n_clusters=N_CLUSTERS, random_state=RANDOM_STATE, n_init=10)
clusters = kmeans.fit_predict(X_scaled)
non_swindon_df["non_swindon_cluster"] = clusters

plt.figure(figsize=(8, 6))
sns.scatterplot(
    data=non_swindon_df,
    x="PC1",
    y="PC2",
    hue="non_swindon_cluster",
    palette="tab10",
    alpha=0.8
)
plt.title("Non-Swindon Economic Clusters in PCA Space")
plt.xlabel("PC1")
plt.ylabel("PC2")
plt.legend(title="Cluster")
savefig("non_swindon_clusters_pca.png")

# Cluster profiling
profile_cols = [
    TARGET,
    "total_employees",
    "employment_rate_per_pop",
    "VOA_total_RV_2023",
    "total_enterprises_2025_msoa",
    "enterprises_per_1k_residents_2025",
    "share_enterprises_kibs_2025_msoa",
    "share_enterprises_creative_2025_msoa",
    "share_enterprises_industrial_2025_msoa",
    "share_enterprises_green_aligned_2025_msoa",
    "IMD_decile",
    "Average download speed (Mbit/s)",
    "bus_stop_count",
    "bus_stop_density"
]
profile_cols = [col for col in profile_cols if col in non_swindon_df.columns]
cluster_profile = (
    non_swindon_df
    .groupby("non_swindon_cluster")[profile_cols]
    .mean()
    .round(3)
)
cluster_profile.to_csv(os.path.join(OUTPUT_DIR, "non_swindon_cluster_profile.csv"))
cluster_summary = (
    non_swindon_df
    .groupby("non_swindon_cluster")[TARGET]
    .agg(["count", "mean", "median", "min", "max"])
    .round(3)
)
cluster_summary.to_csv(os.path.join(OUTPUT_DIR, "non_swindon_cluster_summary.csv"))
plt.figure(figsize=(14, 7))
sns.heatmap(cluster_profile, annot=True, cmap="RdYlGn", fmt=".2f")
plt.title("Non-Swindon Cluster Profile")
savefig("non_swindon_cluster_profile_heatmap.png")

# Export
output_data_path = os.path.join(OUTPUT_DIR, "non_swindon_features_clustered.csv")
non_swindon_df.to_csv(output_data_path, index=False)
print("\nDone.")
print(f"All outputs saved to: {OUTPUT_DIR}")
print(f"Clustered data saved to: {output_data_path}")

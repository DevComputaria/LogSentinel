import numpy as np
from sklearn.cluster import KMeans, DBSCAN
from sklearn.preprocessing import StandardScaler

def cluster_kmeans(embeddings, n_clusters=None, max_clusters=15):
    n = len(embeddings)
    if n == 0:
        return np.array([]), 0
    if n_clusters is None:
        n_clusters = min(max(2, int(np.sqrt(n / 2))), max_clusters, n)
    n_clusters = max(2, min(n_clusters, n - 1))
    model = KMeans(n_clusters=n_clusters, random_state=42, n_init='auto')
    labels = model.fit_predict(embeddings)
    return labels, n_clusters

def cluster_dbscan(embeddings, eps=0.3, min_samples=2):
    if len(embeddings) == 0:
        return np.array([])
    model = DBSCAN(eps=eps, min_samples=min_samples, metric='cosine')
    labels = model.fit_predict(embeddings)
    return labels

def cluster_hierarchical(embeddings, n_clusters=None, max_clusters=15):
    from sklearn.cluster import AgglomerativeClustering
    n = len(embeddings)
    if n == 0:
        return np.array([])
    if n_clusters is None:
        n_clusters = min(max(2, int(np.sqrt(n / 2))), max_clusters, n)
    n_clusters = max(2, min(n_clusters, n - 1))
    model = AgglomerativeClustering(n_clusters=n_clusters, metric='cosine', linkage='average')
    labels = model.fit_predict(embeddings)
    return labels

def compute_cluster_summary(embeddings, labels, template_texts):
    unique_labels = set(labels)
    summaries = []
    for label in sorted(unique_labels):
        mask = np.array(labels) == label
        count = int(mask.sum())
        if count == 0:
            continue
        member_texts = [template_texts[i] for i in np.where(mask)[0]]
        centroid = embeddings[mask].mean(axis=0)
        summaries.append({
            'cluster_id': int(label),
            'size': count,
            'percentage': count / len(labels) * 100,
            'templates': member_texts,
            'sample': member_texts[0] if member_texts else '',
        })
    return sorted(summaries, key=lambda x: x['size'], reverse=True)

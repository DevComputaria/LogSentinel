import numpy as np
from sklearn.preprocessing import normalize
from sklearn.feature_extraction.text import TfidfVectorizer

try:
    from sentence_transformers import SentenceTransformer
    _HAS_SENTENCE = True
except ImportError:
    _HAS_SENTENCE = False

_MODEL = None

def _get_model():
    global _MODEL
    if not _HAS_SENTENCE:
        raise ImportError('sentence-transformers not installed')
    if _MODEL is None:
        _MODEL = SentenceTransformer('all-MiniLM-L6-v2')
    return _MODEL

def compute_embeddings(texts, show_progress=True):
    if _HAS_SENTENCE:
        model = _get_model()
        embeddings = model.encode(
            texts,
            show_progress_bar=show_progress,
            convert_to_numpy=True,
            normalize_embeddings=True
        )
    else:
        vectorizer = TfidfVectorizer(
            max_features=500, analyzer='word',
            token_pattern=r'(?u)\b\w+\b', stop_words='english'
        )
        tfidf = vectorizer.fit_transform(texts)
        embeddings = normalize(tfidf.toarray())
    return embeddings

def cosine_similarity_matrix(embeddings):
    return np.dot(embeddings, embeddings.T)

def semantic_distance_to_centroid(embeddings, labels):
    unique_labels = set(l for l in labels if l >= 0)
    distances = np.full(len(embeddings), np.nan)
    for label in unique_labels:
        mask = np.array(labels) == label
        if mask.sum() == 0:
            continue
        centroid = embeddings[mask].mean(axis=0)
        centroid = normalize(centroid.reshape(1, -1))[0]
        cluster_embeds = embeddings[mask]
        dists = 1 - np.dot(cluster_embeds, centroid)
        distances[mask] = dists
    return distances

def find_semantic_outliers(embeddings, threshold=0.5):
    centroid = embeddings.mean(axis=0)
    centroid = normalize(centroid.reshape(1, -1))[0]
    dists = 1 - np.dot(embeddings, centroid)
    return dists > threshold, dists

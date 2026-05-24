import numpy as np
from .base import Detector
from ..models.result import SemanticAnomaly
from ..extractors.embeddings import compute_embeddings, find_semantic_outliers


class SemanticAnomalyDetector(Detector):
    def __init__(self, threshold=0.4):
        self.threshold = threshold

    def detect(self, df, **kwargs):
        template_texts = kwargs.get('template_texts', [])
        if not template_texts:
            return []
        try:
            embeddings = compute_embeddings(template_texts)
        except Exception:
            return []
        is_outlier, distances = find_semantic_outliers(embeddings, threshold=0.3)
        results = []
        for i, (dist, text) in enumerate(zip(distances, template_texts)):
            if dist > self.threshold and not np.isnan(dist):
                results.append(SemanticAnomaly(
                    template_idx=i,
                    template=text,
                    distance=float(dist),
                    severity='high' if dist > self.threshold * 1.5 else 'medium',
                ))
        return sorted(results, key=lambda x: x.distance, reverse=True)

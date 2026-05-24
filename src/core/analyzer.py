import pandas as pd
from pathlib import Path
from ..models.result import AnalysisResult, Summary, TemplateStats, ClusterSummary
from ..parsers.factory import ParserFactory
from ..extractors.templates import extract_templates_drain
from ..extractors.temporal import extract_temporal_features, compute_template_features_df, compute_time_series
from ..extractors.embeddings import compute_embeddings
from ..detectors.temporal import TemporalAnomalyDetector
from ..detectors.burst import BurstDetector
from ..detectors.semantic import SemanticAnomalyDetector
from ..clustering import cluster_kmeans, cluster_dbscan, compute_cluster_summary
from ..distribution import level_distribution, pattern_summary


class LogAnalyzer:
    def __init__(self, parser=None):
        self.parser = parser
        self.temporal_detector = TemporalAnomalyDetector()
        self.burst_detector = BurstDetector()
        self.semantic_detector = SemanticAnomalyDetector()
        self.template_map = {}

    def analyze(self, path, no_embeddings=False):
        path = Path(path)
        source = path.name

        parser = self.parser or ParserFactory.create(path)
        df = parser.parse(str(path))
        print(f'  -> {len(df)} lines parsed ({df.source.iloc[0] if not df.empty else "?"} format)')

        event_ids, templates, _ = extract_templates_drain(
            df['message_raw'].tolist(), depth=3, sim_threshold=0.75
        )
        df['event_id'] = event_ids
        df['template'] = [t if t else '' for t in templates]
        print(f'  -> {df["event_id"].nunique()} unique templates')

        df = extract_temporal_features(df)
        tstats = compute_template_features_df(df)
        template_stats = tstats.to_dict('records') if not tstats.empty else []

        time_series = compute_time_series(df)
        if not time_series.empty:
            time_series = time_series.reset_index()

        unique_templates = df[['event_id', 'template']].drop_duplicates()
        unique_templates = unique_templates[unique_templates['template'] != '']
        template_texts = unique_templates['template'].tolist()

        embeddings = None
        if not no_embeddings and template_texts:
            try:
                embeddings = compute_embeddings(template_texts)
                print(f'  -> embeddings computed: {embeddings.shape}')
            except Exception as e:
                print(f'  -> embeddings unavailable: {e}')

        cluster_summaries = []
        if embeddings is not None and len(embeddings) > 1:
            labels_kmeans, _ = cluster_kmeans(embeddings)
            summaries = compute_cluster_summary(embeddings, labels_kmeans, template_texts)
            cluster_summaries = [
                ClusterSummary(cluster_id=s['cluster_id'], size=s['size'],
                               percentage=s['percentage'], templates=s['templates'],
                               sample=s['sample'])
                for s in summaries
            ]
            print(f'  -> {len(cluster_summaries)} semantic clusters')

        anomaly_windows = self.temporal_detector.detect(df)
        bursts = self.burst_detector.detect(df)
        semantic_anomalies = self.semantic_detector.detect(
            df, template_texts=template_texts
        )
        print(f'  -> {len(anomaly_windows)} anomaly windows, {len(bursts)} bursts, {len(semantic_anomalies)} semantic anomalies')

        ldist = level_distribution(df)
        s = pattern_summary(df, tstats)

        summary = Summary(
            total_lines=s['total_lines'],
            unique_events=s['unique_events'],
            top_event=s.get('top_event', ''),
            top_event_count=s.get('top_event_count', 0),
            top_event_pct=s.get('top_event_pct', 0),
            error_count=s['error_count'],
            error_pct=s['error_pct'],
            warning_count=s['warning_count'],
            top10_coverage=s['top10_coverage'],
            rare_events_count=s['rare_events_count'],
            n_anomaly_windows=len(anomaly_windows),
            n_bursts=len(bursts),
            n_semantic_anomalies=len(semantic_anomalies),
        )

        return AnalysisResult(
            source=source,
            entries=df,
            template_stats=template_stats,
            time_series=time_series,
            anomaly_windows=anomaly_windows,
            bursts=bursts,
            semantic_anomalies=semantic_anomalies,
            level_dist=ldist,
            cluster_summaries=cluster_summaries,
            summary=summary,
        )

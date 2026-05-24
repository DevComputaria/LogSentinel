# LogSentinel — Especificação de Arquitetura

> **Documento de Arquitetura de Software**
> Versão: 1.0
> Status: Implementado

---

## 1. Visão Geral

LogSentinel é uma ferramenta de análise inteligente de logs que combina **Machine Learning** (clustering, embeddings semânticos) com **detecção de anomalias** (temporal e semântica) para identificar padrões suspeitos, bursts de repetição e eventos raros em logs de sistemas. A arquitetura é modular, baseada em design patterns do catálogo GoF e do guia [python-patterns.guide](https://python-patterns.guide/) (Brandon Rhodes).

### 1.1 Propósito

- Auto-detectar formato de logs (Linux syslog, Windows CBS, CSV estruturado)
- Extrair templates de eventos via algoritmo Drain
- Calcular embeddings semânticos (TF-IDF ou sentence-transformers)
- Detectar anomalias temporais (z-score em janelas móveis)
- Identificar bursts de repetição (mesmo evento em janela curta)
- Detectar anomalias semânticas (distância ao centróide dos embeddings)
- Agrupar eventos por similaridade semântica (K-Means, DBSCAN)
- Gerar relatórios em 3 formatos: CLI interativo, HTML (Plotly), Markdown

### 1.2 Referências Teóricas

O projeto fundamenta-se em três corpos teóricos:

| Referência | Contribuição |
|---|---|
| **Dmitry Vostokov** — *Fundamentals of Trace and Log Analysis: A Pattern-Oriented Approach* | Metodologia APM (Artifacts, Patterns, Mechanisms); diagnóstico orientado a padrões; Software Narratology |
| **J. R. Kantor** — *Interbehavioral Psychology* | Campo intercomportamental como unidade de análise; interdependência sistêmica entre eventos |
| **LogPAI** — *Drain: An Online Log Parsing Approach* | Algoritmo de parsing de logs baseado em árvore de profundidade fixa |
| **python-patterns.guide** (Brandon Rhodes) | Composition over Inheritance, Strategy, Factory Method, Builder, Facade |

---

## 2. Design Patterns Aplicados

### 2.1 Strategy Pattern

**Onde:** `parsers/`, `detectors/`, `reporters/`

Cada família de algoritmos é intercambiável via interface ABC:

```
LogParser (ABC)          Detector (ABC)           ReportBuilder (ABC)
├── LinuxLogParser       ├── TemporalAnomaly...   ├── CliReportBuilder
├── WindowsLogParser     ├── BurstDetector        ├── HtmlReportBuilder
├── CsvLogParser         └── SemanticAnomaly...   └── MdReportBuilder
```

**Benefício:** Novo parser para outro formato de log (ex: Docker, Apache) requer apenas implementar a interface `LogParser` sem modificar o pipeline.

### 2.2 Factory Method Pattern

**Onde:** `parsers/factory.py` — `ParserFactory.create()`

```python
parser = ParserFactory.create("logs/Linux_2k.log")  # → LinuxLogParser
parser = ParserFactory.create("logs/file.csv")       # → CsvLogParser
```

O `ParserFactory` analisa a extensão do arquivo e, para formatos desconhecidos, faz amostragem das primeiras 50 linhas com regex para detectar o formato automaticamente.

### 2.3 Facade Pattern

**Onde:** `core/analyzer.py` — `LogAnalyzer`

Centraliza o pipeline completo de análise em um único ponto de entrada:

```python
analyzer = LogAnalyzer()
result = analyzer.analyze("logs/Linux_2k.log")
```

O `LogAnalyzer` coordena: parser → extração de templates → features → embeddings → clustering → detecção de anomalias → sumarização, sem que o cliente precise conhecer os submódulos.

### 2.4 Builder Pattern

**Onde:** `reporters/` — `ReportBuilder.render()`

Cada `ReportBuilder` constrói uma representação diferente do mesmo `AnalysisResult`:

| Builder | Formato | Tecnologia |
|---|---|---|
| `CliReportBuilder` | Tabelas coloridas no terminal | Rich |
| `HtmlReportBuilder` | Dashboard interativo | Plotly |
| `MdReportBuilder` | Documento estruturado | Markdown |

### 2.5 Composition Over Inheritance

**Onde:** `LogAnalyzer` compõe parsers, detectores e reporters

```python
class LogAnalyzer:
    def __init__(self, parser=None):
        self.parser = parser or ParserFactory
        self.temporal_detector = TemporalAnomalyDetector()
        self.burst_detector = BurstDetector()
        self.semantic_detector = SemanticAnomalyDetector()
```

Não há hierarquia de herança profunda. Cada componente é uma estratégia independente, composta no analyzer.

### 2.6 Data Transfer Object (DTO)

**Onde:** `models/result.py`

```python
@dataclass
class AnalysisResult:
    source: str
    entries: pd.DataFrame
    template_stats: list[TemplateStats]
    anomaly_windows: list[AnomalyWindow]
    bursts: list[RepetitionBurst]
    semantic_anomalies: list[SemanticAnomaly]
    cluster_summaries: list[ClusterSummary]
    summary: Summary
```

Objetos tipados que transitam entre camadas sem acoplamento.

### 2.7 Global Object Pattern (Módulo)

**Onde:** `embeddings.py`

```python
_MODEL = None

def _get_model():
    global _MODEL
    if _MODEL is None:
        _MODEL = SentenceTransformer('all-MiniLM-L6-v2')
    return _MODEL
```

O modelo de embeddings é lazy-loaded e cacheado como singleton no módulo.

---

## 3. Pipeline de Análise

```
                        ┌──────────────────────┐
                        │    Log File (raw)     │
                        └──────────┬───────────┘
                                   ▼
                        ┌──────────────────────┐
                        │  ParserFactory.create │── Strategy: detecta formato
                        └──────────┬───────────┘
                                   ▼
                        ┌──────────────────────┐
                        │   LogParser.parse()   │── Strategy: Linux/Windows/CSV
                        └──────────┬───────────┘
                                   ▼
                        ┌──────────────────────┐
                        │  DataFrame unificado  │
                        │ (timestamp, level,    │
                        │  component, message)  │
                        └──────────┬───────────┘
                                   ▼
                        ┌──────────────────────┐
                        │  Drain Template Ext.  │── Extrai event_id + template
                        └──────────┬───────────┘
                                   ▼
                   ┌───────────────┼───────────────┐
                   ▼               ▼               ▼
            ┌───────────┐   ┌───────────┐   ┌───────────┐
            │ Temporal  │   │Embeddings │   │Features   │
            │ Features  │   │(TF-IDF /  │   │(hora,     │
            │(janelas   │   │ Sentence- │   │ dia,      │
            │ 5min)     │   │Transform) │   │janela)    │
            └─────┬─────┘   └──────┬────┘   └─────┬─────┘
                  │                │               │
                  ▼                ▼               │
            ┌───────────┐   ┌───────────┐          │
            │ Temporal  │   │ Clustering │          │
            │ Anomaly   │   │ K-Means +  │          │
            │(z-score)  │   │ DBSCAN    │          │
            └─────┬─────┘   └──────┬────┘          │
                  │                │               │
                  ▼                ▼               ▼
            ┌──────────────────────────────────────────┐
            │          AnalysisResult (DTO)             │
            │  anomalias + bursts + clusters + stats   │
            └──────────────────┬───────────────────────┘
                               ▼
                   ┌─────────────────────┐
                   │   ReportBuilder     │── Strategy: escolhe formato
                   ├─────────────────────┤
                   │ CLI │ HTML │ MD     │
                   └─────────────────────┘
```

### 3.1 Etapas Detalhadas

| Etapa | Módulo | Descrição | Algoritmo |
|---|---|---|---|
| **Parsing** | `parsers/` | Detecta formato e converte para DataFrame | Regex + amostragem estatística |
| **Template Extraction** | `extractors/templates.py` | Agrupa mensagens por template | Drain (árvore de profundidade fixa) |
| **Temporal Features** | `extractors/temporal.py` | Janelas de 5min, hora, dia da semana | Rolling window |
| **Embeddings** | `extractors/embeddings.py` | Vetoriza templates | TF-IDF (fallback) ou sentence-transformers |
| **Clustering** | `clustering.py` | Agrupa templates similares | K-Means + DBSCAN + Hierarchical |
| **Temporal Anomaly** | `detectors/temporal.py` | Janelas com volume anômalo | Z-score rolling + global |
| **Repetition Burst** | `detectors/burst.py` | Mesmo evento repetido em janela curta | Sliding window count |
| **Semantic Anomaly** | `detectors/semantic.py` | Templates semanticamente distantes | Cosine distance ao centróide |
| **Distribution** | `distribution.py` | Top problemas, nível, componente | Agregações pandas |
| **Reporting** | `reporters/` | Gera saída no formato escolhido | Rich / Plotly / Markdown |

---

## 4. Modelo de Dados

### 4.1 LogEntry (DataFrame)

| Coluna | Tipo | Origem |
|---|---|---|
| `timestamp` | datetime | Parsed from log line |
| `level` | str (Info/Warning/Error) | Inferred from message or explicit column |
| `component` | str | Program name (Linux) or Component (Windows) |
| `message_raw` | str | Original message text |
| `pid` | str | Process ID if available |
| `source` | str | linux / windows / csv |
| `line` | int | Original line number |
| `event_id` | int | Template ID from Drain |
| `template` | str | Normalized template string |
| `hour` | int | 0-23 |
| `day_of_week` | int | 0=Monday |
| `window_id` | int | 5-min window index |

### 4.2 AnomalyWindow

| Campo | Tipo | Descrição |
|---|---|---|
| `timestamp` | datetime | Início da janela |
| `count` | int | Total de eventos na janela |
| `count_zscore` | float | Z-score do volume |
| `unique_zscore` | float | Z-score da diversidade |
| `global_zscore` | float | Z-score global |
| `anomaly_type` | str | `volume_burst+diversity_spike+global_burst` |
| `top_events` | list | Top 3 eventos com template e contagem |
| `interpretation` | str | Descrição textual: "volume burst (24 eventos)" |

### 4.3 Tipos de Anomalia

| Tipo | Detecção | Interpretação |
|---|---|---|
| `volume_burst` | count_zscore > threshold | Pico de atividade na janela |
| `volume_drop` | count_zscore < -threshold | Queda súbita de atividade |
| `diversity_spike` | unique_zscore > threshold | Muitos templates diferentes no mesmo período |
| `diversity_drop` | unique_zscore < -threshold | Atividade monótona/repetitiva |
| `global_burst` | global_zscore > threshold*1.5 | Outlier em relação à média geral |

---

## 5. Detecção de Anomalias

### 5.1 Anomalia Temporal (z-score)

```python
# Janela deslizante de 5 minutos
ts = df.resample('5min').agg(count=...)

# Média móvel com janela adaptativa
rolling_w = min(10, max(3, len(ts) // 5))
ts['count_ma'] = ts['count'].rolling(rolling_w).mean()
ts['count_std'] = ts['count'].rolling(rolling_w).std()

# Z-score = (valor - média) / desvio
ts['count_zscore'] = (ts['count'] - ts['count_ma']) / (ts['count_std'] + 1e-8)

# Anomalia se |z-score| > 2.5
```

### 5.2 Burst de Repetição

```python
# Mesmo event_id repetido N+ vezes em janela de 10s
window = df[(df['timestamp'] >= cutoff) & (df['timestamp'] <= current)]
event_counts = window.groupby('event_id').size()
bursts = event_counts[event_counts >= 5]
```

### 5.3 Anomalia Semântica

```python
# Distância cosseno ao centróide dos embeddings
embeddings = compute_embeddings(template_texts)
centroid = embeddings.mean(axis=0)
distances = 1 - np.dot(embeddings, centroid)

# Anomalia se distância > threshold (0.4)
anomalous = distances > 0.4
```

---

## 6. Estrutura do Projeto

```
LogSentinel/
├── src/
│   ├── main.py                 # CLI entry point (Facade)
│   ├── core/
│   │   └── analyzer.py         # LogAnalyzer (Facade)
│   ├── parsers/
│   │   ├── base.py             # LogParser (ABC — Strategy)
│   │   ├── linux.py            # LinuxLogParser
│   │   ├── windows.py          # WindowsLogParser
│   │   ├── csvparser.py        # CsvLogParser
│   │   └── factory.py          # ParserFactory (Factory Method)
│   ├── detectors/
│   │   ├── base.py             # Detector (ABC — Strategy)
│   │   ├── temporal.py         # TemporalAnomalyDetector
│   │   ├── burst.py            # BurstDetector
│   │   └── semantic.py         # SemanticAnomalyDetector
│   ├── extractors/
│   │   ├── templates.py        # Drain algorithm
│   │   ├── temporal.py         # Temporal features
│   │   └── embeddings.py       # TF-IDF / sentence-transformers
│   ├── reporters/
│   │   ├── base.py             # ReportBuilder (ABC — Strategy+Builder)
│   │   ├── cli_reporter.py     # CliReportBuilder (Rich)
│   │   ├── html_reporter.py    # HtmlReportBuilder (Plotly)
│   │   └── md_reporter.py      # MdReportBuilder (Markdown)
│   ├── models/
│   │   └── result.py           # DTOs (AnalysisResult, AnomalyWindow...)
│   ├── clustering.py           # K-Means + DBSCAN + Hierarchical
│   ├── distribution.py         # Estatísticas de distribuição
│   ├── features.py             # Feature engineering
│   ├── templates.py            # Drain implementation
│   ├── embeddings.py           # Embeddings with TF-IDF fallback
│   ├── anomaly.py              # (legacy) imported by extractors
│   ├── parser.py               # (legacy) imported by extractors
│   └── reporter.py             # (legacy) imported by extractors
├── logs/                       # Dados de teste (LogHub)
├── output/                     # Relatórios gerados
├── docs/
│   └── plan.md                 # Este documento
├── README.md
├── .gitignore
└── requirements.txt
```

---

## 7. Dependências

### 7.1 Obrigatórias

| Pacote | Versão | Uso |
|---|---|---|
| pandas | >=1.5 | Manipulação de DataFrames |
| numpy | >=1.23 | Operações numéricas |
| scikit-learn | >=1.2 | K-Means, DBSCAN, TF-IDF |
| plotly | >=5.13 | Dashboard HTML interativo |
| rich | >=13.0 | Output CLI colorido |
| scipy | >=1.10 | Distâncias, estatísticas |
| regex | >=2023.0 | Parsing de logs |

### 7.2 Opcionais

| Pacote | Uso |
|---|---|
| sentence-transformers | Embeddings semânticos com transformers (all-MiniLM-L6-v2) |

---

## 8. Métricas de Qualidade

### 8.1 Linux_2k.log (2.000 linhas)

| Métrica | Valor |
|---|---|
| Templates únicos | 150 |
| Erros detectados | 90 (4.5%) |
| Janelas anômalas | 152 |
| Bursts de repetição | 292 |
| Anomalias semânticas | 188 |
| Clusters K-Means | 9 |
| Clusters DBSCAN | 30 |
| Top-10 coverage | 53.6% |

### 8.2 Windows_2k.log (2.000 linhas)

| Métrica | Valor |
|---|---|
| Templates únicos | 59 |
| Erros detectados | 474 (23.7%) |
| Warnings | 280 (14.0%) |
| Janelas anômalas | 3 |
| Bursts de repetição | 260 |
| Anomalias semânticas | 69 |
| Clusters K-Means | 5 |
| Clusters DBSCAN | 10 |
| Top-10 coverage | 96.6% |

---

## 9. Referências

1. **python-patterns.guide** — Brandon Rhodes. https://python-patterns.guide/
2. **LogHub** — LogPAI / Zhu et al. https://github.com/logpai/loghub
3. **Drain: An Online Log Parsing Approach** — He et al., 2017. IEEE ICWS
4. **Vostokov, D.** — *Fundamentals of Trace and Log Analysis: A Pattern-Oriented Approach*. Software Diagnostics Institute
5. **Kantor, J. R.** — *Interbehavioral Psychology*. Principia Press, 1959
6. **Sentence-Transformers** — Reimers & Gurevych, 2019. EMNLP
7. **Gang of Four** — *Design Patterns: Elements of Reusable Object-Oriented Software*. Addison-Wesley, 1994

# LogSentinel

Análise inteligente de logs com Machine Learning — detecta anomalias temporais e semânticas, agrupa eventos por template, identifica bursts de repetição e gera relatórios em CLI, HTML interativo (Plotly) e Markdown. Arquitetura modular com design patterns (Strategy, Facade, Builder, Factory Method).

## Arquitetura (Design Patterns)

O projeto segue padrões de projeto do [python-patterns.guide](https://python-patterns.guide/):

```
src/
├── main.py                      # CLI entry point
├── core/
│   └── analyzer.py              # Facade: LogAnalyzer — centraliza o pipeline
├── parsers/
│   ├── base.py                  # Strategy: interface LogParser (ABC)
│   ├── linux.py                 # LinuxLogParser (syslog/auth)
│   ├── windows.py               # WindowsLogParser (CBS)
│   ├── csvparser.py             # CsvLogParser (CSV estruturado)
│   └── factory.py               # Factory Method: ParserFactory.create()
├── detectors/
│   ├── base.py                  # Strategy: interface Detector (ABC)
│   ├── temporal.py              # TemporalAnomalyDetector (z-score rolling)
│   ├── burst.py                 # BurstDetector (repetição em janela)
│   └── semantic.py              # SemanticAnomalyDetector (distância coseno)
├── extractors/
│   ├── templates.py             # Drain simplificado (template extraction)
│   ├── temporal.py              # Features temporais (janelas 5min)
│   └── embeddings.py            # TF-IDF / sentence-transformers
├── reporters/
│   ├── base.py                  # Strategy + Builder: ReportBuilder (ABC)
│   ├── cli_reporter.py          # CliReportBuilder (Rich tables)
│   ├── html_reporter.py         # HtmlReportBuilder (Plotly dashboard)
│   └── md_reporter.py           # MdReportBuilder (Markdown)
├── models/
│   └── result.py                # Data Transfer Objects (dataclasses)
├── clustering.py                # K-Means + DBSCAN
├── distribution.py              # Estatísticas de distribuição
├── features.py                  # Feature engineering
├── templates.py                 # Algoritmo Drain de template extraction
├── embeddings.py                # Embeddings com fallback TF-IDF
├── anomaly.py                   # (legado) — importado pelos extractors
├── parser.py                    # (legado) — importado pelos extractors
└── reporter.py                  # (legado) — importado pelos extractors
```

### Padrões Aplicados

| Padrão | Aplicação |
|--------|-----------|
| **Strategy** | Parsers, Detectors e Reporters são intercambiáveis via interfaces ABC |
| **Factory Method** | `ParserFactory` cria o parser correto baseado no formato do arquivo |
| **Facade** | `LogAnalyzer.analyze()` expõe o pipeline completo em 1 chamada |
| **Builder** | Cada `ReportBuilder` constrói um formato de saída diferente |
| **Composition** | `LogAnalyzer` compõe parsers, detectores e reporters sem herança |
| **DTO** | `AnalysisResult`, `AnomalyWindow` etc. transportam dados entre camadas |

## Pipeline

```
Log File → Parser (auto-detect) → DataFrame
                                       ↓
                              Drain Template Extraction
                                       ↓
                    ┌──────────────────┼──────────────────┐
                    ↓                  ↓                  ↓
             Temporal Features    Embeddings (TF-IDF)   Clustering
                    ↓                  ↓                  ↓
            Temporal Anomaly     Semantic Anomaly     K-Means/DBSCAN
            (z-score rolling)    (cosine distance)    (template groups)
                    └──────────────────┼──────────────────┘
                                       ↓
                               ReportBuilder
                            (CLI + HTML + MD)
```

## Instalação

```bash
git clone https://github.com/seu-usuario/LogSentinel.git
cd LogSentinel
pip install -r requirements.txt
```

> Para embeddings semânticos completos (sentence-transformers):
> ```bash
> pip install sentence-transformers
> ```

## Uso

```bash
# CLI interativo (default)
python src/main.py logs/Linux_2k.log -f cli

# Todos os formatos
python src/main.py logs/Windows_2k.log -f all

# Formatos específicos
python src/main.py logs/Linux_2k.log -f html md

# CSV estruturado
python src/main.py logs/Linux_2k.log_structured.csv -f cli

# Pular embeddings (mais rápido)
python src/main.py logs/Linux_2k.log -f cli --no-embeddings
```

### Output

```
output/
├── Linux_2k_dashboard.html       # Plotly interativo
├── Linux_2k_report.md            # Relatório markdown
├── Windows_2k_dashboard.html
└── Windows_2k_report.md
```

## Dados de Teste

Os arquivos em `logs/` são extraídos do [**LogHub**](https://github.com/logpai/loghub) ([logpai/loghub](https://github.com/logpai/loghub)), um repositório de referência para pesquisa em análise de logs, mantido pelo grupo LogPAI. Contêm 2.000 linhas cada:

- **Linux_2k.log** — syslog com tentativas de SSH brute force, sessões de usuário, conexões de rede
- **Windows_2k.log** — CBS (Component Based Servicing) com erros de manifest do Windows Update
- **\*_structured.csv** — versões pré-parsadas (Drain) com colunas: `LineId, Month, Date, Time, Level, Component, PID, Content, EventId, EventTemplate`

## Exemplo de Análise

### Linux — Brute Force SSH Detectado

```
Temporal Anomalies: 152 windows

Timestamp          Interpretation
─────────────────────────────────────────────────────────────────
2026-06-15         volume burst (24 events in 5min) + event
12:10:00           diversity spike + global outlier.
                   Top: "authentication failure" (12x),
                        "check pass; user unknown" (12x)

Repetition Bursts: 292 detected
  authentication failure; logname= uid=0 euid=0...  (10x in 10s)
  check pass; user unknown                           (10x in 10s)
```

### Windows — Erros de Manifest do CBS

```
Level Distribution
  Info      1,246   62.3%
  Error       474   23.7%
  Warning     280   14.0%

Top Events:
  Session initialized by client WindowsUpdateAgent  608 (30.4%)
  Warning: Unrecognized packageExtended attribute   280 (14.0%)
  Failed to get next element [HRESULT 0x800f080d]   224 (11.2%)
```

## Dependências

```
pandas, numpy, scikit-learn, plotly, rich, scipy, regex
```

Opcional: `sentence-transformers` (para embeddings semânticos com transformers).

## Licença

MIT

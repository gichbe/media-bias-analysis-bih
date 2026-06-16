# Automatizovana analiza političke pristrasnosti medija u BiH

**Bachelor rad** — ETF, Računarstvo i informatika

## Cilj

Razviti i evaluirati pipeline koji koristi Large Language Models (LLM) za detekciju političke pristrasnosti u člancima bosanskohercegovačkih online medija, te uporediti rezultate sa ručnim anotacijama.

## Istraživačka pitanja

- **RQ1:** Koliko pouzdano LLM modeli mogu detektovati političku pristrasnost u BiH medijima u poređenju s ručnim anotatorima?
- **RQ2:** Da li se performanse LLM modela razlikuju između različitih medijskih portala?
- **RQ3:** Imaju li LLM modeli tendenciju ka neutralnim ili ekstremnim ocjenama?
- **RQ4:** Kako se distribucija pristrasnosti razlikuje između portala različitih političkih/etničkih orijentacija?

## Struktura projekta

```
thesis_project/
├── docs/                   # Kodbook, plan rada, thesis dokumenti
│   └── codebook.md         # Definicija dimenzija pristrasnosti
├── scrapers/               # Web scraperi za pojedinačne portale
│   ├── base_scraper.py     # Bazna klasa
│   ├── klix_scraper.py
│   ├── avaz_scraper.py
│   ├── nezavisne_scraper.py
│   ├── vecernji_scraper.py
│   └── n1_scraper.py
├── src/                    # Glavna logika
│   ├── llm_evaluator.py    # Pozivanje LLM API-ja
│   ├── metrics.py          # Cohen's Kappa, accuracy, F1
│   ├── analysis.py         # Statistička analiza
│   └── visualize.py        # Grafikoni i plotovi
├── data/
│   ├── raw/                # Sirovi scraping output (HTML/JSON)
│   ├── processed/          # Očišćeni članci spremni za anotaciju
│   └── annotations/        # Ručne i LLM anotacije (CSV)
├── notebooks/              # Jupyter notebook-ovi za eksploraciju
└── results/                # Grafikoni, tabele, finalni izlazi
```

## Pipeline

```
[1] Scraping → [2] Preprocessing → [3] Manual annotation
                                    ↓
                                    [4] LLM evaluation (multi-model)
                                    ↓
                                    [5] Comparison & metrics
                                    ↓
                                    [6] Visualization & analysis
```

## Izabrani portali

Cilj: ~80–100 članaka po portalu, ukupno **400–500 članaka**.

| Portal | URL | Orijentacija (uobičajena percepcija) |
|---|---|---|
| Klix | klix.ba | Civic / FBiH-centričan |
| Avaz | avaz.ba | Bošnjačka orijentacija |
| Nezavisne novine | nezavisne.com | Srpska orijentacija (RS) |
| Večernji list BiH | vecernji.ba | Hrvatska orijentacija |
| N1 BiH | ba.n1info.com | Regionalni, civic |

*Napomena:* Klasifikacija orijentacije nije sudija — to je hipoteza koju rad treba empirijski testirati.

## Setup

```bash
# Python 3.10+
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

## Korištenje

```bash
# 1. Scraping (svaki portal posebno)
python -m scrapers.klix_scraper --num-articles 100 --output data/raw/klix.json

# 2. Preprocessing
python -m src.preprocess --input data/raw/ --output data/processed/articles.csv

# 3. LLM evaluacija
python -m src.llm_evaluator --input data/processed/articles.csv --model gpt-4 --output data/annotations/llm_gpt4.csv

# 4. Analiza
python -m src.analysis --human data/annotations/human.csv --llm data/annotations/llm_gpt4.csv
```

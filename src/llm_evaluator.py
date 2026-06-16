"""
LLM evaluator — anotira članke koristeći LLM modele.

Podržava:
  - OpenAI (GPT-4, GPT-4o, GPT-4o-mini)
  - Anthropic (Claude 3.5/4)
  - Lako se proširi za druge API-je

Output: CSV kompatibilan sa human annotation formatom (vidi docs/codebook.md).

Pokretanje:
    python -m src.llm_evaluator \\
        --input data/processed/articles.csv \\
        --model gpt-4o \\
        --output data/annotations/llm_gpt4o.csv
"""

import argparse
import json
import logging
import os
import time
from pathlib import Path
from typing import Optional

import pandas as pd
from tqdm import tqdm

from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


# ---------------------------------------------------------------------------
# Prompt — direktno baziran na docs/codebook.md
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """Ti si stručan analitičar političkog diskursa u bosanskohercegovačkim medijima.
Tvoj zadatak je da za zadani članak ocijeniš četiri dimenzije pristrasnosti prema strogo definisanim kriterijima.

VAŽNO:
- Ocjenjuj objektivno, samo na osnovu sadržaja članka.
- Ne pretpostavljaj šira znanja izvan teksta.
- Ako si u nedoumici između dvije vrijednosti, biraj manje ekstremnu.
- Vrati ISKLJUČIVO validan JSON, bez ikakvog dodatnog teksta.
"""

USER_PROMPT_TEMPLATE = """# DIMENZIJE OCJENJIVANJA

## 1. TON (sentiment prema dominantnom političkom akteru/grupi)
Skala: cjelobrojna od -2 do +2
  -2 = vrlo negativan (pejorativi, otvoreni napad)
  -1 = negativan (kritičan, ali bez napada)
   0 = neutralan (informativan, faktografski)
  +1 = pozitivan (pohvalan, naglašava uspjehe)
  +2 = vrlo pozitivan (idealizuje, superlativi)

Dominantni akter = onaj kojem je posvećeno najviše prostora, ili akter u naslovu.

## 2. FRAMING (način uokvirivanja događaja)
Vrati JEDNU od kategorija (string):
  "konflikt"        - sukob, podjele, mi vs. oni
  "odgovornost"     - ko je kriv/odgovoran
  "ekonomski"       - ekonomske posljedice
  "ljudski_interes" - pojedinačne sudbine, emocije
  "moralni"         - moralna/etička dilema
  "proceduralni"    - procedura, zakon, institucije
  "nacionalni"      - etnički/nacionalni identitet
  "neutralan"       - bez izraženog uokvirivanja

## 3. BALANSIRANOST (multi-perspectivity)
Skala: cjelobrojna 0–2
  0 = jednostrano (samo jedan izvor/pozicija)
  1 = djelimično balansirano (druge strane spomenute površno)
  2 = balansirano (više strana sa približno jednakim prostorom)

## 4. POLITICAL_LEAN (pristrasnost prema političkoj opciji)
Vrati JEDNU od kategorija (string):
  "pro_vlast"
  "pro_opozicija"
  "pro_bosnjacka_opcija"
  "pro_srpska_opcija"
  "pro_hrvatska_opcija"
  "pro_gradjanska_opcija"
  "nejasno"
  "neutralan"

## 5. CONFIDENCE
Cjelobrojno 1–5, koliko si siguran u svoju ocjenu (1 = vrlo nesiguran, 5 = vrlo siguran).

# IZLAZNI FORMAT (strogi JSON)

{{
  "tone": <int>,
  "framing": "<string>",
  "balance": <int>,
  "political_lean": "<string>",
  "dominant_actor": "<string ili null>",
  "confidence": <int>,
  "reasoning": "<kratko obrazloženje, max 2 rečenice>"
}}

# ČLANAK ZA ANALIZU

PORTAL: {portal}
NASLOV: {title}
DATUM: {date}

TEKST:
{body}

Vrati samo JSON.
"""


# ---------------------------------------------------------------------------
# Provider adapteri
# ---------------------------------------------------------------------------


class LLMProvider:
    """Bazna klasa za LLM provajdere."""

    name = "base"

    def call(self, system: str, user: str, model: str) -> str:
        raise NotImplementedError


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self):
        from openai import OpenAI
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def call(self, system: str, user: str, model: str) -> str:
        response = self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_format={"type": "json_object"},
            temperature=0.0,
        )
        return response.choices[0].message.content


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(self):
        import anthropic
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    def call(self, system: str, user: str, model: str) -> str:
        response = self.client.messages.create(
            model=model,
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": user}],
            temperature=0.0,
        )
        # Claude može da vrati tekst koji nije čist JSON pa skidamo eventualne fences
        text = response.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:].strip()
        return text


PROVIDER_MAP = {
    # OpenAI modeli
    "gpt-4": OpenAIProvider,
    "gpt-4o": OpenAIProvider,
    "gpt-4o-mini": OpenAIProvider,
    "gpt-4-turbo": OpenAIProvider,
    # Anthropic modeli
    "claude-opus-4-20250514": AnthropicProvider,
    "claude-sonnet-4-20250514": AnthropicProvider,
    "claude-3-5-sonnet-20241022": AnthropicProvider,
    "claude-3-5-haiku-20241022": AnthropicProvider,
}


# ---------------------------------------------------------------------------
# Glavna evaluacija
# ---------------------------------------------------------------------------


def evaluate_article(
    provider: LLMProvider,
    model: str,
    article: dict,
    max_body_chars: int = 6000,
) -> Optional[dict]:
    """Šalje jedan članak LLM-u i vraća strukturirani JSON."""
    body = article.get("body", "")
    if len(body) > max_body_chars:
        body = body[:max_body_chars] + "\n\n[...skraćeno...]"

    user_prompt = USER_PROMPT_TEMPLATE.format(
        portal=article.get("portal", ""),
        title=article.get("title", ""),
        date=article.get("date_published", "nepoznat"),
        body=body,
    )

    try:
        raw = provider.call(SYSTEM_PROMPT, user_prompt, model)
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("JSON parse fail za %s: %s", article.get("article_id"), exc)
        logger.debug("Raw output: %s", raw[:500])
        return None
    except Exception as exc:
        logger.exception("LLM poziv pao za %s: %s", article.get("article_id"), exc)
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="JSON ili CSV sa člancima")
    parser.add_argument(
        "--model", required=True, help="Naziv modela (npr. gpt-4o, claude-sonnet-4-20250514)"
    )
    parser.add_argument("--output", required=True, help="Output CSV")
    parser.add_argument(
        "--limit", type=int, default=None, help="Ograniči broj članaka (za testiranje)"
    )
    parser.add_argument(
        "--retry-delay", type=float, default=1.0, help="Pauza između poziva (sekunde)"
    )
    args = parser.parse_args()

    # Učitaj članke
    input_path = Path(args.input)
    if input_path.suffix == ".json":
        with input_path.open(encoding="utf-8") as f:
            articles = json.load(f)
    else:
        articles = pd.read_csv(input_path).to_dict("records")

    if args.limit:
        articles = articles[: args.limit]

    logger.info("Evaluiram %d članaka modelom %s", len(articles), args.model)

    # Odaberi provajdera
    provider_cls = PROVIDER_MAP.get(args.model)
    if provider_cls is None:
        raise ValueError(
            f"Nepoznat model: {args.model}. Podržani: {list(PROVIDER_MAP.keys())}"
        )
    provider = provider_cls()

    # Anotiraj
    results = []
    for article in tqdm(articles, desc=f"LLM eval ({args.model})"):
        annotation = evaluate_article(provider, args.model, article)
        if annotation is None:
            continue

        results.append({
            "article_id": article.get("article_id"),
            "portal": article.get("portal"),
            "url": article.get("url"),
            "title": article.get("title"),
            "date_published": article.get("date_published"),
            "annotator_id": f"LLM_{args.model}",
            "tone": annotation.get("tone"),
            "framing": annotation.get("framing"),
            "balance": annotation.get("balance"),
            "political_lean": annotation.get("political_lean"),
            "dominant_actor": annotation.get("dominant_actor"),
            "confidence": annotation.get("confidence"),
            "notes": annotation.get("reasoning"),
        })

        time.sleep(args.retry_delay)

    # Snimi
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(results).to_csv(output_path, index=False, encoding="utf-8")
    logger.info("Snimljeno %d anotacija u %s", len(results), output_path)


if __name__ == "__main__":
    main()

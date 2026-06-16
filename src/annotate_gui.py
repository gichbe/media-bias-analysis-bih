"""
Streamlit GUI za ručnu anotaciju političke pristrasnosti.

Pokretanje:
    streamlit run src/annotate_gui.py
"""

import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st


FRAMING_OPTIONS = [
    "konflikt", "odgovornost", "ekonomski", "ljudski_interes",
    "moralni", "proceduralni", "nacionalni", "neutralan",
]

LEAN_OPTIONS = [
    "neutralan", "nejasno",
    "pro_vlast", "pro_opozicija",
    "pro_bosnjacka_opcija", "pro_srpska_opcija", "pro_hrvatska_opcija",
    "pro_gradjanska_opcija",
]


# -- konfiguracija ----------------------------------------------------------

st.set_page_config(
    page_title="Anotacija pristrasnosti",
    page_icon="📰",
    layout="wide",
)

st.markdown("""
<style>
.article-title { font-size: 1.5rem; font-weight: 600; line-height: 1.3; }
.article-meta  { color: #666; font-size: 0.9rem; }
.article-body  { font-size: 1.05rem; line-height: 1.6; }
.stRadio > label { font-weight: 600; }
</style>
""", unsafe_allow_html=True)


# -- sidebar postavke -------------------------------------------------------

with st.sidebar:
    st.markdown("### ⚙️ Postavke")
    input_file = st.text_input("Input (JSON)", "data/processed/articles_shuffled.json")
    output_file = st.text_input("Output anotacija (CSV)", "data/annotations/human_A1.csv")
    annotator_id = st.text_input("Anotator ID", "A1")
    excluded_file = f"data/annotations/excluded_{annotator_id}.csv"
    st.caption(f"Odbačeni se snimaju u: `{excluded_file}`")
    st.markdown("---")
    st.caption("Pred sobom drži otvoren docs/codebook.md za referencu.")


# -- helpers ----------------------------------------------------------------

@st.cache_data
def load_articles(path):
    p = Path(path)
    if not p.exists():
        return []
    with p.open(encoding="utf-8") as f:
        return json.load(f)


def load_ids_from_csv(path):
    p = Path(path)
    if not p.exists():
        return set()
    try:
        df = pd.read_csv(p)
        return set(df["article_id"].astype(str).values)
    except (pd.errors.EmptyDataError, KeyError):
        return set()


def save_row(row, path):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    df_new = pd.DataFrame([row])
    header = not p.exists()
    df_new.to_csv(p, mode="a" if not header else "w",
                  header=header, index=False, encoding="utf-8")


def save_exclusion(article, annotator, reason, path):
    row = {
        "article_id": article.get("article_id"),
        "portal": article.get("portal"),
        "url": article.get("url"),
        "title": article.get("title"),
        "annotator_id": annotator,
        "reason": reason or "manual exclusion",
        "excluded_at": datetime.now().isoformat(timespec="seconds"),
    }
    save_row(row, path)


# -- main -------------------------------------------------------------------

articles = load_articles(input_file)
if not articles:
    st.error(f"Ne mogu ucitati fajl: `{input_file}`")
    st.info("Provjeri put u sidebar-u.")
    st.stop()

done = load_ids_from_csv(output_file)
excluded = load_ids_from_csv(excluded_file)
seen = done | excluded
todo = [a for a in articles if str(a.get("article_id")) not in seen]

# Header sa progres barom
top_left, top_right = st.columns([3, 2])
with top_left:
    st.markdown(f"### Anotacija pristrasnosti - anotator **{annotator_id}**")
with top_right:
    c1, c2, c3 = st.columns(3)
    c1.metric("Anotirano", len(done))
    c2.metric("Odbaceno", len(excluded))
    c3.metric("Preostalo", len(todo))

st.progress(len(seen) / max(len(articles), 1))

if not todo:
    st.success("Zavrseno! Svi clanci su obradjeni.")
    if Path(output_file).exists():
        st.dataframe(pd.read_csv(output_file), use_container_width=True)
    st.stop()

# Trenutni clanak
article = todo[0]
article_id = str(article.get("article_id"))

st.markdown("---")

# Naslov i meta info
st.markdown(f"<div class='article-title'>{article.get('title', '')}</div>",
            unsafe_allow_html=True)
meta_parts = [
    f"**Portal:** {article.get('portal', '')}",
    f"**Datum:** {article.get('date_published', 'n/a')}",
]
if article.get("author"):
    meta_parts.append(f"**Autor:** {article['author']}")
st.markdown(
    f"<div class='article-meta'>{' &nbsp;|&nbsp; '.join(meta_parts)}</div>",
    unsafe_allow_html=True,
)
if article.get("url"):
    st.markdown(f"[Otvori original]({article['url']})")

st.markdown("")

# Tekst clanka (skup na lijevoj, anotacija na desnoj strani)
col_text, col_form = st.columns([3, 2])

with col_text:
    body = article.get("body", "")
    st.markdown(
        f"<div class='article-body'>{body[:8000].replace(chr(10), '<br>')}</div>",
        unsafe_allow_html=True,
    )
    if len(body) > 8000:
        st.caption(f"... prikazano prvih 8000 od {len(body)} znakova")

with col_form:
    with st.container(border=True):
        st.markdown("#### Anotacija")

        tone = st.radio(
            "**1. Ton** (prema dominantnom akteru)",
            options=[-2, -1, 0, 1, 2],
            index=2,
            horizontal=True,
            format_func=lambda x: {-2: "-2", -1: "-1", 0: "0", 1: "+1", 2: "+2"}[x],
            help="-2 = vrlo negativan, 0 = neutralan, +2 = vrlo pozitivan",
            key=f"tone_{article_id}",
        )

        framing = st.selectbox(
            "**2. Framing** (nacin uokvirivanja)",
            FRAMING_OPTIONS,
            index=FRAMING_OPTIONS.index("neutralan"),
            key=f"framing_{article_id}",
        )

        balance = st.radio(
            "**3. Balansiranost**",
            options=[0, 1, 2],
            index=1,
            horizontal=True,
            format_func=lambda x: {
                0: "0 - jednostrano",
                1: "1 - djelimicno",
                2: "2 - balansirano"
            }[x],
            key=f"balance_{article_id}",
        )

        political_lean = st.selectbox(
            "**4. Political lean**",
            LEAN_OPTIONS,
            key=f"lean_{article_id}",
        )

        dominant_actor = st.text_input(
            "**5. Dominantni akter** (npr. SDA, Dodik, Vlada FBiH)",
            key=f"actor_{article_id}",
        )

        confidence = st.slider(
            "**6. Confidence**",
            min_value=1, max_value=5, value=3,
            key=f"conf_{article_id}",
        )

        notes = st.text_area(
            "**7. Napomene** (opciono)",
            height=80,
            key=f"notes_{article_id}",
        )

        st.markdown("")
        submit = st.button("Sacuvaj i sljedeci", type="primary",
                           use_container_width=True, key=f"save_{article_id}")

    # Sekcija za odbacivanje
    st.markdown("")
    with st.container(border=True):
        st.markdown("##### Odbaci clanak iz seta")
        st.caption("Ako clanak nije politicki relevantan / los sadrzaj / duplikat.")
        exclude_reason = st.selectbox(
            "Razlog",
            [
                "nije politika",
                "duplikat",
                "los sadrzaj (listing/navigation)",
                "mojibake / necitljiv tekst",
                "prazan clanak",
                "drugo",
            ],
            key=f"reason_{article_id}",
        )
        exclude_custom = ""
        if exclude_reason == "drugo":
            exclude_custom = st.text_input(
                "Tvoj razlog",
                key=f"reason_custom_{article_id}",
            )
        exclude_btn = st.button(
            "Odbaci ovaj clanak",
            use_container_width=True,
            key=f"exclude_{article_id}",
        )


if submit:
    row = {
        "article_id": article.get("article_id"),
        "portal": article.get("portal"),
        "url": article.get("url"),
        "title": article.get("title"),
        "date_published": article.get("date_published"),
        "annotator_id": annotator_id,
        "tone": tone,
        "framing": framing,
        "balance": balance,
        "political_lean": political_lean,
        "dominant_actor": dominant_actor or None,
        "confidence": confidence,
        "notes": notes or None,
    }
    save_row(row, output_file)
    st.cache_data.clear()
    st.rerun()

if exclude_btn:
    reason = exclude_custom if exclude_reason == "drugo" else exclude_reason
    save_exclusion(article, annotator_id, reason, excluded_file)
    st.cache_data.clear()
    st.toast(f"Odbacen: {article.get('title', '')[:50]}", icon=":wastebasket:")
    st.rerun()

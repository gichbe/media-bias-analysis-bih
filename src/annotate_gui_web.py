"""
Web verzija anotacijskog GUI-ja za Streamlit Cloud.

Razlika od annotate_gui.py:
- Anotacije se cuvaju u session_state (ne na disku, jer Cloud disk je efemeralan)
- "Preuzmi CSV" dugme uvijek prikazano - anotator preuzima i salje korisniku
- Dataset se cita iz repo-a (data/processed/articles_shuffled.json)

Pokretanje lokalno za test:
    streamlit run src/annotate_gui_web.py

Deployment:
    1. Push kod na GitHub
    2. Idi na https://streamlit.io/cloud
    3. New app -> izaberi repo -> Main file: src/annotate_gui_web.py
"""

import io
import json
from pathlib import Path

import pandas as pd
import streamlit as st


def scroll_to_top(nonce):
    """Pomjeri skrol na vrh; nonce prisiljava ponovno izvrsavanje skripte."""
    html = """
        <script data-scroll-nonce="__NONCE__">
            (() => {
                const scrollUp = () => {
                    const targets = [
                        document.querySelector('[data-testid="stAppViewContainer"]'),
                        document.querySelector('[data-testid="stMain"]'),
                        document.scrollingElement,
                        document.documentElement,
                        document.body,
                    ].filter(Boolean);

                    for (const target of targets) {
                        target.scrollTop = 0;
                        if (typeof target.scrollTo === "function") {
                            target.scrollTo({top: 0, left: 0, behavior: "auto"});
                        }
                    }

                    window.scrollTo({top: 0, left: 0, behavior: "auto"});
                };

                // Izvrsi nakon sto Streamlit iscrta novi clanak.
                requestAnimationFrame(() => requestAnimationFrame(scrollUp));
                setTimeout(scrollUp, 100);
                setTimeout(scrollUp, 300);
                setTimeout(scrollUp, 600);
            })();
        </script>
    """.replace("__NONCE__", str(nonce))

    st.html(html, unsafe_allow_javascript=True)


DATASET_PATH = "data/processed/articles_shuffled.json"

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


st.set_page_config(
    page_title="Anotacija pristrasnosti",
    page_icon=":newspaper:",
    layout="wide",
)

st.markdown('<div id="page-top"></div>', unsafe_allow_html=True)

st.markdown("""
<style>
.article-title { font-size: 1.5rem; font-weight: 600; line-height: 1.3; }
.article-meta  { color: #666; font-size: 0.9rem; }
.article-body  { font-size: 1.05rem; line-height: 1.6; }
.stRadio > label { font-weight: 600; }
.welcome { background: #f0f7ff; padding: 1rem; border-radius: 8px; border-left: 4px solid #1c7ed6; }
</style>
""", unsafe_allow_html=True)


# -- Session state init -----------------------------------------------------

if "annotations" not in st.session_state:
    st.session_state.annotations = []
if "excluded" not in st.session_state:
    st.session_state.excluded = []
if "started" not in st.session_state:
    st.session_state.started = False
if "scroll_to_top" not in st.session_state:
    st.session_state.scroll_to_top = False
if "scroll_nonce" not in st.session_state:
    st.session_state.scroll_nonce = 0


# -- Helpers ----------------------------------------------------------------

@st.cache_data
def load_articles():
    p = Path(DATASET_PATH)
    if not p.exists():
        return []
    with p.open(encoding="utf-8") as f:
        return json.load(f)


def annotations_to_csv(annotations):
    if not annotations:
        return ""
    df = pd.DataFrame(annotations)
    buf = io.StringIO()
    df.to_csv(buf, index=False, encoding="utf-8")
    return buf.getvalue()


# -- Welcome screen ---------------------------------------------------------

if not st.session_state.started:
    st.title(":newspaper: Anotacija politicke pristrasnosti")
    st.markdown("""
    <div class='welcome'>
    Hvala sto pomazes! Tvoj zadatak je da ocijenis politicku pristrasnost
    clanaka iz bosanskohercegovackih medija. Po clanku trazimo ocjenu na
    <b>4 dimenzije</b>:
    <br><br>
    1. <b>Ton</b> - koliko je clanak negativan/pozitivan prema akteru (-2 do +2)<br>
    2. <b>Framing</b> - kako je prica postavljena (sukob, ekonomija, itd.)<br>
    3. <b>Balansiranost</b> - koliko strana dobiva prostor (0-2)<br>
    4. <b>Politicki lean</b> - kojoj strani je clanak naklonjen<br>
    <br>
    Po clanku ~3 minute. Mozes pauzirati kad god - <b>preuzmi CSV</b> na kraju
    sesije i posalji ga osobi koja te je pozvala.
    </div>
    """, unsafe_allow_html=True)

    st.markdown("")
    annotator_id = st.text_input("Tvoje ime (ili oznaka anotatora):",
                                  placeholder="npr. Majka, Tata, Marko...",
                                  key="annotator_input")

    # Opciono: nastavak prethodne sesije
    with st.expander("Nastavljas anotaciju iz prethodne sesije? Uploaduj CSV"):
        uploaded = st.file_uploader(
            "Tvoj prethodni CSV (human_*.csv)",
            type=["csv"],
            help="Ako si vec ranije anotirao/la dio clanaka i preuzeo/la CSV, ucitaj ga ovdje da nastavis odakle si stao/la."
        )
        uploaded_excluded = st.file_uploader(
            "Opciono: prethodni CSV odbacenih (excluded_*.csv)",
            type=["csv"],
            key="upload_excluded",
        )

    if st.button(":arrow_forward: Pokreni anotaciju", type="primary"):
        if not annotator_id.strip():
            st.warning("Molim te unesi ime ili oznaku.")
            st.stop()

        st.session_state.annotator_id = annotator_id.strip()

        # Ako je uploaded prethodni CSV, ucitaj
        if uploaded is not None:
            try:
                df = pd.read_csv(uploaded)
                st.session_state.annotations = df.to_dict("records")
                st.success(f"Ucitano {len(df)} prethodnih anotacija.")
            except Exception as e:
                st.error(f"Ne mogu ucitati CSV: {e}")
                st.stop()

        if uploaded_excluded is not None:
            try:
                df_ex = pd.read_csv(uploaded_excluded)
                st.session_state.excluded = df_ex.to_dict("records")
            except Exception:
                pass  # excluded je opcionalan

        st.session_state.started = True
        st.rerun()

    st.stop()


# -- Main app ---------------------------------------------------------------

articles = load_articles()
if not articles:
    st.error(f"Dataset nije dostupan: `{DATASET_PATH}`")
    st.stop()

annotator_id = st.session_state.annotator_id
done_ids = {a["article_id"] for a in st.session_state.annotations}
excluded_ids = {e["article_id"] for e in st.session_state.excluded}
seen = done_ids | excluded_ids
todo = [a for a in articles if str(a.get("article_id")) not in seen]


# -- Sidebar: download i status --------------------------------------------

with st.sidebar:
    st.markdown(f"### Anotator: **{annotator_id}**")
    st.markdown("---")

    c1, c2 = st.columns(2)
    c1.metric("Anotirano", len(done_ids))
    c2.metric("Odbaceno", len(excluded_ids))
    st.metric("Preostalo", len(todo))

    st.markdown("---")
    st.markdown("### :inbox_tray: Preuzmi rezultate")
    st.caption("Klikni nakon svake sesije i posalji CSV korisniku.")

    csv_data = annotations_to_csv(st.session_state.annotations)
    st.download_button(
        label=":arrow_down: Preuzmi moje anotacije (CSV)",
        data=csv_data,
        file_name=f"human_{annotator_id}.csv",
        mime="text/csv",
        disabled=not st.session_state.annotations,
        use_container_width=True,
    )

    if st.session_state.excluded:
        excluded_csv = annotations_to_csv(st.session_state.excluded)
        st.download_button(
            label=":wastebasket: Preuzmi odbacene (CSV)",
            data=excluded_csv,
            file_name=f"excluded_{annotator_id}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    st.markdown("---")
    st.caption(":bulb: Tip: Otvori `docs/codebook.md` u repo-u za detaljne definicije.")


# -- Progress bar -----------------------------------------------------------

st.progress(len(seen) / max(len(articles), 1))
st.caption(f"Napredak: {len(seen)} / {len(articles)} clanaka obradjeno")

if not todo:
    st.success(":tada: Zavrseno! Preuzmi CSV iz sidebar-a i posalji korisniku.")
    if st.session_state.annotations:
        st.dataframe(pd.DataFrame(st.session_state.annotations),
                     use_container_width=True)
    st.stop()


# -- Trenutni clanak --------------------------------------------------------

article = todo[0]
article_id = str(article.get("article_id"))

st.markdown("---")
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

    st.markdown("")
    with st.container(border=True):
        st.markdown("##### Odbaci clanak")
        exclude_reason = st.selectbox(
            "Razlog",
            ["nije politika", "duplikat", "los sadrzaj", "necitljiv tekst", "drugo"],
            key=f"reason_{article_id}",
        )
        exclude_btn = st.button(
            "Odbaci ovaj clanak",
            use_container_width=True,
            key=f"exclude_{article_id}",
        )


if submit:
    st.session_state.annotations.append({
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
    })
    st.session_state.scroll_nonce += 1
    st.session_state.scroll_to_top = True
    st.rerun()

if exclude_btn:
    st.session_state.excluded.append({
        "article_id": article.get("article_id"),
        "portal": article.get("portal"),
        "title": article.get("title"),
        "annotator_id": annotator_id,
        "reason": exclude_reason,
    })
    st.session_state.scroll_nonce += 1
    st.session_state.scroll_to_top = True
    st.rerun()

# -- Scroll to top (na samom kraju, nakon sto je sav sadrzaj renderovan) ----
if st.session_state.scroll_to_top:
    scroll_to_top(st.session_state.scroll_nonce)
    st.session_state.scroll_to_top = False

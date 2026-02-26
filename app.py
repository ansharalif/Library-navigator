import streamlit as st
import pandas as pd

st.set_page_config(page_title="FTF Intel Library Navigator", page_icon="📚", layout="wide")

REQUIRED_COLS = ["title", "year", "country", "topic", "keywords", "source", "link", "priority", "notes"]
PRIORITY_ORDER = {"high": 1, "medium": 2, "low": 3}

# ----------------- Sample data (ringan) -----------------
@st.cache_data(show_spinner=False)
def get_sample_df() -> pd.DataFrame:
    data = [
        {
            "title": "Policy approaches to FTF returnees",
            "year": 2021,
            "country": "United Kingdom",
            "topic": "Prosecution",
            "keywords": "returnees, sentencing, criminal law",
            "source": "Academic",
            "link": "https://example.com/uk-ftf-policy",
            "priority": "High",
            "notes": "Ringkas kebijakan penuntutan & pembuktian",
        },
        {
            "title": "Rehabilitation and reintegration programs",
            "year": 2020,
            "country": "Denmark",
            "topic": "Rehabilitation",
            "keywords": "rehab, reintegration, risk assessment",
            "source": "Government",
            "link": "https://example.com/dk-rehab",
            "priority": "Medium",
            "notes": "Fokus multi-agency",
        },
        {
            "title": "Women and children in returnee management",
            "year": 2022,
            "country": "Iraq",
            "topic": "Women & Children",
            "keywords": "women, children, repatriation, safeguarding",
            "source": "NGO",
            "link": "https://example.com/iq-wc",
            "priority": "High",
            "notes": "Isu perlindungan & screening",
        },
        {
            "title": "Administrative measures for prevention",
            "year": 2019,
            "country": "France",
            "topic": "Prevention",
            "keywords": "administrative, prevention, travel restrictions",
            "source": "Policy brief",
            "link": "https://example.com/fr-prevent",
            "priority": "Low",
            "notes": "Langkah non-penal",
        },
        {
            "title": "Repatriation decision frameworks",
            "year": 2023,
            "country": "Netherlands",
            "topic": "Repatriation",
            "keywords": "repatriation, decision-making, case-by-case",
            "source": "Think tank",
            "link": "https://example.com/nl-repat",
            "priority": "High",
            "notes": "Cocok untuk bahan SOP/brief",
        },
    ]
    return pd.DataFrame(data)

# ----------------- Load + validate (di-cache) -----------------
@st.cache_data(show_spinner=False)
def load_and_validate_csv(file_bytes: bytes) -> pd.DataFrame:
    df = pd.read_csv(pd.io.common.BytesIO(file_bytes))
    df.columns = [c.strip().lower() for c in df.columns]

    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"Kolom kurang: {missing}. Harus ada: {REQUIRED_COLS}")

    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    df["priority"] = df["priority"].fillna("Low")
    df["topic"] = df["topic"].fillna("Uncategorized")
    df["country"] = df["country"].fillna("Unknown")
    for c in ["keywords", "source", "link", "notes", "title"]:
        df[c] = df[c].fillna("").astype(str)

    # normalisasi priority agar konsisten
    df["priority_norm"] = df["priority"].astype(str).str.strip().str.lower()
    df["priority_rank"] = df["priority_norm"].map(PRIORITY_ORDER).fillna(3).astype(int)
    return df

def df_to_csv_bytes(df: pd.DataFrame) -> bytes:
    out = df.drop(columns=[c for c in ["priority_norm", "priority_rank"] if c in df.columns], errors="ignore")
    return out.to_csv(index=False).encode("utf-8")

# ----------------- UI -----------------
st.title("📚 FTF Intel Library Navigator")
st.caption("Katalog referensi tematik FTF untuk analis — search, filter, dan prioritas bacaan.")

with st.sidebar:
    st.header("⚙️ Data Sumber")
    uploaded = st.file_uploader("Upload CSV", type=["csv"])
    use_sample = st.checkbox("Gunakan sample data", value=(uploaded is None))

    st.divider()
    st.header("🧭 Kolom CSV wajib")
    st.code(", ".join(REQUIRED_COLS), language="text")

# ----------------- Get df -----------------
try:
    if uploaded is not None:
        df = load_and_validate_csv(uploaded.getvalue())
    elif use_sample:
        df = get_sample_df()
        # samakan struktur dengan hasil validate
        df.columns = [c.strip().lower() for c in df.columns]
        for col in REQUIRED_COLS:
            if col not in df.columns:
                df[col] = ""
        df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
        df["priority"] = df["priority"].fillna("Low")
        df["priority_norm"] = df["priority"].astype(str).str.strip().str.lower()
        df["priority_rank"] = df["priority_norm"].map(PRIORITY_ORDER).fillna(3).astype(int)
    else:
        st.info("Upload CSV atau centang 'Gunakan sample data'.")
        st.stop()
except Exception as e:
    st.error(f"Gagal memuat data: {e}")
    st.stop()

# ----------------- Filters (ringan) -----------------
with st.sidebar:
    st.header("🔎 Filter & Search")
    q = st.text_input("Search (judul/keyword/catatan/sumber)", value="").strip().lower()

    years = df["year"].dropna()
    if len(years) > 0:
        y_min, y_max = int(years.min()), int(years.max())
    else:
        y_min, y_max = 2000, 2026
    yr = st.slider("Rentang Tahun", min_value=y_min, max_value=y_max, value=(y_min, y_max))

    countries = sorted(df["country"].dropna().unique().tolist())
    topics = sorted(df["topic"].dropna().unique().tolist())
    priorities = ["High", "Medium", "Low"]

    sel_country = st.multiselect("Negara", options=countries, default=[])
    sel_topic = st.multiselect("Topik", options=topics, default=[])
    sel_priority = st.multiselect("Prioritas", options=priorities, default=[])

    st.divider()
    sort_mode = st.selectbox("Urutkan", ["Prioritas → Tahun (baru)", "Tahun (baru) → Prioritas", "Judul A→Z"])
    only_high = st.checkbox("Hanya High", value=False)

    st.divider()
    max_rows = st.number_input("Batasi tampilan baris (biar ringan)", min_value=50, max_value=5000, value=500, step=50)

# ----------------- Filtering (cepat) -----------------
filtered = df.copy()

filtered = filtered[(filtered["year"].isna()) | ((filtered["year"] >= yr[0]) & (filtered["year"] <= yr[1]))]

if sel_country:
    filtered = filtered[filtered["country"].isin(sel_country)]
if sel_topic:
    filtered = filtered[filtered["topic"].isin(sel_topic)]
if sel_priority:
    filtered = filtered[filtered["priority"].astype(str).str.strip().isin(sel_priority)]
if only_high:
    filtered = filtered[filtered["priority_norm"] == "high"]

if q:
    # pakai satu kolom gabungan biar cepat
    blob = (
        filtered["title"].str.lower() + " " +
        filtered["keywords"].str.lower() + " " +
        filtered["notes"].str.lower() + " " +
        filtered["source"].str.lower()
    )
    filtered = filtered[blob.str.contains(q, na=False)]

# sort
if sort_mode == "Prioritas → Tahun (baru)":
    filtered = filtered.sort_values(by=["priority_rank", "year"], ascending=[True, False])
elif sort_mode == "Tahun (baru) → Prioritas":
    filtered = filtered.sort_values(by=["year", "priority_rank"], ascending=[False, True])
else:
    filtered = filtered.sort_values(by=["title"], ascending=True)

# ----------------- KPIs -----------------
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Referensi", len(df))
c2.metric("Hasil Filter", len(filtered))
c3.metric("Prioritas High", int((df["priority_norm"] == "high").sum()))
c4.metric("Topik Unik", int(df["topic"].nunique()))

st.divider()

# ----------------- Priority list -----------------
st.subheader("⭐ Daftar Bacaan Prioritas (High)")
prio = df[df["priority_norm"] == "high"].sort_values(by=["year"], ascending=False)
if len(prio) == 0:
    st.info("Belum ada item prioritas High.")
else:
    st.dataframe(
        prio[["title", "year", "country", "topic", "source", "link", "notes"]],
        use_container_width=True,
        hide_index=True,
        height=260
    )

st.divider()

# ----------------- Main table (dibatasi biar ringan) -----------------
st.subheader("📌 Katalog (Hasil Search/Filter)")
show_df = filtered.head(int(max_rows))
st.caption(f"Menampilkan {len(show_df)} dari {len(filtered)} baris (untuk performa).")
st.dataframe(
    show_df[["title", "year", "country", "topic", "keywords", "source", "link", "priority", "notes"]],
    use_container_width=True,
    hide_index=True,
    height=520
)

# ----------------- Downloads -----------------
colA, colB = st.columns(2)
with colA:
    st.download_button(
        "⬇️ Download hasil filter (CSV)",
        data=df_to_csv_bytes(filtered),
        file_name="ftf_library_filtered.csv",
        mime="text/csv"
    )
with colB:
    st.download_button(
        "⬇️ Download template kosong (CSV)",
        data=",".join(REQUIRED_COLS) + "\n",
        file_name="ftf_library_template.csv",
        mime="text/csv"
    )

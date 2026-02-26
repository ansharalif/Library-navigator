import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(
    page_title="FTF Intel Library Navigator",
    page_icon="📚",
    layout="wide"
)

st.title("📚 FTF Intel Library Navigator")
st.caption("Katalog referensi tematik FTF untuk analis — search, filter, dan prioritas bacaan.")

# ---------- Helpers ----------
REQUIRED_COLS = ["title", "year", "country", "topic", "keywords", "source", "link", "priority", "notes"]

def load_csv(uploaded_file) -> pd.DataFrame:
    df = pd.read_csv(uploaded_file)
    # normalisasi nama kolom
    df.columns = [c.strip().lower() for c in df.columns]
    return df

def validate_df(df: pd.DataFrame) -> pd.DataFrame:
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"Kolom kurang: {missing}. Harus ada: {REQUIRED_COLS}")
    # Tipe data ringan
    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    df["priority"] = df["priority"].fillna("Low")
    df["topic"] = df["topic"].fillna("Uncategorized")
    df["country"] = df["country"].fillna("Unknown")
    df["keywords"] = df["keywords"].fillna("")
    df["source"] = df["source"].fillna("")
    df["link"] = df["link"].fillna("")
    df["notes"] = df["notes"].fillna("")
    return df

def to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")

def priority_rank(p: str) -> int:
    p = (p or "").strip().lower()
    if p == "high":
        return 1
    if p == "medium":
        return 2
    return 3

# ---------- Sidebar: Data ----------
with st.sidebar:
    st.header("⚙️ Data Sumber")
    st.write("Upload CSV katalog kamu, atau gunakan sample bawaan.")
    uploaded = st.file_uploader("Upload file CSV", type=["csv"])

    use_sample = st.checkbox("Gunakan sample data", value=(uploaded is None))

    st.divider()
    st.header("🧭 Panduan Kolom CSV")
    st.code(", ".join(REQUIRED_COLS), language="text")
    st.caption("Minimal kolom di atas harus ada (huruf kecil/kapital tidak masalah).")

# ---------- Load data ----------
df = None
try:
    if uploaded is not None:
        df = load_csv(uploaded)
        df = validate_df(df)
    elif use_sample:
        # fallback sample via embedded creation
        sample_csv = """title,year,country,topic,keywords,source,link,priority,notes
Policy approaches to FTF returnees,2021,United Kingdom,Prosecution,"returnees, sentencing, criminal law",Academic,https://example.com/uk-ftf-policy,High,"Ringkas kebijakan penuntutan & pembuktian"
Rehabilitation and reintegration programs,2020,Denmark,Rehabilitation,"rehab, reintegration, risk assessment",Government,https://example.com/dk-rehab,Medium,"Fokus multi-agency"
Women and children in returnee management,2022,Iraq,Women & Children,"women, children, repatriation, safeguarding",NGO,https://example.com/iq-wc,High,"Isu perlindungan & screening"
Administrative measures for prevention,2019,France,Prevention,"administrative, prevention, travel restrictions",Policy brief,https://example.com/fr-prevent,Low,"Langkah non-penal"
Repatriation decision frameworks,2023,Netherlands,Repatriation,"repatriation, decision-making, case-by-case",Think tank,https://example.com/nl-repat,High,"Cocok untuk bahan SOP/brief"
"""
        df = pd.read_csv(BytesIO(sample_csv.encode("utf-8")))
        df.columns = [c.strip().lower() for c in df.columns]
        df = validate_df(df)
    else:
        st.info("Silakan upload CSV atau centang 'Gunakan sample data'.")
        st.stop()
except Exception as e:
    st.error(f"Gagal memuat data: {e}")
    st.stop()

# ---------- Sidebar: Filters ----------
with st.sidebar:
    st.header("🔎 Filter & Search")

    q = st.text_input("Search (judul/keyword/catatan)", value="").strip()

    # Year range
    year_min = int(df["year"].dropna().min()) if df["year"].notna().any() else 2000
    year_max = int(df["year"].dropna().max()) if df["year"].notna().any() else 2026
    yr = st.slider("Rentang Tahun", min_value=year_min, max_value=year_max, value=(year_min, year_max))

    countries = sorted(df["country"].dropna().unique().tolist())
    topics = sorted(df["topic"].dropna().unique().tolist())
    priorities = ["High", "Medium", "Low"]

    sel_country = st.multiselect("Negara", options=countries, default=[])
    sel_topic = st.multiselect("Topik", options=topics, default=[])
    sel_priority = st.multiselect("Prioritas", options=priorities, default=[])

    st.divider()
    sort_mode = st.selectbox("Urutkan", options=["Prioritas → Tahun (baru)", "Tahun (baru) → Prioritas", "Judul A→Z"])
    show_priority_only = st.checkbox("Tampilkan hanya prioritas High", value=False)

# ---------- Apply filters ----------
filtered = df.copy()

# year filter
filtered = filtered[(filtered["year"].isna()) | ((filtered["year"] >= yr[0]) & (filtered["year"] <= yr[1]))]

if sel_country:
    filtered = filtered[filtered["country"].isin(sel_country)]
if sel_topic:
    filtered = filtered[filtered["topic"].isin(sel_topic)]
if sel_priority:
    filtered = filtered[filtered["priority"].str.strip().isin(sel_priority)]
if show_priority_only:
    filtered = filtered[filtered["priority"].str.strip().str.lower() == "high"]

if q:
    ql = q.lower()
    mask = (
        filtered["title"].str.lower().str.contains(ql, na=False) |
        filtered["keywords"].str.lower().str.contains(ql, na=False) |
        filtered["notes"].str.lower().str.contains(ql, na=False) |
        filtered["source"].str.lower().str.contains(ql, na=False)
    )
    filtered = filtered[mask]

# sort
if sort_mode == "Prioritas → Tahun (baru)":
    filtered = filtered.assign(_pr=filtered["priority"].map(priority_rank))
    filtered = filtered.sort_values(by=["_pr", "year"], ascending=[True, False]).drop(columns=["_pr"])
elif sort_mode == "Tahun (baru) → Prioritas":
    filtered = filtered.assign(_pr=filtered["priority"].map(priority_rank))
    filtered = filtered.sort_values(by=["year", "_pr"], ascending=[False, True]).drop(columns=["_pr"])
else:
    filtered = filtered.sort_values(by=["title"], ascending=True)

# ---------- Main: KPIs ----------
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Referensi", len(df))
c2.metric("Hasil Filter", len(filtered))
c3.metric("Prioritas High", int((df["priority"].str.strip().str.lower() == "high").sum()))
c4.metric("Topik Unik", df["topic"].nunique())

st.divider()

# ---------- Main: Priority reading list ----------
st.subheader("⭐ Daftar Bacaan Prioritas (High)")
prio = df[df["priority"].str.strip().str.lower() == "high"].copy()
prio = prio.sort_values(by=["year"], ascending=False)

if len(prio) == 0:
    st.info("Belum ada item prioritas High di data kamu.")
else:
    st.dataframe(
        prio[["title", "year", "country", "topic", "source", "link", "notes"]],
        use_container_width=True,
        hide_index=True
    )

st.divider()

# ---------- Main: Filtered table ----------
st.subheader("📌 Katalog (Hasil Search/Filter)")
st.dataframe(
    filtered[["title", "year", "country", "topic", "keywords", "source", "link", "priority", "notes"]],
    use_container_width=True,
    hide_index=True
)

# ---------- Downloads ----------
colA, colB = st.columns(2)
with colA:
    st.download_button(
        "⬇️ Download hasil filter (CSV)",
        data=to_csv_bytes(filtered),
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

st.caption("Catatan: aplikasi ini contoh. Untuk produksi internal, link/sumber sebaiknya disesuaikan dan divalidasi.")

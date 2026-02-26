import streamlit as st
import csv
import io
from typing import List, Dict, Tuple

st.set_page_config(page_title="FTF Intel Library Navigator", page_icon="📚", layout="wide")

REQUIRED_COLS = ["title", "year", "country", "topic", "keywords", "source", "link", "priority", "notes"]
PRIORITY_ORDER = {"high": 1, "medium": 2, "low": 3}

def normalize_colname(s: str) -> str:
    return (s or "").strip().lower()

def normalize_priority(p: str) -> str:
    p = (p or "").strip().lower()
    return p if p in ("high", "medium", "low") else "low"

def parse_year(y: str):
    try:
        yy = int(str(y).strip())
        if 0 < yy < 3000:
            return yy
    except:
        pass
    return None

@st.cache_data(show_spinner=False)
def get_sample_rows() -> List[Dict[str, str]]:
    return [
        {
            "title": "Policy approaches to FTF returnees",
            "year": "2021",
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
            "year": "2020",
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
            "year": "2022",
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
            "year": "2019",
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
            "year": "2023",
            "country": "Netherlands",
            "topic": "Repatriation",
            "keywords": "repatriation, decision-making, case-by-case",
            "source": "Think tank",
            "link": "https://example.com/nl-repat",
            "priority": "High",
            "notes": "Cocok untuk bahan SOP/brief",
        },
    ]

@st.cache_data(show_spinner=False)
def load_csv_bytes(file_bytes: bytes) -> List[Dict[str, str]]:
    text = file_bytes.decode("utf-8", errors="replace")
    f = io.StringIO(text)
    reader = csv.DictReader(f)
    if reader.fieldnames is None:
        raise ValueError("CSV tidak memiliki header.")

    # normalisasi nama kolom
    original_fields = reader.fieldnames
    fields_norm = [normalize_colname(c) for c in original_fields]

    # map original -> normalized
    mapping = {orig: norm for orig, norm in zip(original_fields, fields_norm)}

    missing = [c for c in REQUIRED_COLS if c not in fields_norm]
    if missing:
        raise ValueError(f"Kolom kurang: {missing}. Wajib: {REQUIRED_COLS}")

    rows: List[Dict[str, str]] = []
    for r in reader:
        row_norm = {mapping[k]: (v if v is not None else "") for k, v in r.items()}
        # pastikan semua kolom ada
        for col in REQUIRED_COLS:
            row_norm.setdefault(col, "")
        rows.append(row_norm)
    return rows

def compute_meta(rows: List[Dict[str, str]]) -> Dict:
    years = [parse_year(r.get("year", "")) for r in rows]
    years_clean = [y for y in years if y is not None]
    y_min = min(years_clean) if years_clean else 2000
    y_max = max(years_clean) if years_clean else 2026

    countries = sorted({(r.get("country") or "Unknown").strip() or "Unknown" for r in rows})
    topics = sorted({(r.get("topic") or "Uncategorized").strip() or "Uncategorized" for r in rows})

    high_count = sum(1 for r in rows if normalize_priority(r.get("priority")) == "high")
    topic_count = len({(r.get("topic") or "").strip().lower() for r in rows if (r.get("topic") or "").strip()})

    return {
        "y_min": y_min,
        "y_max": y_max,
        "countries": countries,
        "topics": topics,
        "high_count": high_count,
        "topic_count": topic_count,
    }

def matches_query(r: Dict[str, str], q: str) -> bool:
    if not q:
        return True
    blob = " ".join([
        r.get("title", ""),
        r.get("keywords", ""),
        r.get("notes", ""),
        r.get("source", ""),
        r.get("country", ""),
        r.get("topic", ""),
        r.get("priority", ""),
    ]).lower()
    return q in blob

def apply_filters(
    rows: List[Dict[str, str]],
    q: str,
    year_range: Tuple[int, int],
    sel_country: List[str],
    sel_topic: List[str],
    sel_priority: List[str],
    only_high: bool
) -> List[Dict[str, str]]:
    y0, y1 = year_range
    sel_country_set = set(sel_country)
    sel_topic_set = set(sel_topic)
    sel_priority_norm = {s.strip().lower() for s in sel_priority}

    out = []
    for r in rows:
        y = parse_year(r.get("year", ""))
        if y is not None and not (y0 <= y <= y1):
            continue

        country = (r.get("country") or "Unknown").strip() or "Unknown"
        topic = (r.get("topic") or "Uncategorized").strip() or "Uncategorized"
        pr_norm = normalize_priority(r.get("priority"))

        if sel_country_set and country not in sel_country_set:
            continue
        if sel_topic_set and topic not in sel_topic_set:
            continue
        if sel_priority_norm and pr_norm not in sel_priority_norm:
            continue
        if only_high and pr_norm != "high":
            continue
        if not matches_query(r, q):
            continue

        out.append(r)
    return out

def sort_rows(rows: List[Dict[str, str]], mode: str) -> List[Dict[str, str]]:
    def yval(r): 
        y = parse_year(r.get("year", ""))
        return y if y is not None else -1

    def prank(r):
        return PRIORITY_ORDER.get(normalize_priority(r.get("priority")), 3)

    if mode == "Prioritas → Tahun (baru)":
        return sorted(rows, key=lambda r: (prank(r), -yval(r)))
    if mode == "Tahun (baru) → Prioritas":
        return sorted(rows, key=lambda r: (-yval(r), prank(r)))
    return sorted(rows, key=lambda r: (r.get("title") or "").lower())

def to_csv(rows: List[Dict[str, str]]) -> bytes:
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=REQUIRED_COLS, extrasaction="ignore")
    writer.writeheader()
    for r in rows:
        writer.writerow({c: r.get(c, "") for c in REQUIRED_COLS})
    return out.getvalue().encode("utf-8")

# ---------------- UI ----------------
st.title("📚 FTF Intel Library Navigator")
st.caption("Versi ringan (tanpa pandas) agar deployment Streamlit Cloud lebih cepat.")

with st.sidebar:
    st.header("⚙️ Data Sumber")
    uploaded = st.file_uploader("Upload CSV", type=["csv"])
    use_sample = st.checkbox("Gunakan sample data", value=(uploaded is None))

    st.divider()
    st.header("🧭 Kolom CSV wajib")
    st.code(", ".join(REQUIRED_COLS), language="text")

# Load rows
try:
    if uploaded is not None:
        rows = load_csv_bytes(uploaded.getvalue())
    elif use_sample:
        rows = get_sample_rows()
    else:
        st.info("Upload CSV atau centang 'Gunakan sample data'.")
        st.stop()
except Exception as e:
    st.error(f"Gagal memuat data: {e}")
    st.stop()

meta = compute_meta(rows)

with st.sidebar:
    st.header("🔎 Filter & Search")
    q = st.text_input("Search", value="").strip().lower()

    yr = st.slider("Rentang Tahun", min_value=meta["y_min"], max_value=meta["y_max"], value=(meta["y_min"], meta["y_max"]))

    sel_country = st.multiselect("Negara", options=meta["countries"], default=[])
    sel_topic = st.multiselect("Topik", options=meta["topics"], default=[])
    sel_priority = st.multiselect("Prioritas", options=["High", "Medium", "Low"], default=[])

    st.divider()
    sort_mode = st.selectbox("Urutkan", ["Prioritas → Tahun (baru)", "Tahun (baru) → Prioritas", "Judul A→Z"])
    only_high = st.checkbox("Hanya High", value=False)

    st.divider()
    max_rows = st.number_input("Batasi tampilan baris", min_value=50, max_value=5000, value=500, step=50)

filtered = apply_filters(rows, q, yr, sel_country, sel_topic, sel_priority, only_high)
filtered = sort_rows(filtered, sort_mode)

high_rows = [r for r in rows if normalize_priority(r.get("priority")) == "high"]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Referensi", len(rows))
c2.metric("Hasil Filter", len(filtered))
c3.metric("Prioritas High", len(high_rows))
c4.metric("Topik Unik", meta["topic_count"])

st.divider()

st.subheader("⭐ Daftar Bacaan Prioritas (High)")
high_sorted = sorted(high_rows, key=lambda r: -(parse_year(r.get("year", "")) or -1))
if not high_sorted:
    st.info("Belum ada item prioritas High.")
else:
    show_high = high_sorted[: min(200, len(high_sorted))]
    st.dataframe(show_high, use_container_width=True, hide_index=True, height=260)

st.divider()

st.subheader("📌 Katalog (Hasil Search/Filter)")
show_df = filtered[: int(max_rows)]
st.caption(f"Menampilkan {len(show_df)} dari {len(filtered)} baris (untuk performa).")
st.dataframe(show_df, use_container_width=True, hide_index=True, height=520)

colA, colB = st.columns(2)
with colA:
    st.download_button(
        "⬇️ Download hasil filter (CSV)",
        data=to_csv(filtered),
        file_name="ftf_library_filtered.csv",
        mime="text/csv"
    )
with colB:
    st.download_button(
        "⬇️ Download template kosong (CSV)",
        data=(",".join(REQUIRED_COLS) + "\n").encode("utf-8"),
        file_name="ftf_library_template.csv",
        mime="text/csv"
    )

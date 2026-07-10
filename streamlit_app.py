import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from supabase import create_client
from datetime import date

st.set_page_config(page_title="Monitoring Pembayaran Principal", layout="wide")

# =========================================================
# PALET WARNA -- White Tissue + Merah
# =========================================================
TISSUE       = "#F7F1E8"   # background utama, putih tisu hangat
TISSUE_SOFT  = "#FFFDF9"   # background kartu, lebih terang
RED          = "#A31D25"   # merah utama
RED_DARK     = "#7A151B"   # merah gelap (hover/aksen)
RED_SOFT     = "#F1D9D6"   # merah muda utk background lembut
INK          = "#2B2422"   # warna teks utama
INK_SOFT     = "#6B6058"   # teks sekunder
LINE         = "#E4D9C8"   # garis pembatas halus

st.markdown(f"""
<style>
    .stApp {{
        background-color: {TISSUE};
    }}
    html, body, [class*="css"] {{
        color: {INK};
        font-family: 'Georgia', 'Times New Roman', serif;
    }}
    section[data-testid="stSidebar"] {{
        background-color: {TISSUE_SOFT};
        border-right: 1px solid {LINE};
    }}
    div[data-testid="stMetric"] {{
        background-color: {TISSUE_SOFT};
        border: 1px solid {LINE};
        border-left: 4px solid {RED};
        border-radius: 4px;
        padding: 14px 16px 10px 16px;
    }}
    div[data-testid="stMetricLabel"] {{
        color: {INK_SOFT};
        letter-spacing: 0.04em;
        text-transform: uppercase;
        font-size: 0.75rem;
    }}
    div[data-testid="stMetricValue"] {{
        color: {RED_DARK};
        font-weight: 700;
    }}
    .brand-row {{
        display: flex;
        align-items: center;
        gap: 16px;
        padding-bottom: 6px;
        border-bottom: 2px solid {RED};
        margin-bottom: 18px;
    }}
    .brand-title {{
        font-size: 1.6rem;
        font-weight: 700;
        color: {INK};
        letter-spacing: 0.02em;
    }}
    .brand-subtitle {{
        font-size: 0.85rem;
        color: {INK_SOFT};
        letter-spacing: 0.06em;
        text-transform: uppercase;
    }}
    .notice-box {{
        border: 1px solid {RED};
        border-left: 5px solid {RED};
        background-color: {RED_SOFT};
        color: {INK};
        border-radius: 4px;
        padding: 12px 16px;
        margin: 10px 0 18px 0;
        font-size: 0.95rem;
    }}
    .notice-box .mark {{
        color: {RED_DARK};
        font-weight: 700;
        margin-right: 6px;
    }}
    .section-head {{
        display: flex;
        align-items: center;
        gap: 8px;
        margin-top: 6px;
        margin-bottom: 4px;
    }}
    .section-mark {{
        display: inline-block;
        width: 10px;
        height: 10px;
        background-color: {RED};
        transform: rotate(45deg);
    }}
    .section-title {{
        font-size: 1.05rem;
        font-weight: 700;
        color: {INK};
    }}
    .stDownloadButton button {{
        background-color: {RED};
        color: {TISSUE_SOFT};
        border: none;
        border-radius: 3px;
    }}
    .stDownloadButton button:hover {{
        background-color: {RED_DARK};
        color: {TISSUE_SOFT};
    }}
    hr {{
        border-color: {LINE};
    }}
</style>
""", unsafe_allow_html=True)

# ── Logo/simbol custom (SVG buatan sendiri, bukan emoji) ──
LOGO_SVG = f"""
<svg width="46" height="46" viewBox="0 0 46 46" xmlns="http://www.w3.org/2000/svg">
  <rect x="1" y="1" width="44" height="44" rx="6" fill="{TISSUE_SOFT}" stroke="{RED}" stroke-width="2"/>
  <path d="M23 8 L23 38 M8 23 L38 23" stroke="{RED_SOFT}" stroke-width="2"/>
  <path d="M14 30 L20 18 L26 26 L32 14" fill="none" stroke="{RED}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
  <circle cx="32" cy="14" r="2.6" fill="{RED_DARK}"/>
</svg>
"""

def section_head(text):
    st.markdown(
        f'<div class="section-head"><span class="section-mark"></span>'
        f'<span class="section-title">{text}</span></div>',
        unsafe_allow_html=True,
    )

def notice(text, mark="!"):
    st.markdown(
        f'<div class="notice-box"><span class="mark">[{mark}]</span>{text}</div>',
        unsafe_allow_html=True,
    )

# =========================================================
# Koneksi Supabase (pakai ANON key -- aman untuk publik, read-only)
# Diisi lewat Streamlit Secrets, lihat PANDUAN_WEB.txt
# =========================================================
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_ANON_KEY = st.secrets["SUPABASE_ANON_KEY"]

@st.cache_resource
def get_client():
    return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

sb = get_client()

@st.cache_data(ttl=300)  # cache 5 menit biar tidak boros request
def load_data():
    all_rows = []
    page_size = 1000
    start = 0
    while True:
        resp = (
            sb.table("monitoring_pembayaran")
            .select("*")
            .range(start, start + page_size - 1)
            .execute()
        )
        chunk = resp.data
        all_rows.extend(chunk)
        if len(chunk) < page_size:
            break
        start += page_size
    df = pd.DataFrame(all_rows)
    if df.empty:
        return df
    df["tanggal_jatuh_tempo"] = pd.to_datetime(df["tanggal_jatuh_tempo"], errors="coerce")
    df["tanggal_bayar"] = pd.to_datetime(df["tanggal_bayar"], errors="coerce")
    df["nominal_invoice"] = pd.to_numeric(df["nominal_invoice"], errors="coerce")
    return df

# ── Header / brand ──────────────────────────────
st.markdown(
    f'<div class="brand-row">{LOGO_SVG}'
    f'<div><div class="brand-title">Monitoring Pembayaran Principal</div>'
    f'<div class="brand-subtitle">SIMBA &middot; NSI &middot; MEIJI</div></div></div>',
    unsafe_allow_html=True,
)

df = load_data()

if df.empty:
    notice("Belum ada data di Supabase. Jalankan upload_to_supabase.py dulu di komputer kamu.")
    st.stop()

# ── Sidebar filter ─────────────────────────────
st.sidebar.markdown('<div class="section-title">Filter</div>', unsafe_allow_html=True)
principals = sorted(df["principal"].dropna().unique().tolist())
pilih_principal = st.sidebar.multiselect("Principal", principals, default=principals)

status_opsi = ["LUNAS", "BELUM LUNAS"]
pilih_status = st.sidebar.multiselect("Status", status_opsi, default=status_opsi)

cari_invoice = st.sidebar.text_input("Cari No Invoice")

df_f = df[df["principal"].isin(pilih_principal) & df["status"].isin(pilih_status)]
if cari_invoice:
    df_f = df_f[df_f["no_invoice"].astype(str).str.contains(cari_invoice, case=False, na=False)]

# ── Ringkasan / KPI ─────────────────────────────
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Invoice", f"{len(df_f):,}")
col2.metric("Lunas", f"{(df_f['status']=='LUNAS').sum():,}")
col3.metric("Belum Lunas", f"{(df_f['status']=='BELUM LUNAS').sum():,}")
total_belum_rp = df_f.loc[df_f["status"] == "BELUM LUNAS", "nominal_invoice"].sum()
col4.metric("Nominal Belum Lunas", f"Rp {total_belum_rp:,.0f}")

# invoice jatuh tempo / lewat jatuh tempo tapi belum lunas
today = pd.Timestamp(date.today())
overdue = df_f[(df_f["status"] == "BELUM LUNAS") & (df_f["tanggal_jatuh_tempo"] < today)]
if len(overdue):
    notice(
        f"{len(overdue):,} invoice sudah LEWAT JATUH TEMPO dan belum dibayar "
        f"(total Rp {overdue['nominal_invoice'].sum():,.0f})"
    )

st.divider()

# ── Grafik (Plotly, palet tissue + merah) ───────

def styled_fig(fig, height=340):
    fig.update_layout(
        plot_bgcolor=TISSUE_SOFT,
        paper_bgcolor=TISSUE_SOFT,
        font=dict(color=INK, family="Georgia, serif"),
        legend=dict(bgcolor=TISSUE_SOFT),
        height=height,
        margin=dict(l=10, r=10, t=30, b=10),
    )
    fig.update_xaxes(gridcolor=LINE, zerolinecolor=LINE)
    fig.update_yaxes(gridcolor=LINE, zerolinecolor=LINE)
    return fig

c1, c2 = st.columns(2)

with c1:
    section_head("Status per Principal")
    pivot = df_f.groupby(["principal", "status"]).size().unstack(fill_value=0)
    fig = go.Figure()
    for status in pivot.columns:
        color = RED if status == "BELUM LUNAS" else INK_SOFT
        fig.add_bar(name=status, x=pivot.index, y=pivot[status], marker_color=color)
    fig.update_layout(barmode="stack")
    st.plotly_chart(styled_fig(fig), use_container_width=True)

with c2:
    section_head("Nominal Belum Lunas per Principal")
    nominal_pivot = (
        df_f[df_f["status"] == "BELUM LUNAS"]
        .groupby("principal")["nominal_invoice"].sum()
        .sort_values(ascending=False)
    )
    fig = go.Figure(go.Bar(x=nominal_pivot.index, y=nominal_pivot.values, marker_color=RED))
    st.plotly_chart(styled_fig(fig), use_container_width=True)

section_head("Tren Jatuh Tempo (Belum Lunas) per Bulan")
belum = df_f[df_f["status"] == "BELUM LUNAS"].copy()
if not belum.empty:
    belum["bulan_jatuh_tempo"] = belum["tanggal_jatuh_tempo"].dt.to_period("M").astype(str)
    tren = belum.groupby("bulan_jatuh_tempo")["nominal_invoice"].sum().sort_index()
    fig = go.Figure(go.Bar(x=tren.index, y=tren.values, marker_color=RED_DARK))
    st.plotly_chart(styled_fig(fig, height=300), use_container_width=True)

st.divider()

# ── Tabel detail ────────────────────────────────
section_head("Detail Data")
kolom_tampil = [
    "principal", "no_invoice", "no_payment_advice", "nominal_invoice",
    "no_miro", "tanggal_jatuh_tempo", "tanggal_bayar", "status",
    "sumber_file", "sumber_sheet",
]
st.dataframe(
    df_f[kolom_tampil].sort_values("tanggal_jatuh_tempo", ascending=False),
    use_container_width=True,
    hide_index=True,
)

st.download_button(
    "Unduh Hasil Filter (CSV)",
    df_f[kolom_tampil].to_csv(index=False, sep=";").encode("utf-8-sig"),
    file_name="monitoring_pembayaran_filtered.csv",
    mime="text/csv",
)

st.caption("Data otomatis dari Supabase. Untuk update data terbaru, jalankan "
           "upload_to_supabase.py di komputer lalu refresh halaman ini "
           "(cache dashboard otomatis kadaluarsa tiap 5 menit).")

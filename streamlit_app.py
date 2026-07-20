import base64
import os

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from supabase import create_client
from datetime import date

st.set_page_config(
    page_title="Monitoring Pembayaran Principal",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =========================================================
# PALET WARNA -- disamakan dengan design system app.py (Monitoring EBT)
# supaya kedua dashboard PMA terasa satu keluarga: bone-white +
# PMA red + IBM Plex Mono untuk angka, bukan lagi merah generik.
# =========================================================
BG        = "#FFFFFF"
BG_SOFT   = "#FBF9F6"   # bone white -- sama seperti BONE_WHITE di app.py
CARD      = "#FFFFFF"
RED       = "#B01C2E"   # PMA_RED -- disamakan dengan app.py
RED_HOVER = "#D94F5C"   # PMA_RED_SOFT -- state hover tombol, sama seperti app.py
RED_DARK  = "#8A1522"
RED_SOFT  = "#F6DADD"   # disamakan dengan PRIMARY_FIXED app.py
INK       = "#26221F"   # disamakan dengan app.py
INK_SOFT  = "#8A8078"   # disamakan dengan MUTED app.py
LINE      = "#ECE6DF"   # disamakan dengan BORDER app.py
GREEN     = "#16A34A"
GREEN_SOFT= "#E9F9EF"
AMBER     = "#B45309"
AMBER_SOFT= "#FEF3E2"
MONO_FONT = "'IBM Plex Mono', monospace"  # font angka finansial, seperti di app.py

# =========================================================
# LOGO -- assets/logo.png (satu folder dengan file ini di repo),
# sama persis polanya dengan app.py: dibaca sekali, di-cache sebagai
# base64, dan kalau filenya belum ada, fallback ke mark teks lama
# supaya app tetap jalan normal (tidak error).
# =========================================================
LOGO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "logo.png")


@st.cache_data(show_spinner=False)
def load_logo_b64():
    try:
        with open(LOGO_PATH, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except FileNotFoundError:
        return None


def logo_html(height_px, fallback_html):
    b64 = load_logo_b64()
    if b64:
        return (f'<img src="data:image/png;base64,{b64}" '
                f'style="height:{height_px}px;width:auto;display:block;border-radius:8px;" alt="Logo">')
    return fallback_html  # jaga-jaga kalau assets/logo.png belum ke-upload ke repo


# =========================================================
# IKON KUSTOM (SVG, bukan emoji) -- dipakai di sidebar, notice box,
# judul halaman, dan tombol download supaya tampilan konsisten &
# tidak bergantung pada font emoji bawaan OS/browser.
# Semua ikon digambar sendiri dengan gaya garis (outline) yang
# seragam: stroke 1.8, ujung & sambungan membulat.
# =========================================================
def icon_svg(name, color="currentColor", size=16):
    common = 'fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"'
    bodies = {
        # 4 kotak membulat tersusun rapi -> "Dashboard"
        "grid": f'''
            <rect x="3" y="3" width="7.5" height="7.5" rx="2" {common}/>
            <rect x="13.5" y="3" width="7.5" height="7.5" rx="2" {common}/>
            <rect x="3" y="13.5" width="7.5" height="7.5" rx="2" {common}/>
            <rect x="13.5" y="13.5" width="7.5" height="7.5" rx="2" {common}/>
        ''',
        # tiga batang naik dengan titik tren -> "Principal"
        "bars": f'''
            <rect x="3" y="13" width="4" height="8" rx="1.2" fill="currentColor" stroke="none"/>
            <rect x="10" y="8.5" width="4" height="12.5" rx="1.2" fill="currentColor" stroke="none"/>
            <rect x="17" y="3.5" width="4" height="17.5" rx="1.2" fill="currentColor" stroke="none"/>
            <path d="M3 9.5 L9.5 5 L14.5 7.5 L21 2" {common}/>
        ''',
        # koin bergaris tepi + simbol nilai -> "Pembayaran"
        "coin": f'''
            <circle cx="12" cy="12" r="9" {common}/>
            <circle cx="12" cy="12" r="4.6" {common}/>
            <line x1="12" y1="3" x2="12" y2="5.4" {common}/>
            <line x1="12" y1="18.6" x2="12" y2="21" {common}/>
        ''',
        # lingkaran + centang -> "Lunas"
        "check": f'''
            <circle cx="12" cy="12" r="9" {common}/>
            <path d="M7.5 12.5 L10.5 15.5 L16.5 9" {common}/>
        ''',
        # segitiga peringatan membulat + seru -> pengganti "⚠"
        "warn": f'''
            <path d="M12 3.2 L21 19.6 A1.6 1.6 0 0 1 19.6 22 H4.4 A1.6 1.6 0 0 1 3 19.6 Z" {common}/>
            <line x1="12" y1="9.6" x2="12" y2="14.6" {common}/>
            <circle cx="12" cy="17.6" r="1" fill="currentColor" stroke="none"/>
        ''',
        # panah turun menuju baki -> pengganti "⬇"
        "download": f'''
            <line x1="12" y1="3" x2="12" y2="14.5" {common}/>
            <path d="M7 10 L12 15 L17 10" {common}/>
            <path d="M4 18 v1.6 a1.4 1.4 0 0 0 1.4 1.4 h13.2 a1.4 1.4 0 0 0 1.4 -1.4 V18" {common}/>
        ''',
    }
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" '
        f'xmlns="http://www.w3.org/2000/svg" style="vertical-align:-3px;color:{color};">'
        f'{bodies[name]}</svg>'
    )

def icon_badge(name, fg, bg, size=34, icon_size=16, radius=None):
    """Bungkus ikon dalam lingkaran/kotak membulat berwarna -- biar terasa
    seperti ikon buatan sendiri yang matang, bukan garis polos mengambang."""
    radius = size / 2.6 if radius is None else radius
    return (
        f'<span style="display:inline-flex;align-items:center;justify-content:center;'
        f'width:{size}px;height:{size}px;min-width:{size}px;border-radius:{radius}px;'
        f'background:{bg};color:{fg};flex-shrink:0;">'
        f'{icon_svg(name, fg, icon_size)}</span>'
    )

def section_title(name, text):
    """Judul seksi bergaris merah + ikon, murni presentasi -- dipakai untuk
    memberi jarak & hierarki visual antar blok konten, meniru .section-title
    di app.py."""
    return f'<div class="section-title">{icon_svg(name, RED, 18)}{text}</div>'


st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=IBM+Plex+Mono:wght@500;600&display=swap');

    #MainMenu, footer {{visibility: hidden;}}
    /* Sengaja TIDAK menyentuh visibility/display pada elemen <header>,
       cukup disamakan warna latarnya -- kalau header ikut disembunyikan,
       tombol buka-tutup sidebar (<< / >>) ikut hilang dan sidebar yang
       sudah dikecilkan jadi tidak bisa dimunculkan lagi. */
    [data-testid="stHeader"] {{ background-color: {BG_SOFT}; }}

    .stApp {{
        background-color: {BG_SOFT};
    }}
    html, body, [class*="css"] {{
        color: {INK};
        font-family: 'Inter', 'Segoe UI', -apple-system, sans-serif;
    }}

    /* angka finansial (invoice, rupiah) pakai mono biar rapi & mudah dibaca,
       konsisten dengan gaya kartu di app.py */
    .mono-num {{
        font-family: {MONO_FONT};
        font-variant-numeric: tabular-nums;
    }}

    /* judul seksi bergaris merah -- pemisah antar blok konten,
       sama seperti .section-title di app.py */
    .section-title {{
        display: flex; align-items: center; gap: 8px;
        font-size: 1.02rem; font-weight: 700; color: {INK};
        border-left: 3px solid {RED};
        padding-left: 10px;
        margin: 28px 0 14px 0;
    }}
    .section-title svg {{ color: {RED}; }}

    /* kartu KPI custom (label + ikon, nilai mono, keterangan) --
       menggantikan st.metric polos di baris ringkasan atas */
    .kpi-label {{
        display: flex; align-items: center; gap: 6px;
        font-size: 0.74rem; font-weight: 700; color: {INK_SOFT};
        text-transform: uppercase; letter-spacing: 0.03em;
        white-space: nowrap;
    }}
    .kpi-value {{
        font-family: {MONO_FONT};
        font-size: 1.55rem; font-weight: 600; color: {INK};
        margin-top: 8px; font-variant-numeric: tabular-nums;
    }}
    .kpi-value.red {{ color: {RED}; }}
    .kpi-delta {{
        font-size: 0.76rem; margin-top: 4px; color: {INK_SOFT};
    }}

    /* ---- sidebar ---- */
    section[data-testid="stSidebar"] {{
        background-color: {BG};
        border-right: 1px solid {LINE};
    }}
    section[data-testid="stSidebar"] .block-container {{
        padding-top: 1.2rem;
    }}

    /* ---- main container padding ---- */
    .block-container {{
        padding-top: 1.6rem;
        padding-bottom: 2rem;
        max-width: 1400px;
    }}

    /* ---- top bar ---- */
    .topbar {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding-bottom: 14px;
        border-bottom: 1px solid {LINE};
        margin-bottom: 22px;
    }}
    .topbar-brand {{
        display: flex;
        align-items: center;
        gap: 10px;
    }}
    .topbar-brand .mark {{
        width: 34px; height: 34px;
        background: {RED};
        border-radius: 10px;
        display: flex; align-items: center; justify-content: center;
        color: white; font-weight: 800; font-size: 1rem;
    }}
    .topbar-title {{
        font-size: 1.15rem;
        font-weight: 800;
        color: {RED_DARK};
        letter-spacing: -0.01em;
    }}
    .topbar-user {{
        text-align: right;
        font-size: 0.82rem;
        color: {INK_SOFT};
    }}
    .topbar-user b {{ color: {INK}; font-size: 0.9rem; }}

    /* ---- sidebar brand ---- */
    .side-brand {{
        display: flex; align-items: center; gap: 10px;
        padding: 4px 6px 20px 6px;
        margin-bottom: 6px;
        border-bottom: 1px solid {LINE};
    }}
    .side-brand .mark {{
        width: 38px; height: 38px;
        background: {RED};
        border-radius: 11px;
        display: flex; align-items: center; justify-content: center;
        color: white; font-weight: 800; font-size: 1.1rem;
    }}
    .side-brand-title {{ font-weight: 800; font-size: 1rem; color: {INK}; }}
    .side-brand-sub {{ font-size: 0.72rem; color: {INK_SOFT}; }}

    /* ---- page heading ---- */
    .page-title {{
        font-size: 1.9rem;
        font-weight: 800;
        color: {INK};
        letter-spacing: -0.02em;
        margin-bottom: 2px;
    }}
    .page-subtitle {{
        font-size: 0.92rem;
        color: {INK_SOFT};
        margin-bottom: 22px;
    }}

    /* ---- KPI cards ---- */
    div[data-testid="stMetric"] {{
        background-color: {CARD};
        border: 1px solid {LINE};
        border-radius: 14px;
        padding: 16px 18px 14px 18px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.03);
    }}
    div[data-testid="stMetricLabel"] {{
        color: {INK_SOFT};
        letter-spacing: 0.04em;
        text-transform: uppercase;
        font-size: 0.7rem;
        font-weight: 700;
    }}
    div[data-testid="stMetricValue"] {{
        color: {INK};
        font-weight: 600;
        font-size: 1.6rem;
        font-family: {MONO_FONT};
        font-variant-numeric: tabular-nums;
    }}

    /* ---- generic card ---- */
    .card {{
        background-color: {CARD};
        border: 1px solid {LINE};
        border-radius: 16px;
        padding: 22px 24px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.03);
        height: 100%;
    }}
    .card-title {{
        font-size: 1.02rem;
        font-weight: 800;
        color: {INK};
    }}
    .card-subtitle {{
        font-size: 0.8rem;
        color: {INK_SOFT};
        margin-bottom: 14px;
    }}

    /* ---- notice ---- */
    .notice-box {{
        display: flex;
        align-items: center;
        gap: 12px;
        border: 1px solid #F3C6C6;
        background-color: {RED_SOFT};
        color: {RED_DARK};
        border-radius: 8px;
        padding: 10px 16px;
        margin: 4px 0 20px 0;
        font-size: 0.9rem;
        font-weight: 600;
    }}

    /* ---- badges ---- */
    .badge {{
        display: inline-block;
        padding: 3px 10px;
        border-radius: 999px;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.02em;
    }}
    .badge-lunas {{ background: {GREEN_SOFT}; color: {GREEN}; }}
    .badge-belum {{ background: {RED_SOFT}; color: {RED_DARK}; }}

    /* ---- aging bars ---- */
    .aging-row {{ margin-bottom: 14px; }}
    .aging-label-row {{
        display: flex; justify-content: space-between;
        font-size: 0.82rem; margin-bottom: 5px;
    }}
    .aging-bar-bg {{
        background: {LINE};
        border-radius: 6px;
        height: 7px;
        overflow: hidden;
    }}
    .aging-bar-fill {{
        height: 100%;
        border-radius: 6px;
    }}

    /* buttons */
    .stDownloadButton button, .stButton button {{
        background-color: {RED};
        color: white;
        border: none;
        border-radius: 10px;
        font-weight: 600;
    }}
    .stDownloadButton button:hover, .stButton button:hover {{
        background-color: {RED_HOVER};
        color: white;
    }}

    hr {{ border-color: {LINE}; }}

    .footer-note {{
        text-align: center;
        color: {INK_SOFT};
        font-size: 0.78rem;
        padding-top: 18px;
    }}

    /* ---- sidebar nav (dibuat dari st.radio, disamarkan jadi menu klik) ---- */
    section[data-testid="stSidebar"] div[role="radiogroup"] {{
        display: flex;
        flex-direction: column;
        gap: 4px;
        margin-bottom: 4px;
    }}
    /* zero-kan margin bawaan Streamlit pada wrapper tiap opsi, biar jarak
       antar menu murni diatur dari gap di atas -- ini yang bikin
       "Dashboard/Principal/Pembayaran" kelihatan renggang tidak rata */
    section[data-testid="stSidebar"] div[role="radiogroup"] > * {{
        margin: 0 !important;
    }}
    section[data-testid="stSidebar"] div[role="radiogroup"] label {{
        display: flex;
        align-items: center;
        width: 100%;
        padding: 10px 12px;
        border-radius: 8px;
        font-weight: 600;
        font-size: 0.9rem;
        color: {INK} !important;
        opacity: 1 !important;
        cursor: pointer;
        transition: background 0.12s ease, color 0.12s ease;
    }}
    /* paksa semua elemen di dalam label (termasuk <p> teks) ikut warna
       label -- ini kunci perbaikan "menu blur": tema gelap bawaan Streamlit
       suka menimpa warna/opacity elemen anak secara langsung. */
    section[data-testid="stSidebar"] div[role="radiogroup"] label * {{
        color: inherit !important;
        opacity: 1 !important;
    }}
    section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {{
        background: {RED_SOFT};
        color: {RED_DARK} !important;
    }}
    section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {{
        background: {RED};
        color: #FFFFFF !important;
    }}
    /* bulatan radio bawaan Streamlit (BaseWeb) -- disembunyikan lewat 2
       selector sekaligus (posisi + atribut data-baseweb) supaya tetap kena
       walau struktur DOM-nya berubah antar versi Streamlit. Ini perbaikan
       untuk ikon dobel (bulatan kosong + ◆/▲/●) yang kelihatan berantakan. */
    section[data-testid="stSidebar"] div[role="radiogroup"] label > div:first-child,
    section[data-testid="stSidebar"] div[role="radiogroup"] label [data-baseweb="radio"] {{
        display: none !important;
        width: 0 !important;
        height: 0 !important;
    }}
    section[data-testid="stSidebar"] div[role="radiogroup"] label div[data-testid="stMarkdownContainer"] p {{
        font-size: 0.9rem;
        font-weight: 600;
        margin: 0;
    }}

    /* ---- widget filter sidebar (multiselect & text input) --
       dipaksa terang, supaya tidak ikut dark-mode browser/OS pengunjung.
       Ini perbaikan untuk kotak MEIJI/NSI/SIMBA & "Cari Invoice" yang
       kelihatan hitam. ---- */
    section[data-testid="stSidebar"] label {{
        color: {INK_SOFT} !important;
    }}
    section[data-testid="stSidebar"] [data-baseweb="select"] > div,
    section[data-testid="stSidebar"] .stTextInput input {{
        background-color: {CARD} !important;
        border: 1px solid {LINE} !important;
        color: {INK} !important;
        border-radius: 8px !important;
    }}
    section[data-testid="stSidebar"] [data-baseweb="tag"] {{
        background-color: {RED} !important;
        border-radius: 999px !important;
    }}
    section[data-testid="stSidebar"] [data-baseweb="tag"] span {{
        color: #FFFFFF !important;
    }}
    /* menu dropdown multiselect kadang dirender di luar sidebar (portal ke
       body) -- selector di bawah ini tidak dibatasi ke sidebar supaya tetap
       kena. */
    div[data-baseweb="popover"], ul[data-baseweb="menu"], li[data-baseweb="menu-item"] {{
        background-color: {CARD} !important;
        color: {INK} !important;
    }}
    li[data-baseweb="menu-item"]:hover {{
        background-color: {RED_SOFT} !important;
    }}
</style>
""", unsafe_allow_html=True)

# =========================================================
# Sidebar
# =========================================================
with st.sidebar:
    st.markdown(f"""
        <div class="side-brand">
            {logo_html(38, '<div class="mark">MP</div>')}
            <div>
                <div class="side-brand-title">Monitoring Pembayaran</div>
                <div class="side-brand-sub">Principal</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    nav_options = ["Dashboard", "Principal", "Pembayaran"]
    nav_labels = {
        "Dashboard": "◆  Dashboard",
        "Principal": "▲  Principal",
        "Pembayaran": "●  Pembayaran",
    }
    halaman = st.radio(
        "Menu", nav_options,
        format_func=lambda x: nav_labels[x],
        key="nav_page",
        label_visibility="collapsed",
    )
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown('<div class="card-title" style="font-size:0.85rem;">Filter</div>', unsafe_allow_html=True)

# =========================================================
# Koneksi Supabase (pakai ANON key -- aman untuk publik, read-only)
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

def fmt_num(n):
    """Format angka dengan titik sebagai pemisah ribuan (gaya Indonesia)."""
    try:
        return f"{n:,.0f}".replace(",", ".")
    except (ValueError, TypeError):
        return str(n)

def fmt_rupiah(n):
    """Rp dengan titik ribuan, tanpa disingkat. Contoh: Rp 14.300.000"""
    return f"Rp {fmt_num(n)}"

def fmt_rupiah_short(n):
    """Rp disingkat pakai Rb/Jt/M dengan koma sebagai desimal (gaya Indonesia).
    Contoh: 14.300.000 -> Rp 14,3Jt ; 1.250.000.000 -> Rp 1,3M"""
    sign = "-" if n < 0 else ""
    n = abs(n)
    if n >= 1_000_000_000:
        val, suf = n / 1_000_000_000, "M"
    elif n >= 1_000_000:
        val, suf = n / 1_000_000, "Jt"
    elif n >= 1_000:
        val, suf = n / 1_000, "Rb"
    else:
        return f"{sign}Rp {fmt_num(n)}"
    return f"{sign}Rp {val:.1f}{suf}"

# ── Top bar ─────────────────────────────────────
st.markdown(f"""
    <div class="topbar">
        <div class="topbar-brand">
            {logo_html(34, '<div class="mark">₨</div>')}
            <div class="topbar-title">Monitoring Pembayaran Principal</div>
        </div>
        <div class="topbar-user"><b>Dashboard</b><br>SIMBA &middot; NSI &middot; MEIJI</div>
    </div>
""", unsafe_allow_html=True)

df = load_data()

if df.empty:
    st.markdown('<div class="page-title">Payment Monitoring Overview</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="notice-box">{icon_badge("warn", RED, "#FFFFFF", size=30, icon_size=15)}<span>Belum ada data di Supabase. Jalankan upload_to_supabase.py dulu di komputer kamu.</span></div>', unsafe_allow_html=True)
    st.stop()

# ── Sidebar filter (isi setelah data ada) ───────
with st.sidebar:
    principals = sorted(df["principal"].dropna().unique().tolist())
    pilih_principal = st.multiselect("Principal", principals, default=principals)
    status_opsi = ["LUNAS", "BELUM LUNAS"]
    pilih_status = st.multiselect("Status", status_opsi, default=status_opsi)
    cari_invoice = st.text_input("Cari No Invoice")

df_f = df[df["principal"].isin(pilih_principal) & df["status"].isin(pilih_status)]
if cari_invoice:
    df_f = df_f[df_f["no_invoice"].astype(str).str.contains(cari_invoice, case=False, na=False)]

# ── Data umum (dipakai di semua halaman) ────────
today = pd.Timestamp(date.today())
kolom_tampil = [
    "principal", "no_invoice", "no_payment_advice", "nominal_invoice",
    "no_miro", "tanggal_jatuh_tempo", "tanggal_bayar", "status",
    "sumber_file", "sumber_sheet",
]
overdue = df_f[(df_f["status"] == "BELUM LUNAS") & (df_f["tanggal_jatuh_tempo"] < today)]

def styled_fig(fig, height=320):
    fig.update_layout(
        plot_bgcolor=CARD,
        paper_bgcolor=CARD,
        font=dict(color=INK, family="Inter, sans-serif"),
        legend=dict(bgcolor=CARD, orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=height,
        margin=dict(l=10, r=10, t=10, b=10),
    )
    fig.update_xaxes(gridcolor=LINE, zerolinecolor=LINE)
    fig.update_yaxes(gridcolor=LINE, zerolinecolor=LINE)
    return fig

def hitung_summary_principal(data):
    summary = (
        data.groupby("principal")
        .apply(lambda g: pd.Series({
            "Total Nominal": g["nominal_invoice"].sum(),
            "Nominal Belum Lunas": g.loc[g["status"] == "BELUM LUNAS", "nominal_invoice"].sum(),
            "Jumlah Invoice": len(g),
            "Jumlah Lunas": (g["status"] == "LUNAS").sum(),
            "Jumlah Belum Lunas": (g["status"] == "BELUM LUNAS").sum(),
        }))
        .reset_index()
        .sort_values("Nominal Belum Lunas", ascending=False)
    )

    def risk_level(row):
        if row["Nominal Belum Lunas"] == 0:
            return "LOW"
        ratio = row["Nominal Belum Lunas"] / row["Total Nominal"] if row["Total Nominal"] else 0
        if ratio > 0.5:
            return "CRITICAL"
        if ratio > 0.25:
            return "HIGH"
        if ratio > 0.1:
            return "MEDIUM"
        return "LOW"

    summary["Risk"] = summary.apply(risk_level, axis=1)
    return summary

risk_colors = {
    "LOW": (GREEN, GREEN_SOFT),
    "MEDIUM": (AMBER, AMBER_SOFT),
    "HIGH": (RED_DARK, RED_SOFT),
    "CRITICAL": ("#FFFFFF", RED),
}

def render_tabel_principal(summary, judul="Ringkasan per Principal", sub="Total saldo dan status keterlambatan tiap principal"):
    st.markdown(f"""
        <div class="card">
            <div class="card-title">{judul}</div>
            <div class="card-subtitle">{sub}</div>
    """, unsafe_allow_html=True)

    header_cols = st.columns([2.0, 1.5, 1.5, 1.1, 1.1, 1])
    for c, h in zip(header_cols, ["PRINCIPAL", "TOTAL NOMINAL", "NOMINAL BELUM LUNAS", "LUNAS", "BELUM LUNAS", "RISK"]):
        c.markdown(f"<span style='color:{INK_SOFT};font-size:0.72rem;font-weight:700;letter-spacing:0.03em;'>{h}</span>", unsafe_allow_html=True)
    st.markdown("<hr style='margin:6px 0 4px 0;'>", unsafe_allow_html=True)

    for _, row in summary.iterrows():
        fg, bg = risk_colors[row["Risk"]]
        rc = st.columns([2.0, 1.5, 1.5, 1.1, 1.1, 1])
        rc[0].markdown(f"**{row['principal']}**")
        rc[1].markdown(f"<span class='mono-num'>{fmt_rupiah(row['Total Nominal'])}</span>", unsafe_allow_html=True)
        color_amt = RED_DARK if row["Nominal Belum Lunas"] > 0 else INK
        rc[2].markdown(f"<span class='mono-num' style='color:{color_amt};font-weight:700;'>{fmt_rupiah(row['Nominal Belum Lunas'])}</span>", unsafe_allow_html=True)
        rc[3].markdown(f"<span style='color:{GREEN};font-weight:700;'>{fmt_num(int(row['Jumlah Lunas']))}</span>", unsafe_allow_html=True)
        rc[4].markdown(f"<span style='color:{RED_DARK};font-weight:700;'>{fmt_num(int(row['Jumlah Belum Lunas']))}</span>", unsafe_allow_html=True)
        rc[5].markdown(f"<span class='badge' style='background:{bg};color:{fg};'>{row['Risk']}</span>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

def render_overdue_notice(data_overdue, key_suffix=""):
    if len(data_overdue):
        st.markdown(
            f'<div class="notice-box">{icon_badge("warn", RED, "#FFFFFF", size=30, icon_size=15)}'
            f'<span>{fmt_num(len(data_overdue))} invoice sudah LEWAT JATUH TEMPO dan belum '
            f'dibayar (total {fmt_rupiah(data_overdue["nominal_invoice"].sum())})</span></div>',
            unsafe_allow_html=True,
        )
        st.download_button(
            "↓  Unduh Daftar Invoice Lewat Jatuh Tempo (CSV)",
            data_overdue[kolom_tampil].sort_values("tanggal_jatuh_tempo").to_csv(index=False, sep=";").encode("utf-8-sig"),
            file_name=f"invoice_lewat_jatuh_tempo_{today.date()}.csv",
            mime="text/csv",
            key=f"download_overdue{key_suffix}",
        )

# ── Judul per halaman ────────────────────────────
judul_halaman = {
    "Dashboard": ("grid", "Payment Monitoring Overview", "Status pembayaran invoice principal secara real-time."),
    "Principal": ("bars", "Ringkasan per Principal", "Perbandingan saldo, risiko, dan status keterlambatan SIMBA, NSI, dan MEIJI."),
    "Pembayaran": ("coin", "Detail Pembayaran", "Rincian transaksi, tren pembayaran, dan status lunas / belum lunas per invoice."),
}
ikon_halaman, judul, subjudul = judul_halaman[halaman]
st.markdown(f"""
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:2px;">
        {icon_badge(ikon_halaman, "#FFFFFF", RED, size=40, icon_size=19, radius=11)}
        <div>
            <div class="page-title" style="margin-bottom:0;">{judul}</div>
        </div>
    </div>
""", unsafe_allow_html=True)
st.markdown(f'<div class="page-subtitle">{subjudul}</div>', unsafe_allow_html=True)

# ── KPI cards (tampil di semua halaman) ──────────
# Nilai yang dihitung sama persis seperti sebelumnya -- hanya dipindah ke
# variabel dulu supaya bisa dirender sebagai kartu custom (bukan st.metric).
total_invoice_n = len(df_f)
lunas_n = (df_f['status'] == 'LUNAS').sum()
belum_lunas_n = (df_f['status'] == 'BELUM LUNAS').sum()
total_belum_rp = df_f.loc[df_f["status"] == "BELUM LUNAS", "nominal_invoice"].sum()

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown(f"""
        <div class="card">
            <div class="kpi-label">{icon_svg("grid", INK_SOFT)} Total Invoice</div>
            <div class="kpi-value">{fmt_num(total_invoice_n)}</div>
            <div class="kpi-delta">Sesuai filter aktif</div>
        </div>
    """, unsafe_allow_html=True)
with col2:
    st.markdown(f"""
        <div class="card">
            <div class="kpi-label">{icon_svg("check", GREEN)} Lunas</div>
            <div class="kpi-value" style="color:{GREEN};">{fmt_num(lunas_n)}</div>
            <div class="kpi-delta">Invoice sudah dibayar</div>
        </div>
    """, unsafe_allow_html=True)
with col3:
    st.markdown(f"""
        <div class="card">
            <div class="kpi-label">{icon_svg("warn", RED_DARK)} Belum Lunas</div>
            <div class="kpi-value" style="color:{RED_DARK};">{fmt_num(belum_lunas_n)}</div>
            <div class="kpi-delta">Invoice belum dibayar</div>
        </div>
    """, unsafe_allow_html=True)
with col4:
    st.markdown(f"""
        <div class="card">
            <div class="kpi-label">{icon_svg("coin", RED)} Nominal Belum Lunas</div>
            <div class="kpi-value red">{fmt_rupiah_short(total_belum_rp)}</div>
            <div class="kpi-delta mono-num">{fmt_rupiah(total_belum_rp)}</div>
        </div>
    """, unsafe_allow_html=True)

# =========================================================
# HALAMAN: DASHBOARD -- ringkasan umum semua principal
# =========================================================
if halaman == "Dashboard":
    render_overdue_notice(overdue, key_suffix="_dash")
    st.write("")

    st.markdown(section_title("bars", "Tren &amp; Ringkasan Aging"), unsafe_allow_html=True)
    c1, c2 = st.columns([1.6, 1])
    with c1:
        st.markdown(f"""
            <div class="card">
                <div class="card-title">Tren Pembayaran</div>
                <div class="card-subtitle">Nominal invoice yang dibayar per bulan</div>
        """, unsafe_allow_html=True)
        lunas = df_f[(df_f["status"] == "LUNAS") & df_f["tanggal_bayar"].notna()].copy()
        if not lunas.empty:
            lunas["bulan_bayar"] = lunas["tanggal_bayar"].dt.to_period("M").astype(str)
            tren_bayar = lunas.groupby("bulan_bayar")["nominal_invoice"].sum().sort_index()
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=tren_bayar.index, y=tren_bayar.values,
                mode="lines+markers", name="Pembayaran",
                line=dict(color=RED, width=3, shape="spline"),
                marker=dict(color=RED, size=7),
                fill="tozeroy", fillcolor="rgba(200,30,44,0.06)",
            ))
            st.plotly_chart(styled_fig(fig), use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("Belum ada data pembayaran untuk ditampilkan.")
        st.markdown("</div>", unsafe_allow_html=True)

    with c2:
        st.markdown(f"""
            <div class="card">
                <div class="card-title">Ringkasan Aging</div>
                <div class="card-subtitle">Sebaran saldo belum lunas berdasarkan umur</div>
        """, unsafe_allow_html=True)
        belum = df_f[df_f["status"] == "BELUM LUNAS"].copy()
        if not belum.empty:
            belum["hari_lewat"] = (today - belum["tanggal_jatuh_tempo"]).dt.days
            buckets = [
                ("Belum Jatuh Tempo", belum["hari_lewat"] < 0, INK_SOFT),
                ("1-30 Hari", (belum["hari_lewat"] >= 0) & (belum["hari_lewat"] <= 30), "#F0BFC4"),
                ("31-60 Hari", (belum["hari_lewat"] > 30) & (belum["hari_lewat"] <= 60), "#E28D96"),
                ("61-90 Hari", (belum["hari_lewat"] > 60) & (belum["hari_lewat"] <= 90), "#CE5A66"),
                ("90+ Hari", belum["hari_lewat"] > 90, RED),
            ]
            max_val = max(belum.loc[cond, "nominal_invoice"].sum() for _, cond, _ in buckets) or 1
            for label, cond, color in buckets:
                val = belum.loc[cond, "nominal_invoice"].sum()
                pct = max(3, (val / max_val) * 100)
                st.markdown(f"""
                    <div class="aging-row">
                        <div class="aging-label-row">
                            <span>{label}</span>
                            <b class="mono-num">{fmt_rupiah(val)}</b>
                        </div>
                        <div class="aging-bar-bg">
                            <div class="aging-bar-fill" style="width:{pct}%;background:{color};"></div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Tidak ada invoice belum lunas.")
        st.markdown("</div>", unsafe_allow_html=True)

    st.write("")
    st.markdown(section_title("grid", "Ringkasan per Principal"), unsafe_allow_html=True)
    render_tabel_principal(hitung_summary_principal(df_f))

# =========================================================
# HALAMAN: PRINCIPAL -- fokus perbandingan & drill-down tiap principal
# =========================================================
elif halaman == "Principal":
    st.markdown(section_title("grid", "Ringkasan per Principal"), unsafe_allow_html=True)
    render_tabel_principal(hitung_summary_principal(df_f))
    st.write("")

    st.markdown(section_title("bars", "Detail per Principal"), unsafe_allow_html=True)
    st.markdown('<div class="card-title" style="margin-bottom:8px;">Lihat Detail 1 Principal</div>', unsafe_allow_html=True)
    daftar_principal = ["Semua Principal"] + sorted(df_f["principal"].dropna().unique().tolist())
    pilih_satu = st.selectbox("Pilih Principal", daftar_principal, label_visibility="collapsed")

    if pilih_satu != "Semua Principal":
        df_p = df_f[df_f["principal"] == pilih_satu]
        overdue_p = df_p[(df_p["status"] == "BELUM LUNAS") & (df_p["tanggal_jatuh_tempo"] < today)]

        pcol1, pcol2, pcol3, pcol4 = st.columns(4)
        pcol1.metric("Total Invoice", fmt_num(len(df_p)))
        pcol2.metric("Lunas", fmt_num((df_p['status']=='LUNAS').sum()))
        pcol3.metric("Belum Lunas", fmt_num((df_p['status']=='BELUM LUNAS').sum()))
        pcol4.metric("Nominal Belum Lunas", fmt_rupiah_short(df_p.loc[df_p["status"]=="BELUM LUNAS","nominal_invoice"].sum()))

        render_overdue_notice(overdue_p, key_suffix=f"_principal_{pilih_satu}")

        st.write("")
        st.markdown(f"""
            <div class="card">
                <div class="card-title">Daftar Invoice -- {pilih_satu}</div>
                <div class="card-subtitle">Seluruh invoice principal ini sesuai filter aktif</div>
        """, unsafe_allow_html=True)
        st.dataframe(
            df_p[kolom_tampil].sort_values("tanggal_jatuh_tempo", ascending=False),
            use_container_width=True,
            hide_index=True,
        )
        st.download_button(
            f"↓  Unduh Data {pilih_satu} (CSV)",
            df_p[kolom_tampil].to_csv(index=False, sep=";").encode("utf-8-sig"),
            file_name=f"monitoring_pembayaran_{pilih_satu.lower()}.csv",
            mime="text/csv",
            key=f"download_principal_{pilih_satu}",
        )
        st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# HALAMAN: PEMBAYARAN -- fokus tren, status, & detail transaksi
# =========================================================
elif halaman == "Pembayaran":
    render_overdue_notice(overdue, key_suffix="_bayar")
    st.write("")

    st.markdown(section_title("bars", "Tren Pembayaran"), unsafe_allow_html=True)
    st.markdown(f"""
        <div class="card">
            <div class="card-title">Tren Pembayaran</div>
            <div class="card-subtitle">Nominal invoice yang dibayar per bulan (seluruh principal sesuai filter)</div>
    """, unsafe_allow_html=True)
    lunas = df_f[(df_f["status"] == "LUNAS") & df_f["tanggal_bayar"].notna()].copy()
    if not lunas.empty:
        lunas["bulan_bayar"] = lunas["tanggal_bayar"].dt.to_period("M").astype(str)
        tren_bayar = lunas.groupby("bulan_bayar")["nominal_invoice"].sum().sort_index()
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=tren_bayar.index, y=tren_bayar.values,
            mode="lines+markers", name="Pembayaran",
            line=dict(color=RED, width=3, shape="spline"),
            marker=dict(color=RED, size=7),
            fill="tozeroy", fillcolor="rgba(200,30,44,0.06)",
        ))
        st.plotly_chart(styled_fig(fig), use_container_width=True, config={"displayModeBar": False})
    else:
        st.info("Belum ada data pembayaran untuk ditampilkan.")
    st.markdown("</div>", unsafe_allow_html=True)

    st.write("")

    # ── Status lunas vs belum lunas per sumber file ──
    st.write("")
    st.markdown(section_title("grid", "Ringkasan Sumber Data"), unsafe_allow_html=True)
    st.markdown(f"""
        <div class="card">
            <div class="card-title">Status per Sumber File</div>
            <div class="card-subtitle">Jumlah & nominal LUNAS vs BELUM LUNAS tiap sumber data</div>
    """, unsafe_allow_html=True)
    status_sumber = (
        df_f.groupby("sumber_file")
        .apply(lambda g: pd.Series({
            "Lunas": (g["status"] == "LUNAS").sum(),
            "Belum Lunas": (g["status"] == "BELUM LUNAS").sum(),
            "Nominal Lunas": g.loc[g["status"] == "LUNAS", "nominal_invoice"].sum(),
            "Nominal Belum Lunas": g.loc[g["status"] == "BELUM LUNAS", "nominal_invoice"].sum(),
        }))
        .reset_index()
    )
    if not status_sumber.empty:
        hcols = st.columns([2, 1, 1, 1.5, 1.5])
        for c, h in zip(hcols, ["SUMBER FILE", "LUNAS", "BELUM LUNAS", "NOMINAL LUNAS", "NOMINAL BELUM LUNAS"]):
            c.markdown(f"<span style='color:{INK_SOFT};font-size:0.72rem;font-weight:700;letter-spacing:0.03em;'>{h}</span>", unsafe_allow_html=True)
        st.markdown("<hr style='margin:6px 0 4px 0;'>", unsafe_allow_html=True)
        for _, row in status_sumber.iterrows():
            rc = st.columns([2, 1, 1, 1.5, 1.5])
            rc[0].markdown(f"**{row['sumber_file']}**")
            rc[1].markdown(f"<span style='color:{GREEN};font-weight:700;'>{fmt_num(int(row['Lunas']))}</span>", unsafe_allow_html=True)
            rc[2].markdown(f"<span style='color:{RED_DARK};font-weight:700;'>{fmt_num(int(row['Belum Lunas']))}</span>", unsafe_allow_html=True)
            rc[3].markdown(f"<span class='mono-num'>{fmt_rupiah(row['Nominal Lunas'])}</span>", unsafe_allow_html=True)
            rc[4].markdown(f"<span class='mono-num'>{fmt_rupiah(row['Nominal Belum Lunas'])}</span>", unsafe_allow_html=True)
    else:
        st.info("Tidak ada data.")
    st.markdown("</div>", unsafe_allow_html=True)

    st.write("")

    # ── Tabel detail transaksi ──
    st.markdown(section_title("coin", "Detail Transaksi"), unsafe_allow_html=True)
    st.markdown(f"""
        <div class="card">
            <div class="card-title">Detail Transaksi</div>
            <div class="card-subtitle">Rincian seluruh invoice sesuai filter</div>
    """, unsafe_allow_html=True)
    st.dataframe(
        df_f[kolom_tampil].sort_values("tanggal_jatuh_tempo", ascending=False),
        use_container_width=True,
        hide_index=True,
    )
    st.download_button(
        "↓  Unduh Hasil Filter (CSV)",
        df_f[kolom_tampil].to_csv(index=False, sep=";").encode("utf-8-sig"),
        file_name="monitoring_pembayaran_filtered.csv",
        mime="text/csv",
        key="download_pembayaran_detail",
    )
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown(
    '<div class="footer-note">Data otomatis dari Supabase &middot; jalankan upload_to_supabase.py '
    'lalu refresh halaman untuk data terbaru (cache 5 menit)</div>',
    unsafe_allow_html=True,
)

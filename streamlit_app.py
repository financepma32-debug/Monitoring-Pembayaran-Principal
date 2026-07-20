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
# PALET WARNA -- disamakan PERSIS dengan hasil redesign Stitch
# (design system "Vivid Crimson Metric", dipakai konsisten di semua
# varian *_final_redesign: Dashboard, Outstanding, Lunas).
# =========================================================
BG        = "#FFFFFF"
BG_SOFT   = "#F9F9FF"   # "surface"/"background" -- ganti dari bone-white ke ini
CARD      = "#FFFFFF"   # "surface-container-lowest"
RED       = "#9E0013"   # "primary"
RED_HOVER = "#C61A23"   # "primary-container" -- state hover/aktif
RED_DARK  = "#930011"   # "on-primary-fixed-variant"
RED_SOFT  = "#FFDAD6"   # "primary-fixed" -- background lembut merah (badge dsb)
INK       = "#151C27"   # "on-surface"
INK_SOFT  = "#575E70"   # "secondary"
LINE      = "#E5BDB9"   # "outline-variant"
GREEN     = "#16A34A"
GREEN_SOFT= "#DCFCE7"   # "success-container"
AMBER     = "#9A3412"   # dekat "orange-800" di badge Warning
AMBER_SOFT= "#FFEDD5"   # "orange-100"
BLUE      = "#0049A0"   # "tertiary" -- dipakai untuk badge gaya "Low Risk"
BLUE_SOFT = "#DBEAFE"
MONO_FONT = "'Inter', sans-serif"  # desain baru pakai Inter saja (IBM Plex Mono dilepas)

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
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

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
        padding-top: 2.75rem;
    }}

    /* ---- main container padding ----
       padding-top dinaikkan supaya topbar (logo + judul) tidak lagi
       kepotong toolbar Streamlit Cloud (Share/Star/GitHub) yang tetap
       tampil sekarang karena header tidak lagi disembunyikan total
       (perlu dibiarkan tampil supaya tombol << / >> sidebar berfungsi). */
    .block-container {{
        padding-top: 3.2rem;
        padding-bottom: 2rem;
        max-width: 1440px;
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
        letter-spacing: 0.02em;
        text-transform: uppercase;
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
        border-radius: 10px;
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
        border-radius: 12px;
        padding: 22px 24px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.03);
        height: 100%;
        position: relative;
        overflow: hidden;
    }}
    .card-stripe {{
        position: absolute;
        top: 0; left: 0;
        width: 100%;
        height: 4px;
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
       kelihatan hitam, sekaligus dipercantik biar terasa lebih
       profesional: radius lebih besar, shadow tipis, jarak antar field
       lebih lega. ---- */
    section[data-testid="stSidebar"] label {{
        color: {INK} !important;
        font-weight: 600 !important;
        font-size: 0.85rem !important;
        margin-bottom: 2px !important;
    }}
    section[data-testid="stSidebar"] .stTextInput,
    section[data-testid="stSidebar"] .stMultiSelect {{
        margin-bottom: 14px;
    }}
    section[data-testid="stSidebar"] [data-baseweb="select"] > div,
    section[data-testid="stSidebar"] .stTextInput input {{
        background-color: {CARD} !important;
        border: 1px solid {LINE} !important;
        color: {INK} !important;
        border-radius: 12px !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.04);
        min-height: 44px;
    }}
    section[data-testid="stSidebar"] .stTextInput input {{
        padding: 10px 14px !important;
    }}
    section[data-testid="stSidebar"] [data-baseweb="select"] input::placeholder,
    section[data-testid="stSidebar"] .stTextInput input::placeholder {{
        color: {INK_SOFT} !important;
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
    /* tombol sekunder (mis. Reset Filter) -- gaya outline terang, beda
       dari tombol aksi utama (download, dsb) yang solid merah */
    section[data-testid="stSidebar"] button[kind="secondary"] {{
        background-color: {CARD} !important;
        color: {INK} !important;
        border: 1px solid {LINE} !important;
    }}
    section[data-testid="stSidebar"] button[kind="secondary"]:hover {{
        background-color: {RED_SOFT} !important;
        color: {RED_DARK} !important;
        border-color: {RED_SOFT} !important;
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

    nav_options = ["Dashboard", "Outstanding", "Lunas"]
    nav_labels = {
        "Dashboard": "◆  Dashboard",
        "Outstanding": "▲  Outstanding",
        "Lunas": "●  Lunas",
    }
    halaman = st.radio(
        "Menu", nav_options,
        format_func=lambda x: nav_labels[x],
        key="nav_page",
        label_visibility="collapsed",
    )
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown('<div class="card-title" style="font-size:1rem;margin-bottom:12px;">Filter</div>', unsafe_allow_html=True)

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

def initials(name):
    """Ambil 2 huruf inisial dari nama principal, buat badge avatar -- murni
    presentasi (mengikuti pola badge 'SI'/'MJ'/'NS' di desain Stitch), bukan
    kalkulasi data."""
    parts = str(name).split()
    if len(parts) >= 2:
        return (parts[0][:1] + parts[1][:1]).upper()
    return str(name)[:2].upper()

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
def reset_filters():
    """Callback tombol Reset Filter -- HARUS lewat on_click (bukan ditulis
    langsung di badan skrip) supaya boleh mengubah session_state punya
    widget yang sudah pernah dirender, sesuai aturan Streamlit."""
    st.session_state["cari_invoice_input"] = ""
    st.session_state["principal_multiselect"] = []

with st.sidebar:
    principals = sorted(df["principal"].dropna().unique().tolist())
    cari_invoice = st.text_input(
        "Cari No Invoice", key="cari_invoice_input", placeholder="Ketik...",
    )
    pilih_principal = st.multiselect(
        "Principal", principals, default=[], key="principal_multiselect",
        placeholder="Choose options",
    )
    st.markdown("<hr>", unsafe_allow_html=True)
    st.button("Reset Filter", use_container_width=True, type="secondary", on_click=reset_filters)

# Kotak kosong (belum pilih apapun) = tampilkan semua principal -- bukan
# berarti tidak ada yang cocok. Ini yang bikin kotak filter bersih (placeholder
# "Choose options") alih-alih penuh chip merah menumpuk sejak awal.
df_f = df[df["principal"].isin(pilih_principal)] if pilih_principal else df.copy()
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
            "Nominal Lunas": g.loc[g["status"] == "LUNAS", "nominal_invoice"].sum(),
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

def render_tabel_outstanding(summary, judul="Ringkasan Outstanding per Principal",
                              sub="Saldo & jumlah invoice yang masih belum lunas per principal"):
    """Versi render_tabel_principal khusus halaman Outstanding -- sengaja TIDAK
    menampilkan kolom Lunas/Total Nominal supaya halaman ini murni info
    outstanding saja. Risk tetap dihitung dari hitung_summary_principal (data
    lengkap semua status) supaya rasionya tetap akurat, cuma kolomnya yang
    disembunyikan dari tampilan."""
    st.markdown(f"""
        <div class="card">
            <div class="card-title">{judul}</div>
            <div class="card-subtitle">{sub}</div>
    """, unsafe_allow_html=True)

    header_cols = st.columns([2.4, 1.8, 1.3, 1.3])
    for c, h in zip(header_cols, ["PRINCIPAL", "NOMINAL BELUM LUNAS", "JUMLAH INVOICE", "RISK"]):
        c.markdown(f"<span style='color:{INK_SOFT};font-size:0.72rem;font-weight:700;letter-spacing:0.03em;'>{h}</span>", unsafe_allow_html=True)
    st.markdown("<hr style='margin:6px 0 4px 0;'>", unsafe_allow_html=True)

    for _, row in summary.iterrows():
        fg, bg = risk_colors[row["Risk"]]
        rc = st.columns([2.4, 1.8, 1.3, 1.3])
        rc[0].markdown(f"**{row['principal']}**")
        rc[1].markdown(f"<span class='mono-num' style='color:{RED_DARK};font-weight:700;'>{fmt_rupiah(row['Nominal Belum Lunas'])}</span>", unsafe_allow_html=True)
        rc[2].markdown(f"<span style='font-weight:700;'>{fmt_num(int(row['Jumlah Belum Lunas']))}</span>", unsafe_allow_html=True)
        rc[3].markdown(f"<span class='badge' style='background:{bg};color:{fg};'>{row['Risk']}</span>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

def render_tabel_lunas(summary, judul="Ringkasan Lunas per Principal",
                        sub="Total nominal & jumlah invoice yang sudah dibayar per principal"):
    """Versi render_tabel_principal khusus halaman Lunas -- sengaja TIDAK
    menampilkan kolom Belum Lunas/Risk supaya halaman ini murni info invoice
    yang sudah dibayar saja. Diurutkan berdasarkan Nominal Lunas (bukan
    Nominal Belum Lunas seperti tabel lain) supaya principal pembayar
    terbesar tampil di atas."""
    st.markdown(f"""
        <div class="card">
            <div class="card-title">{judul}</div>
            <div class="card-subtitle">{sub}</div>
    """, unsafe_allow_html=True)

    header_cols = st.columns([2.6, 2.0, 1.4])
    for c, h in zip(header_cols, ["PRINCIPAL", "NOMINAL LUNAS", "JUMLAH INVOICE"]):
        c.markdown(f"<span style='color:{INK_SOFT};font-size:0.72rem;font-weight:700;letter-spacing:0.03em;'>{h}</span>", unsafe_allow_html=True)
    st.markdown("<hr style='margin:6px 0 4px 0;'>", unsafe_allow_html=True)

    for _, row in summary.sort_values("Nominal Lunas", ascending=False).iterrows():
        rc = st.columns([2.6, 2.0, 1.4])
        rc[0].markdown(f"**{row['principal']}**")
        rc[1].markdown(f"<span class='mono-num' style='color:{GREEN};font-weight:700;'>{fmt_rupiah(row['Nominal Lunas'])}</span>", unsafe_allow_html=True)
        rc[2].markdown(f"<span style='font-weight:700;'>{fmt_num(int(row['Jumlah Lunas']))}</span>", unsafe_allow_html=True)

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
    "Outstanding": ("warn", "Outstanding Invoices", "Invoice yang masih belum lunas -- saldo, jatuh tempo, dan risiko keterlambatan per principal."),
    "Lunas": ("check", "Invoice Lunas", "Invoice yang sudah dibayar -- tren pembayaran dan rekap per principal."),
}
ikon_halaman, judul, subjudul = judul_halaman[halaman]
st.markdown(f"""
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:2px;">
        {icon_badge(ikon_halaman, "#FFFFFF", RED, size=32, icon_size=16, radius=9)}
        <div>
            <div class="page-title" style="margin-bottom:0;">{judul}</div>
        </div>
    </div>
""", unsafe_allow_html=True)
st.markdown(f'<div class="page-subtitle">{subjudul}</div>', unsafe_allow_html=True)

# =========================================================
# HALAMAN: DASHBOARD -- ringkasan umum semua principal
# =========================================================
if halaman == "Dashboard":
    # KPI ringkasan umum -- gabungan lunas & belum lunas, sama seperti
    # sebelumnya, cuma sekarang khusus di halaman ini saja.
    total_invoice_n = len(df_f)
    lunas_n = (df_f['status'] == 'LUNAS').sum()
    belum_lunas_n = (df_f['status'] == 'BELUM LUNAS').sum()
    total_belum_rp = df_f.loc[df_f["status"] == "BELUM LUNAS", "nominal_invoice"].sum()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
            <div class="card">
                <div class="card-stripe" style="background:{INK_SOFT};"></div>
                <div class="kpi-label">{icon_svg("grid", INK_SOFT)} Total Invoice</div>
                <div class="kpi-value">{fmt_num(total_invoice_n)}</div>
                <div class="kpi-delta">Sesuai filter aktif</div>
            </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
            <div class="card">
                <div class="card-stripe" style="background:{GREEN};"></div>
                <div class="kpi-label">{icon_svg("check", GREEN)} Lunas</div>
                <div class="kpi-value" style="color:{GREEN};">{fmt_num(lunas_n)}</div>
                <div class="kpi-delta">Invoice sudah dibayar</div>
            </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
            <div class="card">
                <div class="card-stripe" style="background:{RED};"></div>
                <div class="kpi-label">{icon_svg("warn", RED_DARK)} Belum Lunas</div>
                <div class="kpi-value" style="color:{RED_DARK};">{fmt_num(belum_lunas_n)}</div>
                <div class="kpi-delta">Invoice belum dibayar</div>
            </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
            <div class="card">
                <div class="card-stripe" style="background:{RED};"></div>
                <div class="kpi-label">{icon_svg("coin", RED)} Nominal Belum Lunas</div>
                <div class="kpi-value red">{fmt_rupiah_short(total_belum_rp)}</div>
                <div class="kpi-delta mono-num">{fmt_rupiah(total_belum_rp)}</div>
            </div>
        """, unsafe_allow_html=True)

    st.write("")
    render_overdue_notice(overdue, key_suffix="_dash")
    st.write("")

    st.markdown(section_title("bars", "Komposisi &amp; Principal Teratas"), unsafe_allow_html=True)
    dc1, dc2 = st.columns([1, 1.15])
    with dc1:
        st.markdown(f"""
            <div class="card">
                <div class="card-title">Komposisi Status</div>
                <div class="card-subtitle">Proporsi nominal lunas vs belum lunas</div>
        """, unsafe_allow_html=True)
        nominal_lunas_all = df_f.loc[df_f["status"] == "LUNAS", "nominal_invoice"].sum()
        nominal_belum_all = df_f.loc[df_f["status"] == "BELUM LUNAS", "nominal_invoice"].sum()
        total_nominal_all = nominal_lunas_all + nominal_belum_all
        if total_nominal_all > 0:
            fig_komposisi = go.Figure(go.Bar(
                x=[nominal_lunas_all, nominal_belum_all],
                y=["Lunas", "Belum Lunas"],
                orientation="h",
                marker_color=[GREEN, RED],
                text=[fmt_rupiah_short(nominal_lunas_all), fmt_rupiah_short(nominal_belum_all)],
                textposition="outside",
                textfont=dict(family="Inter", size=12, color=INK),
                hovertext=[fmt_rupiah(nominal_lunas_all), fmt_rupiah(nominal_belum_all)],
                hoverinfo="text",
            ))
            fig_komposisi.update_layout(
                height=220,
                margin=dict(l=10, r=10, t=10, b=10),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Inter", color=INK),
                showlegend=False,
                xaxis=dict(showgrid=False, zeroline=True, zerolinecolor=LINE, tickfont=dict(size=10, color=INK_SOFT)),
                yaxis=dict(tickfont=dict(size=12, color=INK, family="Inter")),
            )
            st.plotly_chart(fig_komposisi, use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("Tidak ada data.")
        st.markdown("</div>", unsafe_allow_html=True)

    with dc2:
        st.markdown(f"""
            <div class="card">
                <div class="card-title">Top 5 Principal -- Belum Lunas Terbesar</div>
                <div class="card-subtitle">Nominal outstanding tertinggi sesuai filter aktif</div>
        """, unsafe_allow_html=True)
        top5_principal = hitung_summary_principal(df_f).head(5)
        if not top5_principal.empty and top5_principal["Nominal Belum Lunas"].sum() > 0:
            max_top = top5_principal["Nominal Belum Lunas"].max() or 1
            for _, row in top5_principal.iterrows():
                pct = max(3, (row["Nominal Belum Lunas"] / max_top) * 100)
                st.markdown(f"""
                    <div style="display:flex;align-items:center;justify-content:space-between;
                                padding:14px;background:{CARD};border:1px solid {LINE};
                                border-radius:8px;margin-bottom:10px;">
                        <div style="display:flex;align-items:center;gap:12px;">
                            <div style="width:40px;height:40px;border-radius:8px;background:{RED_SOFT};
                                        display:flex;align-items:center;justify-content:center;
                                        font-weight:800;color:{RED};font-size:0.8rem;flex-shrink:0;">
                                {initials(row['principal'])}
                            </div>
                            <div>
                                <div style="font-weight:700;font-size:0.85rem;color:{INK};">{row['principal']}</div>
                                <div style="font-size:0.72rem;color:{INK_SOFT};">{fmt_num(int(row['Jumlah Belum Lunas']))} invoice belum lunas</div>
                            </div>
                        </div>
                        <div style="text-align:right;">
                            <div class="mono-num" style="font-weight:800;color:{RED};font-size:0.85rem;">{fmt_rupiah(row['Nominal Belum Lunas'])}</div>
                            <div style="width:100px;height:6px;background:{LINE};border-radius:999px;margin-top:6px;overflow:hidden;margin-left:auto;">
                                <div style="width:{pct}%;height:100%;background:{RED};"></div>
                            </div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Tidak ada invoice belum lunas.")
        st.markdown("</div>", unsafe_allow_html=True)

    st.write("")
    st.markdown(section_title("grid", "Ringkasan per Principal"), unsafe_allow_html=True)
    render_tabel_principal(hitung_summary_principal(df_f))
    st.caption("Rincian khusus invoice outstanding ada di halaman **Outstanding**, "
               "dan rincian pembayaran ada di halaman **Lunas**.")

# =========================================================
# HALAMAN: OUTSTANDING -- murni invoice belum lunas, tanpa info lunas
# =========================================================
elif halaman == "Outstanding":
    df_belum = df_f[df_f["status"] == "BELUM LUNAS"]

    total_outstanding_n = len(df_belum)
    nominal_outstanding = df_belum["nominal_invoice"].sum()
    overdue_n = len(overdue)
    overdue_rp = overdue["nominal_invoice"].sum()

    ocol1, ocol2, ocol3, ocol4 = st.columns(4)
    with ocol1:
        st.markdown(f"""
            <div class="card">
                <div class="card-stripe" style="background:{INK_SOFT};"></div>
                <div class="kpi-label">{icon_svg("warn", INK_SOFT)} Total Outstanding</div>
                <div class="kpi-value">{fmt_num(total_outstanding_n)}</div>
                <div class="kpi-delta">Invoice belum lunas</div>
            </div>
        """, unsafe_allow_html=True)
    with ocol2:
        st.markdown(f"""
            <div class="card">
                <div class="card-stripe" style="background:{RED};"></div>
                <div class="kpi-label">{icon_svg("coin", RED)} Nominal Outstanding</div>
                <div class="kpi-value red">{fmt_rupiah_short(nominal_outstanding)}</div>
                <div class="kpi-delta mono-num">{fmt_rupiah(nominal_outstanding)}</div>
            </div>
        """, unsafe_allow_html=True)
    with ocol3:
        st.markdown(f"""
            <div class="card">
                <div class="card-stripe" style="background:{RED_DARK};"></div>
                <div class="kpi-label">{icon_svg("warn", RED_DARK)} Lewat Jatuh Tempo</div>
                <div class="kpi-value" style="color:{RED_DARK};">{fmt_num(overdue_n)}</div>
                <div class="kpi-delta">Invoice</div>
            </div>
        """, unsafe_allow_html=True)
    with ocol4:
        st.markdown(f"""
            <div class="card">
                <div class="card-stripe" style="background:{RED_DARK};"></div>
                <div class="kpi-label">{icon_svg("coin", RED_DARK)} Nominal Lewat Tempo</div>
                <div class="kpi-value" style="color:{RED_DARK};">{fmt_rupiah_short(overdue_rp)}</div>
                <div class="kpi-delta mono-num">{fmt_rupiah(overdue_rp)}</div>
            </div>
        """, unsafe_allow_html=True)

    st.write("")
    render_overdue_notice(overdue, key_suffix="_outstanding")
    st.write("")

    st.markdown(section_title("bars", "Ringkasan Aging &amp; Outstanding per Principal"), unsafe_allow_html=True)
    ac1, ac2 = st.columns([1, 1.15])
    with ac1:
        st.markdown(f"""
            <div class="card">
                <div class="card-title">Ringkasan Aging</div>
                <div class="card-subtitle">Sebaran saldo belum lunas berdasarkan umur</div>
        """, unsafe_allow_html=True)
        belum = df_belum.copy()
        if not belum.empty:
            belum["hari_lewat"] = (today - belum["tanggal_jatuh_tempo"]).dt.days
            buckets = [
                ("Belum Jatuh Tempo", belum["hari_lewat"] < 0, INK_SOFT),
                ("1-30 Hari", (belum["hari_lewat"] >= 0) & (belum["hari_lewat"] <= 30), "#E8929B"),
                ("31-60 Hari", (belum["hari_lewat"] > 30) & (belum["hari_lewat"] <= 60), "#D45A69"),
                ("61-90 Hari", (belum["hari_lewat"] > 60) & (belum["hari_lewat"] <= 90), "#BB2E42"),
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

    with ac2:
        st.markdown(f"""
            <div class="card">
                <div class="card-title">Outstanding per Principal</div>
                <div class="card-subtitle">Proporsi nominal belum lunas per principal</div>
        """, unsafe_allow_html=True)
        summary_o = hitung_summary_principal(df_f)
        summary_o_chart = summary_o[summary_o["Nominal Belum Lunas"] > 0]
        if not summary_o_chart.empty:
            # tiap principal dapat warna sendiri (bukan warna per level risiko --
            # kalau semua principal kebetulan level risikonya sama, chart jadi
            # satu warna doang dan nggak kebaca). Risiko tetap ditampilkan,
            # dipindah ke legend badge di bawah chart.
            palet_principal = [RED, RED_HOVER, RED_DARK, "#7A2A34", "#5C1019", "#B8515E", "#4A0D14", "#8F3B45"]
            warna_slice = [palet_principal[i % len(palet_principal)] for i in range(len(summary_o_chart))]
            hover_text = [fmt_rupiah(v) for v in summary_o_chart["Nominal Belum Lunas"]]
            fig_pie = go.Figure(go.Pie(
                labels=summary_o_chart["principal"],
                values=summary_o_chart["Nominal Belum Lunas"],
                customdata=hover_text,
                hole=0.58,
                sort=False,
                marker=dict(colors=warna_slice, line=dict(color=CARD, width=2)),
                textinfo="label+percent",
                textfont=dict(size=11, family="Inter", color="#FFFFFF"),
                hovertemplate="<b>%{label}</b><br>%{customdata}<extra></extra>",
            ))
            fig_pie.update_layout(
                showlegend=False,
                height=260,
                margin=dict(l=10, r=10, t=10, b=10),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Inter", color=INK),
                annotations=[dict(
                    text=f"<b>{fmt_rupiah_short(nominal_outstanding)}</b><br><span style='font-size:11px;color:{INK_SOFT}'>Total Outstanding</span>",
                    x=0.5, y=0.5, showarrow=False, font=dict(size=15, color=INK),
                )],
            )
            st.plotly_chart(fig_pie, use_container_width=True, config={"displayModeBar": False})

            # legend: warna slice + nama principal + persentase + badge risiko,
            # menyamakan persis pola legend di mockup Stitch
            total_chart = summary_o_chart["Nominal Belum Lunas"].sum() or 1
            for i, (_, row) in enumerate(summary_o_chart.iterrows()):
                dot = warna_slice[i]
                fg, bg = risk_colors[row["Risk"]]
                pct_slice = row["Nominal Belum Lunas"] / total_chart * 100
                st.markdown(f"""
                    <div style="display:flex;align-items:center;justify-content:space-between;padding:5px 2px;">
                        <div style="display:flex;align-items:center;gap:8px;">
                            <span style="width:10px;height:10px;border-radius:50%;background:{dot};display:inline-block;flex-shrink:0;"></span>
                            <span style="font-size:0.82rem;font-weight:600;color:{INK};">{row['principal']}</span>
                        </div>
                        <div style="display:flex;align-items:center;gap:8px;">
                            <span style="font-size:0.74rem;color:{INK_SOFT};">{pct_slice:.1f}%</span>
                            <span class="badge" style="background:{bg};color:{fg};font-size:0.66rem;">{row['Risk']}</span>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Tidak ada invoice belum lunas.")
        st.markdown("</div>", unsafe_allow_html=True)

    st.write("")

    st.markdown(section_title("coin", "Detail Invoice Outstanding"), unsafe_allow_html=True)
    st.markdown('<div class="card-title" style="margin-bottom:8px;">Lihat Detail 1 Principal (opsional)</div>', unsafe_allow_html=True)
    daftar_principal_o = ["Semua Principal"] + sorted(df_belum["principal"].dropna().unique().tolist())
    pilih_principal_o = st.selectbox("Pilih Principal", daftar_principal_o,
                                      label_visibility="collapsed", key="pilih_principal_outstanding")
    df_belum_tampil = (df_belum if pilih_principal_o == "Semua Principal"
                        else df_belum[df_belum["principal"] == pilih_principal_o])

    st.write("")
    st.markdown(f"""
        <div class="card">
            <div class="card-title">Daftar Invoice Belum Lunas</div>
            <div class="card-subtitle">Rincian invoice outstanding sesuai filter aktif -- tanpa data invoice lunas</div>
    """, unsafe_allow_html=True)
    st.dataframe(
        df_belum_tampil[kolom_tampil].sort_values("tanggal_jatuh_tempo", ascending=True),
        use_container_width=True,
        hide_index=True,
    )
    st.download_button(
        "↓  Unduh Daftar Outstanding (CSV)",
        df_belum_tampil[kolom_tampil].to_csv(index=False, sep=";").encode("utf-8-sig"),
        file_name="monitoring_pembayaran_outstanding.csv",
        mime="text/csv",
        key="download_outstanding_detail",
    )
    st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# HALAMAN: LUNAS -- murni invoice yang sudah dibayar, tanpa info outstanding
# =========================================================
elif halaman == "Lunas":
    df_lunas_page = df_f[df_f["status"] == "LUNAS"]

    total_lunas_n = len(df_lunas_page)
    nominal_lunas_total = df_lunas_page["nominal_invoice"].sum()
    rata_rata_lunas = (nominal_lunas_total / total_lunas_n) if total_lunas_n else 0

    lcol1, lcol2, lcol3 = st.columns(3)
    with lcol1:
        st.markdown(f"""
            <div class="card">
                <div class="card-stripe" style="background:{GREEN};"></div>
                <div class="kpi-label">{icon_svg("check", GREEN)} Total Invoice Lunas</div>
                <div class="kpi-value" style="color:{GREEN};">{fmt_num(total_lunas_n)}</div>
                <div class="kpi-delta">Sudah dibayar</div>
            </div>
        """, unsafe_allow_html=True)
    with lcol2:
        st.markdown(f"""
            <div class="card">
                <div class="card-stripe" style="background:{GREEN};"></div>
                <div class="kpi-label">{icon_svg("coin", GREEN)} Nominal Lunas</div>
                <div class="kpi-value" style="color:{GREEN};">{fmt_rupiah_short(nominal_lunas_total)}</div>
                <div class="kpi-delta mono-num">{fmt_rupiah(nominal_lunas_total)}</div>
            </div>
        """, unsafe_allow_html=True)
    with lcol3:
        st.markdown(f"""
            <div class="card">
                <div class="card-stripe" style="background:{INK_SOFT};"></div>
                <div class="kpi-label">{icon_svg("grid", INK_SOFT)} Rata-rata per Invoice</div>
                <div class="kpi-value">{fmt_rupiah_short(rata_rata_lunas)}</div>
                <div class="kpi-delta mono-num">{fmt_rupiah(rata_rata_lunas)}</div>
            </div>
        """, unsafe_allow_html=True)

    st.write("")
    st.markdown(section_title("bars", "Tren Pembayaran"), unsafe_allow_html=True)
    st.markdown(f"""
        <div class="card">
            <div class="card-title">Tren Pembayaran</div>
            <div class="card-subtitle">Nominal invoice yang dibayar per bulan (seluruh principal sesuai filter)</div>
    """, unsafe_allow_html=True)
    lunas = df_lunas_page[df_lunas_page["tanggal_bayar"].notna()].copy()
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
    st.markdown(section_title("grid", "Ringkasan Lunas per Principal"), unsafe_allow_html=True)
    render_tabel_lunas(hitung_summary_principal(df_f))
    st.write("")

    st.markdown(section_title("coin", "Detail Invoice Lunas"), unsafe_allow_html=True)
    st.markdown('<div class="card-title" style="margin-bottom:8px;">Lihat Detail 1 Principal (opsional)</div>', unsafe_allow_html=True)
    daftar_principal_l = ["Semua Principal"] + sorted(df_lunas_page["principal"].dropna().unique().tolist())
    pilih_principal_l = st.selectbox("Pilih Principal", daftar_principal_l,
                                      label_visibility="collapsed", key="pilih_principal_lunas")
    df_lunas_tampil = (df_lunas_page if pilih_principal_l == "Semua Principal"
                        else df_lunas_page[df_lunas_page["principal"] == pilih_principal_l])

    st.write("")
    st.markdown(f"""
        <div class="card">
            <div class="card-title">Daftar Invoice Lunas</div>
            <div class="card-subtitle">Rincian invoice yang sudah dibayar sesuai filter aktif -- tanpa data invoice outstanding</div>
    """, unsafe_allow_html=True)
    st.dataframe(
        df_lunas_tampil[kolom_tampil].sort_values("tanggal_bayar", ascending=False),
        use_container_width=True,
        hide_index=True,
    )
    st.download_button(
        "↓  Unduh Daftar Lunas (CSV)",
        df_lunas_tampil[kolom_tampil].to_csv(index=False, sep=";").encode("utf-8-sig"),
        file_name="monitoring_pembayaran_lunas.csv",
        mime="text/csv",
        key="download_lunas_detail",
    )
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown(
    '<div class="footer-note">Data otomatis dari Supabase &middot; jalankan upload_to_supabase.py '
    'lalu refresh halaman untuk data terbaru (cache 5 menit)</div>',
    unsafe_allow_html=True,
)

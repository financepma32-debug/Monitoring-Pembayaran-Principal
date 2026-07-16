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
# PALET WARNA -- White + Red corporate (ref: Google Stitch)
# =========================================================
BG        = "#FFFFFF"
BG_SOFT   = "#FAFAFA"
CARD      = "#FFFFFF"
RED       = "#C81E2C"
RED_DARK  = "#9E1620"
RED_SOFT  = "#FDEDEE"
INK       = "#111111"
INK_SOFT  = "#6B7280"
LINE      = "#E7E5E4"
GREEN     = "#16A34A"
GREEN_SOFT= "#E9F9EF"
AMBER     = "#B45309"
AMBER_SOFT= "#FEF3E2"

# =========================================================
# IKON KUSTOM (SVG, bukan emoji) -- dipakai di sidebar, notice box,
# dan tombol download supaya tampilan konsisten & tidak bergantung
# pada font emoji bawaan OS/browser.
# =========================================================
def icon_svg(name, color="currentColor", size=15):
    paths = {
        # kotak grid 2x2 -> "Dashboard"
        "grid": '<rect x="1" y="1" width="6" height="6" rx="1"/><rect x="9" y="1" width="6" height="6" rx="1"/><rect x="1" y="9" width="6" height="6" rx="1"/><rect x="9" y="9" width="6" height="6" rx="1"/>',
        # tiga batang naik -> "Principal"
        "bars": '<rect x="1" y="9" width="3.2" height="6" rx="0.6"/><rect x="6.4" y="5" width="3.2" height="10" rx="0.6"/><rect x="11.8" y="1" width="3.2" height="14" rx="0.6"/>',
        # lingkaran + garis tengah -> "Pembayaran"
        "coin": '<circle cx="8" cy="8" r="6.5" fill="none" stroke="currentColor" stroke-width="1.6"/><line x1="8" y1="4.3" x2="8" y2="11.7" stroke="currentColor" stroke-width="1.6"/>',
        # segitiga peringatan + seru -> pengganti "⚠"
        "warn": '<path d="M8 1.4 L15 14.6 H1 Z" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/><line x1="8" y1="6.2" x2="8" y2="10" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/><circle cx="8" cy="12.3" r="0.9"/>',
        # panah ke bawah menuju garis -> pengganti "⬇"
        "download": '<line x1="8" y1="1.5" x2="8" y2="10" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/><path d="M4.2 7 L8 11 L11.8 7" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/><line x1="2" y1="14" x2="14" y2="14" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>',
    }
    fill = "none" if name in ("warn", "download") else color
    extra_fill = f'fill="{color}"' if name in ("grid", "bars") else ""
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 16 16" '
        f'xmlns="http://www.w3.org/2000/svg" style="vertical-align:-3px;color:{color};" {extra_fill}>'
        f'{paths[name]}</svg>'
    )

st.markdown(f"""
<style>
    #MainMenu, footer, header {{visibility: hidden;}}

    .stApp {{
        background-color: {BG_SOFT};
    }}
    html, body, [class*="css"] {{
        color: {INK};
        font-family: 'Inter', 'Segoe UI', -apple-system, sans-serif;
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
        border-radius: 8px;
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
        border-radius: 9px;
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
        font-weight: 800;
        font-size: 1.6rem;
    }}

    /* ---- generic card ---- */
    .card {{
        background-color: {CARD};
        border: 1px solid {LINE};
        border-radius: 10px;
        padding: 20px 22px;
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
        border: 1px solid #F3C6C6;
        background-color: {RED_SOFT};
        color: {RED_DARK};
        border-radius: 8px;
        padding: 12px 16px;
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
        border-radius: 6px;
        font-weight: 600;
    }}
    .stDownloadButton button:hover, .stButton button:hover {{
        background-color: {RED_DARK};
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
        gap: 4px;
        margin-bottom: 4px;
    }}
    section[data-testid="stSidebar"] div[role="radiogroup"] label {{
        width: 100%;
        padding: 10px 12px;
        border-radius: 8px;
        font-weight: 600;
        font-size: 0.9rem;
        color: {INK_SOFT};
        cursor: pointer;
        transition: background 0.12s ease;
    }}
    section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {{
        background: {RED_SOFT};
        color: {RED_DARK};
    }}
    section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {{
        background: {RED};
        color: white;
    }}
    section[data-testid="stSidebar"] div[role="radiogroup"] label > div:first-child {{
        display: none;
    }}
    section[data-testid="stSidebar"] div[role="radiogroup"] label div[data-testid="stMarkdownContainer"] p {{
        font-size: 0.9rem;
        font-weight: 600;
    }}
</style>
""", unsafe_allow_html=True)

# =========================================================
# Sidebar
# =========================================================
with st.sidebar:
    st.markdown(f"""
        <div class="side-brand">
            <div class="mark">MP</div>
            <div>
                <div class="side-brand-title">Monitoring Pembayaran</div>
                <div class="side-brand-sub">Principal</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    nav_options = ["Dashboard", "Principal", "Pembayaran"]
    nav_labels = {
        "Dashboard": "▦  Dashboard",
        "Principal": "▤  Principal",
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
            <div class="mark">₨</div>
            <div class="topbar-title">Monitoring Pembayaran Principal</div>
        </div>
        <div class="topbar-user"><b>Dashboard</b><br>SIMBA &middot; NSI &middot; MEIJI</div>
    </div>
""", unsafe_allow_html=True)

df = load_data()

if df.empty:
    st.markdown('<div class="page-title">Payment Monitoring Overview</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="notice-box">{icon_svg("warn", RED_DARK)} Belum ada data di Supabase. Jalankan upload_to_supabase.py dulu di komputer kamu.</div>', unsafe_allow_html=True)
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
        rc[1].markdown(fmt_rupiah(row['Total Nominal']))
        color_amt = RED_DARK if row["Nominal Belum Lunas"] > 0 else INK
        rc[2].markdown(f"<span style='color:{color_amt};font-weight:700;'>{fmt_rupiah(row['Nominal Belum Lunas'])}</span>", unsafe_allow_html=True)
        rc[3].markdown(f"<span style='color:{GREEN};font-weight:700;'>{fmt_num(int(row['Jumlah Lunas']))}</span>", unsafe_allow_html=True)
        rc[4].markdown(f"<span style='color:{RED_DARK};font-weight:700;'>{fmt_num(int(row['Jumlah Belum Lunas']))}</span>", unsafe_allow_html=True)
        rc[5].markdown(f"<span class='badge' style='background:{bg};color:{fg};'>{row['Risk']}</span>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

def render_overdue_notice(data_overdue, key_suffix=""):
    if len(data_overdue):
        st.markdown(
            f'<div class="notice-box">{icon_svg("warn", RED_DARK)} {fmt_num(len(data_overdue))} invoice sudah LEWAT JATUH TEMPO dan belum '
            f'dibayar (total {fmt_rupiah(data_overdue["nominal_invoice"].sum())})</div>',
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
    "Dashboard": ("Payment Monitoring Overview", "Status pembayaran invoice principal secara real-time."),
    "Principal": ("Ringkasan per Principal", "Perbandingan saldo, risiko, dan status keterlambatan SIMBA, NSI, dan MEIJI."),
    "Pembayaran": ("Detail Pembayaran", "Rincian transaksi, tren pembayaran, dan status lunas / belum lunas per invoice."),
}
judul, subjudul = judul_halaman[halaman]
st.markdown(f'<div class="page-title">{judul}</div>', unsafe_allow_html=True)
st.markdown(f'<div class="page-subtitle">{subjudul}</div>', unsafe_allow_html=True)

# ── KPI cards (tampil di semua halaman) ──────────
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Invoice", fmt_num(len(df_f)))
col2.metric("Lunas", fmt_num((df_f['status']=='LUNAS').sum()))
col3.metric("Belum Lunas", fmt_num((df_f['status']=='BELUM LUNAS').sum()))
total_belum_rp = df_f.loc[df_f["status"] == "BELUM LUNAS", "nominal_invoice"].sum()
col4.metric("Nominal Belum Lunas", fmt_rupiah_short(total_belum_rp), help=fmt_rupiah(total_belum_rp))

# =========================================================
# HALAMAN: DASHBOARD -- ringkasan umum semua principal
# =========================================================
if halaman == "Dashboard":
    render_overdue_notice(overdue, key_suffix="_dash")
    st.write("")

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
                ("1-30 Hari", (belum["hari_lewat"] >= 0) & (belum["hari_lewat"] <= 30), "#F3B4B9"),
                ("31-60 Hari", (belum["hari_lewat"] > 30) & (belum["hari_lewat"] <= 60), "#E8828B"),
                ("61-90 Hari", (belum["hari_lewat"] > 60) & (belum["hari_lewat"] <= 90), "#D64B57"),
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
                            <b>{fmt_rupiah(val)}</b>
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
    render_tabel_principal(hitung_summary_principal(df_f))

# =========================================================
# HALAMAN: PRINCIPAL -- fokus perbandingan & drill-down tiap principal
# =========================================================
elif halaman == "Principal":
    render_tabel_principal(hitung_summary_principal(df_f))
    st.write("")

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
            rc[3].markdown(fmt_rupiah(row['Nominal Lunas']))
            rc[4].markdown(fmt_rupiah(row['Nominal Belum Lunas']))
    else:
        st.info("Tidak ada data.")
    st.markdown("</div>", unsafe_allow_html=True)

    st.write("")

    # ── Tabel detail transaksi ──
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

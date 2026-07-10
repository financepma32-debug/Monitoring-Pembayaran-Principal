import streamlit as st
import pandas as pd
from supabase import create_client
from datetime import date

st.set_page_config(page_title="Monitoring Pembayaran Principal", layout="wide")

# ─────────────────────────────────────────────
# Koneksi Supabase (pakai ANON key -- aman untuk publik, read-only)
# Diisi lewat Streamlit Secrets, lihat PANDUAN_WEB.txt
# ─────────────────────────────────────────────
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

st.title("📊 Dashboard Monitoring Pembayaran Principal")

df = load_data()

if df.empty:
    st.warning("Belum ada data di Supabase. Jalankan `upload_to_supabase.py` dulu di komputer kamu.")
    st.stop()

# ── Sidebar filter ─────────────────────────────
st.sidebar.header("Filter")
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
    st.error(f"⚠️ {len(overdue):,} invoice sudah LEWAT JATUH TEMPO dan belum dibayar "
              f"(total Rp {overdue['nominal_invoice'].sum():,.0f})")

st.divider()

# ── Grafik ──────────────────────────────────────
c1, c2 = st.columns(2)

with c1:
    st.subheader("Status per Principal")
    pivot = df_f.groupby(["principal", "status"]).size().unstack(fill_value=0)
    st.bar_chart(pivot)

with c2:
    st.subheader("Nominal Belum Lunas per Principal")
    nominal_pivot = (
        df_f[df_f["status"] == "BELUM LUNAS"]
        .groupby("principal")["nominal_invoice"].sum()
        .sort_values(ascending=False)
    )
    st.bar_chart(nominal_pivot)

st.subheader("Tren Jatuh Tempo (Belum Lunas) per Bulan")
belum = df_f[df_f["status"] == "BELUM LUNAS"].copy()
if not belum.empty:
    belum["bulan_jatuh_tempo"] = belum["tanggal_jatuh_tempo"].dt.to_period("M").astype(str)
    tren = belum.groupby("bulan_jatuh_tempo")["nominal_invoice"].sum().sort_index()
    st.bar_chart(tren)

st.divider()

# ── Tabel detail ────────────────────────────────
st.subheader("Detail Data")
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
    "⬇️ Download hasil filter (CSV)",
    df_f[kolom_tampil].to_csv(index=False, sep=";").encode("utf-8-sig"),
    file_name="monitoring_pembayaran_filtered.csv",
    mime="text/csv",
)

st.caption("Data otomatis dari Supabase. Untuk update data terbaru, jalankan "
           "upload_to_supabase.py di komputer lalu refresh halaman ini "
           "(cache dashboard otomatis kadaluarsa tiap 5 menit).")

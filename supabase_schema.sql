-- =========================================================
-- SKEMA TABEL: monitoring_pembayaran
-- Jalankan ini SEKALI di Supabase Dashboard -> SQL Editor
-- =========================================================

create table if not exists monitoring_pembayaran (
    id                   bigint generated always as identity primary key,
    principal            text,
    no_invoice           text,
    no_payment_advice    text,
    nominal_invoice      numeric,
    no_miro              text,
    tanggal_jatuh_tempo  date,
    tanggal_bayar        date,
    status               text,              -- 'LUNAS' atau 'BELUM LUNAS'
    sumber_file          text,
    sumber_sheet         text,
    batch_id             text,              -- id unik tiap kali proses upload dijalankan
    updated_at           timestamptz default now()
);

-- kunci unik: 1 invoice dari 1 file sumber tidak boleh dobel
-- (kalau di-upload ulang, baris lama akan di-UPDATE, bukan ditambah lagi)
create unique index if not exists uniq_invoice_sumber
    on monitoring_pembayaran (principal, no_invoice, sumber_file);

-- index biar dashboard filter cepat
create index if not exists idx_status on monitoring_pembayaran (status);
create index if not exists idx_principal on monitoring_pembayaran (principal);
create index if not exists idx_jatuh_tempo on monitoring_pembayaran (tanggal_jatuh_tempo);

-- Aktifkan Row Level Security, lalu izinkan SEMUA ORANG hanya BACA (SELECT)
-- lewat anon key. Tulis/update HANYA lewat service_role key (dipakai script
-- upload di komputer kamu, bukan di dashboard publik).
alter table monitoring_pembayaran enable row level security;

drop policy if exists "public_read" on monitoring_pembayaran;
create policy "public_read"
    on monitoring_pembayaran
    for select
    to anon
    using (true);

"""
app.py
======
Antarmuka Streamlit untuk SoilLab (Soil Mechanics Laboratory Data Processing System).

Berkas ini HANYA mengurus tampilan: input, tabel, grafik, pesan, dan tombol unduh.
Semua rumus berada di calculations.py.

Jalankan dari direktori utama proyek:
    python -m streamlit run app.py
"""

import re

import numpy as np
import pandas as pd
import streamlit as st
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter, NullFormatter

import calculations as calc

# --------------------------------------------------------------------------
# Konstanta antarmuka
# --------------------------------------------------------------------------
HALAMAN = [
    "Dashboard",
    "Uji Kadar Air",
    "Berat Isi dan Berat Isi Kering",
    "Analisis Distribusi Ukuran Butir",
    "Uji Pemadatan Proctor",
    "Petunjuk dan Teori",
]

DESKRIPSI_MODUL = {
    "Uji Kadar Air": "Menghitung massa air, massa tanah kering, dan kadar air dari data penimbangan.",
    "Berat Isi dan Berat Isi Kering": "Menghitung massa jenis dan berat isi tanah basah serta kering.",
    "Analisis Distribusi Ukuran Butir": "Mengolah data analisis saringan menjadi tabel dan kurva distribusi ukuran butir.",
    "Uji Pemadatan Proctor": "Mengolah beberapa percobaan pemadatan menjadi kurva kadar air terhadap berat isi kering.",
    "Petunjuk dan Teori": "Definisi, rumus, satuan, contoh perhitungan, dan batasan interpretasi.",
}

# Pilihan format CSV: nilai True berarti format Excel pengaturan Indonesia.
FORMAT_CSV = {
    "Internasional (pemisah koma, desimal titik)": False,
    "Excel Indonesia (pemisah titik koma, desimal koma)": True,
}

# Kunci session state untuk input sederhana. Nilai awal None = kolom kosong.
STATE_AWAL = {
    "menu": HALAMAN[0],
    "format_csv": list(FORMAT_CSV)[0],
    "ka_kode": "", "ka_wadah": None, "ka_basah": None, "ka_kering": None,
    "bi_kode": "", "bi_massa": None, "bi_volume": None, "bi_kadar_air": None,
    "sv_kode": "", "sv_massa_awal": None,
    "pr_kode": "", "pr_volume": None,
}
# Kunci input yang harus tetap tersimpan saat pengguna berpindah halaman.
KUNCI_PERSISTEN = [k for k in STATE_AWAL if k not in ("menu", "format_csv")]

CSS = """
<style>
.block-container { padding-top: 2rem; max-width: 1180px; }
.soillab-header {
    background: #24435f; color: #ffffff; padding: 1.1rem 1.5rem;
    border-radius: 8px; margin-bottom: 1.2rem; border-left: 8px solid #b08a4e;
}
.soillab-header h1 { margin: 0; padding: 0; font-size: 1.9rem; letter-spacing: 0.1em; color: #ffffff; }
.soillab-header .sub { margin: 0.15rem 0 0.35rem 0; font-style: italic; color: #d6e2ee; }
.soillab-header .desk { margin: 0; font-size: 0.92rem; color: #eef3f8; }
div[data-testid="stMetric"] {
    background-color: rgba(128, 128, 128, 0.08);
    border: 1px solid rgba(128, 128, 128, 0.28);
    border-left: 5px solid #b08a4e;
    padding: 0.7rem 0.9rem; border-radius: 6px;
}
</style>
"""


# --------------------------------------------------------------------------
# Data awal dan data contoh
# --------------------------------------------------------------------------
def tabel_saringan_awal() -> pd.DataFrame:
    """Daftar saringan awal (BISA DISESUAIKAN). Massa dikosongkan agar diisi pengguna."""
    return pd.DataFrame({
        calc.KOLOM_NAMA_SARINGAN: ["No. 4", "No. 10", "No. 20", "No. 40", "No. 60", "No. 100", "No. 200", "Pan"],
        calc.KOLOM_BUKAAN: [4.75, 2.00, 0.850, 0.425, 0.250, 0.150, 0.075, 0.0],
        calc.KOLOM_MASSA_TERTAHAN: [np.nan] * 8,
    })


def tabel_saringan_contoh() -> pd.DataFrame:
    """DATA CONTOH untuk mencoba aplikasi (bukan hasil pengujian nyata)."""
    tabel = tabel_saringan_awal()
    tabel[calc.KOLOM_MASSA_TERTAHAN] = [12.5, 35.0, 58.0, 92.0, 80.0, 55.0, 38.0, 29.5]
    return tabel


def tabel_proctor_awal() -> pd.DataFrame:
    return pd.DataFrame({
        calc.KOLOM_NO_PERCOBAAN: [1, 2, 3, 4, 5],
        calc.KOLOM_KADAR_AIR: [np.nan] * 5,
        calc.KOLOM_MASSA_CETAKAN_TANAH: [np.nan] * 5,
        calc.KOLOM_MASSA_CETAKAN: [np.nan] * 5,
    })


def tabel_proctor_contoh() -> pd.DataFrame:
    """DATA CONTOH untuk mencoba aplikasi (bukan hasil pengujian nyata)."""
    return pd.DataFrame({
        calc.KOLOM_NO_PERCOBAAN: [1, 2, 3, 4, 5],
        calc.KOLOM_KADAR_AIR: [8.0, 10.0, 12.0, 14.0, 16.0],
        calc.KOLOM_MASSA_CETAKAN_TANAH: [5810.0, 5930.0, 6010.0, 6000.0, 5940.0],
        calc.KOLOM_MASSA_CETAKAN: [4200.0] * 5,
    })


def inisialisasi_state() -> None:
    """Siapkan session state sekali, dan cegah input hilang saat pindah halaman."""
    for kunci, nilai in STATE_AWAL.items():
        st.session_state.setdefault(kunci, nilai)
    for awalan, fungsi in (("sv", tabel_saringan_awal), ("pr", tabel_proctor_awal)):
        st.session_state.setdefault(f"{awalan}_dasar", fungsi())   # data yang diberikan ke editor
        st.session_state.setdefault(f"{awalan}_edit", fungsi())    # hasil edit terakhir pengguna
        st.session_state.setdefault(f"{awalan}_versi", 0)          # mengganti kunci editor saat perlu reset
    # Streamlit menghapus nilai widget yang tidak ditampilkan pada satu putaran skrip.
    # Menetapkan ulang nilainya di sini membuat input tetap tersimpan antarhalaman.
    for kunci in KUNCI_PERSISTEN:
        st.session_state[kunci] = st.session_state[kunci]


def sinkronkan_editor_saat_pindah_halaman(halaman: str) -> None:
    """Saat berpindah halaman, jadikan hasil edit terakhir sebagai data dasar editor tabel."""
    if st.session_state.get("_halaman_terakhir") != halaman:
        for awalan in ("sv", "pr"):
            st.session_state[f"{awalan}_dasar"] = st.session_state[f"{awalan}_edit"].copy()
            st.session_state[f"{awalan}_versi"] += 1
        st.session_state["_halaman_terakhir"] = halaman


# --------------------------------------------------------------------------
# Fungsi bantu tampilan
# --------------------------------------------------------------------------
def tampilkan_header() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown(
        """
        <div class="soillab-header">
            <h1>SOILLAB</h1>
            <p class="sub">Soil Mechanics Laboratory Data Processing System</p>
            <p class="desk">Alat bantu perhitungan dasar mekanika tanah dari data pengujian laboratorium.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def input_angka(label: str, kunci: str, bantuan: str | None = None) -> None:
    """Kolom angka kosong secara awal; satuan wajib ada di dalam label."""
    st.number_input(label, value=None, step=0.01, format="%.4f", key=kunci,
                    help=bantuan, placeholder="Isi angka")


def tampilkan_tabel(tabel: pd.DataFrame, desimal: int = 3) -> None:
    """Tampilkan tabel dengan format angka konsisten (hanya tampilan; nilai asli tidak dibulatkan)."""
    konfigurasi = {}
    for kolom in tabel.columns:
        if pd.api.types.is_integer_dtype(tabel[kolom]):
            konfigurasi[kolom] = st.column_config.NumberColumn(kolom, format="%d")
        elif pd.api.types.is_float_dtype(tabel[kolom]):
            konfigurasi[kolom] = st.column_config.NumberColumn(kolom, format=f"%.{desimal}f")
    st.dataframe(tabel, hide_index=True, column_config=konfigurasi)


def tombol_unduh_csv(tabel: pd.DataFrame, nama_dasar: str, kode: str, kunci: str) -> None:
    """Tombol unduh CSV. File hanya dibuat saat pengguna menekan tombol unduh di browser."""
    slug = re.sub(r"[^A-Za-z0-9_-]+", "_", kode).strip("_") or "sampel"
    format_excel_id = FORMAT_CSV[st.session_state["format_csv"]]
    st.download_button(
        "Unduh hasil (CSV)",
        data=calc.buat_csv_bytes(tabel, format_excel_id),
        file_name=f"{nama_dasar}_{slug}.csv",
        mime="text/csv",
        key=kunci,
    )
    st.caption("Format CSV dapat diganti di sidebar (Internasional atau Excel Indonesia).")


def tampilkan_galat(galat: calc.ValidasiError) -> None:
    st.error(f"Data belum dapat dihitung:\n\n{galat}")


def pindah_halaman(nama: str) -> None:
    st.session_state["menu"] = nama


# --------------------------------------------------------------------------
# Grafik
# --------------------------------------------------------------------------
def gambar_kurva_saringan(titik: pd.DataFrame, kode: str) -> Figure:
    """Kurva distribusi ukuran butir: sumbu X logaritmik, Y persen lolos."""
    fig = Figure(figsize=(8, 4.6), dpi=110)
    ax = fig.subplots()
    ax.plot(titik[calc.KOLOM_BUKAAN], titik[calc.KOLOM_PERSEN_LOLOS], marker="o", linewidth=1.8,
            color="#24435f", label=f"Distribusi ukuran butir ({kode})")
    ax.set_xscale("log")
    ax.invert_xaxis()  # konvensi geoteknik: butir terbesar di kiri
    ax.set_xticks(list(titik[calc.KOLOM_BUKAAN]))  # label sumbu X tepat pada bukaan saringan yang diukur
    ax.xaxis.set_major_formatter(FuncFormatter(lambda nilai, _: f"{nilai:g}"))
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.set_ylim(0, 100)
    ax.set_xlabel("Ukuran butir / bukaan saringan (mm), skala logaritmik")
    ax.set_ylabel("Persentase lolos (%)")
    ax.set_title("Kurva Distribusi Ukuran Butir")
    ax.grid(True, which="both", linestyle=":", linewidth=0.7)
    ax.legend(loc="best", fontsize=8)
    fig.tight_layout()
    return fig


def gambar_kurva_proctor(hasil: pd.DataFrame, pengamatan: calc.PengamatanProctor,
                         kurva: calc.KurvaKuadratik, kode: str) -> Figure:
    """Titik percobaan Proctor, titik maksimum pengamatan, dan kurva pendekatan (jika layak)."""
    fig = Figure(figsize=(8, 4.6), dpi=110)
    ax = fig.subplots()
    w = hasil[calc.KOLOM_KADAR_AIR].to_numpy(dtype=float)
    gamma_d = hasil[calc.KOLOM_GAMMA_KERING].to_numpy(dtype=float)

    ax.scatter(w, gamma_d, s=45, color="#24435f", zorder=3, label=f"Titik percobaan ({kode})")
    for nomor, x, y in zip(hasil[calc.KOLOM_NO_PERCOBAAN], w, gamma_d):
        ax.annotate(str(nomor), (x, y), textcoords="offset points", xytext=(6, 6), fontsize=8)
    ax.scatter([pengamatan.kadar_air_pada_maks_persen], [pengamatan.berat_isi_kering_maks_kn_m3],
               s=150, facecolors="none", edgecolors="#b03a2e", linewidths=1.8, zorder=4,
               label="γd maksimum pengamatan")
    if kurva.layak:
        xs = np.linspace(w.min(), w.max(), 200)
        ax.plot(xs, calc.evaluasi_kurva(kurva, xs), linestyle="--", color="#b08a4e", linewidth=1.8,
                label="Pendekatan polinomial derajat 2")
        ax.scatter([kurva.kadar_air_optimum_persen], [kurva.berat_isi_kering_maks_kn_m3], marker="*",
                   s=170, color="#b08a4e", zorder=5,
                   label=f"Puncak estimasi (OMC {kurva.kadar_air_optimum_persen:.2f}%)")
    ax.set_xlabel("Kadar air, w (%)")
    ax.set_ylabel("Berat isi kering, γd (kN/m³)")
    ax.set_title("Kurva Pemadatan: Kadar Air terhadap Berat Isi Kering")
    ax.grid(True, linestyle=":", linewidth=0.7)
    ax.legend(loc="lower center", fontsize=8)
    fig.tight_layout()
    return fig


# --------------------------------------------------------------------------
# Halaman 1: Dashboard
# --------------------------------------------------------------------------
def halaman_dashboard() -> None:
    st.header("Dashboard")
    st.write(
        "SoilLab membantu mahasiswa Teknik Sipil mengolah data pengujian laboratorium mekanika tanah: "
        "memasukkan data hasil penimbangan atau pembacaan, memeriksa kewajarannya, menghitung parameter, "
        "dan mengunduh hasilnya untuk laporan praktikum."
    )

    st.subheader("Alur penggunaan")
    st.markdown(
        "**Input data laboratorium** → **Validasi data** → **Perhitungan** → "
        "**Visualisasi hasil** → **Unduh laporan (CSV)**"
    )

    st.subheader("Modul pengujian")
    nama_modul = list(DESKRIPSI_MODUL)
    kolom = st.columns(2)
    for indeks, nama in enumerate(nama_modul):
        with kolom[indeks % 2]:
            with st.container(border=True):
                st.markdown(f"**{nama}**")
                st.write(DESKRIPSI_MODUL[nama])
                st.button("Buka modul", key=f"buka_{indeks}", on_click=pindah_halaman, args=(nama,))

    st.subheader("Hal yang perlu diperhatikan")
    st.info(
        "Hasil perhitungan hanya sebaik data yang dimasukkan. Periksa satuan, ketelitian penimbangan, "
        "dan prosedur pengujian sebelum memakai hasilnya."
    )
    st.warning(
        "SoilLab adalah alat bantu pembelajaran. Aplikasi ini bukan pengganti pemeriksaan teknis oleh "
        "tenaga ahli dan tidak dimaksudkan untuk menentukan desain fondasi atau struktur."
    )
    st.caption(
        "Setiap modul menyediakan tombol untuk mengisi DATA CONTOH. Data contoh hanya untuk mencoba "
        "aplikasi, diberi label jelas, dan bukan hasil pengujian nyata."
    )


# --------------------------------------------------------------------------
# Halaman 2: Uji Kadar Air
# --------------------------------------------------------------------------
def isi_contoh_kadar_air() -> None:
    st.session_state.update(ka_kode="DATA CONTOH", ka_wadah=20.0, ka_basah=120.0, ka_kering=100.0)


def kosongkan_kadar_air() -> None:
    st.session_state.update(ka_kode="", ka_wadah=None, ka_basah=None, ka_kering=None)


def halaman_kadar_air() -> None:
    st.header("Uji Kadar Air Tanah")
    st.write("Menghitung kadar air tanah dari data penimbangan: wadah kosong, wadah + tanah basah, "
             "dan wadah + tanah kering.")

    with st.expander("Rumus yang digunakan", expanded=True):
        st.latex(r"M_{\text{air}} = M_{\text{wadah+tanah basah}} - M_{\text{wadah+tanah kering}}")
        st.latex(r"M_{\text{tanah kering}} = M_{\text{wadah+tanah kering}} - M_{\text{wadah kosong}}")
        st.latex(r"w = \frac{M_{\text{air}}}{M_{\text{tanah kering}}} \times 100\,\%")

    st.subheader("Data penimbangan")
    st.text_input("Kode / nama sampel", key="ka_kode", placeholder="Contoh: BH-1 kedalaman 1,5 m")
    kol1, kol2, kol3 = st.columns(3)
    with kol1:
        input_angka("Massa wadah kosong (g)", "ka_wadah")
    with kol2:
        input_angka("Massa wadah + tanah basah (g)", "ka_basah")
    with kol3:
        input_angka("Massa wadah + tanah kering (g)", "ka_kering")

    tb1, tb2, _ = st.columns([1, 1, 3])
    tb1.button("Isi DATA CONTOH", key="ka_contoh", on_click=isi_contoh_kadar_air,
               help="Mengisi kolom dengan angka contoh (bukan hasil uji nyata).")
    tb2.button("Kosongkan input", key="ka_kosong", on_click=kosongkan_kadar_air)

    nilai = [st.session_state[k] for k in ("ka_wadah", "ka_basah", "ka_kering")]
    if any(v is None for v in nilai):
        st.info("Lengkapi ketiga massa untuk menampilkan hasil.")
        return
    try:
        hasil = calc.hitung_kadar_air(*nilai)
    except calc.ValidasiError as galat:
        tampilkan_galat(galat)
        return

    kode = st.session_state["ka_kode"].strip() or "Tanpa kode"
    st.session_state["hasil_ka_terakhir"] = hasil.kadar_air_persen  # dipakai tombol di Modul 3
    st.success("Perhitungan berhasil.")

    st.subheader("Hasil")
    m1, m2, m3 = st.columns(3)
    m1.metric("Massa air", f"{hasil.massa_air_g:.2f} g")
    m2.metric("Massa tanah kering", f"{hasil.massa_tanah_kering_g:.2f} g")
    m3.metric("Kadar air, w", f"{hasil.kadar_air_persen:.2f} %")

    tabel = calc.buat_tabel_kadar_air(kode, *nilai, hasil)
    st.subheader("Tabel ringkasan data dan hasil")
    tampilkan_tabel(tabel, desimal=2)
    tombol_unduh_csv(tabel, "kadar_air", kode, "unduh_ka")


# --------------------------------------------------------------------------
# Halaman 3: Berat Isi
# --------------------------------------------------------------------------
def isi_contoh_berat_isi() -> None:
    st.session_state.update(bi_kode="DATA CONTOH", bi_massa=100.0, bi_volume=50.0, bi_kadar_air=25.0)


def kosongkan_berat_isi() -> None:
    st.session_state.update(bi_kode="", bi_massa=None, bi_volume=None, bi_kadar_air=None)


def salin_kadar_air_dari_modul_2() -> None:
    st.session_state["bi_kadar_air"] = st.session_state["hasil_ka_terakhir"]


def halaman_berat_isi() -> None:
    st.header("Berat Isi Tanah dan Berat Isi Kering")
    st.write("Menghitung massa jenis dan berat isi tanah basah serta kering dari massa tanah, volume sampel, "
             "dan kadar air.")

    with st.expander("Rumus yang digunakan", expanded=True):
        st.latex(r"\rho = \frac{M_{\text{basah}}}{V} \quad (\mathrm{g/cm^3})")
        st.latex(r"\gamma = \rho \times 9{,}80665 \quad (\mathrm{kN/m^3})")
        st.latex(r"w_{\text{desimal}} = \frac{w_{\%}}{100}")
        st.latex(r"\rho_d = \frac{\rho}{1 + w_{\text{desimal}}} \qquad \gamma_d = \frac{\gamma}{1 + w_{\text{desimal}}}")
        st.caption("Dengan massa dalam gram dan volume dalam cm³, ρ berada dalam g/cm³. "
                   "Nilai numerik ρ (g/cm³) dikali g = 9,80665 m/s² sama dengan γ dalam kN/m³.")

    st.subheader("Data sampel")
    st.text_input("Kode / nama sampel", key="bi_kode", placeholder="Contoh: UD-2 tabung 1")
    kol1, kol2, kol3 = st.columns(3)
    with kol1:
        input_angka("Massa tanah basah, tanpa wadah (g)", "bi_massa",
                    "Massa tanah saja, tidak termasuk wadah atau cetakan.")
    with kol2:
        input_angka("Volume sampel (cm³)", "bi_volume")
    with kol3:
        input_angka("Kadar air, w (%)", "bi_kadar_air",
                    "Masukkan dalam persen: tulis 25 untuk 25%. Aplikasi mengubahnya menjadi 0,25 di dalam rumus.")

    tb1, tb2, tb3 = st.columns([1, 1, 2])
    tb1.button("Isi DATA CONTOH", key="bi_contoh", on_click=isi_contoh_berat_isi,
               help="Mengisi kolom dengan angka contoh (bukan hasil uji nyata).")
    tb2.button("Kosongkan input", key="bi_kosong", on_click=kosongkan_berat_isi)
    if "hasil_ka_terakhir" in st.session_state:
        tb3.button(f"Pakai kadar air hasil Modul 2 ({st.session_state['hasil_ka_terakhir']:.2f} %)",
                   key="bi_salin", on_click=salin_kadar_air_dari_modul_2)

    nilai = [st.session_state[k] for k in ("bi_massa", "bi_volume", "bi_kadar_air")]
    if any(v is None for v in nilai):
        st.info("Lengkapi massa tanah, volume, dan kadar air untuk menampilkan hasil.")
        return
    try:
        hasil = calc.hitung_berat_isi_tanah(*nilai)
    except calc.ValidasiError as galat:
        tampilkan_galat(galat)
        return

    kode = st.session_state["bi_kode"].strip() or "Tanpa kode"
    st.success("Perhitungan berhasil.")
    st.caption(f"Kadar air dikonversi ke desimal untuk rumus: {nilai[2]:g} % → {hasil.kadar_air_desimal:.4f}")

    st.subheader("Hasil")
    a1, a2 = st.columns(2)
    a1.metric("Massa jenis basah, ρ", f"{hasil.massa_jenis_basah_g_cm3:.3f} g/cm³")
    a2.metric("Berat isi basah, γ", f"{hasil.berat_isi_basah_kn_m3:.3f} kN/m³")
    b1, b2 = st.columns(2)
    b1.metric("Massa jenis kering, ρd", f"{hasil.massa_jenis_kering_g_cm3:.3f} g/cm³")
    b2.metric("Berat isi kering, γd", f"{hasil.berat_isi_kering_kn_m3:.3f} kN/m³")

    tabel = calc.buat_tabel_berat_isi(kode, *nilai, hasil)
    st.subheader("Tabel ringkasan data dan hasil")
    tampilkan_tabel(tabel, desimal=3)
    tombol_unduh_csv(tabel, "berat_isi", kode, "unduh_bi")


# --------------------------------------------------------------------------
# Halaman 4: Analisis Saringan
# --------------------------------------------------------------------------
def isi_contoh_saringan() -> None:
    st.session_state["sv_dasar"] = tabel_saringan_contoh()
    st.session_state["sv_edit"] = tabel_saringan_contoh()
    st.session_state["sv_versi"] += 1
    st.session_state["sv_kode"] = "DATA CONTOH"
    st.session_state["sv_massa_awal"] = 400.0


def reset_saringan() -> None:
    st.session_state["sv_dasar"] = tabel_saringan_awal()
    st.session_state["sv_edit"] = tabel_saringan_awal()
    st.session_state["sv_versi"] += 1
    st.session_state["sv_kode"] = ""
    st.session_state["sv_massa_awal"] = None


def halaman_saringan() -> None:
    st.header("Analisis Distribusi Ukuran Butir Tanah")
    st.write("Mengolah hasil analisis saringan (sieve analysis) menjadi persentase tertahan, tertahan kumulatif, "
             "dan lolos, serta kurva distribusi ukuran butir.")

    with st.expander("Rumus yang digunakan", expanded=True):
        st.latex(r"M_{\text{total}} = \sum M_{\text{tertahan}} \ (\text{termasuk pan})")
        st.latex(r"\%\ \text{tertahan} = \frac{M_{\text{tertahan}}}{M_{\text{total}}} \times 100")
        st.latex(r"\%\ \text{tertahan kumulatif} = \sum \%\ \text{tertahan (dari saringan terbesar sampai saringan ini)}")
        st.latex(r"\%\ \text{lolos} = 100 - \%\ \text{tertahan kumulatif}")

    st.subheader("Data saringan")
    st.text_input("Kode / nama sampel", key="sv_kode", placeholder="Contoh: Sampel pasir BH-3")
    input_angka("Massa sampel kering awal (g), opsional", "sv_massa_awal",
                "Jika diisi, aplikasi membandingkannya dengan total massa tertahan untuk memeriksa "
                "kehilangan atau kelebihan massa.")
    st.caption("Daftar saringan di bawah adalah DATA AWAL yang dapat disesuaikan: ubah nama atau bukaan, "
               "tambah baris di baris paling bawah, atau hapus baris (pilih baris, lalu tekan Delete). "
               "Gunakan saringan yang benar-benar dipakai dalam pengujian. Baris pan memakai bukaan 0 mm. "
               "Isi massa 0 untuk saringan yang tidak menahan tanah.")

    editor = st.data_editor(
        st.session_state["sv_dasar"],
        key=f"sv_editor_{st.session_state['sv_versi']}",
        num_rows="dynamic",
        hide_index=True,
        column_config={
            calc.KOLOM_NAMA_SARINGAN: st.column_config.TextColumn(calc.KOLOM_NAMA_SARINGAN),
            calc.KOLOM_BUKAAN: st.column_config.NumberColumn(
                calc.KOLOM_BUKAAN, format="%.4f", help="Bukaan saringan dalam mm. Pan = 0."),
            calc.KOLOM_MASSA_TERTAHAN: st.column_config.NumberColumn(
                calc.KOLOM_MASSA_TERTAHAN, format="%.3f", help="Massa tanah tertahan dalam gram."),
        },
    )
    st.session_state["sv_edit"] = editor

    tb1, tb2, _ = st.columns([1, 1.4, 2.6])
    tb1.button("Isi DATA CONTOH", key="sv_contoh", on_click=isi_contoh_saringan,
               help="Mengisi tabel dengan angka contoh (bukan hasil uji nyata).")
    tb2.button("Kembalikan ke data awal", key="sv_reset", on_click=reset_saringan)

    if editor[calc.KOLOM_MASSA_TERTAHAN].isna().all():
        st.info("Isi kolom massa tertahan untuk menampilkan hasil.")
        return
    try:
        hasil = calc.hitung_analisis_saringan(editor, st.session_state["sv_massa_awal"])
    except calc.ValidasiError as galat:
        tampilkan_galat(galat)
        return

    kode = st.session_state["sv_kode"].strip() or "Tanpa kode"
    st.success("Perhitungan berhasil.")
    for pesan in hasil.peringatan:
        st.warning(pesan)

    st.subheader("Hasil")
    m1, m2 = st.columns(2)
    m1.metric("Total massa tertahan", f"{hasil.massa_total_g:.2f} g")
    if hasil.selisih_massa_persen is not None:
        m2.metric("Selisih terhadap massa awal", f"{hasil.selisih_massa_persen:.2f} %")

    tampilkan_tabel(hasil.tabel, desimal=3)

    st.subheader("Kurva distribusi ukuran butir")
    titik = calc.ambil_titik_kurva_saringan(hasil.tabel)
    if len(titik) >= 2:
        st.pyplot(gambar_kurva_saringan(titik, kode))
        st.caption("Sumbu X berskala logaritmik dan dibalik (butir terbesar di kiri) sesuai kebiasaan "
                   "penyajian di geoteknik. Baris pan (0 mm) tidak dapat digambar pada skala logaritmik, "
                   "tetapi tetap dihitung dalam total massa.")
    else:
        st.warning("Kurva tidak dapat digambar karena jumlah saringan dengan bukaan positif kurang dari 2.")

    tabel_csv = calc.buat_tabel_csv_saringan(kode, hasil, st.session_state["sv_massa_awal"])
    tombol_unduh_csv(tabel_csv, "analisis_saringan", kode, "unduh_sv")


# --------------------------------------------------------------------------
# Halaman 5: Pemadatan Proctor
# --------------------------------------------------------------------------
def isi_contoh_proctor() -> None:
    st.session_state["pr_dasar"] = tabel_proctor_contoh()
    st.session_state["pr_edit"] = tabel_proctor_contoh()
    st.session_state["pr_versi"] += 1
    st.session_state["pr_kode"] = "DATA CONTOH"
    st.session_state["pr_volume"] = 944.0


def reset_proctor() -> None:
    st.session_state["pr_dasar"] = tabel_proctor_awal()
    st.session_state["pr_edit"] = tabel_proctor_awal()
    st.session_state["pr_versi"] += 1
    st.session_state["pr_kode"] = ""
    st.session_state["pr_volume"] = None


def halaman_proctor() -> None:
    st.header("Uji Pemadatan Proctor")
    st.write("Mengolah data beberapa percobaan pemadatan pada kadar air berbeda untuk menggambarkan hubungan "
             "kadar air dan berat isi kering.")

    with st.expander("Rumus yang digunakan", expanded=True):
        st.latex(r"M_{\text{basah}} = M_{\text{cetakan+tanah basah}} - M_{\text{cetakan}}")
        st.latex(r"\rho = \frac{M_{\text{basah}}}{V_{\text{cetakan}}} \qquad "
                 r"\rho_d = \frac{\rho}{1 + w/100} \qquad \gamma_d = \rho_d \times 9{,}80665")
        st.latex(r"\gamma_d \approx a\,w^2 + b\,w + c \quad \text{(pendekatan kuadratik; puncak di } w = -\tfrac{b}{2a}\text{)}")

    st.subheader("Data percobaan")
    st.text_input("Kode / nama sampel", key="pr_kode", placeholder="Contoh: Timbunan STA 0+100")
    input_angka("Volume cetakan (cm³)", "pr_volume", "Volume dalam cetakan pemadatan yang Anda gunakan.")
    st.caption("Ubah, tambah (baris paling bawah), atau hapus baris percobaan. Setiap baris dihitung terpisah. "
               "Kadar air dalam persen; massa dalam gram. Baris yang sama sekali kosong diabaikan.")

    editor = st.data_editor(
        st.session_state["pr_dasar"],
        key=f"pr_editor_{st.session_state['pr_versi']}",
        num_rows="dynamic",
        hide_index=True,
        column_config={
            calc.KOLOM_NO_PERCOBAAN: st.column_config.NumberColumn(calc.KOLOM_NO_PERCOBAAN, format="%d"),
            calc.KOLOM_KADAR_AIR: st.column_config.NumberColumn(calc.KOLOM_KADAR_AIR, format="%.3f"),
            calc.KOLOM_MASSA_CETAKAN_TANAH: st.column_config.NumberColumn(
                calc.KOLOM_MASSA_CETAKAN_TANAH, format="%.2f"),
            calc.KOLOM_MASSA_CETAKAN: st.column_config.NumberColumn(calc.KOLOM_MASSA_CETAKAN, format="%.2f"),
        },
    )
    st.session_state["pr_edit"] = editor

    tb1, tb2, _ = st.columns([1, 1.4, 2.6])
    tb1.button("Isi DATA CONTOH", key="pr_contoh", on_click=isi_contoh_proctor,
               help="Mengisi tabel dan volume dengan angka contoh (bukan hasil uji nyata).")
    tb2.button("Kembalikan ke data awal", key="pr_reset", on_click=reset_proctor)

    volume = st.session_state["pr_volume"]
    data_terisi = editor[[calc.KOLOM_KADAR_AIR, calc.KOLOM_MASSA_CETAKAN_TANAH, calc.KOLOM_MASSA_CETAKAN]]
    if volume is None or data_terisi.isna().all().all():
        st.info("Isi volume cetakan dan data percobaan untuk menampilkan hasil.")
        return
    try:
        hasil = calc.hitung_pemadatan(editor, volume)
        pengamatan = calc.cari_maksimum_pengamatan(hasil)
        kurva = calc.sesuaikan_kurva_kuadratik(hasil[calc.KOLOM_KADAR_AIR], hasil[calc.KOLOM_GAMMA_KERING])
    except calc.ValidasiError as galat:
        tampilkan_galat(galat)
        return

    kode = st.session_state["pr_kode"].strip() or "Tanpa kode"
    st.success(f"Perhitungan berhasil untuk {len(hasil)} percobaan.")

    st.subheader("Tabel data dan hasil hitungan")
    tampilkan_tabel(hasil, desimal=3)

    st.subheader("Hasil utama")
    st.markdown("**Nilai maksimum hasil pengamatan** (titik data tertinggi)")
    a1, a2 = st.columns(2)
    a1.metric("Berat isi kering maksimum, γd", f"{pengamatan.berat_isi_kering_maks_kn_m3:.3f} kN/m³")
    a2.metric(f"Kadar air pada γd maksimum (percobaan No. {pengamatan.nomor_percobaan})",
              f"{pengamatan.kadar_air_pada_maks_persen:.2f} %")

    st.markdown("**Estimasi dari kurva pendekatan kuadratik**")
    if kurva.layak:
        b1, b2 = st.columns(2)
        b1.metric("Kadar air optimum estimasi (OMC)", f"{kurva.kadar_air_optimum_persen:.2f} %")
        b2.metric("Berat isi kering maksimum estimasi (MDD)", f"{kurva.berat_isi_kering_maks_kn_m3:.3f} kN/m³")
        if kurva.r_kuadrat is not None:
            st.caption(f"R² pendekatan = {kurva.r_kuadrat:.4f} (dari {kurva.jumlah_titik} titik).")
        for catatan in kurva.catatan:
            st.info(catatan)
    else:
        st.warning(f"Estimasi OMC dan MDD dari kurva tidak dilaporkan. {kurva.alasan}")

    with st.expander("Perbedaan nilai maksimum pengamatan dan estimasi kurva", expanded=True):
        st.write(
            "Nilai maksimum pengamatan adalah titik data tertinggi yang benar-benar diukur, sehingga hanya "
            "berada pada kadar air yang dicoba. Estimasi kurva adalah puncak parabola yang dicocokkan pada "
            "seluruh titik; letaknya dapat berada di antara dua titik data dan nilainya dapat lebih tinggi "
            "atau lebih rendah daripada titik pengamatan tertinggi. Estimasi bergantung pada model kuadratik "
            "dan sebaran data. Pendekatan sederhana ini membantu belajar dan bukan pengganti prosedur serta "
            "interpretasi uji Proctor sesuai standar."
        )

    st.subheader("Grafik pemadatan")
    st.pyplot(gambar_kurva_proctor(hasil, pengamatan, kurva, kode))

    tabel_csv = calc.buat_tabel_csv_proctor(kode, float(volume), hasil, pengamatan, kurva)
    tombol_unduh_csv(tabel_csv, "pemadatan_proctor", kode, "unduh_pr")


# --------------------------------------------------------------------------
# Halaman 6: Petunjuk dan Teori
# --------------------------------------------------------------------------
def halaman_teori() -> None:
    st.header("Petunjuk dan Teori")
    tab_def, tab_rumus, tab_contoh, tab_batas = st.tabs(
        ["Definisi", "Rumus dan variabel", "Contoh perhitungan", "Standar dan batasan"]
    )

    with tab_def:
        st.markdown(
            """
**Kadar air tanah (w)** adalah perbandingan massa air dalam tanah terhadap massa butiran tanah kering,
dinyatakan dalam persen.

**Massa jenis (ρ)** adalah massa per satuan volume (g/cm³). **Berat isi (γ)** adalah berat per satuan
volume (kN/m³), yaitu massa jenis dikali percepatan gravitasi.

**Berat isi basah dan kering.** Berat isi basah (γ) dihitung dari massa tanah *beserta air* di dalam pori.
Berat isi kering (γd) dihitung dari massa butiran padat saja (tanpa air) per volume total. Untuk kadar air
yang sama, γd selalu lebih kecil daripada γ.

**Analisis distribusi ukuran butir.** Tanah kering diayak melalui susunan saringan dengan bukaan berurutan.
Massa yang tertahan di tiap saringan dibandingkan dengan massa total sehingga diperoleh persentase lolos
untuk setiap ukuran. Hasilnya digambar sebagai kurva dengan ukuran butir pada skala logaritmik.

**Uji pemadatan Proctor.** Tanah dengan beberapa kadar air berbeda dipadatkan dalam cetakan dengan usaha
pemadatan tertentu. Berat isi kering tiap percobaan digambarkan terhadap kadar air. Kurvanya biasanya
memiliki puncak: berat isi kering maksimum (MDD) pada kadar air optimum (OMC).
            """
        )

    with tab_rumus:
        st.markdown("**Kadar air**")
        st.latex(r"w = \frac{M_{\text{wadah+tanah basah}} - M_{\text{wadah+tanah kering}}}"
                 r"{M_{\text{wadah+tanah kering}} - M_{\text{wadah kosong}}} \times 100\,\%")
        st.markdown("**Massa jenis dan berat isi**")
        st.latex(r"\rho = \frac{M}{V} \qquad \gamma = \rho \, g \qquad \rho_d = \frac{\rho}{1+w} \qquad \gamma_d = \frac{\gamma}{1+w}")
        st.warning("Dalam persamaan di atas, w harus berupa **desimal** (25 % dipakai sebagai 0,25). "
                   "Aplikasi melakukan konversi ini otomatis dari nilai persen yang Anda masukkan.")
        st.markdown("**Analisis saringan**")
        st.latex(r"\%\,\text{tertahan} = \frac{M_i}{M_{\text{total}}} \times 100 \qquad "
                 r"\%\,\text{kumulatif}_i = \sum_{j \le i} \%\,\text{tertahan}_j \qquad "
                 r"\%\,\text{lolos}_i = 100 - \%\,\text{kumulatif}_i")
        st.markdown("**Pemadatan Proctor**")
        st.latex(r"\gamma_d(w) \approx a\,w^2 + b\,w + c \qquad "
                 r"w_{\text{opt}} = -\frac{b}{2a} \qquad \gamma_{d,\max} = c - \frac{b^2}{4a}")
        st.markdown(
            """
| Simbol | Arti | Satuan |
|---|---|---|
| M | Massa | g |
| V | Volume | cm³ |
| w | Kadar air (input dalam persen; desimal di dalam rumus) | % |
| ρ, ρd | Massa jenis basah, massa jenis kering | g/cm³ |
| γ, γd | Berat isi basah, berat isi kering | kN/m³ |
| g | Percepatan gravitasi, 9,80665 | m/s² |
| Mi | Massa tertahan pada saringan ke-i | g |
| Bukaan | Ukuran lubang saringan (pan = 0) | mm |
| OMC, MDD | Kadar air optimum, berat isi kering maksimum | %, kN/m³ |
            """
        )
        st.caption("Konversi satuan: 1 g/cm³ = 1000 kg/m³, sehingga ρ dalam g/cm³ dikali 9,80665 memberi γ dalam kN/m³.")

    with tab_contoh:
        st.markdown("Contoh ini konsisten dengan rumus di aplikasi dan hasilnya sama dengan data contoh pada Modul 2 dan 3.")
        st.markdown(
            """
**Kadar air.** Wadah kosong 20 g, wadah + tanah basah 120 g, wadah + tanah kering 100 g.
- M_air = 120 − 100 = 20 g
- M_tanah kering = 100 − 20 = 80 g
- w = (20 / 80) × 100 = **25 %**

**Berat isi.** Massa tanah basah 100 g, volume 50 cm³, w = 25 %.
- ρ = 100 / 50 = **2,00 g/cm³**; γ = 2,00 × 9,80665 = **19,613 kN/m³**
- w desimal = 25 / 100 = 0,25
- ρd = 2,00 / 1,25 = **1,60 g/cm³**; γd = 19,613 / 1,25 = **15,691 kN/m³**

**Analisis saringan.** Massa tertahan 10, 20, 30, dan 40 g (pan) → M_total = 100 g.
- % tertahan = 10, 20, 30, 40
- % kumulatif = 10, 30, 60, 100
- % lolos = 90, 70, 40, 0

**Proctor (satu percobaan).** V = 1000 cm³, cetakan kosong 2000 g, cetakan + tanah basah 3650 g, w = 10 %.
- M_basah = 1650 g; ρ = 1,65 g/cm³; ρd = 1,65 / 1,10 = 1,50 g/cm³
- γd = 1,50 × 9,80665 = **14,710 kN/m³**
            """
        )

    with tab_batas:
        st.markdown(
            """
**Rujukan standar yang lazim dipakai** (periksa edisi yang berlaku dan ikuti prosedur laboratorium Anda):
- Kadar air: SNI 1965:2008 *Cara uji penentuan kadar air untuk tanah dan batuan di laboratorium*; ASTM D2216.
- Analisis ukuran butir: SNI 3423:2008 *Cara uji analisis ukuran butir tanah*; ASTM D6913.
- Pemadatan: SNI 1742:2008 *Cara uji kepadatan ringan untuk tanah*; SNI 1743:2008 *Cara uji kepadatan berat
  untuk tanah*; ASTM D698 (standard Proctor) dan ASTM D1557 (modified Proctor).

SoilLab tidak menjamin bahwa data atau hasil memenuhi standar tersebut. Penerapan aktual harus mengikuti
edisi standar yang berlaku dan prosedur laboratorium.

**Batasan interpretasi hasil**
- Hasil hanya sebaik data masukan dan ketelitian penimbangan atau pembacaan.
- Aplikasi tidak mengklasifikasikan tanah (misalnya USCS) dan tidak menyimpulkan jenis tanah dari data saringan saja.
- Pendekatan kuadratik pada kurva Proctor hanya memperkirakan puncak dan hanya dilaporkan jika kurva terbuka
  ke bawah serta puncaknya berada di dalam rentang kadar air data.
- Aplikasi ini tidak memberi rekomendasi desain fondasi, timbunan, atau struktur.
- SoilLab adalah alat bantu belajar, bukan pengganti pemeriksaan oleh tenaga ahli.
            """
        )


# --------------------------------------------------------------------------
# Program utama
# --------------------------------------------------------------------------
def main() -> None:
    st.set_page_config(page_title="SoilLab", page_icon="🧪", layout="wide")
    inisialisasi_state()

    with st.sidebar:
        st.markdown("### SOILLAB")
        st.caption("Soil Mechanics Laboratory Data Processing System")
        halaman = st.radio("Menu navigasi", HALAMAN, key="menu")
        st.divider()
        st.radio("Format berkas CSV", list(FORMAT_CSV), key="format_csv",
                 help="Pilih 'Excel Indonesia' jika Excel Anda memakai koma sebagai pemisah desimal.")
        st.divider()
        st.caption("Alat bantu pembelajaran. Bukan pengganti pemeriksaan teknis oleh tenaga ahli.")

    sinkronkan_editor_saat_pindah_halaman(halaman)
    tampilkan_header()

    peta_halaman = {
        "Dashboard": halaman_dashboard,
        "Uji Kadar Air": halaman_kadar_air,
        "Berat Isi dan Berat Isi Kering": halaman_berat_isi,
        "Analisis Distribusi Ukuran Butir": halaman_saringan,
        "Uji Pemadatan Proctor": halaman_proctor,
        "Petunjuk dan Teori": halaman_teori,
    }
    peta_halaman[halaman]()


if __name__ == "__main__":
    main()

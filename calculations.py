"""
calculations.py
===============
Logika perhitungan SoilLab (Soil Mechanics Laboratory Calculator).

Berkas ini sengaja TIDAK mengimpor Streamlit, sehingga semua fungsi dapat diuji
terpisah dengan unittest. Antarmuka (app.py) hanya memanggil fungsi-fungsi di sini.

Satuan yang dipakai di seluruh modul:
    massa            : gram (g)
    volume           : sentimeter kubik (cm³)
    massa jenis      : g/cm³
    berat isi        : kN/m³  (g/cm³ x 9,80665 menghasilkan kN/m³ secara numerik)
    kadar air        : persen (%) pada input dan output; desimal hanya di dalam rumus
    bukaan saringan  : milimeter (mm)
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

# --------------------------------------------------------------------------
# Konstanta
# --------------------------------------------------------------------------
GRAVITASI = 9.80665  # percepatan gravitasi standar, m/s²

# Batas peringatan sederhana untuk selisih massa awal dan total massa tertahan.
# Ini parameter aplikasi untuk membantu pemeriksaan data, BUKAN batas dari standar.
BATAS_PERINGATAN_SELISIH_MASSA_PERSEN = 2.0

DESIMAL_CSV = 6          # pembulatan nilai pada berkas CSV (hanya untuk keluaran)
TOLERANSI_NUMERIK = 1e-9  # toleransi untuk perbandingan bilangan desimal

# Nama kolom tabel saringan
KOLOM_NAMA_SARINGAN = "Nama Saringan"
KOLOM_BUKAAN = "Bukaan (mm)"
KOLOM_MASSA_TERTAHAN = "Massa Tertahan (g)"
KOLOM_UKURAN_SARINGAN = "Ukuran Saringan"
KOLOM_PERSEN_TERTAHAN = "Tertahan (%)"
KOLOM_PERSEN_KUMULATIF = "Tertahan Kumulatif (%)"
KOLOM_PERSEN_LOLOS = "Lolos (%)"

# Nama kolom tabel Proctor
KOLOM_NO_PERCOBAAN = "No. Percobaan"
KOLOM_KADAR_AIR = "Kadar Air (%)"
KOLOM_MASSA_CETAKAN_TANAH = "Massa Cetakan + Tanah Basah (g)"
KOLOM_MASSA_CETAKAN = "Massa Cetakan Kosong (g)"
KOLOM_MASSA_TANAH_BASAH = "Massa Tanah Basah (g)"
KOLOM_RHO_BASAH = "Massa Jenis Basah (g/cm³)"
KOLOM_RHO_KERING = "Massa Jenis Kering (g/cm³)"
KOLOM_GAMMA_KERING = "Berat Isi Kering (kN/m³)"


# --------------------------------------------------------------------------
# Kesalahan validasi
# --------------------------------------------------------------------------
class ValidasiError(ValueError):
    """Kesalahan pada data masukan pengguna (bukan kesalahan program).

    Pesannya sudah ramah dan boleh langsung ditampilkan ke pengguna.
    Atribut `daftar_pesan` berisi semua masalah yang ditemukan.
    """

    def __init__(self, pesan: str | list[str]):
        if isinstance(pesan, str):
            self.daftar_pesan = [pesan]
        else:
            self.daftar_pesan = list(pesan)
        super().__init__("\n".join(self.daftar_pesan))

    def __str__(self) -> str:
        if len(self.daftar_pesan) == 1:
            return self.daftar_pesan[0]
        return "\n".join(f"- {pesan}" for pesan in self.daftar_pesan)


def _fmt(angka: float) -> str:
    """Format angka ringkas untuk pesan kesalahan."""
    return f"{angka:g}"


def _kosong(nilai: Any) -> bool:
    """True jika nilai dianggap kosong (None, NaN, atau teks kosong)."""
    if nilai is None:
        return True
    if isinstance(nilai, str):
        return nilai.strip() == ""
    return bool(pd.isna(nilai))


# --------------------------------------------------------------------------
# Validasi dasar
# --------------------------------------------------------------------------
def ke_angka(nilai: Any, nama: str) -> float:
    """Ubah `nilai` menjadi float yang valid, atau lempar ValidasiError.

    Menolak: kosong, teks yang bukan angka, nilai benar/salah, NaN, dan tak hingga.
    Teks dengan koma desimal ("25,5") diterima dan diubah menjadi 25.5.
    """
    if _kosong(nilai):
        raise ValidasiError(f"{nama} masih kosong. Isi dengan angka.")
    if isinstance(nilai, bool):
        raise ValidasiError(f"{nama} harus berupa angka, bukan nilai benar/salah.")
    try:
        if isinstance(nilai, str):
            angka = float(nilai.strip().replace(",", "."))
        else:
            angka = float(nilai)
    except (TypeError, ValueError):
        raise ValidasiError(f"{nama} bukan angka yang valid: {nilai!r}.") from None
    if not math.isfinite(angka):
        raise ValidasiError(f"{nama} harus berupa bilangan berhingga.")
    return angka


# --------------------------------------------------------------------------
# MODUL 2: KADAR AIR
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class HasilKadarAir:
    massa_air_g: float
    massa_tanah_kering_g: float
    kadar_air_persen: float


def hitung_kadar_air(
    massa_wadah_kosong_g: Any,
    massa_wadah_tanah_basah_g: Any,
    massa_wadah_tanah_kering_g: Any,
) -> HasilKadarAir:
    """Hitung kadar air tanah dari data penimbangan.

    M_air          = M_(wadah+tanah basah) - M_(wadah+tanah kering)
    M_tanah_kering = M_(wadah+tanah kering) - M_wadah_kosong
    w (%)          = (M_air / M_tanah_kering) x 100
    """
    m_wadah = ke_angka(massa_wadah_kosong_g, "Massa wadah kosong")
    m_basah = ke_angka(massa_wadah_tanah_basah_g, "Massa wadah + tanah basah")
    m_kering = ke_angka(massa_wadah_tanah_kering_g, "Massa wadah + tanah kering")

    galat: list[str] = []
    if m_wadah < 0:
        galat.append("Massa wadah kosong tidak boleh negatif.")
    if m_basah < 0:
        galat.append("Massa wadah + tanah basah tidak boleh negatif.")
    if m_kering < 0:
        galat.append("Massa wadah + tanah kering tidak boleh negatif.")
    if galat:
        raise ValidasiError(galat)

    if m_wadah >= m_kering:
        galat.append(
            "Massa wadah kosong harus lebih kecil daripada massa wadah + tanah kering "
            f"(massa tanah kering = {_fmt(m_kering - m_wadah)} g, harus lebih dari nol)."
        )
    if m_kering > m_basah:
        galat.append(
            "Massa wadah + tanah kering tidak boleh melebihi massa wadah + tanah basah."
        )
    if galat:
        raise ValidasiError(galat)

    massa_air = m_basah - m_kering
    massa_tanah_kering = m_kering - m_wadah  # dijamin > 0 oleh pemeriksaan di atas
    kadar_air = (massa_air / massa_tanah_kering) * 100.0
    return HasilKadarAir(massa_air, massa_tanah_kering, kadar_air)


# --------------------------------------------------------------------------
# MODUL 3: MASSA JENIS DAN BERAT ISI
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class HasilBeratIsi:
    massa_jenis_basah_g_cm3: float
    berat_isi_basah_kn_m3: float
    massa_jenis_kering_g_cm3: float
    berat_isi_kering_kn_m3: float
    kadar_air_desimal: float


def hitung_massa_jenis_basah(massa_basah_g: Any, volume_cm3: Any) -> float:
    """Massa jenis basah: rho = M_basah / V  (g/cm³)."""
    massa = ke_angka(massa_basah_g, "Massa tanah basah")
    volume = ke_angka(volume_cm3, "Volume sampel")
    galat: list[str] = []
    if massa <= 0:
        galat.append("Massa tanah basah harus lebih besar dari nol.")
    if volume <= 0:
        galat.append("Volume sampel harus lebih besar dari nol.")
    if galat:
        raise ValidasiError(galat)
    return massa / volume


def massa_jenis_ke_berat_isi(massa_jenis_g_cm3: Any) -> float:
    """Ubah massa jenis (g/cm³) menjadi berat isi (kN/m³): gamma = rho x 9,80665.

    1 g/cm³ = 1000 kg/m³, sehingga 1 g/cm³ x 9,80665 m/s² = 9,80665 kN/m³.
    """
    rho = ke_angka(massa_jenis_g_cm3, "Massa jenis")
    if rho <= 0:
        raise ValidasiError("Massa jenis harus lebih besar dari nol.")
    return rho * GRAVITASI


def persen_ke_desimal(kadar_air_persen: Any) -> float:
    """Ubah kadar air dari persen ke desimal (25 % -> 0,25) dan periksa nilainya."""
    w_persen = ke_angka(kadar_air_persen, "Kadar air")
    if w_persen < 0:
        raise ValidasiError("Kadar air tidak boleh negatif.")
    return w_persen / 100.0


def hitung_massa_jenis_kering(massa_jenis_basah_g_cm3: Any, kadar_air_persen: Any) -> float:
    """Massa jenis kering: rho_d = rho / (1 + w_desimal)  (g/cm³)."""
    rho = ke_angka(massa_jenis_basah_g_cm3, "Massa jenis basah")
    if rho <= 0:
        raise ValidasiError("Massa jenis basah harus lebih besar dari nol.")
    return rho / (1.0 + persen_ke_desimal(kadar_air_persen))


def hitung_berat_isi_kering(berat_isi_basah_kn_m3: Any, kadar_air_persen: Any) -> float:
    """Berat isi kering: gamma_d = gamma / (1 + w_desimal)  (kN/m³)."""
    gamma = ke_angka(berat_isi_basah_kn_m3, "Berat isi basah")
    if gamma <= 0:
        raise ValidasiError("Berat isi basah harus lebih besar dari nol.")
    return gamma / (1.0 + persen_ke_desimal(kadar_air_persen))


def hitung_berat_isi_tanah(massa_basah_g: Any, volume_cm3: Any, kadar_air_persen: Any) -> HasilBeratIsi:
    """Hitung semua parameter Modul 3 sekaligus (lihat fungsi-fungsi di atas)."""
    w_desimal = persen_ke_desimal(kadar_air_persen)  # periksa kadar air lebih dahulu
    rho = hitung_massa_jenis_basah(massa_basah_g, volume_cm3)
    gamma = massa_jenis_ke_berat_isi(rho)
    rho_d = hitung_massa_jenis_kering(rho, kadar_air_persen)
    gamma_d = hitung_berat_isi_kering(gamma, kadar_air_persen)
    return HasilBeratIsi(rho, gamma, rho_d, gamma_d, w_desimal)


# --------------------------------------------------------------------------
# MODUL 4: ANALISIS SARINGAN
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class HasilSaringan:
    tabel: pd.DataFrame            # tabel hasil, urut dari bukaan terbesar ke terkecil
    massa_total_g: float
    selisih_massa_persen: float | None   # None jika massa awal tidak diisi
    peringatan: tuple[str, ...]


def hitung_analisis_saringan(data: pd.DataFrame, massa_awal_g: Any = None) -> HasilSaringan:
    """Hitung distribusi ukuran butir dari tabel massa tertahan.

    % tertahan           = massa tertahan / M_total x 100
    % tertahan kumulatif = jumlah % tertahan dari bukaan terbesar sampai saringan ini
    % lolos              = 100 - % tertahan kumulatif

    Urutan baris masukan TIDAK dipakai: data selalu diurutkan dari bukaan terbesar
    ke terkecil (baris pan, bukaan 0 mm, otomatis berada di akhir).
    Baris yang benar-benar kosong diabaikan.
    """
    kolom = [KOLOM_NAMA_SARINGAN, KOLOM_BUKAAN, KOLOM_MASSA_TERTAHAN]
    hilang = [k for k in kolom if k not in data.columns]
    if hilang:
        raise ValidasiError(f"Kolom tabel saringan tidak lengkap: {', '.join(hilang)}.")

    df = data[kolom].reset_index(drop=True)
    galat: list[str] = []
    baris: list[tuple[str, float, float]] = []  # (nama, bukaan, massa)

    for i in range(len(df)):
        nama = "" if _kosong(df.at[i, KOLOM_NAMA_SARINGAN]) else str(df.at[i, KOLOM_NAMA_SARINGAN]).strip()
        mentah_bukaan = df.at[i, KOLOM_BUKAAN]
        mentah_massa = df.at[i, KOLOM_MASSA_TERTAHAN]
        if nama == "" and _kosong(mentah_bukaan) and _kosong(mentah_massa):
            continue  # baris kosong diabaikan

        label = f"Baris {i + 1}" + (f" ({nama})" if nama else "")
        bukaan = massa = None
        if _kosong(mentah_bukaan):
            galat.append(f"{label}: bukaan saringan masih kosong (isi 0 untuk pan).")
        else:
            try:
                bukaan = ke_angka(mentah_bukaan, f"{label}: bukaan saringan")
                if bukaan < 0:
                    galat.append(f"{label}: bukaan saringan tidak boleh negatif.")
                    bukaan = None
            except ValidasiError as err:
                galat.append(str(err))
        if _kosong(mentah_massa):
            galat.append(f"{label}: massa tertahan masih kosong (isi 0 jika tidak ada tanah tertahan).")
        else:
            try:
                massa = ke_angka(mentah_massa, f"{label}: massa tertahan")
                if massa < 0:
                    galat.append(f"{label}: massa tertahan tidak boleh negatif.")
                    massa = None
            except ValidasiError as err:
                galat.append(str(err))
        if bukaan is not None and massa is not None:
            baris.append((nama, bukaan, massa))

    if galat:
        raise ValidasiError(galat)
    if not baris:
        raise ValidasiError("Tabel saringan masih kosong. Isi minimal satu baris data.")

    tabel = pd.DataFrame(baris, columns=[KOLOM_NAMA_SARINGAN, KOLOM_BUKAAN, KOLOM_MASSA_TERTAHAN])

    # Bukaan positif harus unik; pan (0 mm) hanya boleh satu.
    positif = tabel[tabel[KOLOM_BUKAAN] > 0]
    duplikat = positif[positif[KOLOM_BUKAAN].duplicated(keep=False)]
    if not duplikat.empty:
        nilai = sorted({_fmt(v) for v in duplikat[KOLOM_BUKAAN]})
        raise ValidasiError(
            "Bukaan saringan positif harus unik. Bukaan ganda ditemukan: "
            + ", ".join(f"{v} mm" for v in nilai) + "."
        )
    if (tabel[KOLOM_BUKAAN] == 0).sum() > 1:
        raise ValidasiError("Hanya boleh ada satu baris pan (bukaan 0 mm).")

    massa_total = float(tabel[KOLOM_MASSA_TERTAHAN].sum())
    if massa_total <= 0:
        raise ValidasiError("Total massa tertahan harus lebih besar dari nol.")

    # Urutkan dari bukaan terbesar ke terkecil, tidak bergantung pada urutan input.
    tabel = tabel.sort_values(KOLOM_BUKAAN, ascending=False, kind="stable").reset_index(drop=True)

    def _nama_tampil(nama: str, bukaan: float) -> str:
        if nama:
            return nama
        return "Pan" if bukaan == 0 else f"{_fmt(bukaan)} mm"

    persen_tertahan = tabel[KOLOM_MASSA_TERTAHAN] / massa_total * 100.0
    persen_kumulatif = persen_tertahan.cumsum()
    persen_lolos = 100.0 - persen_kumulatif
    # Hilangkan sisa galat floating-point yang sangat kecil (misal 1e-14) agar tampil 0.
    persen_lolos = persen_lolos.where(persen_lolos.abs() > TOLERANSI_NUMERIK, 0.0)

    hasil = pd.DataFrame({
        KOLOM_UKURAN_SARINGAN: [_nama_tampil(n, b) for n, b in zip(tabel[KOLOM_NAMA_SARINGAN], tabel[KOLOM_BUKAAN])],
        KOLOM_BUKAAN: tabel[KOLOM_BUKAAN],
        KOLOM_MASSA_TERTAHAN: tabel[KOLOM_MASSA_TERTAHAN],
        KOLOM_PERSEN_TERTAHAN: persen_tertahan,
        KOLOM_PERSEN_KUMULATIF: persen_kumulatif,
        KOLOM_PERSEN_LOLOS: persen_lolos,
    })

    # ---- Peringatan data ----
    peringatan: list[str] = []
    if abs(float(persen_tertahan.sum()) - 100.0) > 1e-6:
        peringatan.append("Jumlah persentase tertahan tidak sama dengan 100%. Periksa kembali data.")
    if not (tabel[KOLOM_BUKAAN] == 0).any():
        peringatan.append(
            "Tidak ada baris pan. Total massa hanya dihitung dari saringan yang diisi, sehingga "
            "persentase lolos pada saringan terkecil selalu 0%. Jika ada tanah yang lolos "
            "saringan terkecil, tambahkan baris pan (bukaan 0 mm)."
        )

    selisih = None
    if not _kosong(massa_awal_g):
        massa_awal = ke_angka(massa_awal_g, "Massa sampel awal")
        if massa_awal <= 0:
            raise ValidasiError("Massa sampel awal harus lebih besar dari nol.")
        selisih = (massa_awal - massa_total) / massa_awal * 100.0
        if abs(selisih) > BATAS_PERINGATAN_SELISIH_MASSA_PERSEN:
            arah = "lebih kecil" if selisih > 0 else "lebih besar"
            peringatan.append(
                f"Total massa tertahan ({massa_total:.2f} g) {arah} daripada massa sampel awal "
                f"({massa_awal:.2f} g); selisih {abs(selisih):.2f}%. Periksa penimbangan atau kehilangan "
                f"massa saat pengayakan (batas peringatan aplikasi {BATAS_PERINGATAN_SELISIH_MASSA_PERSEN:g}%, "
                "bukan batas standar)."
            )

    return HasilSaringan(hasil, massa_total, selisih, tuple(peringatan))


def ambil_titik_kurva_saringan(tabel_hasil: pd.DataFrame) -> pd.DataFrame:
    """Ambil hanya baris dengan bukaan positif (bukaan 0 mm tidak bisa di sumbu log)."""
    return tabel_hasil[tabel_hasil[KOLOM_BUKAAN] > 0].reset_index(drop=True)


# --------------------------------------------------------------------------
# MODUL 5: PEMADATAN PROCTOR
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class PengamatanProctor:
    berat_isi_kering_maks_kn_m3: float
    kadar_air_pada_maks_persen: float
    nomor_percobaan: int


@dataclass(frozen=True)
class KurvaKuadratik:
    """Hasil pendekatan kuadratik gamma_d = a x² + b x + c dengan x = w - w_pusat."""
    layak: bool
    alasan: str
    jumlah_titik: int
    jumlah_kadar_air_berbeda: int
    koefisien: tuple[float, float, float] | None = None
    w_pusat: float = 0.0
    kadar_air_optimum_persen: float | None = None
    berat_isi_kering_maks_kn_m3: float | None = None
    r_kuadrat: float | None = None
    catatan: tuple[str, ...] = ()


def hitung_pemadatan(data: pd.DataFrame, volume_cetakan_cm3: Any) -> pd.DataFrame:
    """Hitung berat isi kering untuk setiap percobaan Proctor (tiap baris berdiri sendiri).

    M_basah = M_(cetakan+tanah basah) - M_cetakan
    rho     = M_basah / V_cetakan                (g/cm³)
    rho_d   = rho / (1 + w/100)                  (g/cm³)
    gamma_d = rho_d x 9,80665                    (kN/m³)
    """
    volume = ke_angka(volume_cetakan_cm3, "Volume cetakan")
    if volume <= 0:
        raise ValidasiError("Volume cetakan harus lebih besar dari nol.")

    kolom = [KOLOM_NO_PERCOBAAN, KOLOM_KADAR_AIR, KOLOM_MASSA_CETAKAN_TANAH, KOLOM_MASSA_CETAKAN]
    hilang = [k for k in kolom if k not in data.columns]
    if hilang:
        raise ValidasiError(f"Kolom tabel Proctor tidak lengkap: {', '.join(hilang)}.")

    df = data[kolom].reset_index(drop=True)
    galat: list[str] = []
    baris_hasil: list[dict[str, float]] = []

    for i in range(len(df)):
        w_mentah = df.at[i, KOLOM_KADAR_AIR]
        mt_mentah = df.at[i, KOLOM_MASSA_CETAKAN_TANAH]
        mc_mentah = df.at[i, KOLOM_MASSA_CETAKAN]
        no_mentah = df.at[i, KOLOM_NO_PERCOBAAN]
        if _kosong(w_mentah) and _kosong(mt_mentah) and _kosong(mc_mentah):
            continue  # baris tanpa data diabaikan (nomor percobaan saja tidak cukup)

        label = f"Baris {i + 1}"
        try:
            w = ke_angka(w_mentah, f"{label}: kadar air")
            mt = ke_angka(mt_mentah, f"{label}: massa cetakan + tanah basah")
            mc = ke_angka(mc_mentah, f"{label}: massa cetakan kosong")
        except ValidasiError as err:
            galat.append(str(err))
            continue

        galat_baris: list[str] = []
        if w < 0:
            galat_baris.append(f"{label}: kadar air tidak boleh negatif.")
        if mc < 0:
            galat_baris.append(f"{label}: massa cetakan kosong tidak boleh negatif.")
        if mt <= mc:
            galat_baris.append(
                f"{label}: massa cetakan + tanah basah harus lebih besar daripada massa cetakan kosong."
            )
        if galat_baris:
            galat.extend(galat_baris)
            continue

        if _kosong(no_mentah):
            nomor = len(baris_hasil) + 1
        else:
            try:
                nomor_angka = ke_angka(no_mentah, f"{label}: nomor percobaan")
            except ValidasiError as err:
                galat.append(str(err))
                continue
            if not float(nomor_angka).is_integer():
                galat.append(f"{label}: nomor percobaan harus bilangan bulat.")
                continue
            nomor = int(nomor_angka)

        massa_basah = mt - mc
        rho = hitung_massa_jenis_basah(massa_basah, volume)
        rho_d = hitung_massa_jenis_kering(rho, w)
        gamma_d = massa_jenis_ke_berat_isi(rho_d)
        baris_hasil.append({
            KOLOM_NO_PERCOBAAN: nomor,
            KOLOM_KADAR_AIR: w,
            KOLOM_MASSA_CETAKAN_TANAH: mt,
            KOLOM_MASSA_CETAKAN: mc,
            KOLOM_MASSA_TANAH_BASAH: massa_basah,
            KOLOM_RHO_BASAH: rho,
            KOLOM_RHO_KERING: rho_d,
            KOLOM_GAMMA_KERING: gamma_d,
        })

    if galat:
        raise ValidasiError(galat)
    if not baris_hasil:
        raise ValidasiError("Belum ada baris percobaan yang terisi lengkap.")
    return pd.DataFrame(baris_hasil)


def cari_maksimum_pengamatan(hasil: pd.DataFrame) -> PengamatanProctor:
    """Cari percobaan dengan berat isi kering terbesar (nilai pengamatan, bukan estimasi)."""
    if hasil.empty:
        raise ValidasiError("Tidak ada data percobaan untuk dicari nilai maksimumnya.")
    idx = hasil[KOLOM_GAMMA_KERING].idxmax()
    return PengamatanProctor(
        berat_isi_kering_maks_kn_m3=float(hasil.at[idx, KOLOM_GAMMA_KERING]),
        kadar_air_pada_maks_persen=float(hasil.at[idx, KOLOM_KADAR_AIR]),
        nomor_percobaan=int(hasil.at[idx, KOLOM_NO_PERCOBAAN]),
    )


def sesuaikan_kurva_kuadratik(kadar_air_persen: Any, berat_isi_kering_kn_m3: Any) -> KurvaKuadratik:
    """Pendekatan polinomial derajat dua untuk memperkirakan puncak kurva pemadatan.

    Hasil dinyatakan layak HANYA jika:
      1. ada sekurang-kurangnya 3 nilai kadar air yang berbeda,
      2. kurva terbuka ke bawah (koefisien a < 0), dan
      3. titik puncak berada di dalam rentang kadar air data percobaan.
    Jika salah satu syarat tidak terpenuhi, OMC dan MDD hasil regresi TIDAK dilaporkan
    dan `alasan` menjelaskan penyebabnya.
    """
    w = np.asarray(kadar_air_persen, dtype=float).ravel()
    y = np.asarray(berat_isi_kering_kn_m3, dtype=float).ravel()
    if w.size == 0 or w.size != y.size:
        raise ValidasiError("Data kadar air dan berat isi kering harus berjumlah sama dan tidak kosong.")
    if not (np.all(np.isfinite(w)) and np.all(np.isfinite(y))):
        raise ValidasiError("Data kurva mengandung nilai yang bukan angka berhingga.")

    jumlah_titik = int(w.size)
    jumlah_berbeda = int(np.unique(np.round(w, 6)).size)

    def tidak_layak(alasan: str) -> KurvaKuadratik:
        return KurvaKuadratik(False, alasan, jumlah_titik, jumlah_berbeda)

    if jumlah_berbeda < 3:
        return tidak_layak(
            "Data belum memadai: pendekatan kuadratik memerlukan sekurang-kurangnya 3 nilai kadar air "
            f"yang berbeda, sedangkan data hanya memiliki {jumlah_berbeda}."
        )

    # Kadar air dipusatkan (x = w - rata-rata) agar perhitungan lebih stabil secara numerik.
    w_pusat = float(w.mean())
    x = w - w_pusat
    try:
        a, b, c = (float(v) for v in np.polyfit(x, y, 2))
    except (np.linalg.LinAlgError, ValueError) as err:
        return tidak_layak(f"Pendekatan kurva gagal karena kesalahan numerik ({err}).")
    if not all(math.isfinite(v) for v in (a, b, c)):
        return tidak_layak("Pendekatan kurva menghasilkan koefisien yang tidak valid.")

    if a >= -1e-12:
        return tidak_layak(
            "Kurva pendekatan tidak terbuka ke bawah (koefisien kuadrat tidak negatif), sehingga "
            "tidak memiliki titik puncak maksimum. Periksa data atau tambah percobaan di sekitar puncak."
        )

    x_puncak = -b / (2.0 * a)
    omc = x_puncak + w_pusat
    w_min, w_maks = float(w.min()), float(w.max())
    if omc < w_min - TOLERANSI_NUMERIK or omc > w_maks + TOLERANSI_NUMERIK:
        return tidak_layak(
            f"Titik puncak kurva pendekatan (kadar air ≈ {omc:.2f}%) berada di luar rentang data "
            f"percobaan ({w_min:g}% – {w_maks:g}%). Estimasi puncak tidak dilaporkan; tambahkan "
            "percobaan pada kadar air yang melingkupi puncak."
        )

    mdd = c - (b * b) / (4.0 * a)  # = a x0² + b x0 + c
    fit = a * x**2 + b * x + c
    ss_res = float(np.sum((y - fit) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else None

    catatan: list[str] = []
    if jumlah_titik == 3:
        catatan.append(
            "Dengan tepat 3 titik, kurva kuadratik melewati ketiga titik secara eksak (tanpa sisa "
            "derajat kebebasan), sehingga R² = 1 tidak menunjukkan kualitas kecocokan."
        )
    return KurvaKuadratik(
        layak=True,
        alasan="Syarat pendekatan terpenuhi: kurva terbuka ke bawah dan puncak berada dalam rentang data.",
        jumlah_titik=jumlah_titik,
        jumlah_kadar_air_berbeda=jumlah_berbeda,
        koefisien=(a, b, c),
        w_pusat=w_pusat,
        kadar_air_optimum_persen=omc,
        berat_isi_kering_maks_kn_m3=mdd,
        r_kuadrat=r2,
        catatan=tuple(catatan),
    )


def evaluasi_kurva(kurva: KurvaKuadratik, kadar_air_persen: Any) -> np.ndarray:
    """Hitung nilai berat isi kering pada kurva pendekatan (hanya jika kurva layak)."""
    if not kurva.layak or kurva.koefisien is None:
        raise ValidasiError("Kurva pendekatan tidak layak digunakan, sehingga tidak dapat dievaluasi.")
    a, b, c = kurva.koefisien
    x = np.asarray(kadar_air_persen, dtype=float) - kurva.w_pusat
    return a * x**2 + b * x + c


# --------------------------------------------------------------------------
# TABEL UNTUK TAMPILAN DAN CSV (memuat input penting + hasil agar bisa diaudit)
# --------------------------------------------------------------------------
def buat_tabel_kadar_air(kode: str, m_wadah: float, m_basah: float, m_kering: float,
                         hasil: HasilKadarAir) -> pd.DataFrame:
    return pd.DataFrame([{
        "Kode Sampel": kode,
        "Massa Wadah Kosong (g)": m_wadah,
        "Massa Wadah + Tanah Basah (g)": m_basah,
        "Massa Wadah + Tanah Kering (g)": m_kering,
        "Massa Air (g)": hasil.massa_air_g,
        "Massa Tanah Kering (g)": hasil.massa_tanah_kering_g,
        "Kadar Air w (%)": hasil.kadar_air_persen,
    }])


def buat_tabel_berat_isi(kode: str, massa_basah: float, volume: float, kadar_air: float,
                         hasil: HasilBeratIsi) -> pd.DataFrame:
    return pd.DataFrame([{
        "Kode Sampel": kode,
        "Massa Tanah Basah (g)": massa_basah,
        "Volume Sampel (cm³)": volume,
        "Kadar Air w (%)": kadar_air,
        "Massa Jenis Basah (g/cm³)": hasil.massa_jenis_basah_g_cm3,
        "Berat Isi Basah (kN/m³)": hasil.berat_isi_basah_kn_m3,
        "Massa Jenis Kering (g/cm³)": hasil.massa_jenis_kering_g_cm3,
        "Berat Isi Kering (kN/m³)": hasil.berat_isi_kering_kn_m3,
    }])


def buat_tabel_csv_saringan(kode: str, hasil: HasilSaringan, massa_awal_g: float | None) -> pd.DataFrame:
    tabel = hasil.tabel.copy()
    tabel.insert(0, "Kode Sampel", kode)
    tabel["Massa Total Tertahan (g)"] = hasil.massa_total_g
    tabel["Massa Sampel Awal (g)"] = np.nan if _kosong(massa_awal_g) else float(massa_awal_g)
    return tabel


def buat_tabel_csv_proctor(kode: str, volume: float, hasil: pd.DataFrame,
                           pengamatan: PengamatanProctor, kurva: KurvaKuadratik) -> pd.DataFrame:
    tabel = hasil.copy()
    tabel.insert(0, "Volume Cetakan (cm³)", volume)
    tabel.insert(0, "Kode Sampel", kode)
    tabel["γd maks pengamatan (kN/m³)"] = pengamatan.berat_isi_kering_maks_kn_m3
    tabel["w pada γd maks pengamatan (%)"] = pengamatan.kadar_air_pada_maks_persen
    tabel["Kurva kuadratik layak"] = "Ya" if kurva.layak else "Tidak"
    tabel["OMC estimasi (%)"] = kurva.kadar_air_optimum_persen if kurva.layak else np.nan
    tabel["MDD estimasi (kN/m³)"] = kurva.berat_isi_kering_maks_kn_m3 if kurva.layak else np.nan
    return tabel


def buat_csv_bytes(tabel: pd.DataFrame, format_excel_indonesia: bool = False) -> bytes:
    """Ubah DataFrame menjadi byte CSV (UTF-8 dengan BOM agar terbaca benar di Excel).

    format_excel_indonesia=False : pemisah koma, desimal titik  (format internasional)
    format_excel_indonesia=True  : pemisah titik koma, desimal koma (Excel pengaturan Indonesia)
    Pembulatan hanya dilakukan pada berkas keluaran, bukan pada perhitungan.
    """
    tabel_bulat = tabel.round(DESIMAL_CSV)
    if format_excel_indonesia:
        teks = tabel_bulat.to_csv(index=False, sep=";", decimal=",")
    else:
        teks = tabel_bulat.to_csv(index=False)
    return teks.encode("utf-8-sig")

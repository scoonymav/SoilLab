# SoilLab — Soil Mechanics Laboratory Data Processing System

SoilLab adalah aplikasi lokal berbasis Python dan Streamlit untuk membantu mahasiswa Teknik Sipil
mengolah data pengujian laboratorium mekanika tanah: kadar air, berat isi, analisis saringan, dan
pemadatan Proctor. Seluruh antarmuka berbahasa Indonesia dan aplikasi tidak memerlukan internet
setelah dependensi terpasang.

> **Penting:** SoilLab adalah alat bantu pembelajaran. Hasilnya bergantung pada ketelitian data input
> dan bukan pengganti pemeriksaan teknis oleh tenaga ahli.

## Fitur

| Menu | Fungsi |
|---|---|
| Dashboard | Ringkasan aplikasi, alur penggunaan, dan tombol menuju tiap modul |
| Uji Kadar Air | Massa air, massa tanah kering, kadar air (%) |
| Berat Isi dan Berat Isi Kering | ρ, γ, ρd, γd (g/cm³ dan kN/m³) |
| Analisis Distribusi Ukuran Butir | Tabel saringan yang dapat diedit, % tertahan, % kumulatif, % lolos, kurva semilog |
| Uji Pemadatan Proctor | Tabel percobaan yang dapat diedit, γd tiap percobaan, grafik, estimasi OMC dan MDD jika layak |
| Petunjuk dan Teori | Definisi, rumus, variabel, contoh perhitungan, batasan |

Setiap modul memiliki tombol **Isi DATA CONTOH** (data ilustrasi, bukan hasil uji nyata) dan tombol
**Unduh hasil (CSV)**. Format CSV dapat dipilih di sidebar: *Internasional* (koma, titik desimal) atau
*Excel Indonesia* (titik koma, koma desimal). Berkas CSV memakai UTF-8 dengan BOM agar terbaca benar di Excel.

## Struktur proyek

```
soillab/
├── app.py                    # antarmuka Streamlit
├── calculations.py           # semua rumus dan validasi (tanpa Streamlit)
├── requirements.txt          # dependensi
├── README.md                 # berkas ini
└── tests/
    └── test_calculations.py  # unit test (unittest)
```

## Instalasi dan menjalankan di Windows + VS Code

Semua perintah di bawah dijalankan di **PowerShell** (di VS Code: menu *Terminal → New Terminal*).

### 1. Buat folder proyek

```powershell
mkdir C:\Proyek\soillab
cd C:\Proyek\soillab
```

Salin `app.py`, `calculations.py`, `requirements.txt`, dan `README.md` ke folder ini, serta
`test_calculations.py` ke subfolder `tests`. Di VS Code, Anda dapat membuat berkas lewat
panel *Explorer* → ikon *New File* / *New Folder*.

### 2. Buka folder di VS Code

```powershell
code .
```

Jika perintah `code` tidak dikenali, buka VS Code lalu pilih *File → Open Folder* dan pilih `C:\Proyek\soillab`.

### 3. Pastikan Python terpasang

```powershell
python --version
```

Gunakan Python **3.10 atau lebih baru**. Jika perintah tidak dikenali, coba `py --version`. Jika Python belum
ada, unduh dari python.org dan **centang "Add python.exe to PATH"** saat instalasi, lalu tutup dan buka kembali terminal.

### 4. Buat virtual environment

```powershell
python -m venv .venv
```

### 5. Aktifkan virtual environment

```powershell
.\.venv\Scripts\Activate.ps1
```

Jika berhasil, awal baris terminal menampilkan `(.venv)`.

**Jika PowerShell memblokir skrip** (pesan "running scripts is disabled on this system"), ada dua pilihan:

- Izinkan skrip hanya untuk sesi terminal yang sedang terbuka (tidak mengubah pengaturan permanen):

  ```powershell
  Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
  .\.venv\Scripts\Activate.ps1
  ```

- Atau jalankan tanpa aktivasi, dengan memanggil Python di dalam `.venv` secara langsung:

  ```powershell
  .\.venv\Scripts\python.exe -m pip install -r requirements.txt
  .\.venv\Scripts\python.exe -m unittest discover -s tests -v
  .\.venv\Scripts\python.exe -m streamlit run app.py
  ```

Agar VS Code memakai environment ini: tekan `Ctrl+Shift+P`, ketik *Python: Select Interpreter*, lalu pilih
yang berada di `.venv`.

### 6. Pasang dependensi (dari direktori utama proyek)

```powershell
python -m pip install -r requirements.txt
```

### 7. Jalankan unit test (dari direktori utama proyek)

```powershell
python -m unittest discover -s tests -v
```

Hasil yang diharapkan: semua test berstatus `ok`, diakhiri `Ran 35 tests ... OK`.

### 8. Jalankan aplikasi

```powershell
python -m streamlit run app.py
```

Terminal tetap dipakai untuk menampilkan pesan aplikasi, jadi biarkan terbuka. Streamlit biasanya membuka
browser otomatis di `http://localhost:8501`. Jika tidak terbuka, salin alamat tersebut ke browser.
Jika Streamlit meminta alamat email pada pemakaian pertama, cukup tekan Enter.

### 9. Menghentikan aplikasi

Klik terminal tempat aplikasi berjalan lalu tekan `Ctrl+C`. Setelah itu tab browser boleh ditutup.

## Cara menguji hasil secara manual

Gunakan tombol **Isi DATA CONTOH** pada modul, atau isi nilai berikut:

**Modul Uji Kadar Air:** wadah kosong 20 g, wadah + tanah basah 120 g, wadah + tanah kering 100 g.
Hasil: massa air 20 g, massa tanah kering 80 g, kadar air 25%.

**Modul Berat Isi:** massa tanah basah 100 g, volume 50 cm³, kadar air 25%.
Hasil: ρ = 2,00 g/cm³, γ ≈ 19,613 kN/m³, ρd = 1,60 g/cm³, γd ≈ 15,691 kN/m³.

## Rumus dan satuan

| Parameter | Rumus | Satuan |
|---|---|---|
| Massa air | M_air = M_(wadah+basah) − M_(wadah+kering) | g |
| Massa tanah kering | M_tk = M_(wadah+kering) − M_wadah | g |
| Kadar air | w = (M_air / M_tk) × 100 | % |
| Massa jenis basah | ρ = M_basah / V | g/cm³ |
| Berat isi basah | γ = ρ × 9,80665 | kN/m³ |
| Kadar air desimal | w_desimal = w(%) / 100 | – |
| Massa jenis kering | ρd = ρ / (1 + w_desimal) | g/cm³ |
| Berat isi kering | γd = γ / (1 + w_desimal) | kN/m³ |
| % tertahan | M_i / M_total × 100 | % |
| % tertahan kumulatif | jumlah % tertahan dari saringan terbesar | % |
| % lolos | 100 − % tertahan kumulatif | % |
| Proctor | γd = (M_basah / V) / (1 + w/100) × 9,80665 | kN/m³ |
| Pendekatan kurva | γd ≈ a·w² + b·w + c; w_opt = −b / (2a) | %, kN/m³ |

Catatan satuan: 1 g/cm³ = 1000 kg/m³, sehingga ρ (g/cm³) × 9,80665 menghasilkan γ dalam kN/m³.
Kadar air dimasukkan dalam **persen** dan diubah ke **desimal** di dalam rumus oleh aplikasi.

Aturan pendekatan kurva Proctor: estimasi OMC dan MDD hanya dilaporkan jika ada minimal 3 nilai kadar air
berbeda, kurva terbuka ke bawah, dan puncaknya berada di dalam rentang kadar air data. Jika tidak,
aplikasi menjelaskan alasannya dan tidak menampilkan estimasi.

## Rujukan standar

Standar yang lazim dirujuk (periksa edisi yang berlaku dan ikuti prosedur laboratorium Anda):
SNI 1965:2008 (kadar air), SNI 3423:2008 (analisis ukuran butir), SNI 1742:2008 (kepadatan ringan),
SNI 1743:2008 (kepadatan berat); ASTM D2216, D6913, D698, dan D1557. SoilLab tidak menjamin bahwa data atau
hasil memenuhi standar tersebut.

## Pemecahan masalah umum

| Masalah | Penyebab dan solusi |
|---|---|
| `python` tidak dikenali | Python belum terpasang atau belum masuk PATH. Instal ulang dengan opsi *Add python.exe to PATH*, atau coba `py` sebagai pengganti `python`. Tutup dan buka kembali terminal. |
| `streamlit` tidak dikenali | Selalu jalankan dengan `python -m streamlit run app.py`. Pastikan dependensi sudah dipasang di environment yang aktif. |
| Aktivasi `.venv` ditolak PowerShell | Lihat langkah 5 (izin sementara untuk sesi ini, atau pakai `.\.venv\Scripts\python.exe`). |
| `ModuleNotFoundError: No module named 'calculations'` | Jalankan perintah dari direktori utama proyek (folder yang berisi `app.py`). |
| `ModuleNotFoundError` untuk streamlit/pandas/numpy/matplotlib | Aktifkan `.venv` lalu jalankan `python -m pip install -r requirements.txt`. |
| Port 8501 sudah dipakai | Jalankan `python -m streamlit run app.py --server.port 8502`. |
| CSV terbuka dalam satu kolom di Excel | Pilih *Excel Indonesia* pada sidebar SoilLab sebelum mengunduh, atau impor lewat *Data → From Text/CSV*. |
| Kurva Proctor tidak menampilkan estimasi | Syarat pendekatan belum terpenuhi (lihat pesan di aplikasi). Tambahkan percobaan pada kadar air yang melingkupi puncak. |

## Keterbatasan

- Hanya perhitungan dasar; tidak ada klasifikasi tanah (misalnya USCS), batas Atterberg, atau garis zero air voids.
- Pendekatan kuadratik pada kurva Proctor sangat sederhana dan bukan pengganti prosedur serta interpretasi
  uji sesuai standar.
- Aplikasi tidak memberi rekomendasi desain fondasi, timbunan, atau struktur.
- Data tidak disimpan ke database; simpan hasil dengan tombol unduh CSV.

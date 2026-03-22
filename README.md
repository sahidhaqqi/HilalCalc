```markdown
# 📆 Hisab Awal Bulan Hijriyah (MABIMS + Yallop + Odeh) – Multi-Lokasi Indonesia

Script Python ini menghitung **1 Ramadan** dan **1 Syawal** menggunakan kriteria **MABIMS**, serta menampilkan prediksi visibilitas hilal dengan model **Yallop (1997)** dan **Odeh (2006)**. Perhitungan astronomi menggunakan Skyfield + ephemeris NASA DE440 (fallback DE421) dan mencakup **13 titik representatif Indonesia**, sehingga hasil hisab mendekati keputusan nasional.

## ✨ Fitur Utama

- **Multi-lokasi Indonesia** (13 titik: Sabang, Medan, Padang, Jakarta, Bandung, Surabaya, Banjarmasin, Balikpapan, Makassar, Manado, Kupang, Ambon, Jayapura)  
- **Keputusan nasional** – awal bulan ditetapkan jika **minimal satu lokasi** memenuhi MABIMS  
- **MABIMS historis** (pra-2022 & Neo MABIMS 2022+ dengan elongasi geosentris)  
- **Yallop & Odeh** (dengan ARCV airless, best time = maghrib + 4/9 lag)  
- **Lebar sabit** (geometris, arcsin semi-diameter)  
- **Azimuth bulan**, **lag time (menit)** , **moonset setelah maghrib**  
- **Scan grid Indonesia** (peta potensi rukyat)  
- **Koreksi refraksi** (altitude MABIMS) dan **Delta-T**  
- **Illumination fraction**, probabilitas, kontras langit  
- **JSON generator** untuk data tahunan + frontend interaktif  

## 📋 Persyaratan

- Python 3.8+
- Pustaka: `skyfield`, `numpy`, `pytz`, `hijridate`

## 🔧 Instalasi

```bash
git clone https://github.com/sahidhaqqi/HilalCalc.git
cd HilalCalc
pip install -r requirements.txt
```

## 🚀 Cara Penggunaan

### CLI Langsung
```bash
python hitung_final.py
```
Masukkan tahun Hijriah (contoh: `1447`). Script akan mencetak hasil hisab multi-lokasi dengan detail lengkap.

### Generate JSON untuk Frontend
```bash
python generate_json.py --dari 1444 --sampai 1460
```
Hasil JSON disimpan di folder `data/`. Upload folder `data/` dan `index.html` ke web server (misal Cloudflare Pages) untuk menampilkan dashboard interaktif.

## 🌍 Titik Lokasi Representatif

| No | Kota        | Lintang | Bujur | Elevasi (m) |
|----|-------------|---------|-------|-------------|
| 1  | Sabang      |  5.8943 | 95.3184| 15 |
| 2  | Medan       |  3.5952 | 98.6722| 25 |
| 3  | Padang      | -0.9471 |100.4172| 10 |
| 4  | Jakarta     | -6.2088 |106.8456|  8 |
| 5  | Bandung     | -6.9175 |107.6191| 10 |
| 6  | Surabaya    | -7.2575 |112.7521|  5 |
| 7  | Banjarmasin | -3.3194 |114.5928| 10 |
| 8  | Balikpapan  | -1.2379 |116.8529| 10 |
| 9  | Makassar    | -5.1477 |119.4327| 10 |
| 10 | Manado      |  1.4748 |124.8421| 10 |
| 11 | Kupang      |-10.1772 |123.6070| 10 |
| 12 | Ambon       | -3.6550 |128.1908| 10 |
| 13 | Jayapura    | -2.5337 |140.7181| 10 |

## 📊 Contoh Output (CLI)

```
✅ Menggunakan ephemeris de440.bsp
Masukkan tahun Hijriah: 1447
Delta-T: 69.4 detik | Ephemeris: de440.bsp
Evaluasi MABIMS dilakukan di 13 titik representatif Indonesia.
Keputusan awal bulan diambil jika minimal SATU lokasi memenuhi kriteria MABIMS.
Toleransi elongasi: 0.05° untuk mengakomodasi perbedaan ephemeris.

Perkiraan awal bulan 1447-9: 2026-02-18
Mencari new moon antara 2026-01-29 00:00:00+00:00 dan 2026-03-10 23:59:00+00:00
Ditemukan 1 new moon
Ijtimak: 17-02-2026 19:01 WIB, tanggal lokal: 2026-02-17
  ℹ️  Ijtimak setelah maghrib → pengecekan dimulai besok

Memeriksa maghrib tanggal 2026-02-18
  [Jakarta] Maghrib: 18:14 WIB (11:14 UTC)
  [MABIMS Jakarta] Neo MABIMS (2022+): alt=8.77° (✓), elong_geo=93.95° (✓), umur=23.2 jam (✓) -> ✅ Lolos
  [VISIBILITAS Jakarta] Altitude bulan (airless): 4.23°, Matahari: -5.51°
    Elongasi (toposentrik): 11.23°, ARCV (airless): 9.74°
    Lebar sabit: 0.30 menit busur, Illumination: 0.72%
    Yallop q = -0.03 -> C — perlu alat bantu, bisa naked eye jika ditemukan
    Odeh V = 4.42 -> B — Terlihat dengan alat bantu (bisa naked eye)
    Probabilitas terlihat: 99.2%
    Kontras hilal vs langit: 0.0810 → Hilal kemungkinan terlihat

  🌏 LOKASI YANG MEMENUHI MABIMS NASIONAL (1 titik):
     - Sabang (Aceh): alt=8.68°, az=271.2°, elong=6.42°, umur=23.2 jam, lag=39 menit, maghrib=11:14 UTC, moonset=11:53 UTC

  ✅ Berdasarkan hisab multi-lokasi, awal bulan = 2026-02-19
...
=== HASIL AKHIR ===
1 Ramadan 1447 H (MABIMS Indonesia): 2026-02-19
1 Syawal  1447 H (MABIMS Indonesia): 2026-03-21
```

## 🖥️ Dashboard Web

Folder proyek sudah menyertakan `index.html` yang membaca data JSON hasil `generate_json.py`. Tampilkan dalam browser untuk melihat:
- Peta interaktif lokasi lolos MABIMS dan grid visibilitas  
- Grafik probabilitas, Yallop q, Odeh V  
- Tabel perbandingan semua tahun  
- Detail hari per hari  

## 📜 Lisensi

MIT License. Silakan digunakan, dimodifikasi, dan disebarluaskan dengan menyertakan atribusi.

---

**Dibuat dengan ❤️ oleh [Sahid](https://github.com/sahid) dan bantuan AI (Claude, ChatGPT, DeepSeek, Gemini).**  
Jika ada pertanyaan atau saran, silakan buka *issue* atau *pull request*.
```

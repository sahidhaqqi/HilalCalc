#!/usr/bin/env python3
"""
Hisab Awal Bulan Hijriyah (MABIMS + Yallop + Odeh)
Versi final dengan fitur lengkap:
- Pemisahan altitude refraksi (MABIMS) dan airless (ARCV Yallop/Odeh)
- Best time menggunakan faktor 4/9 lag time
- Koreksi konstanta Odeh (7.1651) dan threshold klasifikasi (-0.96)
- Moonset range diperluas hingga +1 hari
- Semi-diameter bulan menggunakan arcsin
- Elongasi geosentris dihitung dari pusat Bumi (bukan barycenter)
- Illumination fraction
- Probabilitas visibilitas hilal (model logistic)
- Kontras kecerahan hilal vs langit senja
- Scan visibilitas Indonesia (grid sederhana)
- Delta-T approximation (estimasi)
"""

import numpy as np
from skyfield.api import load, wgs84
from skyfield import almanac
from datetime import datetime, timedelta, timezone
import pytz
from hijridate import Hijri
import sys
import traceback

# ===================================================================
# Konfigurasi
# ===================================================================
LATITUDE = -6.2088
LONGITUDE = 106.8456
ELEVATION = 8.0  # meter
TEMPERATURE_C = 25.0
PRESSURE_MBAR = 1010.0
TZ_WIB = pytz.timezone('Asia/Jakarta')

# Ephemeris (DE440 lebih akurat, fallback DE421)
EPH_FILE = 'de440.bsp'
try:
    ts = load.timescale()
    eph = load(EPH_FILE)
    print(f"✅ Menggunakan ephemeris {EPH_FILE}")
except Exception:
    print(f"⚠️  {EPH_FILE} tidak ditemukan, fallback ke de421.bsp")
    eph = load('de421.bsp')

# ===================================================================
# Fungsi bantu timezone
# ===================================================================
def to_utc_naive(dt):
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)

# ===================================================================
# Delta-T approximation
# ===================================================================
def delta_t_approx(year):
    """
    Aproksimasi Delta-T (TT - UT) dalam detik.
    Formula sederhana cukup akurat untuk 1900–2100.
    """
    y = year + 0.5  # tengah tahun
    if 2005 <= y <= 2050:
        t = y - 2000
        dt = 62.92 + 0.32217 * t + 0.005589 * t**2
    elif 1986 <= y < 2005:
        t = y - 2000
        dt = 63.86 + 0.3345 * t - 0.060374 * t**2 + 0.0017275 * t**3
    else:
        # fallback kasar
        t = (y - 2000) / 100
        dt = 64 + 59 * t
    return dt

# ===================================================================
# Pencarian waktu matahari terbenam & bulan terbenam
# ===================================================================
def cari_waktu_maghrib(tanggal, ts, eph, topos):
    t0 = ts.utc(tanggal.year, tanggal.month, tanggal.day, 0)
    t1 = ts.utc(tanggal.year, tanggal.month, tanggal.day, 23, 59)
    f = almanac.sunrise_sunset(eph, topos)
    times, events = almanac.find_discrete(t0, t1, f)
    sunset_times = [t for t, e in zip(times, events) if not e]
    return sunset_times[0].utc_datetime() if sunset_times else None

def cari_waktu_moonset(tanggal, ts, eph, topos):
    """
    Mencari waktu terbenam bulan pada tanggal lokal tertentu.
    Pencarian diperluas hingga 36 jam (hari ini +1 hari) untuk menangkap moonset
    yang terjadi setelah tengah malam.
    """
    t0 = ts.utc(tanggal.year, tanggal.month, tanggal.day, 0)
    t1 = ts.utc(tanggal.year, tanggal.month, tanggal.day, 36)  # +1 hari
    f = almanac.risings_and_settings(eph, eph['moon'], topos)
    times, events = almanac.find_discrete(t0, t1, f)
    moonset_times = [t for t, e in zip(times, events) if not e]
    if moonset_times:
        return moonset_times[0].utc_datetime()
    return None

# ===================================================================
# Pencarian best time (optimal visibility)
# ===================================================================
def cari_best_time(maghrib_utc, moonset_utc):
    """
    Best time untuk observasi hilal diambil pada 4/9 × lag time setelah maghrib.
    Lag time = selisih waktu terbenam bulan dan matahari.
    """
    if moonset_utc is None:
        return None
    lag = (moonset_utc - maghrib_utc).total_seconds() / 3600  # dalam jam
    if lag <= 0:
        return None
    offset_hours = lag * (4 / 9)
    best = maghrib_utc + timedelta(hours=offset_hours)
    return best

# ===================================================================
# Fungsi perhitungan posisi (toposentrik) dan elongasi geosentris
# ===================================================================
def hitung_bulan_pada_waktu(waktu_utc, ts, eph, lokasi_geo):
    """
    Mengembalikan:
        alt_bulan_ref, alt_matahari_ref,     # dengan refraksi (MABIMS)
        alt_bulan_airless, alt_matahari_airless,  # tanpa refraksi (ARCV)
        elong_toposentrik_deg, jarak_bulan_km,
        elong_geosentris_deg
    """
    detik = waktu_utc.second + waktu_utc.microsecond / 1e6
    t = ts.utc(waktu_utc.year, waktu_utc.month, waktu_utc.day,
               waktu_utc.hour, waktu_utc.minute, detik)

    # Toposentrik
    posisi = lokasi_geo.at(t)
    bulan_top = posisi.observe(eph['moon']).apparent()
    matahari_top = posisi.observe(eph['sun']).apparent()

    # Dengan refraksi (untuk MABIMS)
    alt_bulan_ref, _, _ = bulan_top.altaz(temperature_C=TEMPERATURE_C, pressure_mbar=PRESSURE_MBAR)
    alt_matahari_ref, _, _ = matahari_top.altaz(temperature_C=TEMPERATURE_C, pressure_mbar=PRESSURE_MBAR)

    # Tanpa refraksi (airless) untuk ARCV Yallop & Odeh
    alt_bulan_airless, _, _ = bulan_top.altaz()
    alt_matahari_airless, _, _ = matahari_top.altaz()

    elong_top = bulan_top.separation_from(matahari_top).degrees

    # Geosentris (untuk MABIMS) – dihitung dari pusat Bumi
    earth = eph['earth']
    bulan_geo = earth.at(t).observe(eph['moon']).apparent()
    matahari_geo = earth.at(t).observe(eph['sun']).apparent()
    elong_geo = bulan_geo.separation_from(matahari_geo).degrees

    jarak_bulan = bulan_top.distance().km

    return (alt_bulan_ref.degrees, alt_matahari_ref.degrees,
            alt_bulan_airless.degrees, alt_matahari_airless.degrees,
            elong_top, jarak_bulan, elong_geo)

# ===================================================================
# Illumination fraction bulan
# ===================================================================
def hitung_illumination_fraction(waktu_utc, ts, eph):
    """
    Menghitung illumination fraction (persentase cahaya bulan).
    Rumus: k = (1 + cos(phase_angle)) / 2
    phase_angle = sudut Sun-Moon-Earth
    """
    detik = waktu_utc.second + waktu_utc.microsecond / 1e6
    t = ts.utc(waktu_utc.year, waktu_utc.month, waktu_utc.day,
               waktu_utc.hour, waktu_utc.minute, detik)

    earth = eph['earth']
    # posisi dari pusat bumi
    moon = earth.at(t).observe(eph['moon']).apparent()
    sun = earth.at(t).observe(eph['sun']).apparent()
    # sudut fase
    phase_angle = moon.separation_from(sun).radians
    k = (1 + np.cos(phase_angle)) / 2
    return k * 100  # persen

# ===================================================================
# Probabilitas terlihat hilal (model logistic)
# ===================================================================
def probabilitas_hilal(v):
    """
    Mengubah parameter Odeh V menjadi probabilitas terlihat (%).
    Model logistic sederhana.
    """
    k = 2.0
    p = 1 / (1 + np.exp(-k * v))
    return p * 100

# ===================================================================
# Model kontras kecerahan hilal vs langit senja
# ===================================================================
def hitung_kontras_hilal(arcv_deg, elong_deg, width_menit):
    """
    Estimasi kontras kecerahan sabit terhadap langit twilight.
    Model empiris sederhana untuk analisis visibilitas.
    """
    # brightness sabit (aproksimasi)
    B_moon = width_menit * (elong_deg / 10)
    # brightness langit senja (dipengaruhi ARCV)
    # semakin besar ARCV → langit makin gelap
    B_sky = np.exp(-0.25 * arcv_deg)
    if B_sky <= 0:
        return 0
    contrast = B_moon / (B_sky * 100)
    return contrast

# ===================================================================
# Scan visibilitas Indonesia (grid sederhana)
# ===================================================================
def scan_visibilitas_indonesia(tanggal, maghrib_utc, ts, eph):
    """
    Membuat peta kasar visibilitas hilal Indonesia.
    Grid sederhana tiap ~4-6 derajat.
    """
    print("\n=== SCAN VISIBILITAS INDONESIA (grid kasar) ===")

    earth = eph['earth']
    # grid kasar Indonesia
    latitudes = np.arange(-10, 7, 4)     # dari selatan ke utara
    longitudes = np.arange(95, 141, 6)   # dari barat ke timur

    visible_points = []

    for lat in latitudes:
        for lon in longitudes:
            topos = wgs84.latlon(lat, lon)
            lokasi = earth + topos

            (_, _, alt_bulan_air,
             alt_matahari_air,
             elong_top,
             jarak_bulan,
             _) = hitung_bulan_pada_waktu(maghrib_utc, ts, eph, lokasi)

            arcv = alt_bulan_air - alt_matahari_air
            sd_rad = np.arcsin(1737.4 / jarak_bulan)
            width = sd_rad * (1 - np.cos(np.radians(elong_top)))
            width = width * (180 / np.pi) * 60
            a = 11.8371 - 6.3226 * width + 0.7319 * width**2 - 0.1018 * width**3
            q = (arcv - a) / 10

            if q > -0.232:  # minimal kelas D Yallop
                visible_points.append((lat, lon))

    if visible_points:
        print(f"Wilayah potensial rukyat: {len(visible_points)} titik grid")
        for lat, lon in visible_points[:15]:
            print(f"  lat={lat:.1f}, lon={lon:.1f}")
    else:
        print("Tidak ada wilayah Indonesia dengan kemungkinan rukyat")

# ===================================================================
# Pencarian new moon
# ===================================================================
def cari_new_moon_terdekat(tanggal_acuan, ts, eph, rentang_hari=20):
    t_start = tanggal_acuan - timedelta(days=rentang_hari)
    t_end = tanggal_acuan + timedelta(days=rentang_hari)
    t0 = ts.utc(t_start.year, t_start.month, t_start.day, 0)
    t1 = ts.utc(t_end.year, t_end.month, t_end.day, 23, 59)
    print(f"Mencari new moon antara {t0.utc_datetime()} dan {t1.utc_datetime()}")

    f = almanac.moon_phases(eph)
    times, phases = almanac.find_discrete(t0, t1, f)
    new_moon_times = [t for t, p in zip(times, phases) if p == 0]
    print(f"Ditemukan {len(new_moon_times)} new moon")

    if not new_moon_times:
        return None, None

    new_moon_utc = [t.utc_datetime() for t in new_moon_times]
    acuan_wib = TZ_WIB.localize(datetime.combine(tanggal_acuan, datetime.min.time()))
    acuan_utc = acuan_wib.astimezone(timezone.utc)
    terdekat_utc = min(new_moon_utc, key=lambda d: abs((d - acuan_utc).total_seconds()))
    terdekat_wib = terdekat_utc.astimezone(TZ_WIB)
    tanggal_lokal_newmoon = terdekat_wib.date()
    return terdekat_utc, tanggal_lokal_newmoon

# ===================================================================
# Klasifikasi Yallop & Odeh
# ===================================================================
def yallop_class(q):
    if q > 0.216:
        return "A — mudah terlihat mata telanjang"
    elif q > -0.014:
        return "B — terlihat kondisi sempurna"
    elif q > -0.160:
        return "C — perlu alat bantu, bisa naked eye jika ditemukan"
    elif q > -0.232:
        return "D — perlu alat bantu optik"
    else:
        return "E — tidak terlihat walau dengan teleskop"

def odeh_class(v):
    if v >= 5.65:
        return "A — Mudah terlihat (mata telanjang)"
    elif v >= 2.0:
        return "B — Terlihat dengan alat bantu (bisa naked eye)"
    elif v >= -0.96:
        return "C — Hanya terlihat dengan alat bantu optik/teleskop"
    else:
        return "D — Tidak terlihat"

# ===================================================================
# Kriteria MABIMS historis
# ===================================================================
def cek_mabims_historis(tanggal, alt_bulan, elong_geosentris, umur_jam, EPS=1e-6):
    if tanggal.year >= 2022:
        alt_ok = (alt_bulan + EPS) >= 3.0
        elong_ok = (elong_geosentris + EPS) >= 6.4
        terpenuhi = alt_ok and elong_ok
        label = "Neo MABIMS (2022+)"
        umur_ok = True
    else:
        alt_ok = (alt_bulan + EPS) >= 2.0
        elong_ok = (elong_geosentris + EPS) >= 3.0
        umur_ok = (umur_jam + EPS) >= 8.0
        terpenuhi = (alt_ok and elong_ok) or (umur_ok and alt_ok)
        label = "MABIMS Lama (pre-2022)"
    return terpenuhi, alt_ok, elong_ok, umur_ok, label

# ===================================================================
# Fungsi utama hitung awal bulan
# ===================================================================
def hitung_awal_bulan_hijriah(tahun_hijriah, bulan_hijriah, ts, eph, topos, lokasi_geo):
    hijri_date = Hijri(tahun_hijriah, bulan_hijriah, 1)
    gregorian = hijri_date.to_gregorian()
    perkiraan = datetime(gregorian.year, gregorian.month, gregorian.day).date()
    print(f"Perkiraan awal bulan {tahun_hijriah}-{bulan_hijriah}: {perkiraan}")

    nm_utc, tgl_lokal_newmoon = cari_new_moon_terdekat(perkiraan, ts, eph)
    if nm_utc is None:
        raise RuntimeError(f"Tidak ditemukan new moon untuk {tahun_hijriah}-{bulan_hijriah}")
    nm_wib = nm_utc.astimezone(TZ_WIB)
    print(f"Ijtimak: {nm_wib.strftime('%d-%m-%Y %H:%M WIB')}, tanggal lokal: {tgl_lokal_newmoon}")

    # Tentukan start_i
    maghrib_nm = cari_waktu_maghrib(tgl_lokal_newmoon, ts, eph, topos)
    nm_naive = to_utc_naive(nm_utc)
    if maghrib_nm is not None and nm_naive < to_utc_naive(maghrib_nm):
        start_i = 0
        print("  ℹ️  Ijtimak sebelum maghrib → pengecekan dimulai hari yang sama")
    else:
        start_i = 1
        print("  ℹ️  Ijtimak setelah maghrib → pengecekan dimulai besok")

    EPS = 1e-6
    for i in range(start_i, start_i + 3):
        tanggal_periksa = tgl_lokal_newmoon + timedelta(days=i)
        print(f"\nMemeriksa maghrib tanggal {tanggal_periksa}")

        # Waktu maghrib
        maghrib_utc = cari_waktu_maghrib(tanggal_periksa, ts, eph, topos)
        if maghrib_utc is None:
            print("  Tidak ada maghrib?")
            continue
        maghrib_wib = maghrib_utc.astimezone(TZ_WIB)
        print(f"  Maghrib: {maghrib_wib.strftime('%H:%M WIB')} ({maghrib_utc.strftime('%H:%M UTC')})")

        # Moonset pada hari yang sama (rentang hingga +1 hari)
        moonset_utc = cari_waktu_moonset(tanggal_periksa, ts, eph, topos)
        if moonset_utc is None:
            print("  Tidak ada moonset? (bulan tidak terbenam?)")
            continue
        moonset_wib = moonset_utc.astimezone(TZ_WIB)
        print(f"  Moonset: {moonset_wib.strftime('%H:%M WIB')} ({moonset_utc.strftime('%H:%M UTC')})")

        # Best time (optimal visibility)
        best_utc = cari_best_time(maghrib_utc, moonset_utc)
        if best_utc is None:
            print("  Best time tidak ditemukan (lag time negatif/lemah)")
            continue
        best_wib = best_utc.astimezone(TZ_WIB)
        print(f"  Best time: {best_wib.strftime('%H:%M WIB')}")

        # --- Hitung parameter pada waktu maghrib (untuk MABIMS) ---
        (alt_bulan_ref_m, alt_matahari_ref_m,
         alt_bulan_air_m, alt_matahari_air_m,
         elong_top_m, _, elong_geo_m) = hitung_bulan_pada_waktu(maghrib_utc, ts, eph, lokasi_geo)

        # Umur bulan
        maghrib_naive = to_utc_naive(maghrib_utc)
        nm_naive = to_utc_naive(nm_utc)
        umur_jam = (maghrib_naive - nm_naive).total_seconds() / 3600
        if umur_jam < 0:
            print("  ❌ Umur bulan negatif (ijtimak setelah maghrib) — tidak memenuhi syarat")
            continue

        # Evaluasi MABIMS
        mabims_ok, alt_ok, elong_ok, umur_ok, label_mabims = cek_mabims_historis(
            tanggal_periksa, alt_bulan_ref_m, elong_geo_m, umur_jam, EPS
        )
        print(f"  [MABIMS] {label_mabims}: alt={alt_bulan_ref_m:.2f}° ({'✓' if alt_ok else '✗'}), "
              f"elong_geo={elong_geo_m:.2f}° ({'✓' if elong_ok else '✗'}), "
              f"umur={umur_jam:.1f} jam ({'✓' if umur_ok else '✗'}) -> {'✅ Lolos' if mabims_ok else '❌ Gagal'}")

        if not mabims_ok and tanggal_periksa.year >= 2022 and not elong_ok and (6.4 - elong_geo_m) < 1.0:
            print(f"      ⚠️  Elongasi borderline ({elong_geo_m:.2f}°, kurang {6.4-elong_geo_m:.2f}° dari threshold)")
            print(f"          → Rukyat mungkin berhasil, keputusan final di Sidang Isbat")

        # --- Hitung parameter pada best time (untuk Yallop & Odeh) ---
        (_, _, alt_bulan_air_b, alt_matahari_air_b,
         elong_top_b, jarak_bulan, _) = hitung_bulan_pada_waktu(best_utc, ts, eph, lokasi_geo)

        # ARCV menggunakan altitude airless
        arcv_deg = alt_bulan_air_b - alt_matahari_air_b

        # Semi-diameter bulan dalam radian (koreksi: arcsin)
        sd_rad = np.arcsin(1737.4 / jarak_bulan)  # radius bulan (km) / jarak (km)
        width_rad = sd_rad * (1 - np.cos(np.radians(elong_top_b)))
        width_rad = max(0.0, width_rad)
        width_menit = width_rad * (180 / np.pi) * 60

        # Illumination fraction
        illum = hitung_illumination_fraction(best_utc, ts, eph)

        print(f"  [VISIBILITAS] Altitude bulan (airless): {alt_bulan_air_b:.2f}°, Matahari: {alt_matahari_air_b:.2f}°")
        print(f"    Elongasi (toposentrik): {elong_top_b:.2f}°, ARCV (airless): {arcv_deg:.2f}°")
        print(f"    Lebar sabit (geometris): {width_menit:.2f} menit busur")
        print(f"    Illumination fraction: {illum:.2f}%")

        # Yallop
        W = width_menit
        a = 11.8371 - 6.3226 * W + 0.7319 * W**2 - 0.1018 * W**3
        q_yallop = (arcv_deg - a) / 10
        yallop_klas = yallop_class(q_yallop)
        print(f"    Yallop q = {q_yallop:.2f} -> {yallop_klas}")

        # Odeh
        f_odeh = -0.1018 * W**3 + 0.7319 * W**2 - 6.3226 * W + 7.1651
        v_odeh = arcv_deg - f_odeh
        odeh_klas = odeh_class(v_odeh)
        print(f"    Odeh V = {v_odeh:.2f} -> {odeh_klas}")

        # Probabilitas terlihat
        prob = probabilitas_hilal(v_odeh)
        print(f"    Probabilitas terlihat: {prob:.1f}%")

        # Kontras hilal vs langit
        contrast = hitung_kontras_hilal(arcv_deg, elong_top_b, width_menit)
        print(f"    Kontras hilal vs langit: {contrast:.4f}")
        if contrast > 0.15:
            print("      → Hilal sangat mudah terlihat")
        elif contrast > 0.05:
            print("      → Hilal kemungkinan terlihat")
        elif contrast > 0.01:
            print("      → Hilal sangat sulit terlihat")
        else:
            print("      → Hilal hampir mustahil terlihat")

        # Jika MABIMS lolos, awal bulan = besok
        if mabims_ok:
            # Panggil scan visibilitas Indonesia
            scan_visibilitas_indonesia(tanggal_periksa, maghrib_utc, ts, eph)

            tanggal_1 = tanggal_periksa + timedelta(days=1)
            print(f"  ✅ Awal bulan = {tanggal_1} (sesuai MABIMS)")
            return tanggal_1

    # Istikmal
    tanggal_istikmal = tgl_lokal_newmoon + timedelta(days=start_i + 3)
    print(f"\n⚠️  MABIMS tidak terpenuhi dalam 3 hari berturut-turut → Istikmal")
    print(f"   Awal bulan (istikmal) = {tanggal_istikmal}")
    return tanggal_istikmal

# ===================================================================
# Main
# ===================================================================
def main():
    try:
        tahun = int(input("Masukkan tahun Hijriah (contoh: 1445): "))
    except ValueError:
        print("Tahun harus berupa angka.")
        return

    # Tampilkan Delta-T
    tahun_masehi = Hijri(tahun, 1, 1).to_gregorian().year
    dt = delta_t_approx(tahun_masehi)
    print(f"Delta-T (perkiraan): {dt:.1f} detik")

    earth = eph['earth']
    topos = wgs84.latlon(LATITUDE, LONGITUDE, elevation_m=ELEVATION)
    lokasi_geo = earth + topos
    print(f"Lokasi: {LATITUDE}°S, {LONGITUDE}°E, elevasi {ELEVATION} m")
    print(f"Atmosfer: T={TEMPERATURE_C}°C, P={PRESSURE_MBAR} mbar")

    try:
        ramadan = hitung_awal_bulan_hijriah(tahun, 9, ts, eph, topos, lokasi_geo)
        syawal = hitung_awal_bulan_hijriah(tahun, 10, ts, eph, topos, lokasi_geo)
        print(f"\n=== HASIL AKHIR ===")
        print(f"1 Ramadan {tahun} H (MABIMS Jakarta): {ramadan}")
        print(f"1 Syawal  {tahun} H (MABIMS Jakarta): {syawal}")
    except Exception as e:
        print(f"Terjadi kesalahan: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()

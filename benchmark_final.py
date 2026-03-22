#!/usr/bin/env python3
"""
Benchmark hisab hilal vs data real Pemerintah/NU & Muhammadiyah.
Menguji akurasi MABIMS (hitung_final.py) dan Wujudul Hilal (hitung_muhammadiyah.py).
"""

import sys
from datetime import date

# ===================================================================
# LOAD BACKEND
# ===================================================================
print("Memuat backend MABIMS...")
from hitung_final import (
    hitung_awal_bulan_hijriah as hitung_mabims,
    ts, eph, wgs84, LATITUDE, LONGITUDE, ELEVATION
)

print("Memuat backend Muhammadiyah...")
import importlib.util, io, contextlib
spec = importlib.util.spec_from_file_location("hitung_muhammadiyah", "hitung_muhammadiyah.py")
mod  = importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()):
    spec.loader.exec_module(mod)
hitung_muham = mod.hitung_awal_bulan_hijriah
print("Siap.\n")

earth     = eph['earth']
topos     = wgs84.latlon(LATITUDE, LONGITUDE, elevation_m=ELEVATION)
lokasi_geo= earth + topos

earth_u    = mod.eph['earth']
topos_u    = mod.wgs84.latlon(mod.LATITUDE, mod.LONGITUDE, elevation_m=mod.ELEVATION)
lokasi_u   = earth_u + topos_u

# ===================================================================
# DATA REAL (dari CSV + sumber resmi)
# Kolom: tahun_hijriah, ramadan_pemerintah, ramadan_muhammadiyah,
#         syawal_pemerintah, syawal_muhammadiyah
# ===================================================================
DATA = [
    # (H,   1-Ramadan-Pem,         1-Ramadan-Muh,         1-Syawal-Pem,          1-Syawal-Muh)
    (1420,  date(1999,12, 9),      date(1999,12, 9),      date(2000, 1, 8),       date(2000, 1, 8)),
    (1421,  date(2000,11,27),      date(2000,11,27),      date(2000,12,27),       date(2000,12,27)),
    (1422,  date(2001,11,17),      date(2001,11,16),      date(2001,12,16),       date(2001,12,16)),
    (1423,  date(2002,11, 6),      date(2002,11, 6),      date(2002,12, 6),       date(2002,12, 5)),
    (1424,  date(2003,10,27),      date(2003,10,27),      date(2003,11,25),       date(2003,11,25)),
    (1425,  date(2004,10,15),      date(2004,10,15),      date(2004,11,14),       date(2004,11,14)),
    (1426,  date(2005,10, 5),      date(2005,10, 5),      date(2005,11, 3),       date(2005,11, 3)),
    (1427,  date(2006, 9,24),      date(2006, 9,24),      date(2006,10,24),       date(2006,10,23)),
    (1428,  date(2007, 9,13),      date(2007, 9,13),      date(2007,10,13),       date(2007,10,12)),
    (1429,  date(2008, 9, 1),      date(2008, 9, 1),      date(2008,10, 1),       date(2008,10, 1)),
    (1430,  date(2009, 8,22),      date(2009, 8,22),      date(2009, 9,20),       date(2009, 9,20)),
    (1431,  date(2010, 8,11),      date(2010, 8,11),      date(2010, 9,10),       date(2010, 9,10)),
    (1432,  date(2011, 8, 1),      date(2011, 8, 1),      date(2011, 8,31),       date(2011, 8,30)),
    (1433,  date(2012, 7,21),      date(2012, 7,20),      date(2012, 8,19),       date(2012, 8,19)),
    (1434,  date(2013, 7,10),      date(2013, 7, 9),      date(2013, 8, 8),       date(2013, 8, 8)),
    (1435,  date(2014, 6,29),      date(2014, 6,28),      date(2014, 7,28),       date(2014, 7,28)),
    (1436,  date(2015, 6,18),      date(2015, 6,18),      date(2015, 7,17),       date(2015, 7,17)),
    (1437,  date(2016, 6, 6),      date(2016, 6, 6),      date(2016, 7, 6),       date(2016, 7, 6)),
    (1438,  date(2017, 5,27),      date(2017, 5,27),      date(2017, 6,25),       date(2017, 6,25)),
    (1439,  date(2018, 5,17),      date(2018, 5,17),      date(2018, 6,15),       date(2018, 6,15)),
    (1440,  date(2019, 5, 6),      date(2019, 5, 6),      date(2019, 6, 5),       date(2019, 6, 5)),
    (1441,  date(2020, 4,24),      date(2020, 4,24),      date(2020, 5,24),       date(2020, 5,24)),
    (1442,  date(2021, 4,13),      date(2021, 4,13),      date(2021, 5,13),       date(2021, 5,13)),
    (1443,  date(2022, 4, 3),      date(2022, 4, 2),      date(2022, 5, 2),       date(2022, 5, 2)),
    (1444,  date(2023, 3,23),      date(2023, 3,23),      date(2023, 4,22),       date(2023, 4,21)),
    (1445,  date(2024, 3,12),      date(2024, 3,11),      date(2024, 4,10),       date(2024, 4,10)),
    (1446,  date(2025, 3, 1),      date(2025, 3, 1),      date(2025, 3,31),       date(2025, 3,31)),
    (1447,  date(2026, 2,19),      date(2026, 2,19),      date(2026, 3,21),       date(2026, 3,20)),
]

# ===================================================================
# HELPER
# ===================================================================
def run_silent(fn, *args):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        result = fn(*args)
    return result

def fmt(d):
    if d is None: return "—"
    return d.strftime("%d-%m-%Y")

def selisih(a, b):
    if a is None or b is None: return None
    return (a - b).days

def status(hitung, real):
    if real is None: return "—"
    if hitung is None: return "ERROR"
    d = (hitung - real).days
    if d == 0:  return "✅ MATCH"
    if abs(d) == 1: return f"⚠️  {'H+1' if d>0 else 'H-1'}"
    return f"❌ MISS ({d:+d})"

# ===================================================================
# BENCHMARK
# ===================================================================
print("=" * 72)
print(f"{'H':>5}  {'MABIMS-R':>12}  {'Pem-R':>12}  {'st':^8}  {'MABIMS-S':>12}  {'Pem-S':>12}  {'st':^8}")
print("-" * 72)

results = []

for row in DATA:
    hijri = row[0]
    real_r_pem, real_r_muh, real_s_pem, real_s_muh = row[1], row[2], row[3], row[4]

    try:
        hasil_r_mabims = run_silent(hitung_mabims, hijri, 9,  ts, eph, topos, lokasi_geo)
        if isinstance(hasil_r_mabims, dict):
            hasil_r_mabims = date.fromisoformat(hasil_r_mabims['tanggal_awal'])
    except Exception as ex:
        hasil_r_mabims = None
        print(f"  [ERROR MABIMS Ramadan {hijri}]: {ex}")

    try:
        hasil_s_mabims = run_silent(hitung_mabims, hijri, 10, ts, eph, topos, lokasi_geo)
        if isinstance(hasil_s_mabims, dict):
            hasil_s_mabims = date.fromisoformat(hasil_s_mabims['tanggal_awal'])
    except Exception as ex:
        hasil_s_mabims = None
        print(f"  [ERROR MABIMS Syawal {hijri}]: {ex}")

    try:
        r_muham = run_silent(hitung_muham, hijri, 9,  mod.ts, mod.eph, topos_u, lokasi_u)
        hasil_r_muham = date.fromisoformat(r_muham['tanggal_awal'])
    except Exception as ex:
        hasil_r_muham = None
        print(f"  [ERROR Muham Ramadan {hijri}]: {ex}")

    try:
        s_muham = run_silent(hitung_muham, hijri, 10, mod.ts, mod.eph, topos_u, lokasi_u)
        hasil_s_muham = date.fromisoformat(s_muham['tanggal_awal'])
    except Exception as ex:
        hasil_s_muham = None
        print(f"  [ERROR Muham Syawal {hijri}]: {ex}")

    sr = status(hasil_r_mabims, real_r_pem)
    ss = status(hasil_s_mabims, real_s_pem)
    smr= status(hasil_r_muham,  real_r_muh)
    sms= status(hasil_s_muham,  real_s_muh)

    print(f"{hijri:>5}  {fmt(hasil_r_mabims):>12}  {fmt(real_r_pem):>12}  {sr:^10}  "
          f"{fmt(hasil_s_mabims):>12}  {fmt(real_s_pem):>12}  {ss:^10}")

    results.append({
        'hijri': hijri,
        'hasil_r_mabims': hasil_r_mabims, 'real_r_pem': real_r_pem,
        'hasil_s_mabims': hasil_s_mabims, 'real_s_pem': real_s_pem,
        'hasil_r_muham':  hasil_r_muham,  'real_r_muh': real_r_muh,
        'hasil_s_muham':  hasil_s_muham,  'real_s_muh': real_s_muh,
    })

# ===================================================================
# RINGKASAN AKURASI
# ===================================================================
def hitung_akurasi(results, key_hasil, key_real, label):
    total = sum(1 for r in results if r[key_real] is not None)
    match = sum(1 for r in results if r[key_real] is not None and r[key_hasil] == r[key_real])
    plus1 = sum(1 for r in results if r[key_real] is not None and r[key_hasil] is not None
                and selisih(r[key_hasil], r[key_real]) == 1)
    min1  = sum(1 for r in results if r[key_real] is not None and r[key_hasil] is not None
                and selisih(r[key_hasil], r[key_real]) == -1)
    miss  = total - match
    akurasi = match / total * 100 if total else 0
    print(f"\n  {label}")
    print(f"    Total   : {total}")
    print(f"    Match   : {match}  ({akurasi:.1f}%)")
    print(f"    H+1     : {plus1}  (hitung lebih lambat 1 hari)")
    print(f"    H-1     : {min1}  (hitung lebih cepat 1 hari)")
    print(f"    Miss>1  : {miss - plus1 - min1}")

    misses = [(r['hijri'], r[key_hasil], r[key_real],
               selisih(r[key_hasil], r[key_real]))
              for r in results if r[key_real] is not None and r[key_hasil] != r[key_real]]
    if misses:
        print(f"    Detail miss:")
        for h, hasil, real, d in misses:
            print(f"      {h} H: hitung={fmt(hasil)}, real={fmt(real)}, selisih={d:+d}")
    return akurasi

print("\n" + "=" * 72)
print("RINGKASAN AKURASI")
print("=" * 72)

ak_mr = hitung_akurasi(results, 'hasil_r_mabims', 'real_r_pem', 'MABIMS vs Pemerintah — Ramadan')
ak_ms = hitung_akurasi(results, 'hasil_s_mabims', 'real_s_pem', 'MABIMS vs Pemerintah — Syawal')
ak_ur = hitung_akurasi(results, 'hasil_r_muham',  'real_r_muh', 'Muhammadiyah vs Real — Ramadan')
ak_us = hitung_akurasi(results, 'hasil_s_muham',  'real_s_muh', 'Muhammadiyah vs Real — Syawal')

print(f"\n{'─'*40}")
print(f"  MABIMS overall  : {(ak_mr+ak_ms)/2:.1f}%")
print(f"  Muhammadiyah    : {(ak_ur+ak_us)/2:.1f}%")
print(f"{'─'*40}")

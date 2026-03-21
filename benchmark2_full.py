from datetime import date
from hitung_final import (
    hitung_awal_bulan_hijriah,
    ts, eph,                # ← ganti get_ephemeris dengan ts, eph
    wgs84,
    LATITUDE,
    LONGITUDE,
    ELEVATION
)

# -------------------------------------------------------------------
# DATA REAL (Pemerintah Indonesia / NU)
# -------------------------------------------------------------------
REAL_SYAWAL = {
    # 1990 - 2000
    1990: date(1990, 4, 26),
    1991: date(1991, 4, 16),
    1992: date(1992, 4, 5),
    1993: date(1993, 3, 25),
    1994: date(1994, 3, 14),
    1995: date(1995, 3, 3),
    1996: date(1996, 2, 20),
    1997: date(1997, 2, 9),
    1998: date(1998, 1, 30),
    1999: date(1999, 1, 19),
    2000: date(2000, 1, 8),

    # 2001 - 2026
    2001: date(2001, 12, 16),
    2002: date(2002, 12, 6),
    2003: date(2003, 11, 25),
    2004: date(2004, 11, 14),
    2005: date(2005, 11, 3),
    2006: date(2006, 10, 24),
    2007: date(2007, 10, 13),
    2008: date(2008, 10, 1),
    2009: date(2009, 9, 20),
    2010: date(2010, 9, 10),
    2011: date(2011, 8, 31),
    2012: date(2012, 8, 19),
    2013: date(2013, 8, 8),
    2014: date(2014, 7, 28),
    2015: date(2015, 7, 17),
    2016: date(2016, 7, 6),
    2017: date(2017, 6, 25),
    2018: date(2018, 6, 15),
    2019: date(2019, 6, 5),
    2020: date(2020, 5, 24),
    2021: date(2021, 5, 13),
    2022: date(2022, 5, 2),
    2023: date(2023, 4, 22),
    2024: date(2024, 4, 10),
    2025: date(2025, 3, 31),
    2026: date(2026, 3, 21),
}

# -------------------------------------------------------------------
# MAPPING TAHUN MASEHI -> HIJRIAH (WAJIB BIAR GAK SHIFT)
# -------------------------------------------------------------------
TAHUN_MAP = {
    1990: 1410,
    1991: 1411,
    1992: 1412,
    1993: 1413,
    1994: 1414,
    1995: 1415,
    1996: 1416,
    1997: 1417,
    1998: 1418,
    1999: 1419,
    2000: 1420,
    2001: 1422,
    2002: 1423,
    2003: 1424,
    2004: 1425,
    2005: 1426,
    2006: 1427,
    2007: 1428,
    2008: 1429,
    2009: 1430,
    2010: 1431,
    2011: 1432,
    2012: 1433,
    2013: 1434,
    2014: 1435,
    2015: 1436,
    2016: 1437,
    2017: 1438,
    2018: 1439,
    2019: 1440,
    2020: 1441,
    2021: 1442,
    2022: 1443,
    2023: 1444,
    2024: 1445,
    2025: 1446,
    2026: 1447,
}

# -------------------------------------------------------------------
# INIT
# -------------------------------------------------------------------
# Tidak perlu get_ephemeris lagi, langsung pakai ts dan eph yang diimpor
earth = eph['earth']
topos = wgs84.latlon(LATITUDE, LONGITUDE, elevation_m=ELEVATION)
lokasi_geo = earth + topos

# -------------------------------------------------------------------
# BENCHMARK
# -------------------------------------------------------------------
total = 0
match = 0
miss_detail = []

for tahun_masehi, real_syawal in REAL_SYAWAL.items():
    tahun_hijriah = TAHUN_MAP[tahun_masehi]

    print(f"\n=== {tahun_masehi} (H: {tahun_hijriah}) ===")

    hasil_syawal = hitung_awal_bulan_hijriah(
        tahun_hijriah, 10, ts, eph, topos, lokasi_geo
    )

    total += 1

    if hasil_syawal == real_syawal:
        print(f"✅ MATCH ({hasil_syawal})")
        match += 1
    else:
        print(f"❌ MISS (hasil={hasil_syawal}, real={real_syawal})")
        selisih = (hasil_syawal - real_syawal).days
        miss_detail.append((tahun_masehi, hasil_syawal, real_syawal, selisih))

# -------------------------------------------------------------------
# HASIL
# -------------------------------------------------------------------
akurasi = (match / total) * 100

print("\n=== HASIL AKHIR ===")
print(f"Total data : {total}")
print(f"Match      : {match}")
print(f"Miss       : {total - match}")
print(f"Akurasi    : {akurasi:.2f}%")

if miss_detail:
    print("\n=== DETAIL MISS ===")
    for t, h, r, d in miss_detail:
        print(f"{t}: hasil={h}, real={r}, selisih={d} hari")

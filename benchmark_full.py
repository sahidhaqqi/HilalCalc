from datetime import date
from hitung_final import hitung_awal_bulan_hijriah, get_ephemeris, wgs84, LATITUDE, LONGITUDE, ELEVATION

# -------------------------------------------------------------------
# DATA REAL (NU / Pemerintah Indonesia)
# Format: tahun masehi -> tanggal idul fitri
# -------------------------------------------------------------------
REAL_SYAWAL = {
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
# INIT
# -------------------------------------------------------------------
ts, eph = get_ephemeris()
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
    tahun_hijriah = tahun_masehi - 579  # pendekatan kasar (cukup untuk loop)

    print(f"\n=== {tahun_masehi} ===")

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

# Detail miss
if miss_detail:
    print("\n=== DETAIL MISS ===")
    for t, h, r, d in miss_detail:
        print(f"{t}: hasil={h}, real={r}, selisih={d} hari")

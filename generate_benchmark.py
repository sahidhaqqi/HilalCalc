#!/usr/bin/env python3
"""
Generate benchmark JSON — MABIMS vs Pemerintah & Muhammadiyah vs Real.
Output: data/benchmark.json

Usage:
    python generate_benchmark.py
    python generate_benchmark.py --output data
"""

import io, contextlib, argparse, json
from datetime import date, datetime
from pathlib import Path

# ===================================================================
# LOAD BACKEND
# ===================================================================
print("Memuat backend MABIMS...")
import contextlib, io, importlib.util

from hitung_final import (
    hitung_awal_bulan_hijriah as hitung_mabims,
    ts, eph, wgs84, LATITUDE, LONGITUDE, ELEVATION
)

print("Memuat backend Muhammadiyah...")
spec = importlib.util.spec_from_file_location("hitung_muhammadiyah", "hitung_muhammadiyah.py")
mod  = importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()):
    spec.loader.exec_module(mod)
hitung_muham = mod.hitung_awal_bulan_hijriah
print("Siap.\n")

earth      = eph['earth']
topos      = wgs84.latlon(LATITUDE, LONGITUDE, elevation_m=ELEVATION)
lokasi_geo = earth + topos

earth_u    = mod.eph['earth']
topos_u    = mod.wgs84.latlon(mod.LATITUDE, mod.LONGITUDE, elevation_m=mod.ELEVATION)
lokasi_u   = earth_u + topos_u

# ===================================================================
# DATA REAL
# ===================================================================
DATA = [
    # (H,   1-Ramadan-Pem,         1-Ramadan-Muh,         1-Syawal-Pem,          1-Syawal-Muh)
    (1420,  date(1999,12, 9),  date(1999,12, 9),  date(2000, 1, 8),  date(2000, 1, 8)),
    (1421,  date(2000,11,27),  date(2000,11,27),  date(2000,12,27),  date(2000,12,27)),
    (1422,  date(2001,11,17),  date(2001,11,16),  date(2001,12,16),  date(2001,12,16)),
    (1423,  date(2002,11, 6),  date(2002,11, 6),  date(2002,12, 6),  date(2002,12, 5)),
    (1424,  date(2003,10,27),  date(2003,10,27),  date(2003,11,25),  date(2003,11,25)),
    (1425,  date(2004,10,15),  date(2004,10,15),  date(2004,11,14),  date(2004,11,14)),
    (1426,  date(2005,10, 5),  date(2005,10, 5),  date(2005,11, 3),  date(2005,11, 3)),
    (1427,  date(2006, 9,24),  date(2006, 9,24),  date(2006,10,24),  date(2006,10,23)),
    (1428,  date(2007, 9,13),  date(2007, 9,13),  date(2007,10,13),  date(2007,10,12)),
    (1429,  date(2008, 9, 1),  date(2008, 9, 1),  date(2008,10, 1),  date(2008,10, 1)),
    (1430,  date(2009, 8,22),  date(2009, 8,22),  date(2009, 9,20),  date(2009, 9,20)),
    (1431,  date(2010, 8,11),  date(2010, 8,11),  date(2010, 9,10),  date(2010, 9,10)),
    (1432,  date(2011, 8, 1),  date(2011, 8, 1),  date(2011, 8,31),  date(2011, 8,30)),
    (1433,  date(2012, 7,21),  date(2012, 7,20),  date(2012, 8,19),  date(2012, 8,19)),
    (1434,  date(2013, 7,10),  date(2013, 7, 9),  date(2013, 8, 8),  date(2013, 8, 8)),
    (1435,  date(2014, 6,29),  date(2014, 6,28),  date(2014, 7,28),  date(2014, 7,28)),
    (1436,  date(2015, 6,18),  date(2015, 6,18),  date(2015, 7,17),  date(2015, 7,17)),
    (1437,  date(2016, 6, 6),  date(2016, 6, 6),  date(2016, 7, 6),  date(2016, 7, 6)),
    (1438,  date(2017, 5,27),  date(2017, 5,27),  date(2017, 6,25),  date(2017, 6,25)),
    (1439,  date(2018, 5,17),  date(2018, 5,17),  date(2018, 6,15),  date(2018, 6,15)),
    (1440,  date(2019, 5, 6),  date(2019, 5, 6),  date(2019, 6, 5),  date(2019, 6, 5)),
    (1441,  date(2020, 4,24),  date(2020, 4,24),  date(2020, 5,24),  date(2020, 5,24)),
    (1442,  date(2021, 4,13),  date(2021, 4,13),  date(2021, 5,13),  date(2021, 5,13)),
    (1443,  date(2022, 4, 3),  date(2022, 4, 2),  date(2022, 5, 2),  date(2022, 5, 2)),
    (1444,  date(2023, 3,23),  date(2023, 3,23),  date(2023, 4,22),  date(2023, 4,21)),
    (1445,  date(2024, 3,12),  date(2024, 3,11),  date(2024, 4,10),  date(2024, 4,10)),
    (1446,  date(2025, 3, 1),  date(2025, 3, 1),  date(2025, 3,31),  date(2025, 3,31)),
    (1447,  date(2026, 2,19),  date(2026, 2,19),  date(2026, 3,21),  date(2026, 3,20)),
]

# ===================================================================
# HELPERS
# ===================================================================
def run_silent(fn, *args):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        result = fn(*args)
    return result

def selisih(a, b):
    if a is None or b is None: return None
    return (a - b).days

def status_label(d):
    if d is None:  return 'error'
    if d == 0:     return 'match'
    if abs(d) == 1: return 'near'
    return 'miss'

# ===================================================================
# RUN BENCHMARK
# ===================================================================
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--output', default='data')
    args = ap.parse_args()
    out_dir = Path(args.output)
    out_dir.mkdir(exist_ok=True)

    rows = []
    n = len(DATA)

    for i, row in enumerate(DATA, 1):
        hijri = row[0]
        real_r_pem, real_r_muh, real_s_pem, real_s_muh = row[1], row[2], row[3], row[4]

        print(f"[{i:02d}/{n}] {hijri} H ...", end=' ', flush=True)

        # MABIMS
        try:
            r_mab = run_silent(hitung_mabims, hijri, 9,  ts, eph, topos, lokasi_geo)
            r_mab = r_mab if isinstance(r_mab, date) else date.fromisoformat(r_mab['tanggal_awal'])
        except Exception as ex: r_mab = None; print(f"\n  MABIMS-R error: {ex}", end='')

        try:
            s_mab = run_silent(hitung_mabims, hijri, 10, ts, eph, topos, lokasi_geo)
            s_mab = s_mab if isinstance(s_mab, date) else date.fromisoformat(s_mab['tanggal_awal'])
        except Exception as ex: s_mab = None; print(f"\n  MABIMS-S error: {ex}", end='')

        # Muhammadiyah
        try:
            rd = run_silent(hitung_muham, hijri, 9,  mod.ts, mod.eph, topos_u, lokasi_u)
            r_muh = date.fromisoformat(rd['tanggal_awal'])
        except Exception as ex: r_muh = None; print(f"\n  Muham-R error: {ex}", end='')

        try:
            sd = run_silent(hitung_muham, hijri, 10, mod.ts, mod.eph, topos_u, lokasi_u)
            s_muh = date.fromisoformat(sd['tanggal_awal'])
        except Exception as ex: s_muh = None; print(f"\n  Muham-S error: {ex}", end='')

        dr_mab = selisih(r_mab, real_r_pem)
        ds_mab = selisih(s_mab, real_s_pem)
        dr_muh = selisih(r_muh, real_r_muh)
        ds_muh = selisih(s_muh, real_s_muh)

        dr_str = f"{dr_mab:+d}" if dr_mab is not None else '?'
        ds_str = f"{ds_mab:+d}" if ds_mab is not None else '?'
        ur_str = f"{dr_muh:+d}" if dr_muh is not None else '?'
        us_str = f"{ds_muh:+d}" if ds_muh is not None else '?'
        print(f"MABIMS-R:{dr_str}  MABIMS-S:{ds_str}  Muham-R:{ur_str}  Muham-S:{us_str}")

        rows.append({
            'tahun_hijri':  hijri,
            'tahun_masehi': real_r_pem.year,
            # MABIMS hasil & real
            'mabims': {
                'ramadan_hitung':  str(r_mab) if r_mab else None,
                'ramadan_real':    str(real_r_pem),
                'ramadan_selisih': dr_mab,
                'ramadan_status':  status_label(dr_mab),
                'syawal_hitung':   str(s_mab) if s_mab else None,
                'syawal_real':     str(real_s_pem),
                'syawal_selisih':  ds_mab,
                'syawal_status':   status_label(ds_mab),
            },
            # Muhammadiyah hasil & real
            'muhammadiyah': {
                'ramadan_hitung':  str(r_muh) if r_muh else None,
                'ramadan_real':    str(real_r_muh),
                'ramadan_selisih': dr_muh,
                'ramadan_status':  status_label(dr_muh),
                'syawal_hitung':   str(s_muh) if s_muh else None,
                'syawal_real':     str(real_s_muh),
                'syawal_selisih':  ds_muh,
                'syawal_status':   status_label(ds_muh),
            },
        })

    # ── Hitung akurasi ──
    def akurasi(rows, metode, bulan):
        vals = [r[metode][bulan+'_selisih'] for r in rows if r[metode][bulan+'_selisih'] is not None]
        total = len(vals)
        if total == 0: return {}
        match = sum(1 for v in vals if v == 0)
        near  = sum(1 for v in vals if abs(v) == 1)
        plus1 = sum(1 for v in vals if v == 1)
        min1  = sum(1 for v in vals if v == -1)
        miss  = sum(1 for v in vals if abs(v) > 1)
        return {
            'total': total,
            'match': match,
            'match_pct': round(match/total*100, 1),
            'near': near,
            'near_pct': round(near/total*100, 1),
            'plus1': plus1,
            'min1': min1,
            'miss': miss,
        }

    summary = {
        'mabims_ramadan':      akurasi(rows, 'mabims', 'ramadan'),
        'mabims_syawal':       akurasi(rows, 'mabims', 'syawal'),
        'muhammadiyah_ramadan': akurasi(rows, 'muhammadiyah', 'ramadan'),
        'muhammadiyah_syawal':  akurasi(rows, 'muhammadiyah', 'syawal'),
    }

    def overall(a, b):
        ta = a.get('total',0) + b.get('total',0)
        ma = a.get('match',0) + b.get('match',0)
        return round(ma/ta*100, 1) if ta else 0

    summary['mabims_overall']       = overall(summary['mabims_ramadan'],       summary['mabims_syawal'])
    summary['muhammadiyah_overall'] = overall(summary['muhammadiyah_ramadan'], summary['muhammadiyah_syawal'])

    out = {
        'generated_at': datetime.now().isoformat(),
        'n_tahun': len(rows),
        'tahun_range': [rows[0]['tahun_hijri'], rows[-1]['tahun_hijri']],
        'summary': summary,
        'rows': rows,
    }

    path = out_dir / 'benchmark.json'
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"\n{'─'*55}")
    print(f"MABIMS overall       : {summary['mabims_overall']}%")
    print(f"Muhammadiyah overall : {summary['muhammadiyah_overall']}%")
    print(f"\nSimpan → {path.resolve()}")

if __name__ == '__main__':
    main()

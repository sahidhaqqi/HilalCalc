#!/usr/bin/env python3
"""
Generate JSON lengkap — semua detail hisab hilal.

Usage:
    python generate_json.py                         # 1444-1450 H default
    python generate_json.py --dari 1444 --sampai 1460
    python generate_json.py --tahun 1446 1447
"""

import json, io, re, os, sys, contextlib, argparse
from pathlib import Path
from datetime import datetime

print("Memuat ephemeris & backend...")
import importlib.util

def load_backend():
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, 'hitung_final.py')
    if not os.path.exists(path):
        sys.exit(f"hitung_final.py tidak ditemukan di {here}")
    spec = importlib.util.spec_from_file_location("hitung_final", path)
    mod  = importlib.util.module_from_spec(spec)
    with contextlib.redirect_stdout(io.StringIO()):
        spec.loader.exec_module(mod)
    return mod

B = load_backend()
print("Backend siap\n")

# ═══════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════
def rx(text, pattern, cast=str, default=None):
    m = re.search(pattern, text)
    if not m: return default
    try:    return cast(m.group(1))
    except: return default


# ═══════════════════════════════════════════════════════
# PARSE SCAN INDONESIA
# ═══════════════════════════════════════════════════════
def parse_scan(blok):
    """Ambil data scan visibilitas Indonesia dari blok teks."""
    if 'SCAN VISIBILITAS INDONESIA' not in blok:
        return None

    # Hitung jumlah titik
    n_match = re.search(r'Wilayah potensial rukyat:\s*(\d+)\s*titik', blok)
    n_titik = int(n_match.group(1)) if n_match else 0

    # Ambil semua koordinat  lat=X, lon=Y
    titik = []
    for m in re.finditer(r'lat=([-\d.]+),\s*lon=([-\d.]+)', blok):
        titik.append({'lat': float(m.group(1)), 'lon': float(m.group(2))})

    return {
        'n_titik_grid': n_titik,
        'titik_sampel': titik,
    }


# ═══════════════════════════════════════════════════════
# PARSE SATU HARI
# ═══════════════════════════════════════════════════════
def parse_hari(blok):
    tanggal    = rx(blok, r'Memeriksa maghrib tanggal (\d{4}-\d{2}-\d{2})')
    maghrib    = rx(blok, r'Maghrib: (\d{2}:\d{2} WIB)')
    maghrib_utc= rx(blok, r'Maghrib:.*?\((\d{2}:\d{2} UTC)\)')
    moonset    = rx(blok, r'Moonset: (\d{2}:\d{2} WIB)')
    moonset_utc= rx(blok, r'Moonset:.*?\((\d{2}:\d{2} UTC)\)')
    best_time  = rx(blok, r'Best time: (\d{2}:\d{2} WIB)')

    # MABIMS
    mabims = None
    mm = re.search(
        r'\[MABIMS\] (.+?):\s+alt=([-\d.]+)[^\(]*\(([^)]+)\).*?'
        r'elong_geo=([-\d.]+)[^\(]*\(([^)]+)\).*?'
        r'umur=([-\d.]+)\s+jam\s*\(([^)]+)\).*?->\s*(.*?)$',
        blok, re.MULTILINE
    )
    if mm:
        mabims = {
            'label':     mm.group(1).strip(),
            'lolos':     'Lolos' in mm.group(8),
            'alt':       float(mm.group(2)),
            'alt_ok':    mm.group(3).strip() == '\u2713',
            'elong_geo': float(mm.group(4)),
            'elong_ok':  mm.group(5).strip() == '\u2713',
            'umur':      float(mm.group(6)),
            'umur_ok':   mm.group(7).strip() == '\u2713',
        }

    # Borderline
    borderline = None
    bm = re.search(r'Elongasi borderline \(([\d.]+)[^,]+, kurang ([\d.]+)', blok)
    if bm:
        borderline = {
            'elong_actual': float(bm.group(1)),
            'kurang_dari':  float(bm.group(2)),
            'pesan':        'Rukyat mungkin berhasil, keputusan final di Sidang Isbat',
        }

    # Visibilitas
    vis = {
        'alt_bulan_airless':    rx(blok, r'Altitude bulan \(airless\): ([-\d.]+)', cast=float),
        'alt_matahari_airless': rx(blok, r'Matahari: ([-\d.]+)', cast=float),
        'elongasi_top':         rx(blok, r'Elongasi \(toposentrik\): ([\d.]+)', cast=float),
        'arcv':                 rx(blok, r'ARCV \(airless\): ([-\d.]+)', cast=float),
        'lebar_sabit_menit':    rx(blok, r'Lebar sabit \(geometris\): ([\d.]+)', cast=float),
        'illumination_pct':     rx(blok, r'Illumination fraction: ([\d.]+)', cast=float),
    }

    yallop_klas = rx(blok, r'Yallop q = [-\d.]+ -> (.+)')
    odeh_klas   = rx(blok, r'Odeh V = [-\d.]+ -> (.+)')

    yallop = {
        'q':     rx(blok, r'Yallop q = ([-\d.]+)', cast=float),
        'huruf': yallop_klas[0] if yallop_klas else None,
        'kelas': yallop_klas,
    }
    odeh = {
        'v':     rx(blok, r'Odeh V = ([-\d.]+)', cast=float),
        'huruf': odeh_klas[0] if odeh_klas else None,
        'kelas': odeh_klas,
    }

    prob    = rx(blok, r'Probabilitas terlihat: ([\d.]+)', cast=float)
    kontras_val = rx(blok, r'Kontras hilal vs langit: ([\d.]+)', cast=float)

    ket = None
    if   re.search(r'Hilal sangat mudah',    blok): ket = 'Sangat mudah terlihat'
    elif re.search(r'Hilal kemungkinan',      blok): ket = 'Kemungkinan terlihat'
    elif re.search(r'Hilal sangat sulit',     blok): ket = 'Sangat sulit terlihat'
    elif re.search(r'Hilal hampir mustahil',  blok): ket = 'Hampir mustahil terlihat'

    lolos_mabims = bool(re.search(r'Awal bulan = \d{4}-\d{2}-\d{2}', blok))
    awal_match   = re.search(r'Awal bulan = (\d{4}-\d{2}-\d{2})', blok)

    # SCAN — ada di dalam blok hari yg lolos
    scan = parse_scan(blok)

    return {
        'tanggal':          tanggal,
        'maghrib':          maghrib,
        'maghrib_utc':      maghrib_utc,
        'moonset':          moonset,
        'moonset_utc':      moonset_utc,
        'best_time':        best_time,
        'mabims':           mabims,
        'borderline':       borderline,
        'visibilitas':      vis,
        'yallop':           yallop,
        'odeh':             odeh,
        'probabilitas_pct': prob,
        'kontras':          {'nilai': kontras_val, 'keterangan': ket},
        'lolos_mabims':     lolos_mabims,
        'awal_bulan':       awal_match.group(1) if awal_match else None,
        'scan_indonesia':   scan,   # <-- sekarang ada di tiap hari
    }


# ═══════════════════════════════════════════════════════
# PARSE LOG PENUH
# ═══════════════════════════════════════════════════════
def parse_full_log(log, tanggal_result):
    ijtimak_wib  = rx(log, r'Ijtimak: (\d{2}-\d{2}-\d{4} \d{2}:\d{2} WIB)')
    tgl_newmoon  = rx(log, r'tanggal lokal: (\d{4}-\d{2}-\d{2})')
    ijtimak_info = rx(log, r'Ijtimak (sebelum|sesudah|setelah) maghrib[^\n]*')

    # Pecah per hari
    blok_pat = re.compile(
        r'(Memeriksa maghrib tanggal \d{4}-\d{2}-\d{2}.*?)(?=Memeriksa maghrib tanggal|Perkiraan awal bulan|\Z)',
        re.DOTALL
    )
    hari_list = [parse_hari(b.group(1)) for b in blok_pat.finditer(log)]
    hari_lolos = next((h for h in hari_list if h['lolos_mabims']), None)

    istikmal_m = re.search(r'istikmal\) = (\d{4}-\d{2}-\d{2})', log, re.IGNORECASE)

    # Scan dari hari yang lolos (sudah ada di hari_lolos['scan_indonesia'])
    scan = hari_lolos['scan_indonesia'] if hari_lolos else None

    rk = hari_lolos  # shortcut

    return {
        'tanggal_awal':      str(tanggal_result),
        'ijtimak_wib':       ijtimak_wib,
        'ijtimak_tgl_lokal': tgl_newmoon,
        'ijtimak_posisi':    ijtimak_info,
        'hari_diperiksa':    hari_list,
        'hari_lolos':        hari_lolos,
        'istikmal':          istikmal_m.group(1) if istikmal_m else None,
        'scan_indonesia':    scan,
        'mabims_lolos':      hari_lolos is not None,
        'ringkas': {
            'tanggal':       str(tanggal_result),
            'ijtimak':       ijtimak_wib,
            'maghrib':       rk['maghrib']                        if rk else None,
            'moonset':       rk['moonset']                        if rk else None,
            'best_time':     rk['best_time']                      if rk else None,
            'mabims_label':  rk['mabims']['label']                if rk and rk['mabims'] else None,
            'alt':           rk['mabims']['alt']                  if rk and rk['mabims'] else None,
            'alt_ok':        rk['mabims']['alt_ok']               if rk and rk['mabims'] else None,
            'elong_geo':     rk['mabims']['elong_geo']            if rk and rk['mabims'] else None,
            'elong_ok':      rk['mabims']['elong_ok']             if rk and rk['mabims'] else None,
            'umur':          rk['mabims']['umur']                 if rk and rk['mabims'] else None,
            'umur_ok':       rk['mabims']['umur_ok']              if rk and rk['mabims'] else None,
            'arcv':          rk['visibilitas']['arcv']            if rk else None,
            'elongasi_top':  rk['visibilitas']['elongasi_top']    if rk else None,
            'lebar_sabit':   rk['visibilitas']['lebar_sabit_menit'] if rk else None,
            'illumination':  rk['visibilitas']['illumination_pct'] if rk else None,
            'yallop_q':      rk['yallop']['q']                    if rk else None,
            'yallop_klas':   rk['yallop']['kelas']                if rk else None,
            'odeh_v':        rk['odeh']['v']                      if rk else None,
            'odeh_klas':     rk['odeh']['kelas']                  if rk else None,
            'prob':          rk['probabilitas_pct']               if rk else None,
            'kontras':       rk['kontras']                        if rk else None,
        },
        '_log_raw': log,
    }


# ═══════════════════════════════════════════════════════
# HITUNG SATU TAHUN
# ═══════════════════════════════════════════════════════
def hitung_tahun(tahun):
    from hijridate import Hijri
    earth  = B.eph['earth']
    topos  = B.wgs84.latlon(B.LATITUDE, B.LONGITUDE, elevation_m=B.ELEVATION)
    lokasi = earth + topos
    tahun_m = Hijri(tahun, 1, 1).to_gregorian().year
    delta_t = round(B.delta_t_approx(tahun_m), 1)

    hasil = {}
    for bulan, key in [(9, 'ramadan'), (10, 'syawal')]:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            tanggal = B.hitung_awal_bulan_hijriah(
                tahun, bulan, B.ts, B.eph, topos, lokasi
            )
        hasil[key] = parse_full_log(buf.getvalue(), tanggal)

    return {
        'tahun':        tahun,
        'tahun_masehi': tahun_m,
        'delta_t':      delta_t,
        'lokasi': {
            'lat': B.LATITUDE, 'lon': B.LONGITUDE,
            'elevasi': B.ELEVATION, 'tz': 'WIB (UTC+7)',
            'T_C': B.TEMPERATURE_C, 'P_mbar': B.PRESSURE_MBAR,
        },
        'ramadan': hasil['ramadan'],
        'syawal':  hasil['syawal'],
        'generated_at': datetime.now().isoformat(),
    }


# ═══════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tahun',  nargs='+', type=int)
    ap.add_argument('--dari',   type=int, default=1444)
    ap.add_argument('--sampai', type=int, default=1450)
    ap.add_argument('--output', type=str, default='data')
    args = ap.parse_args()

    tahun_list = sorted(args.tahun) if args.tahun else list(range(args.dari, args.sampai + 1))
    out_dir = Path(args.output)
    out_dir.mkdir(exist_ok=True)

    print(f"Menghitung {len(tahun_list)} tahun: {tahun_list[0]}-{tahun_list[-1]} H")
    print(f"Output -> {out_dir.resolve()}\n" + "-"*55)

    idx_rows, failed = [], []

    for i, tahun in enumerate(tahun_list, 1):
        print(f"[{i:02d}/{len(tahun_list)}] {tahun} H ...", end=' ', flush=True)
        try:
            data = hitung_tahun(tahun)
            with open(out_dir / f"{tahun}.json", 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            r = data['ramadan']['ringkas']
            s = data['syawal']['ringkas']

            # Debug: cek scan
            r_scan = data['ramadan'].get('scan_indonesia')
            s_scan = data['syawal'].get('scan_indonesia')
            print(f"OK  Ramadan={r['tanggal']} scan={r_scan['n_titik_grid'] if r_scan else 'NONE'}  "
                  f"Syawal={s['tanggal']} scan={s_scan['n_titik_grid'] if s_scan else 'NONE'}")

            idx_rows.append({
                'tahun': tahun, 'tahun_masehi': data['tahun_masehi'],
                'ramadan': {'tanggal': r['tanggal'], 'ijtimak': r['ijtimak'],
                            'mabims': data['ramadan']['mabims_lolos'],
                            'yallop_q': r['yallop_q'], 'odeh_v': r['odeh_v'], 'prob': r['prob']},
                'syawal':  {'tanggal': s['tanggal'], 'ijtimak': s['ijtimak'],
                            'mabims': data['syawal']['mabims_lolos'],
                            'yallop_q': s['yallop_q'], 'odeh_v': s['odeh_v'], 'prob': s['prob']},
            })
        except Exception as ex:
            import traceback; traceback.print_exc()
            print(f"GAGAL: {ex}")
            failed.append(tahun)

    with open(out_dir / 'index.json', 'w', encoding='utf-8') as f:
        json.dump({'tahun_tersedia': [r['tahun'] for r in idx_rows],
                   'data': idx_rows,
                   'generated_at': datetime.now().isoformat()},
                  f, ensure_ascii=False, indent=2)

    print(f"\n{'─'*55}")
    print(f"Selesai: {len(idx_rows)} OK, {len(failed)} gagal" + (f" {failed}" if failed else ""))
    print(f"Upload folder '{out_dir}/' + index.html ke Cloudflare Pages.")

if __name__ == '__main__':
    main()

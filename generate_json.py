#!/usr/bin/env python3
"""
Generate JSON gabungan MABIMS + Muhammadiyah.
Satu file JSON per tahun berisi kedua metode.

Usage:
    python generate_json.py
    python generate_json.py --dari 1444 --sampai 1450
    python generate_json.py --tahun 1446 1447
"""

import json, io, re, os, sys, contextlib, argparse
import numpy as np

class SafeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (np.bool_)):   return bool(obj)
        if isinstance(obj, (np.integer)): return int(obj)
        if isinstance(obj, (np.floating)): return float(obj)
        if isinstance(obj, np.ndarray):   return obj.tolist()
        return super().default(obj)
from pathlib import Path
from datetime import datetime

print("Memuat backend...")
import importlib.util

def load_backend(filename):
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, filename)
    if not os.path.exists(path):
        sys.exit(f"{filename} tidak ditemukan di {here}")
    spec = importlib.util.spec_from_file_location(filename.replace('.py',''), path)
    mod  = importlib.util.module_from_spec(spec)
    with contextlib.redirect_stdout(io.StringIO()):
        spec.loader.exec_module(mod)
    return mod

B_mabims = load_backend('hitung_final.py')
B_muham  = load_backend('hitung_muhammadiyah.py')
print("Backend MABIMS + Muhammadiyah siap\n")


# ═══════════════════════════════════════════════════════
# HELPER
# ═══════════════════════════════════════════════════════
def rx(text, pattern, cast=str, default=None):
    m = re.search(pattern, text)
    if not m: return default
    try:    return cast(m.group(1))
    except: return default


# ═══════════════════════════════════════════════════════
# PARSER MABIMS (hitung_final.py)
# ═══════════════════════════════════════════════════════
def parse_multilokasi_mabims(blok):
    n_match = re.search(r'LOKASI YANG MEMENUHI MABIMS NASIONAL \((\d+) titik\)', blok)
    if not n_match:
        return None
    lokasi_list = []
    for m in re.finditer(
        r'-\s+(.+?):\s+alt=([-\d.]+)°,\s+az=([\d.]+)°,\s+'
        r'elong=([\d.]+)°,\s+umur=([\d.]+)\s+jam,\s+lag=([\d.]+)\s+menit,\s+'
        r'maghrib=(\d{2}:\d{2})\s+UTC,\s+moonset=(\d{2}:\d{2})\s+UTC',
        blok
    ):
        lokasi_list.append({
            'nama': m.group(1).strip(),
            'alt': float(m.group(2)), 'az': float(m.group(3)),
            'elong': float(m.group(4)), 'umur': float(m.group(5)),
            'lag_menit': float(m.group(6)),
            'maghrib_utc': m.group(7), 'moonset_utc': m.group(8),
        })
    return {'n_lokasi': int(n_match.group(1)), 'lokasi': lokasi_list}

def parse_scan(blok):
    if 'SCAN VISIBILITAS INDONESIA' not in blok:
        return None
    n_match = re.search(r'Wilayah potensial rukyat:\s*(\d+)\s*titik', blok)
    n = int(n_match.group(1)) if n_match else 0
    titik = [{'lat': float(m.group(1)), 'lon': float(m.group(2))}
             for m in re.finditer(r'lat=([-\d.]+),\s*lon=([-\d.]+)', blok)]
    return {'n_titik_grid': n, 'titik_sampel': titik}

def parse_hari_mabims(blok):
    tanggal     = rx(blok, r'Memeriksa maghrib tanggal (\d{4}-\d{2}-\d{2})')
    maghrib     = rx(blok, r'Maghrib: (\d{2}:\d{2} WIB)')
    maghrib_utc = rx(blok, r'Maghrib:.*?\((\d{2}:\d{2} UTC)\)')
    best_time   = rx(blok, r'[Bb]est time.*?(\d{2}:\d{2} WIB)')

    mabims = None
    mm = re.search(
        r'\[MABIMS\s+\w+\]\s+(.+?):\s+alt=([-\d.]+)°\s*\(([✓✗])\).*?'
        r'elong_geo=([-\d.]+)°\s*\(([✓✗])\).*?'
        r'umur=([-\d.]+)\s+jam\s*\(([✓✗])\).*?->\s*(.*?)$',
        blok, re.MULTILINE
    )
    if mm:
        mabims = {
            'label': mm.group(1).strip(), 'lolos': 'Lolos' in mm.group(8),
            'alt': float(mm.group(2)), 'alt_ok': mm.group(3) == '✓',
            'elong_geo': float(mm.group(4)), 'elong_ok': mm.group(5) == '✓',
            'umur': float(mm.group(6)), 'umur_ok': mm.group(7) == '✓',
        }

    borderline = None
    bm = re.search(r'Elongasi borderline \(([\d.]+)°.*?kurang ([\d.]+)°', blok)
    if bm:
        borderline = {'elong_actual': float(bm.group(1)), 'kurang_dari': float(bm.group(2)),
                      'pesan': 'Rukyat mungkin berhasil, keputusan final di Sidang Isbat'}

    vis = {
        'alt_bulan_airless':    rx(blok, r'Altitude bulan \(airless\): ([-\d.]+)', cast=float),
        'alt_matahari_airless': rx(blok, r'Matahari: ([-\d.]+)', cast=float),
        'elongasi_top':         rx(blok, r'Elongasi \(toposentrik\): ([\d.]+)', cast=float),
        'arcv':                 rx(blok, r'ARCV \(airless\): ([-\d.]+)', cast=float),
        'lebar_sabit_menit':    rx(blok, r'Lebar sabit: ([\d.]+)', cast=float),
        'illumination_pct':     rx(blok, r'Illumination: ([\d.]+)', cast=float),
    }

    yk = rx(blok, r'Yallop q = [-\d.]+ -> (.+)')
    ok = rx(blok, r'Odeh V = [-\d.]+ -> (.+)')
    yallop = {'q': rx(blok, r'Yallop q = ([-\d.]+)', cast=float), 'huruf': yk[0] if yk else None, 'kelas': yk}
    odeh   = {'v': rx(blok, r'Odeh V = ([-\d.]+)', cast=float),   'huruf': ok[0] if ok else None, 'kelas': ok}

    prob = rx(blok, r'Probabilitas terlihat: ([\d.]+)', cast=float)
    kv   = rx(blok, r'Kontras hilal vs langit: ([\d.]+)', cast=float)
    ket  = None
    if   re.search(r'Hilal sangat mudah',   blok): ket = 'Sangat mudah terlihat'
    elif re.search(r'Hilal kemungkinan',     blok): ket = 'Kemungkinan terlihat'
    elif re.search(r'Hilal sangat sulit',    blok): ket = 'Sangat sulit terlihat'
    elif re.search(r'Hilal hampir mustahil', blok): ket = 'Hampir mustahil terlihat'

    multilokasi  = parse_multilokasi_mabims(blok)
    lolos_mabims = multilokasi is not None
    am = re.search(r'awal bulan = (\d{4}-\d{2}-\d{2})', blok)

    return {
        'tanggal': tanggal, 'maghrib': maghrib, 'maghrib_utc': maghrib_utc, 'best_time': best_time,
        'mabims_jakarta': mabims, 'borderline': borderline, 'visibilitas': vis,
        'yallop': yallop, 'odeh': odeh, 'probabilitas_pct': prob,
        'kontras': {'nilai': kv, 'keterangan': ket},
        'multilokasi': multilokasi, 'lolos_mabims': lolos_mabims,
        'awal_bulan': am.group(1) if am else None,
        'scan_indonesia': parse_scan(blok),
    }

def parse_log_mabims(log, tanggal_result):
    ijtimak_wib = rx(log, r'Ijtimak: (\d{2}-\d{2}-\d{4} \d{2}:\d{2} WIB)')
    tgl_newmoon = rx(log, r'tanggal lokal: (\d{4}-\d{2}-\d{2})')
    ijtimak_info= rx(log, r'Ijtimak (sebelum|sesudah|setelah) maghrib[^\n]*')

    blok_pat = re.compile(
        r'(Memeriksa maghrib tanggal \d{4}-\d{2}-\d{2}.*?)(?=Memeriksa maghrib tanggal|Perkiraan awal bulan|\Z)',
        re.DOTALL)
    hari_list  = [parse_hari_mabims(b.group(1)) for b in blok_pat.finditer(log)]
    hari_lolos = next((h for h in hari_list if h['lolos_mabims']), None)
    istikmal_m = re.search(r'istikmal\) = (\d{4}-\d{2}-\d{2})', log, re.IGNORECASE)
    rk = hari_lolos
    mj = rk['mabims_jakarta'] if rk else None
    ml = rk['multilokasi']    if rk else None

    return {
        'tanggal_awal': str(tanggal_result),
        'ijtimak_wib': ijtimak_wib, 'ijtimak_tgl_lokal': tgl_newmoon, 'ijtimak_posisi': ijtimak_info,
        'hari_diperiksa': hari_list, 'hari_lolos': hari_lolos,
        'istikmal': istikmal_m.group(1) if istikmal_m else None,
        'scan_indonesia': hari_lolos['scan_indonesia'] if hari_lolos else None,
        'mabims_lolos': hari_lolos is not None,
        'ringkas': {
            'tanggal': str(tanggal_result), 'ijtimak': ijtimak_wib,
            'maghrib':      rk['maghrib']                          if rk else None,
            'best_time':    rk['best_time']                        if rk else None,
            'mabims_label': mj['label']                            if mj else None,
            'alt':          mj['alt']                              if mj else None,
            'alt_ok':       mj['alt_ok']                           if mj else None,
            'elong_geo':    mj['elong_geo']                        if mj else None,
            'elong_ok':     mj['elong_ok']                         if mj else None,
            'umur':         mj['umur']                             if mj else None,
            'arcv':         rk['visibilitas']['arcv']              if rk else None,
            'elongasi_top': rk['visibilitas']['elongasi_top']      if rk else None,
            'lebar_sabit':  rk['visibilitas']['lebar_sabit_menit'] if rk else None,
            'illumination': rk['visibilitas']['illumination_pct']  if rk else None,
            'yallop_q':     rk['yallop']['q']                      if rk else None,
            'yallop_klas':  rk['yallop']['kelas']                  if rk else None,
            'odeh_v':       rk['odeh']['v']                        if rk else None,
            'odeh_klas':    rk['odeh']['kelas']                    if rk else None,
            'prob':         rk['probabilitas_pct']                 if rk else None,
            'kontras':      rk['kontras']                          if rk else None,
            'n_lokasi_lolos': ml['n_lokasi']                       if ml else 0,
            'lokasi_lolos':   ml['lokasi']                         if ml else [],
        },
    }


# ═══════════════════════════════════════════════════════
# PARSER MUHAMMADIYAH (hitung_muhammadiyah.py)
# ═══════════════════════════════════════════════════════
def parse_log_muhammadiyah(data_dict, tanggal_result):
    """
    hitung_muhammadiyah.py sudah return structured dict langsung,
    jadi kita tidak perlu parse log — tinggal reformat sedikit.
    """
    rk = data_dict.get('ringkas', {})
    return {
        'tanggal_awal':      data_dict.get('tanggal_awal', str(tanggal_result)),
        'ijtimak_wib':       data_dict.get('ijtimak_wib'),
        'ijtimak_tgl_lokal': data_dict.get('ijtimak_tgl_lokal'),
        'ijtimak_posisi':    data_dict.get('ijtimak_posisi'),
        'wujudul_lolos':     data_dict.get('wujudul_lolos', False),
        'istikmal':          data_dict.get('istikmal', False),
        'hari_diperiksa':    data_dict.get('hari_diperiksa', []),
        'scan_indonesia':    data_dict.get('scan_indonesia'),
        'ringkas': {
            'tanggal':        data_dict.get('tanggal_awal', str(tanggal_result)),
            'ijtimak':        rk.get('ijtimak'),
            'maghrib':        rk.get('maghrib'),
            'moonset':        rk.get('moonset'),
            'best_time':      rk.get('best_time'),
            'umur_jam':       rk.get('umur_jam'),
            'alt_jakarta':    rk.get('alt_jakarta'),
            'syarat_ijtimak': rk.get('syarat_ijtimak'),
            'syarat_alt':     rk.get('syarat_alt'),
            'arcv':           rk.get('arcv'),
            'lebar_sabit':    rk.get('lebar_sabit'),
            'illumination':   rk.get('illumination'),
            'n_lokasi_lolos': rk.get('n_lokasi_lolos', 0),
            'lokasi_lolos':   (data_dict.get('hari_diperiksa') or [{}])[-1].get('multilokasi', {}).get('lokasi', [])
                              if data_dict.get('wujudul_lolos') else [],
        },
    }


# ═══════════════════════════════════════════════════════
# HITUNG SATU TAHUN
# ═══════════════════════════════════════════════════════
def hitung_tahun(tahun):
    from hijridate import Hijri
    tahun_m = Hijri(tahun, 1, 1).to_gregorian().year
    delta_t = round(B_mabims.delta_t_approx(tahun_m), 1)

    # ── MABIMS ──
    earth_m = B_mabims.eph['earth']
    topos_m = B_mabims.wgs84.latlon(B_mabims.LATITUDE, B_mabims.LONGITUDE, elevation_m=B_mabims.ELEVATION)
    lokasi_m = earth_m + topos_m

    hasil_mabims = {}
    for bulan, key in [(9, 'ramadan'), (10, 'syawal')]:
        with contextlib.redirect_stdout(io.StringIO()):
            data = B_mabims.hitung_awal_bulan_hijriah(tahun, bulan, B_mabims.ts, B_mabims.eph, topos_m, lokasi_m)
        hasil_mabims[key] = data

    # ── MUHAMMADIYAH ──
    earth_u = B_muham.eph['earth']
    topos_u = B_muham.wgs84.latlon(B_muham.LATITUDE, B_muham.LONGITUDE, elevation_m=B_muham.ELEVATION)
    lokasi_u = earth_u + topos_u

    hasil_muham = {}
    for bulan, key in [(9, 'ramadan'), (10, 'syawal')]:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            data = B_muham.hitung_awal_bulan_hijriah(tahun, bulan, B_muham.ts, B_muham.eph, topos_u, lokasi_u)
        hasil_muham[key] = parse_log_muhammadiyah(data, data.get('tanggal_awal'))

    return {
        'tahun':             tahun,
        'tahun_masehi':      tahun_m,
        'delta_t':           delta_t,
        'n_lokasi_evaluasi': len(B_mabims.LOKASI_INDONESIA),
        'lokasi_ref': {
            'lat': B_mabims.LATITUDE, 'lon': B_mabims.LONGITUDE,
            'elevasi': B_mabims.ELEVATION, 'tz': 'WIB (UTC+7)',
        },
        'mabims':        hasil_mabims,
        'muhammadiyah':  hasil_muham,
        'generated_at':  datetime.now().isoformat(),
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
    print(f"Output -> {out_dir.resolve()}\n" + "-"*60)

    idx_rows, failed = [], []
    for i, tahun in enumerate(tahun_list, 1):
        print(f"[{i:02d}/{len(tahun_list)}] {tahun} H ...", end=' ', flush=True)
        try:
            data = hitung_tahun(tahun)
            with open(out_dir / f"{tahun}.json", 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2, cls=SafeEncoder)

            rm = data['mabims']['ramadan']['ringkas']
            sm = data['mabims']['syawal']['ringkas']
            ru = data['muhammadiyah']['ramadan']['ringkas']
            su = data['muhammadiyah']['syawal']['ringkas']

            print(f"OK  MABIMS: R={rm['tanggal']} S={sm['tanggal']} | "
                  f"Muham: R={ru['tanggal']} S={su['tanggal']}")

            idx_rows.append({
                'tahun': tahun, 'tahun_masehi': data['tahun_masehi'],
                'mabims': {
                    'ramadan_tanggal': rm['tanggal'], 'ramadan_lolos': data['mabims']['ramadan']['mabims_lolos'],
                    'syawal_tanggal':  sm['tanggal'], 'syawal_lolos':  data['mabims']['syawal']['mabims_lolos'],
                    'ramadan_prob': rm.get('prob'), 'syawal_prob': sm.get('prob'),
                },
                'muhammadiyah': {
                    'ramadan_tanggal': ru['tanggal'], 'ramadan_lolos': data['muhammadiyah']['ramadan']['wujudul_lolos'],
                    'syawal_tanggal':  su['tanggal'], 'syawal_lolos':  data['muhammadiyah']['syawal']['wujudul_lolos'],
                    'ramadan_n_lok': ru.get('n_lokasi_lolos', 0),
                    'syawal_n_lok':  su.get('n_lokasi_lolos', 0),
                },
            })
        except Exception as ex:
            import traceback; traceback.print_exc()
            print(f"GAGAL: {ex}")
            failed.append(tahun)

    with open(out_dir / 'index.json', 'w', encoding='utf-8') as f:
        json.dump({'tahun_tersedia': [r['tahun'] for r in idx_rows],
                   'data': idx_rows, 'generated_at': datetime.now().isoformat()},
                  f, ensure_ascii=False, indent=2)

    print(f"\n{'─'*60}")
    print(f"Selesai: {len(idx_rows)} OK, {len(failed)} gagal" + (f" {failed}" if failed else ""))

if __name__ == '__main__':
    main()

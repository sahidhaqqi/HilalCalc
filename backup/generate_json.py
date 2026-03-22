#!/usr/bin/env python3
"""
Generate JSON hisab hilal — zero regex, langsung pakai dict dari backend.

Usage:
    python generate_json.py
    python generate_json.py --dari 1444 --sampai 1460
    python generate_json.py --tahun 1446 1447 1448
"""

import json, os, sys, argparse
import numpy as np

class SafeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.bool_):    return bool(obj)
        if isinstance(obj, np.integer):  return int(obj)
        if isinstance(obj, np.floating): return float(obj)
        if isinstance(obj, np.ndarray):  return obj.tolist()
        return super().default(obj)
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
    spec.loader.exec_module(mod)
    return mod

B = load_backend()
print("Backend siap\n")


def hitung_tahun(tahun):
    from hijridate import Hijri

    earth         = B.eph['earth']
    topos_jakarta = B.wgs84.latlon(B.LATITUDE, B.LONGITUDE, elevation_m=B.ELEVATION)
    lokasi_jakarta= earth + topos_jakarta
    tahun_m       = Hijri(tahun, 1, 1).to_gregorian().year
    delta_t       = round(B.delta_t_approx(tahun_m), 1)

    hasil = {}
    for bulan, key in [(9, 'ramadan'), (10, 'syawal')]:
        # Langsung dapat dict — tidak ada parsing log sama sekali
        hasil[key] = B.hitung_awal_bulan_hijriah(
            tahun, bulan, B.ts, B.eph, topos_jakarta, lokasi_jakarta
        )

    return {
        'tahun':             tahun,
        'tahun_masehi':      tahun_m,
        'delta_t':           delta_t,
        'n_lokasi_evaluasi': len(B.LOKASI_INDONESIA),
        'engine': {
            'versi':     B.ENGINE_VERSION,
            'model':     B.ENGINE_MODELS,
            'ephemeris': B.EPH_USED,
        },
        'lokasi_referensi': {
            'nama':    'Jakarta',
            'lat':     B.LATITUDE,
            'lon':     B.LONGITUDE,
            'elevasi': B.ELEVATION,
            'tz':      'WIB (UTC+7)',
            'T_C':     B.TEMPERATURE_C,
            'P_mbar':  B.PRESSURE_MBAR,
        },
        'ramadan':      hasil['ramadan'],
        'syawal':       hasil['syawal'],
        'generated_at': datetime.now().isoformat(),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tahun',  nargs='+', type=int)
    ap.add_argument('--dari',   type=int, default=1444)
    ap.add_argument('--sampai', type=int, default=1450)
    ap.add_argument('--output', type=str, default='data')
    args = ap.parse_args()

    tahun_list = sorted(args.tahun) if args.tahun else list(range(args.dari, args.sampai + 1))
    out_dir    = Path(args.output)
    out_dir.mkdir(exist_ok=True)

    print(f"Menghitung {len(tahun_list)} tahun: {tahun_list[0]}-{tahun_list[-1]} H")
    print(f"Output -> {out_dir.resolve()}\n" + "-"*58)

    idx_rows, failed = [], []

    for i, tahun in enumerate(tahun_list, 1):
        print(f"\n[{i:02d}/{len(tahun_list)}] ══ Tahun {tahun} H ══")
        try:
            data = hitung_tahun(tahun)
            with open(out_dir / f"{tahun}.json", 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2, cls=SafeEncoder)

            r = data['ramadan']['ringkas']
            s = data['syawal']['ringkas']
            print(f"  ✅ Ramadan={r['tanggal']} ({r['n_lokasi_lolos']} lok)  "
                  f"Syawal={s['tanggal']} ({s['n_lokasi_lolos']} lok)")

            idx_rows.append({
                'tahun':        tahun,
                'tahun_masehi': data['tahun_masehi'],
                'ramadan': {
                    'tanggal':        r['tanggal'],
                    'ijtimak':        r['ijtimak'],
                    'mabims':         data['ramadan']['mabims_lolos'],
                    'n_lokasi_lolos': r['n_lokasi_lolos'],
                    'yallop_q':       r['yallop_q'],
                    'odeh_v':         r['odeh_v'],
                    'prob':           r['prob'],
                },
                'syawal': {
                    'tanggal':        s['tanggal'],
                    'ijtimak':        s['ijtimak'],
                    'mabims':         data['syawal']['mabims_lolos'],
                    'n_lokasi_lolos': s['n_lokasi_lolos'],
                    'yallop_q':       s['yallop_q'],
                    'odeh_v':         s['odeh_v'],
                    'prob':           s['prob'],
                },
            })
        except Exception as ex:
            import traceback; traceback.print_exc()
            print(f"  ❌ GAGAL: {ex}")
            failed.append(tahun)

    with open(out_dir / 'index.json', 'w', encoding='utf-8') as f:
        json.dump({
            'tahun_tersedia': [r['tahun'] for r in idx_rows],
            'data':           idx_rows,
            'generated_at':   datetime.now().isoformat(),
        }, f, ensure_ascii=False, indent=2, cls=SafeEncoder)

    print(f"\n{'═'*58}")
    print(f"Selesai: {len(idx_rows)} OK, {len(failed)} gagal"
          + (f" → {failed}" if failed else ""))
    print(f"Upload folder '{out_dir}/' + index.html ke Cloudflare Pages.")

if __name__ == '__main__':
    main()

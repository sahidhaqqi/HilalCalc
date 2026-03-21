#!/usr/bin/env python3
"""
Flask API — Hisab Hilal Indonesia
Deploy-ready untuk Render.com
"""

import os, io, re, contextlib, traceback
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ===================================================================
# Ephemeris — auto-download kalau belum ada
# de440s.bsp (~37MB) — akurat, tidak terlalu besar
# ===================================================================
print("🌙 Memuat ephemeris (otomatis download jika perlu)...")
from skyfield.api import load, wgs84
ts  = load.timescale()
try:
    eph = load('de440s.bsp')
    print("✅ de440s.bsp siap")
except Exception:
    try:
        eph = load('de421.bsp')
        print("✅ de421.bsp siap (fallback)")
    except Exception as e:
        print(f"❌ Gagal load ephemeris: {e}")
        eph = None

# ===================================================================
# Load hitung_final.py
# ===================================================================
def load_backend():
    import importlib.util
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, 'hitung_final.py')
    spec = importlib.util.spec_from_file_location("hitung_final", path)
    mod  = importlib.util.module_from_spec(spec)
    with contextlib.redirect_stdout(io.StringIO()):
        spec.loader.exec_module(mod)
    mod.eph = eph
    mod.ts  = ts
    return mod

print("🔭 Memuat modul hitung_final...")
try:
    B = load_backend()
    print("✅ Backend siap")
    BACKEND_OK = True
except Exception as e:
    print(f"❌ Gagal memuat backend: {e}")
    B = None
    BACKEND_OK = False

# ===================================================================
# Parser log → structured dict
# ===================================================================
def parse_log(log: str, tanggal_result) -> dict:
    def rx(pattern, cast=str):
        m = re.search(pattern, log)
        try:   return cast(m.group(1)) if m else None
        except: return None

    mabims_ok, mabims_label, mabims_detail = None, None, {}
    m = re.search(
        r'\[MABIMS\] (.+?):\s+alt=([-\d.]+)° \(([✓✗])\).*?'
        r'elong_geo=([-\d.]+)° \(([✓✗])\).*?'
        r'umur=([-\d.]+) jam \(([✓✗])\).*?-> (✅ Lolos|❌ Gagal)',
        log, re.DOTALL
    )
    if m:
        mabims_label = m.group(1)
        mabims_ok    = m.group(8) == '✅ Lolos'
        mabims_detail = {
            'alt':      float(m.group(2)), 'alt_ok':   m.group(3) == '✓',
            'elong_geo': float(m.group(4)), 'elong_ok': m.group(5) == '✓',
            'umur':     float(m.group(6)), 'umur_ok':  m.group(7) == '✓',
        }

    return {
        'tanggal':       str(tanggal_result),
        'ijtimak':       rx(r'Ijtimak: (\d{2}-\d{2}-\d{4} \d{2}:\d{2} WIB)'),
        'maghrib':       rx(r'Maghrib: (\d{2}:\d{2} WIB)'),
        'moonset':       rx(r'Moonset: (\d{2}:\d{2} WIB)'),
        'best_time':     rx(r'Best time: (\d{2}:\d{2} WIB)'),
        'mabims':        mabims_ok,
        'mabims_label':  mabims_label,
        'mabims_detail': mabims_detail,
        'yallop_q':      rx(r'Yallop q = ([-\d.]+)', cast=float),
        'yallop_klas':   rx(r'Yallop q = [-\d.]+ -> (.+)'),
        'odeh_v':        rx(r'Odeh V = ([-\d.]+)', cast=float),
        'odeh_klas':     rx(r'Odeh V = [-\d.]+ -> (.+)'),
        'illumination':  rx(r'Illumination fraction: ([\d.]+)%', cast=float),
        'arcv':          rx(r'ARCV \(airless\): ([-\d.]+)°', cast=float),
        'elong':         rx(r'Elongasi \(toposentrik\): ([\d.]+)°', cast=float),
        'width':         rx(r'Lebar sabit \(geometris\): ([\d.]+) menit', cast=float),
        'prob':          rx(r'Probabilitas terlihat: ([\d.]+)%', cast=float),
        'log':           log,
    }

# ===================================================================
# Routes
# ===================================================================
@app.route('/')
def index():
    here = os.path.dirname(os.path.abspath(__file__))
    return send_file(os.path.join(here, 'index.html'))

@app.route('/api/health')
def health():
    return jsonify({'status': 'ok', 'backend': BACKEND_OK, 'eph': eph is not None})

@app.route('/api/hitung', methods=['POST'])
def hitung():
    if not BACKEND_OK or eph is None:
        return jsonify({'error': 'Backend belum siap, coba lagi dalam beberapa detik.'}), 503

    data = request.get_json(silent=True) or {}
    try:
        tahun = int(data.get('tahun', 0))
    except (TypeError, ValueError):
        return jsonify({'error': 'Tahun harus berupa angka'}), 400

    if not (1400 <= tahun <= 1500):
        return jsonify({'error': 'Tahun Hijriah harus antara 1400-1500'}), 400

    try:
        from hijridate import Hijri
        earth  = eph['earth']
        topos  = wgs84.latlon(B.LATITUDE, B.LONGITUDE, elevation_m=B.ELEVATION)
        lokasi = earth + topos
        tahun_m = Hijri(tahun, 1, 1).to_gregorian().year
        delta_t = round(B.delta_t_approx(tahun_m), 1)

        results = {}
        for bulan, key in [(9, 'ramadan'), (10, 'syawal')]:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                tanggal = B.hitung_awal_bulan_hijriah(
                    tahun, bulan, ts, eph, topos, lokasi
                )
            results[key] = parse_log(buf.getvalue(), tanggal)

        return jsonify({
            'tahun': tahun, 'tahun_masehi': tahun_m, 'delta_t': delta_t,
            'lokasi': {
                'lat': B.LATITUDE, 'lon': B.LONGITUDE,
                'elevasi': B.ELEVATION, 'tz': 'WIB (UTC+7)',
            },
            'ramadan': results['ramadan'],
            'syawal':  results['syawal'],
        })

    except Exception as e:
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()}), 500

# ===================================================================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, port=port, host='0.0.0.0')

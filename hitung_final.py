#!/usr/bin/env python3
"""
Hisab Awal Bulan Hijriyah (MABIMS + Yallop + Odeh)
Versi refactored: fungsi utama return structured dict langsung.

Fitur:
- Multi-lokasi 13 titik strategis Indonesia
- MABIMS 2022 (alt >= 3°, elong >= 6.4°)
- Yallop & Odeh untuk Jakarta (best time)
- Grid scan maghrib lokal per titik
- Return structured dict — tidak perlu parsing log
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
# Metadata engine
# ===================================================================
ENGINE_VERSION  = "2.0.0"
ENGINE_MODELS   = ["MABIMS 2022", "Yallop 1998", "Odeh 2006"]

# ===================================================================
# Konfigurasi
# ===================================================================
LATITUDE      = -6.2088
LONGITUDE     = 106.8456
ELEVATION     = 8.0
TEMPERATURE_C = 25.0
PRESSURE_MBAR = 1010.0
TZ_WIB        = pytz.timezone('Asia/Jakarta')

EPH_FILE = 'de440.bsp'
try:
    ts  = load.timescale()
    eph = load(EPH_FILE)
    EPH_USED = EPH_FILE
    print(f"✅ Menggunakan ephemeris {EPH_FILE}")
except Exception:
    print(f"⚠️  {EPH_FILE} tidak ditemukan, fallback ke de421.bsp")
    eph      = load('de421.bsp')
    EPH_USED = 'de421.bsp'

# ===================================================================
# Lokasi representatif Indonesia (13 titik)
# ===================================================================
LOKASI_INDONESIA = [
    ("Sabang",      5.8943,   95.3184,  15),
    ("Medan",       3.5952,   98.6722,  25),
    ("Padang",     -0.9471,  100.4172,  10),
    ("Jakarta",    -6.2088,  106.8456,   8),
    ("Bandung",    -6.9175,  107.6191,  10),
    ("Surabaya",   -7.2575,  112.7521,   5),
    ("Banjarmasin",-3.3194,  114.5928,  10),
    ("Balikpapan", -1.2379,  116.8529,  10),
    ("Makassar",   -5.1477,  119.4327,  10),
    ("Manado",      1.4748,  124.8421,  10),
    ("Kupang",    -10.1772,  123.6070,  10),
    ("Ambon",      -3.6550,  128.1908,  10),
    ("Jayapura",   -2.5337,  140.7181,  10),
]

MARGIN_ELONGASI = 0.05

# ===================================================================
# Helpers
# ===================================================================
def to_utc_naive(dt):
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)

def delta_t_approx(year):
    y = year + 0.5
    if 2005 <= y <= 2050:
        t = y - 2000
        return 62.92 + 0.32217 * t + 0.005589 * t**2
    elif 1986 <= y < 2005:
        t = y - 2000
        return 63.86 + 0.3345*t - 0.060374*t**2 + 0.0017275*t**3
    else:
        t = (y - 2000) / 100
        return 64 + 59 * t

# ===================================================================
# Waktu maghrib & moonset
# ===================================================================
def cari_waktu_maghrib(tanggal, ts, eph, topos):
    t0 = ts.utc(tanggal.year, tanggal.month, tanggal.day, 0)
    t1 = ts.utc(tanggal.year, tanggal.month, tanggal.day, 23, 59)
    f  = almanac.sunrise_sunset(eph, topos)
    times, events = almanac.find_discrete(t0, t1, f)
    sunsets = [t for t, e in zip(times, events) if not e]
    return sunsets[0].utc_datetime() if sunsets else None

def cari_waktu_moonset_after_maghrib(maghrib_utc, ts, eph, topos):
    if maghrib_utc is None:
        return None
    t0 = ts.from_datetime(maghrib_utc)
    t1 = ts.from_datetime(maghrib_utc + timedelta(hours=12))
    f  = almanac.risings_and_settings(eph, eph['moon'], topos)
    times, events = almanac.find_discrete(t0, t1, f)
    moonsets = [t for t, e in zip(times, events) if not e]
    return moonsets[0].utc_datetime() if moonsets else None

def cari_best_time(maghrib_utc, moonset_utc):
    if moonset_utc is None:
        return None
    lag = (moonset_utc - maghrib_utc).total_seconds() / 3600
    if lag <= 0:
        return None
    return maghrib_utc + timedelta(hours=lag * 4/9)

# ===================================================================
# Posisi bulan (toposentrik + geosentris)
# ===================================================================
def hitung_bulan_pada_waktu(waktu_utc, ts, eph, lokasi_geo):
    detik = waktu_utc.second + waktu_utc.microsecond / 1e6
    t = ts.utc(waktu_utc.year, waktu_utc.month, waktu_utc.day,
               waktu_utc.hour, waktu_utc.minute, detik)

    pos          = lokasi_geo.at(t)
    bulan_top    = pos.observe(eph['moon']).apparent()
    matahari_top = pos.observe(eph['sun']).apparent()

    alt_b_ref, az_b, _ = bulan_top.altaz(temperature_C=TEMPERATURE_C, pressure_mbar=PRESSURE_MBAR)
    alt_m_ref, _, _    = matahari_top.altaz(temperature_C=TEMPERATURE_C, pressure_mbar=PRESSURE_MBAR)
    alt_b_air, _, _    = bulan_top.altaz()
    alt_m_air, _, _    = matahari_top.altaz()
    elong_top          = bulan_top.separation_from(matahari_top).degrees

    earth       = eph['earth']
    bulan_geo   = earth.at(t).observe(eph['moon']).apparent()
    matahari_geo= earth.at(t).observe(eph['sun']).apparent()
    elong_geo   = bulan_geo.separation_from(matahari_geo).degrees
    jarak_km    = bulan_top.distance().km

    return {
        'alt_ref':    alt_b_ref.degrees,
        'az':         az_b.degrees,
        'alt_mat_ref':alt_m_ref.degrees,
        'alt_air':    alt_b_air.degrees,
        'alt_mat_air':alt_m_air.degrees,
        'elong_top':  elong_top,
        'jarak_km':   jarak_km,
        'elong_geo':  elong_geo,
    }

# ===================================================================
# Illumination, Yallop, Odeh, probabilitas, kontras
# ===================================================================
def hitung_illumination(waktu_utc, ts, eph):
    detik = waktu_utc.second + waktu_utc.microsecond / 1e6
    t     = ts.utc(waktu_utc.year, waktu_utc.month, waktu_utc.day,
                   waktu_utc.hour, waktu_utc.minute, detik)
    earth = eph['earth']
    moon  = earth.at(t).observe(eph['moon']).apparent()
    sun   = earth.at(t).observe(eph['sun']).apparent()
    phase = moon.separation_from(sun).radians
    return (1 + np.cos(phase)) / 2 * 100

def hitung_yallop(arcv, width_menit):
    W = width_menit
    a = 11.8371 - 6.3226*W + 0.7319*W**2 - 0.1018*W**3
    q = (arcv - a) / 10
    if   q >  0.216: kelas = "A"; deskripsi = "Mudah terlihat mata telanjang"
    elif q > -0.014: kelas = "B"; deskripsi = "Terlihat kondisi sempurna"
    elif q > -0.160: kelas = "C"; deskripsi = "Perlu alat bantu, bisa naked eye jika ditemukan"
    elif q > -0.232: kelas = "D"; deskripsi = "Perlu alat bantu optik"
    else:            kelas = "E"; deskripsi = "Tidak terlihat walau dengan teleskop"
    return {'q': round(q, 4), 'kelas': kelas, 'deskripsi': deskripsi}

def hitung_odeh(arcv, width_menit):
    W = width_menit
    f = -0.1018*W**3 + 0.7319*W**2 - 6.3226*W + 7.1651
    v = arcv - f
    if   v >= 5.65: kelas = "A"; deskripsi = "Mudah terlihat mata telanjang"
    elif v >= 2.0:  kelas = "B"; deskripsi = "Terlihat dengan alat bantu, bisa naked eye"
    elif v >= -0.96:kelas = "C"; deskripsi = "Hanya terlihat dengan alat bantu optik"
    else:           kelas = "D"; deskripsi = "Tidak terlihat"
    return {'v': round(v, 4), 'kelas': kelas, 'deskripsi': deskripsi}

def hitung_probabilitas(odeh_v):
    return round(1 / (1 + np.exp(-2.0 * odeh_v)) * 100, 2)

def hitung_kontras(arcv, elong, width):
    B_moon = width * (elong / 10)
    B_sky  = np.exp(-0.25 * arcv)
    if B_sky <= 0: return 0, "Data tidak valid"
    c = B_moon / (B_sky * 100)
    if   c > 0.15: ket = "Sangat mudah terlihat"
    elif c > 0.05: ket = "Kemungkinan terlihat"
    elif c > 0.01: ket = "Sangat sulit terlihat"
    else:          ket = "Hampir mustahil terlihat"
    return round(c, 6), ket

# ===================================================================
# MABIMS
# ===================================================================
def cek_mabims(tanggal, alt, elong_geo, umur_jam, EPS=1e-6):
    if tanggal.year >= 2022:
        alt_ok   = (alt + EPS) >= 3.0
        elong_ok = (elong_geo + EPS) >= 6.4
        # toleransi borderline
        borderline = (not elong_ok) and (6.4 - elong_geo) <= MARGIN_ELONGASI
        if borderline:
            elong_ok = True
        lolos  = alt_ok and elong_ok
        label  = "Neo MABIMS (2022+)"
        umur_ok= True
        return {
            'lolos': lolos, 'label': label,
            'alt_ok': alt_ok, 'elong_ok': elong_ok, 'umur_ok': umur_ok,
            'borderline': borderline,
            'threshold': {'alt': 3.0, 'elong': 6.4, 'umur': None},
        }
    else:
        alt_ok   = (alt + EPS) >= 2.0
        elong_ok = (elong_geo + EPS) >= 3.0
        borderline = (not elong_ok) and (3.0 - elong_geo) <= MARGIN_ELONGASI
        if borderline:
            elong_ok = True
        umur_ok  = (umur_jam + EPS) >= 8.0
        lolos    = (alt_ok and elong_ok) or (umur_ok and alt_ok)
        label    = "MABIMS Lama (pre-2022)"
        return {
            'lolos': lolos, 'label': label,
            'alt_ok': alt_ok, 'elong_ok': elong_ok, 'umur_ok': umur_ok,
            'borderline': borderline,
            'threshold': {'alt': 2.0, 'elong': 3.0, 'umur': 8.0},
        }

# ===================================================================
# Hitung visibilitas (Yallop + Odeh) pada best time
# ===================================================================
def hitung_visibilitas(best_utc, ts, eph, lokasi_geo):
    if best_utc is None:
        return None
    pos     = hitung_bulan_pada_waktu(best_utc, ts, eph, lokasi_geo)
    arcv    = pos['alt_air'] - pos['alt_mat_air']
    elong   = pos['elong_top']
    jarak   = pos['jarak_km']

    sd_rad  = np.arcsin(1737.4 / jarak)
    w_rad   = sd_rad * (1 - np.cos(np.radians(elong)))
    w_rad   = max(0.0, w_rad)
    width   = w_rad * (180 / np.pi) * 60
    illum   = hitung_illumination(best_utc, ts, eph)
    yallop  = hitung_yallop(arcv, width)
    odeh    = hitung_odeh(arcv, width)
    prob    = hitung_probabilitas(odeh['v'])
    kontras, kontras_ket = hitung_kontras(arcv, elong, width)

    return {
        'alt_bulan_airless':    round(pos['alt_air'], 4),
        'alt_matahari_airless': round(pos['alt_mat_air'], 4),
        'elongasi_top':         round(elong, 4),
        'arcv':                 round(arcv, 4),
        'lebar_sabit_menit':    round(width, 4),
        'illumination_pct':     round(illum, 4),
        'yallop':               yallop,
        'odeh':                 odeh,
        'probabilitas_pct':     prob,
        'kontras':              {'nilai': kontras, 'keterangan': kontras_ket},
    }

# ===================================================================
# Scan visibilitas Indonesia (grid, maghrib lokal)
# ===================================================================
def scan_visibilitas_indonesia(tanggal, ts, eph):
    earth     = eph['earth']
    latitudes = np.arange(-10, 7, 4)
    longitudes= np.arange(95, 141, 6)
    visible   = []

    for lat in latitudes:
        for lon in longitudes:
            topos  = wgs84.latlon(lat, lon)
            lokasi = earth + topos
            mgh    = cari_waktu_maghrib(tanggal, ts, eph, topos)
            if not mgh:
                continue
            pos    = hitung_bulan_pada_waktu(mgh, ts, eph, lokasi)
            arcv   = pos['alt_air'] - pos['alt_mat_air']
            jarak  = pos['jarak_km']
            elong  = pos['elong_top']
            sd_rad = np.arcsin(1737.4 / jarak)
            width  = sd_rad * (1 - np.cos(np.radians(elong))) * (180/np.pi) * 60
            a      = 11.8371 - 6.3226*width + 0.7319*width**2 - 0.1018*width**3
            q      = (arcv - a) / 10
            if q > -0.232:
                visible.append({'lat': float(lat), 'lon': float(lon), 'q': round(q,3)})

    return {
        'n_titik_grid': len(visible),
        'titik_sampel': visible[:20],
    }

# ===================================================================
# New moon
# ===================================================================
def cari_new_moon_terdekat(tanggal_acuan, ts, eph, rentang_hari=20):
    t_start = tanggal_acuan - timedelta(days=rentang_hari)
    t_end   = tanggal_acuan + timedelta(days=rentang_hari)
    t0 = ts.utc(t_start.year, t_start.month, t_start.day, 0)
    t1 = ts.utc(t_end.year,   t_end.month,   t_end.day,   23, 59)
    print(f"  Mencari new moon antara {t_start} dan {t_end}")

    f = almanac.moon_phases(eph)
    times, phases = almanac.find_discrete(t0, t1, f)
    nm_times = [t for t, p in zip(times, phases) if p == 0]
    if not nm_times:
        return None, None

    nm_utc  = [t.utc_datetime() for t in nm_times]
    acuan   = TZ_WIB.localize(datetime.combine(tanggal_acuan, datetime.min.time()))
    acuan_u = acuan.astimezone(timezone.utc)
    closest = min(nm_utc, key=lambda d: abs((d - acuan_u).total_seconds()))
    lokal   = closest.astimezone(TZ_WIB).date()
    return closest, lokal

# ===================================================================
# Cek satu lokasi untuk multi-lokasi
# ===================================================================
def cek_lokasi(tanggal, nm_utc, lokasi_info, ts, eph):
    nama, lat, lon, elev = lokasi_info
    topos     = wgs84.latlon(lat, lon, elevation_m=elev)
    lokasi_geo= eph['earth'] + topos

    mgh = cari_waktu_maghrib(tanggal, ts, eph, topos)
    if mgh is None:
        return None

    mset     = cari_waktu_moonset_after_maghrib(mgh, ts, eph, topos)
    nm_naive = to_utc_naive(nm_utc)
    umur_jam = (to_utc_naive(mgh) - nm_naive).total_seconds() / 3600
    if umur_jam < 0:
        return None

    pos  = hitung_bulan_pada_waktu(mgh, ts, eph, lokasi_geo)
    mab  = cek_mabims(tanggal, pos['alt_ref'], pos['elong_geo'], umur_jam)
    if not mab['lolos']:
        return None

    lag_menit = (to_utc_naive(mset) - to_utc_naive(mgh)).total_seconds() / 60 if mset else None

    return {
        'nama':        nama,
        'lat':         lat,
        'lon':         lon,
        'alt':         round(pos['alt_ref'], 3),
        'az':          round(pos['az'], 2),
        'elong_geo':   round(pos['elong_geo'], 3),
        'umur_jam':    round(umur_jam, 2),
        'lag_menit':   round(lag_menit, 1) if lag_menit else None,
        'maghrib_utc': mgh.strftime('%H:%M'),
        'moonset_utc': mset.strftime('%H:%M') if mset else None,
        'mabims':      mab,
    }

# ===================================================================
# FUNGSI UTAMA — return structured dict
# ===================================================================
def hitung_awal_bulan_hijriah(tahun_hijriah, bulan_hijriah, ts, eph, topos_jakarta, lokasi_geo_jakarta):
    hijri    = Hijri(tahun_hijriah, bulan_hijriah, 1)
    greg     = hijri.to_gregorian()
    perkiraan= datetime(greg.year, greg.month, greg.day).date()

    print(f"\n[{tahun_hijriah}-{bulan_hijriah}] Perkiraan: {perkiraan}")
    nm_utc, tgl_nm = cari_new_moon_terdekat(perkiraan, ts, eph)
    if nm_utc is None:
        raise RuntimeError(f"New moon tidak ditemukan untuk {tahun_hijriah}-{bulan_hijriah}")

    nm_wib    = nm_utc.astimezone(TZ_WIB)
    nm_naive  = to_utc_naive(nm_utc)
    mgh_nm    = cari_waktu_maghrib(tgl_nm, ts, eph, topos_jakarta)
    start_i   = 0 if (mgh_nm and nm_naive < to_utc_naive(mgh_nm)) else 1
    ijtimak_posisi = "sebelum maghrib" if start_i == 0 else "setelah maghrib"

    print(f"  Ijtimak: {nm_wib.strftime('%d-%m-%Y %H:%M WIB')} ({ijtimak_posisi})")

    hari_list = []

    for i in range(start_i, start_i + 3):
        tgl = tgl_nm + timedelta(days=i)
        print(f"  Memeriksa {tgl} ...", end=' ')

        hari = {
            'tanggal':        str(tgl),
            'lolos_mabims':   False,
            'dilewati':       False,
            'alasan_lewat':   None,
            'maghrib_wib':    None,
            'maghrib_utc':    None,
            'moonset_wib':    None,
            'moonset_utc':    None,
            'best_time_wib':  None,
            'best_time_utc':  None,
            'umur_jam':       None,
            'mabims_jakarta': None,
            'visibilitas':    None,
            'multilokasi':    None,
            'scan_indonesia': None,
        }

        mgh = cari_waktu_maghrib(tgl, ts, eph, topos_jakarta)
        if mgh is None:
            hari['dilewati']     = True
            hari['alasan_lewat'] = 'Tidak ditemukan waktu maghrib'
            hari_list.append(hari)
            print("LEWAT (no maghrib)")
            continue

        umur_jam = (to_utc_naive(mgh) - nm_naive).total_seconds() / 3600
        if umur_jam < 0:
            hari['dilewati']     = True
            hari['alasan_lewat'] = 'Umur bulan negatif (ijtimak setelah maghrib)'
            hari['maghrib_wib']  = mgh.astimezone(TZ_WIB).strftime('%H:%M WIB')
            hari['maghrib_utc']  = mgh.strftime('%H:%M UTC')
            hari['umur_jam']     = round(umur_jam, 2)
            hari_list.append(hari)
            print("LEWAT (umur negatif)")
            continue

        mset = cari_waktu_moonset_after_maghrib(mgh, ts, eph, topos_jakarta)
        best = cari_best_time(mgh, mset)

        hari['maghrib_wib'] = mgh.astimezone(TZ_WIB).strftime('%H:%M WIB')
        hari['maghrib_utc'] = mgh.strftime('%H:%M UTC')
        hari['moonset_wib'] = mset.astimezone(TZ_WIB).strftime('%H:%M WIB') if mset else None
        hari['moonset_utc'] = mset.strftime('%H:%M UTC') if mset else None
        hari['best_time_wib']= best.astimezone(TZ_WIB).strftime('%H:%M WIB') if best else None
        hari['best_time_utc']= best.strftime('%H:%M UTC') if best else None
        hari['umur_jam']     = round(umur_jam, 2)

        # MABIMS Jakarta
        pos_mgh = hitung_bulan_pada_waktu(mgh, ts, eph, lokasi_geo_jakarta)
        mab_jkt = cek_mabims(tgl, pos_mgh['alt_ref'], pos_mgh['elong_geo'], umur_jam)
        mab_jkt['alt']       = round(pos_mgh['alt_ref'], 3)
        mab_jkt['elong_geo'] = round(pos_mgh['elong_geo'], 3)
        mab_jkt['umur']      = round(umur_jam, 2)
        hari['mabims_jakarta'] = mab_jkt

        # Visibilitas Yallop/Odeh (Jakarta, best time)
        hari['visibilitas'] = hitung_visibilitas(best, ts, eph, lokasi_geo_jakarta)

        # Multi-lokasi nasional
        lokasi_lolos = []
        for lok in LOKASI_INDONESIA:
            res = cek_lokasi(tgl, nm_utc, lok, ts, eph)
            if res:
                lokasi_lolos.append(res)

        hari['multilokasi'] = {
            'n_lokasi':    len(lokasi_lolos),
            'lokasi':      lokasi_lolos,
        }

        lolos_nasional = len(lokasi_lolos) > 0
        hari['lolos_mabims'] = lolos_nasional

        if lolos_nasional:
            hari['scan_indonesia'] = scan_visibilitas_indonesia(tgl, ts, eph)
            nama_lolos = [l['nama'] for l in lokasi_lolos]
            print(f"✅ LOLOS ({len(lokasi_lolos)} lok: {', '.join(nama_lolos[:3])}{'...' if len(nama_lolos)>3 else ''})")
        else:
            print("❌ Tidak lolos")

        hari_list.append(hari)

        if lolos_nasional:
            tanggal_1 = tgl + timedelta(days=1)
            hari_lolos_obj = hari
            break
    else:
        tanggal_1      = tgl_nm + timedelta(days=start_i + 3)
        hari_lolos_obj = None
        print(f"⚠️  Istikmal → {tanggal_1}")

    # Shortcut ringkas
    rk = hari_lolos_obj
    vis = rk['visibilitas'] if rk else None
    mab = rk['mabims_jakarta'] if rk else None
    multi = rk['multilokasi'] if rk else None

    return {
        'tanggal_awal':       str(tanggal_1),
        'ijtimak_wib':        nm_wib.strftime('%d-%m-%Y %H:%M WIB'),
        'ijtimak_tgl_lokal':  str(tgl_nm),
        'ijtimak_posisi':     ijtimak_posisi,
        'istikmal':           hari_lolos_obj is None,
        'mabims_lolos':       hari_lolos_obj is not None,
        'hari_diperiksa':     hari_list,
        'scan_indonesia':     rk['scan_indonesia'] if rk else None,
        'ringkas': {
            'tanggal':        str(tanggal_1),
            'ijtimak':        nm_wib.strftime('%d-%m-%Y %H:%M WIB'),
            'maghrib':        rk['maghrib_wib']           if rk else None,
            'moonset':        rk['moonset_wib']           if rk else None,
            'best_time':      rk['best_time_wib']         if rk else None,
            'umur_jam':       rk['umur_jam']              if rk else None,
            'mabims_label':   mab['label']                if mab else None,
            'alt':            mab['alt']                  if mab else None,
            'alt_ok':         mab['alt_ok']               if mab else None,
            'elong_geo':      mab['elong_geo']            if mab else None,
            'elong_ok':       mab['elong_ok']             if mab else None,
            'arcv':           vis['arcv']                 if vis else None,
            'elongasi_top':   vis['elongasi_top']         if vis else None,
            'lebar_sabit':    vis['lebar_sabit_menit']    if vis else None,
            'illumination':   vis['illumination_pct']     if vis else None,
            'yallop_q':       vis['yallop']['q']          if vis else None,
            'yallop_klas':    vis['yallop']['kelas']      if vis else None,
            'yallop_desk':    vis['yallop']['deskripsi']  if vis else None,
            'odeh_v':         vis['odeh']['v']            if vis else None,
            'odeh_klas':      vis['odeh']['kelas']        if vis else None,
            'odeh_desk':      vis['odeh']['deskripsi']    if vis else None,
            'prob':           vis['probabilitas_pct']     if vis else None,
            'kontras':        vis['kontras']              if vis else None,
            'n_lokasi_lolos': multi['n_lokasi']           if multi else 0,
            'lokasi_lolos':   multi['lokasi']             if multi else [],
        },
    }

# ===================================================================
# Main (CLI)
# ===================================================================
def main():
    try:
        tahun = int(input("Masukkan tahun Hijriah: "))
    except ValueError:
        print("Tahun harus berupa angka."); return

    tahun_m = Hijri(tahun, 1, 1).to_gregorian().year
    dt      = delta_t_approx(tahun_m)
    print(f"Delta-T: {dt:.1f} detik | Ephemeris: {EPH_USED}")
    print(f"Evaluasi {len(LOKASI_INDONESIA)} lokasi Indonesia\n")

    earth         = eph['earth']
    topos_jakarta = wgs84.latlon(LATITUDE, LONGITUDE, elevation_m=ELEVATION)
    lokasi_jakarta= earth + topos_jakarta

    try:
        r = hitung_awal_bulan_hijriah(tahun, 9,  ts, eph, topos_jakarta, lokasi_jakarta)
        s = hitung_awal_bulan_hijriah(tahun, 10, ts, eph, topos_jakarta, lokasi_jakarta)

        print(f"\n=== HASIL AKHIR ===")
        print(f"1 Ramadan {tahun} H : {r['tanggal_awal']}")
        print(f"1 Syawal  {tahun} H : {s['tanggal_awal']}")
        print("\nCatatan: Simulasi hisab multi-lokasi. Keputusan resmi mengikuti Sidang Isbat Kemenag RI.")
    except Exception as ex:
        print(f"Error: {ex}")
        traceback.print_exc()

if __name__ == "__main__":
    main()

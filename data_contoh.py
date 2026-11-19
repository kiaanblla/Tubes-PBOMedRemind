"""Mengisi data contoh seperti pada mockup, untuk mencoba tampilan.

Jalankan:  python data_contoh.py
Lalu masuk dengan:  demo / demo12345
"""
import os
from datetime import date, time, timedelta

from models.database_manager import DatabaseManager
from models.jadwal_pengingat import JadwalPengingat
from models.obat_rutin import ObatRutin
from models.obat_temporer import ObatTemporer
from models.pengguna import Pengguna
from models.riwayat_konsumsi import RiwayatKonsumsi

USERNAME = "demo"
PASSWORD = "demo12345"


def buat_data_contoh(db, hari=None):
    """Buat pengguna 'demo' beserta obat, jadwal, dan dua dosis yang sudah
    diminum pada tanggal 'hari'. Jika pengguna sudah ada, dikembalikan apa adanya."""
    hari = hari or date.today()
    ada = db.ambil_pengguna_by_username(USERNAME)
    if ada is not None:
        return ada

    pengguna = db.tambah_pengguna(Pengguna.daftar(USERNAME, PASSWORD))
    uid = pengguna.id_pengguna

    iuvox = db.tambah_obat(
        uid, ObatRutin(None, "Iuvox", "50 mg", 1, "tablet", 30))
    amoksisilin = db.tambah_obat(
        uid, ObatTemporer(None, "Amoksisilin", "500 mg", 2, "kapsul", 21,
                          hari - timedelta(days=2), hari + timedelta(days=4)))
    amlodipin = db.tambah_obat(
        uid, ObatRutin(None, "Amlodipin", "5 mg", 1, "tablet", 4))
    vitamin_c = db.tambah_obat(
        uid, ObatRutin(None, "Vitamin C", "", 1, "tablet", 40))

    jadwal = {}
    for obat, jam in [(iuvox, 7), (amoksisilin, 13), (amlodipin, 19), (vitamin_c, 21)]:
        jadwal[obat.nama] = db.tambah_jadwal(
            JadwalPengingat(None, obat, time(jam, 0)))

    for nama in ("Iuvox", "Amoksisilin"):
        slot = jadwal[nama].waktu_terjadwal_pada(hari)
        riwayat = db.tambah_riwayat(RiwayatKonsumsi(None, jadwal[nama], slot))
        riwayat.tandai_sudah_minum(slot + timedelta(minutes=2))
        db.ubah_riwayat(riwayat)

    return db.ambil_pengguna(uid)


if __name__ == "__main__":
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "medremind.db")
    db = DatabaseManager(path)
    buat_data_contoh(db)
    db.tutup()
    print(f"Data contoh siap. Masuk dengan: {USERNAME} / {PASSWORD}")
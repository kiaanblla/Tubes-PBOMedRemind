import os
import tempfile
import unittest
from datetime import date, datetime

from app import (buat_app, kelas_status, label_status, persen,
                 ringkas_stok)
from data_contoh import PASSWORD, USERNAME, buat_data_contoh
from models.database_manager import DatabaseManager
from models.obat_rutin import ObatRutin
from models.pengguna import Pengguna
from models.status_konsumsi import StatusKonsumsi

WAKTU = datetime(2026, 11, 12, 14, 0)   # Kamis, 12 November 2026, 14:00


class TestPembantuTampilan(unittest.TestCase):
    def test_label_dan_kelas_status(self):
        self.assertEqual(label_status(StatusKonsumsi.SUDAH_MINUM), "Sudah minum")
        self.assertEqual(label_status(StatusKonsumsi.TERLEWAT), "Terlewat")
        self.assertEqual(label_status(None), "Tidak tercatat")
        self.assertEqual(kelas_status(StatusKonsumsi.SUDAH_MINUM), "sudah")
        self.assertEqual(kelas_status(StatusKonsumsi.MENUNGGU), "menunggu")
        self.assertEqual(kelas_status(StatusKonsumsi.DITUNDA), "ditunda")
        self.assertEqual(kelas_status(StatusKonsumsi.TERLEWAT), "terlewat")
        self.assertEqual(kelas_status(None), "kosong")

    def test_ringkas_stok(self):
        def obat(nama):
            return ObatRutin(1, nama, "", 1, "tablet", 1)
        self.assertEqual(ringkas_stok([]), "Semua stok aman")
        self.assertEqual(ringkas_stok([obat("Amlodipin")]), "Amlodipin hampir habis")
        self.assertEqual(ringkas_stok([obat("A"), obat("B")]), "A dan B hampir habis")
        self.assertEqual(ringkas_stok([obat("A"), obat("B"), obat("C"), obat("D")]),
                         "A, B, dan 2 lainnya hampir habis")

    def test_persen(self):
        self.assertEqual(persen(2, 4), 50)
        self.assertEqual(persen(1, 3), 33)
        self.assertEqual(persen(0, 0), 0)


class DasarBeranda(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.path_db = os.path.join(self.folder.name, "uji.db")
        self.app = buat_app({"TESTING": True, "DATABASE": self.path_db,
                             "SECRET_KEY": "kunci-uji",
                             "WAKTU_SEKARANG": lambda: WAKTU})
        self.client = self.app.test_client()

    def tearDown(self):
        self.folder.cleanup()

    def masuk(self, username, password):
        self.client.get("/masuk")
        with self.client.session_transaction() as sesi:
            token = sesi["csrf_token"]
        return self.client.post("/masuk", data={
            "username": username, "password": password, "csrf_token": token})

    def halaman(self):
        r = self.client.get("/beranda")
        self.assertEqual(r.status_code, 200)
        return r.get_data(as_text=True)


class TestBerandaDenganData(DasarBeranda):
    def setUp(self):
        super().setUp()
        db = DatabaseManager(self.path_db)
        buat_data_contoh(db, hari=date(2026, 11, 12))
        db.tutup()
        self.masuk(USERNAME, PASSWORD)

    def test_sapaan_dan_tanggal(self):
        html = self.halaman()
        self.assertIn("Halo, demo", html)
        self.assertIn("Kamis, 12 November 2026", html)

    def test_kartu_ringkasan_sesuai_mockup(self):
        html = self.halaman()
        self.assertIn("19:00", html)                    # Berikutnya
        self.assertIn("Amlodipin 5 mg", html)
        self.assertIn("2/4", html)                      # Hari ini
        self.assertIn('max="4"', html)
        self.assertIn('value="2"', html)
        self.assertIn("1 obat", html)                   # Stok
        self.assertIn("Amlodipin hampir habis", html)

    def test_tabel_jadwal_hari_ini(self):
        html = self.halaman()
        for teks in ["Iuvox 50 mg", "Amoksisilin 500 mg", "Amlodipin 5 mg",
                     "Vitamin C", "2 kapsul", "1 tablet"]:
            self.assertIn(teks, html)
        self.assertEqual(html.count("lencana sudah"), 2)
        self.assertEqual(html.count("lencana menunggu"), 2)
        tabel = html[html.index("<tbody>"):]      # hanya bagian tabel
        urutan = [tabel.index(jam) for jam in ("07:00", "13:00", "19:00", "21:00")]
        self.assertEqual(urutan, sorted(urutan))

    def test_peringatan_beranda_bisa_dimatikan(self):
        db = DatabaseManager(self.path_db)
        pengguna = db.ambil_pengguna_by_username(USERNAME)
        pengguna.pengaturan.peringatan_beranda = False
        db.simpan_pengaturan(pengguna.id_pengguna, pengguna.pengaturan)
        db.tutup()
        html = self.halaman()
        self.assertNotIn("hampir habis", html)
        self.assertIn("2/4", html)

    def test_batas_stok_dari_pengaturan_dipakai(self):
        db = DatabaseManager(self.path_db)
        pengguna = db.ambil_pengguna_by_username(USERNAME)
        pengguna.pengaturan.batas_stok_menipis = 25
        db.simpan_pengaturan(pengguna.id_pengguna, pengguna.pengaturan)
        db.tutup()
        html = self.halaman()
        self.assertIn("2 obat", html)
        self.assertIn("Amoksisilin dan Amlodipin hampir habis", html)

    def test_data_contoh_tidak_ganda(self):
        db = DatabaseManager(self.path_db)
        buat_data_contoh(db, hari=date(2026, 11, 12))
        pengguna = db.ambil_pengguna_by_username(USERNAME)
        self.assertEqual(len(pengguna.daftar_obat), 4)
        db.tutup()


class TestBerandaKosong(DasarBeranda):
    def test_pengguna_baru_tanpa_jadwal(self):
        db = DatabaseManager(self.path_db)
        db.tambah_pengguna(Pengguna.daftar("siti.n", "rahasia123"))
        db.tutup()
        self.masuk("siti.n", "rahasia123")
        html = self.halaman()
        self.assertIn("Halo, siti.n", html)
        self.assertIn("0/0", html)
        self.assertIn("Tidak ada jadwal berikutnya", html)
        self.assertIn("Semua stok aman", html)
        self.assertIn("Belum ada jadwal untuk hari ini", html)

    def test_butuh_login(self):
        self.assertEqual(self.client.get("/beranda").status_code, 302)


if __name__ == "__main__":
    unittest.main()
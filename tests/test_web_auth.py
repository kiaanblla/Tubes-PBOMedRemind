import os
import tempfile
import unittest
from datetime import date

from app import buat_app, tanggal_indonesia
from models.database_manager import DatabaseManager


class DasarWeb(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.path_db = os.path.join(self.folder.name, "uji.db")
        self.app = buat_app({"TESTING": True, "DATABASE": self.path_db,
                             "SECRET_KEY": "kunci-uji"})
        self.client = self.app.test_client()

    def tearDown(self):
        self.folder.cleanup()

    def token(self, client=None):
        """Ambil token CSRF dari sesi; buka halaman yang menampilkannya bila perlu."""
        client = client or self.client
        for halaman in (None, "/masuk", "/beranda"):
            if halaman:
                client.get(halaman)
            with client.session_transaction() as sesi:
                if "csrf_token" in sesi:
                    return sesi["csrf_token"]
        raise AssertionError("Token CSRF tidak ditemukan.")

    def kirim(self, url, data, client=None, **kw):
        client = client or self.client
        data = dict(data, csrf_token=self.token(client))
        return client.post(url, data=data, **kw)

    def daftar(self, username="budi.s", password="rahasia123"):
        return self.kirim("/daftar", {"username": username, "password": password})


class TestHalaman(DasarWeb):
    def test_tanggal_indonesia(self):
        self.assertEqual(tanggal_indonesia(date(2026, 11, 12)), "Kamis, 12 November 2026")
        self.assertEqual(tanggal_indonesia(date(2026, 1, 4)), "Minggu, 4 Januari 2026")

    def test_root_dan_beranda_butuh_login(self):
        self.assertEqual(self.client.get("/").headers["Location"], "/masuk")
        r = self.client.get("/beranda")
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.headers["Location"], "/masuk")

    def test_halaman_masuk_dan_daftar_tampil(self):
        masuk = self.client.get("/masuk")
        self.assertEqual(masuk.status_code, 200)
        self.assertIn("Pengingat Minum Obat", masuk.get_data(as_text=True))
        daftar = self.client.get("/daftar")
        self.assertEqual(daftar.status_code, 200)
        self.assertIn('name="csrf_token"', daftar.get_data(as_text=True))


class TestDaftar(DasarWeb):
    def test_daftar_berhasil_langsung_masuk(self):
        r = self.daftar()
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.headers["Location"], "/beranda")
        halaman = self.client.get("/beranda")
        self.assertEqual(halaman.status_code, 200)
        self.assertIn("Halo, budi.s", halaman.get_data(as_text=True))
        db = DatabaseManager(self.path_db)
        self.assertIsNotNone(db.ambil_pengguna_by_username("budi.s"))
        db.tutup()

    def test_daftar_gagal_menampilkan_pesan(self):
        kasus = [("budi.s", "pendek", "minimal 8 karakter"),
                 ("b", "rahasia123", "Nama pengguna"),
                 ("budi s", "rahasia123", "Nama pengguna")]
        for username, password, kata in kasus:
            with self.subTest(username=username):
                r = self.daftar(username, password)
                self.assertEqual(r.status_code, 400)
                self.assertIn(kata, r.get_data(as_text=True))

    def test_username_ganda_ditolak(self):
        self.daftar()
        klien_lain = self.app.test_client()
        r = self.kirim("/daftar", {"username": "BUDI.S", "password": "rahasia123"},
                       client=klien_lain)
        self.assertEqual(r.status_code, 400)
        self.assertIn("sudah dipakai", r.get_data(as_text=True))

    def test_password_tidak_tersimpan_polos(self):
        self.daftar()
        db = DatabaseManager(self.path_db)
        tersimpan = db.ambil_pengguna_by_username("budi.s").password_hash
        db.tutup()
        self.assertNotIn("rahasia123", tersimpan)


class TestMasukKeluar(DasarWeb):
    def setUp(self):
        super().setUp()
        self.daftar()
        self.kirim("/keluar", {})      # daftar otomatis login; keluar dulu

    def test_masuk_berhasil_tidak_peka_huruf_besar(self):
        r = self.kirim("/masuk", {"username": " BUDI.S ", "password": "rahasia123"})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.headers["Location"], "/beranda")
        self.assertEqual(self.client.get("/beranda").status_code, 200)

    def test_masuk_salah_pesan_umum(self):
        for username, password in [("budi.s", "salah"), ("tidakada", "rahasia123")]:
            with self.subTest(username=username):
                r = self.kirim("/masuk", {"username": username, "password": password})
                self.assertEqual(r.status_code, 401)
                self.assertIn("Nama pengguna atau kata sandi salah",
                              r.get_data(as_text=True))
                self.assertEqual(self.client.get("/beranda").status_code, 302)

    def test_sudah_masuk_dialihkan_dari_halaman_masuk(self):
        self.kirim("/masuk", {"username": "budi.s", "password": "rahasia123"})
        self.assertEqual(self.client.get("/masuk").headers["Location"], "/beranda")
        self.assertEqual(self.client.get("/daftar").headers["Location"], "/beranda")

    def test_keluar(self):
        self.kirim("/masuk", {"username": "budi.s", "password": "rahasia123"})
        r = self.kirim("/keluar", {})
        self.assertEqual(r.headers["Location"], "/masuk")
        self.assertEqual(self.client.get("/beranda").status_code, 302)
        self.assertEqual(self.client.get("/keluar").status_code, 405)  # GET tidak boleh


class TestKeamanan(DasarWeb):
    def test_post_tanpa_csrf_ditolak(self):
        r = self.client.post("/daftar", data={"username": "budi.s",
                                              "password": "rahasia123"})
        self.assertEqual(r.status_code, 400)
        db = DatabaseManager(self.path_db)
        self.assertIsNone(db.ambil_pengguna_by_username("budi.s"))
        db.tutup()

    def test_csrf_salah_ditolak(self):
        self.token()
        r = self.client.post("/masuk", data={"username": "a", "password": "b",
                                             "csrf_token": "palsu"})
        self.assertEqual(r.status_code, 400)

    def test_halaman_dengan_xss_di_username_di_escape(self):
        r = self.kirim("/masuk", {"username": "<script>x</script>", "password": "y"})
        self.assertEqual(r.status_code, 401)
        self.assertNotIn("<script>x</script>", r.get_data(as_text=True))

    def test_pengguna_dihapus_sesi_tidak_berlaku(self):
        self.daftar()
        db = DatabaseManager(self.path_db)
        db.hapus_pengguna(db.ambil_pengguna_by_username("budi.s").id_pengguna)
        db.tutup()
        self.assertEqual(self.client.get("/beranda").status_code, 302)


if __name__ == "__main__":
    unittest.main()
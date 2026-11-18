import unittest
from datetime import date

from models.obat_rutin import ObatRutin
from models.obat_temporer import ObatTemporer
from models.pengaturan import Pengaturan
from models.pengguna import Pengguna


def buat_pengguna():
    p = Pengguna.daftar("budi.s", "rahasia123", id_pengguna=1)
    p.tambah_obat(ObatRutin(1, "Amlodipin", "5 mg", 1, "tablet", 4))
    p.tambah_obat(ObatTemporer(2, "Amoksisilin", "500 mg", 2, "kapsul", 21,
                               date(2026, 11, 8), date(2026, 11, 14)))
    p.tambah_obat(ObatRutin(3, "Iuvox", "50 mg", 1, "tablet", 30))
    return p


class TestPengaturan(unittest.TestCase):
    def test_nilai_bawaan(self):
        s = Pengaturan()
        self.assertTrue(s.pengingat_bersuara)
        self.assertEqual(s.jenis_suara, "Lonceng lembut")
        self.assertEqual(s.volume, 70)
        self.assertEqual(s.jumlah_bunyi, 4)
        self.assertEqual(s.durasi_tunda, 10)
        self.assertEqual(s.batas_stok_menipis, 5)
        self.assertEqual(s.periode_bawaan, "7 hari terakhir")
        self.assertTrue(s.sertakan_keterangan)

    def test_nilai_tidak_valid_ditolak(self):
        kasus = [
            ("volume", 101), ("volume", -1), ("volume", "keras"),
            ("jumlah_bunyi", 9), ("durasi_tunda", 7),
            ("jenis_suara", "Sirene"), ("batas_stok_menipis", -1),
            ("periode_bawaan", "1 tahun"),
        ]
        for nama, nilai in kasus:
            with self.subTest(nama=nama, nilai=nilai):
                with self.assertRaises(ValueError):
                    setattr(Pengaturan(), nama, nilai)

    def test_to_dict_dan_from_dict(self):
        asli = Pengaturan(volume=50, jumlah_bunyi=3, batas_stok_menipis=10)
        salinan = Pengaturan.from_dict(asli.to_dict())
        self.assertEqual(salinan.to_dict(), asli.to_dict())
        self.assertEqual(salinan.volume, 50)


class TestPengguna(unittest.TestCase):
    def test_daftar_valid_dan_password_di_hash(self):
        p = Pengguna.daftar("  Budi.S ", "rahasia123")
        self.assertEqual(p.username, "budi.s")
        self.assertNotEqual(p.password_hash, "rahasia123")
        self.assertIsInstance(p.pengaturan, Pengaturan)

    def test_username_tidak_valid(self):
        for nama in ["", "ab", "budi s", "a" * 31, "budi@s"]:
            with self.subTest(nama=nama):
                with self.assertRaises(ValueError):
                    Pengguna.daftar(nama, "rahasia123")

    def test_password_terlalu_pendek(self):
        with self.assertRaises(ValueError):
            Pengguna.daftar("budi.s", "1234567")

    def test_verifikasi_dan_ubah_password(self):
        p = Pengguna.daftar("budi.s", "rahasia123")
        self.assertTrue(p.verifikasi_password("rahasia123"))
        self.assertFalse(p.verifikasi_password("salah"))
        with self.assertRaises(ValueError):
            p.ubah_password("salah", "barubaru123")
        with self.assertRaises(ValueError):
            p.ubah_password("rahasia123", "pendek")
        p.ubah_password("rahasia123", "barubaru123")
        self.assertTrue(p.verifikasi_password("barubaru123"))
        self.assertFalse(p.verifikasi_password("rahasia123"))

    def test_kelola_obat(self):
        p = buat_pengguna()
        self.assertEqual(len(p.daftar_obat), 3)
        self.assertEqual(p.cari_obat(2).nama, "Amoksisilin")
        self.assertIsNone(p.cari_obat(99))
        p.hapus_obat(2)
        self.assertEqual(len(p.daftar_obat), 2)
        with self.assertRaises(ValueError):
            p.hapus_obat(99)
        with self.assertRaises(TypeError):
            p.tambah_obat("bukan obat")

    def test_obat_menipis_ikut_pengaturan_global(self):        # T-07
        p = buat_pengguna()
        self.assertEqual([o.id_obat for o in p.obat_menipis()], [1])
        p.pengaturan.batas_stok_menipis = 25
        self.assertEqual([o.id_obat for o in p.obat_menipis()], [1, 2])
        self.assertTrue(p.cari_obat(3).is_menipis(30))
        self.assertFalse(p.cari_obat(3).is_menipis(29))

    def test_obat_aktif_polimorfisme(self):
        p = buat_pengguna()

        def ids(hari):
            return [o.id_obat for o in p.obat_aktif(hari)]

        self.assertEqual(ids(date(2026, 11, 12)), [1, 2, 3])
        self.assertEqual(ids(date(2026, 11, 20)), [1, 3])


if __name__ == "__main__":
    unittest.main()
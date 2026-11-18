import unittest
from datetime import date

from models.obat import Obat
from models.obat_rutin import ObatRutin
from models.obat_temporer import ObatTemporer


class TestObat(unittest.TestCase):
    def test_obat_abstract_tidak_bisa_diinstansiasi(self):
        with self.assertRaises(TypeError):
            Obat(1, "X", "1 mg", 1, "tablet", 10)

    def test_stok_negatif_ditolak(self):                      # T-03
        with self.assertRaises(ValueError):
            ObatRutin(1, "Iuvox", "50 mg", 1, "tablet", -1)

    def test_kurangi_stok_dan_menipis(self):
        obat = ObatRutin(1, "Amlodipin", "5 mg", 1, "tablet", 6)
        self.assertFalse(obat.is_menipis())
        obat.kurangi_stok()
        self.assertEqual(obat.stok, 5)
        self.assertTrue(obat.is_menipis())

    def test_tanggal_selesai_lebih_awal_ditolak(self):        # T-02
        with self.assertRaises(ValueError):
            ObatTemporer(2, "Amoksisilin", "500 mg", 2, "kapsul", 21,
                         date(2026, 11, 10), date(2026, 11, 1))

    def test_polimorfisme_is_aktif(self):                     # T-10
        rutin = ObatRutin(1, "Iuvox", "50 mg", 1, "tablet", 30)
        temp = ObatTemporer(2, "Amoksisilin", "500 mg", 2, "kapsul", 21,
                            date(2026, 11, 8), date(2026, 11, 14))
        self.assertTrue(rutin.is_aktif(date(2030, 1, 1)))
        self.assertTrue(temp.is_aktif(date(2026, 11, 12)))
        self.assertFalse(temp.is_aktif(date(2026, 11, 15)))
        self.assertEqual(temp.hitung_sisa_hari(date(2026, 11, 12)), 2)


if __name__ == "__main__":
    unittest.main()
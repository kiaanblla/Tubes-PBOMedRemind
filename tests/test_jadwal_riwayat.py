import unittest
from datetime import date, datetime, time

from models.jadwal_pengingat import JadwalPengingat
from models.obat_rutin import ObatRutin
from models.obat_temporer import ObatTemporer
from models.riwayat_konsumsi import RiwayatKonsumsi
from models.status_konsumsi import StatusKonsumsi


def buat_jadwal(aktif=True):
    obat = ObatRutin(1, "Amlodipin", "5 mg", 1, "tablet", 10)
    return JadwalPengingat(1, obat, time(19, 0), aktif)


def buat_riwayat():
    return RiwayatKonsumsi(1, buat_jadwal(), datetime(2026, 11, 12, 19, 0))


class TestJadwalPengingat(unittest.TestCase):
    def test_parse_jam_valid(self):
        self.assertEqual(JadwalPengingat.parse_jam("07:00"), time(7, 0))
        self.assertEqual(JadwalPengingat.parse_jam(" 19:30 "), time(19, 30))

    def test_parse_jam_tidak_valid(self):
        for teks in ["25:00", "abc", "7.00", ""]:
            with self.assertRaises(ValueError):
                JadwalPengingat.parse_jam(teks)

    def test_waktu_tiba(self):
        jadwal = buat_jadwal()
        self.assertFalse(jadwal.waktu_tiba(datetime(2026, 11, 12, 18, 59)))
        self.assertTrue(jadwal.waktu_tiba(datetime(2026, 11, 12, 19, 0)))

    def test_jadwal_nonaktif_tidak_tiba(self):
        jadwal = buat_jadwal(aktif=False)
        self.assertFalse(jadwal.waktu_tiba(datetime(2026, 11, 12, 19, 0)))

    def test_obat_temporer_kedaluwarsa_tidak_tiba(self):        # T-08
        obat = ObatTemporer(2, "Amoksisilin", "500 mg", 2, "kapsul", 21,
                            date(2026, 11, 8), date(2026, 11, 14))
        jadwal = JadwalPengingat(2, obat, time(13, 0))
        self.assertTrue(jadwal.waktu_tiba(datetime(2026, 11, 12, 13, 0)))
        self.assertFalse(jadwal.waktu_tiba(datetime(2026, 11, 15, 13, 0)))


class TestRiwayatKonsumsi(unittest.TestCase):
    def test_alur_tunda_lalu_sudah_minum(self):                 # T-06
        r = buat_riwayat()
        r.tunda(10, datetime(2026, 11, 12, 19, 0))
        self.assertEqual(r.status, StatusKonsumsi.DITUNDA)
        self.assertEqual(r.ditunda_sampai, datetime(2026, 11, 12, 19, 10))
        self.assertEqual(r.keterangan, "Ditunda 10 menit")
        r.tandai_sudah_minum(datetime(2026, 11, 12, 19, 12))
        self.assertEqual(r.status, StatusKonsumsi.SUDAH_MINUM)
        self.assertEqual(r.waktu_aktual, datetime(2026, 11, 12, 19, 12))

    def test_status_final_tidak_bisa_diubah(self):
        r = buat_riwayat()
        r.tandai_sudah_minum()
        with self.assertRaises(ValueError):
            r.tunda(10)
        with self.assertRaises(ValueError):
            r.tandai_terlewat()

    def test_hitung_kepatuhan(self):
        daftar = []
        for _ in range(21):
            r = buat_riwayat()
            r.tandai_sudah_minum()
            daftar.append(r)
        for _ in range(6):
            r = buat_riwayat()
            r.tandai_terlewat()
            daftar.append(r)
        self.assertEqual(RiwayatKonsumsi.hitung_kepatuhan(daftar), 78)
        self.assertEqual(RiwayatKonsumsi.hitung_kepatuhan([]), 0)


if __name__ == "__main__":
    unittest.main()
import os
import tempfile
import unittest
from datetime import date, datetime, time

from models.database_manager import DatabaseManager
from models.jadwal_pengingat import JadwalPengingat
from models.obat_rutin import ObatRutin
from models.obat_temporer import ObatTemporer
from models.pengguna import Pengguna
from models.riwayat_konsumsi import RiwayatKonsumsi
from models.status_konsumsi import StatusKonsumsi


class DasarDatabase(unittest.TestCase):
    def setUp(self):
        self.db = DatabaseManager(":memory:")
        self.user = self.db.tambah_pengguna(
            Pengguna.daftar("budi.s", "rahasia123"))

    def tearDown(self):
        self.db.tutup()

    def obat_rutin(self, nama="Amlodipin", stok=4):
        return self.db.tambah_obat(
            self.user.id_pengguna,
            ObatRutin(None, nama, "5 mg", 1, "tablet", stok))

    def obat_temporer(self):
        return self.db.tambah_obat(
            self.user.id_pengguna,
            ObatTemporer(None, "Amoksisilin", "500 mg", 2, "kapsul", 21,
                         date(2026, 11, 8), date(2026, 11, 14)))

    def jadwal(self, obat, jam="19:00"):
        return self.db.tambah_jadwal(
            JadwalPengingat(None, obat, JadwalPengingat.parse_jam(jam)))


class TestPengguna(DasarDatabase):
    def test_tambah_dan_ambil_pengguna(self):
        self.assertIsNotNone(self.user.id_pengguna)
        self.assertEqual(self.user.pengaturan.durasi_tunda, 10)
        lagi = self.db.ambil_pengguna_by_username("  BUDI.S ")
        self.assertEqual(lagi.id_pengguna, self.user.id_pengguna)
        self.assertTrue(lagi.verifikasi_password("rahasia123"))
        self.assertIsNone(self.db.ambil_pengguna_by_username("tidakada"))
        self.assertIsNone(self.db.ambil_pengguna(999))

    def test_username_ganda_ditolak(self):
        with self.assertRaises(ValueError):
            self.db.tambah_pengguna(Pengguna.daftar("budi.s", "passwordlain1"))

    def test_ubah_password_dan_pengaturan(self):
        self.user.ubah_password("rahasia123", "barubaru123")
        self.db.ubah_pengguna(self.user)
        self.user.pengaturan.volume = 40
        self.user.pengaturan.batas_stok_menipis = 8
        self.user.pengaturan.sertakan_keterangan = False
        self.db.simpan_pengaturan(self.user.id_pengguna, self.user.pengaturan)
        lagi = self.db.ambil_pengguna(self.user.id_pengguna)
        self.assertTrue(lagi.verifikasi_password("barubaru123"))
        self.assertEqual(lagi.pengaturan.volume, 40)
        self.assertEqual(lagi.pengaturan.batas_stok_menipis, 8)
        self.assertFalse(lagi.pengaturan.sertakan_keterangan)


class TestObat(DasarDatabase):
    def test_polimorfik_round_trip_dan_dimuat_ke_pengguna(self):
        rutin = self.obat_rutin()
        temp = self.obat_temporer()
        self.assertIsInstance(self.db.ambil_obat(rutin.id_obat), ObatRutin)
        lagi = self.db.ambil_obat(temp.id_obat)
        self.assertIsInstance(lagi, ObatTemporer)
        self.assertEqual(lagi.tanggal_selesai, date(2026, 11, 14))
        pengguna = self.db.ambil_pengguna(self.user.id_pengguna)
        self.assertEqual([o.id_obat for o in pengguna.daftar_obat],
                         [rutin.id_obat, temp.id_obat])
        self.assertEqual(len(pengguna.obat_aktif(date(2026, 11, 20))), 1)

    def test_ubah_dan_hapus_obat(self):
        obat = self.obat_rutin()
        obat.kurangi_stok()
        self.db.ubah_obat(obat)
        self.assertEqual(self.db.ambil_obat(obat.id_obat).stok, 3)
        baru = ObatTemporer(obat.id_obat, "Amlodipin", "5 mg", 1, "tablet", 3,
                            date(2026, 11, 1), date(2026, 11, 30))
        self.db.ubah_obat(baru)           # ganti kategori
        self.assertIsInstance(self.db.ambil_obat(obat.id_obat), ObatTemporer)
        self.db.hapus_obat(obat.id_obat)
        self.assertIsNone(self.db.ambil_obat(obat.id_obat))
        with self.assertRaises(ValueError):
            self.db.hapus_obat(obat.id_obat)
        with self.assertRaises(ValueError):
            self.db.ubah_obat(baru)

    def test_obat_untuk_pengguna_tidak_ada_ditolak(self):
        with self.assertRaises(ValueError):
            self.db.tambah_obat(
                999, ObatRutin(None, "X", "1 mg", 1, "tablet", 1))


class TestJadwal(DasarDatabase):
    def test_jadwal_crud(self):
        obat = self.obat_rutin()
        j2 = self.jadwal(obat, "19:00")
        j1 = self.jadwal(obat, "07:00")
        self.assertEqual([j.waktu_text() for j in self.db.daftar_jadwal(obat.id_obat)],
                         ["07:00", "19:00"])
        j1.aktif = False
        j1.waktu_minum = time(8, 30)
        self.db.ubah_jadwal(j1)
        lagi = self.db.ambil_jadwal(j1.id_jadwal)
        self.assertEqual(lagi.waktu_text(), "08:30")
        self.assertFalse(lagi.aktif)
        self.assertEqual(len(self.db.daftar_jadwal_pengguna(self.user.id_pengguna)), 2)
        self.db.hapus_jadwal(j2.id_jadwal)
        self.assertIsNone(self.db.ambil_jadwal(j2.id_jadwal))
        with self.assertRaises(ValueError):
            self.db.hapus_jadwal(j2.id_jadwal)


class TestRiwayat(DasarDatabase):
    def test_round_trip_dan_unik(self):
        jadwal = self.jadwal(self.obat_rutin())
        waktu = datetime(2026, 11, 12, 19, 0)
        r = self.db.tambah_riwayat(RiwayatKonsumsi(None, jadwal, waktu))
        self.assertEqual(r.status, StatusKonsumsi.MENUNGGU)
        r.tunda(10, waktu)
        self.db.ubah_riwayat(r)
        lagi = self.db.ambil_riwayat(r.id_riwayat)
        self.assertEqual(lagi.status, StatusKonsumsi.DITUNDA)
        self.assertEqual(lagi.ditunda_sampai, datetime(2026, 11, 12, 19, 10))
        self.assertEqual(lagi.keterangan, "Ditunda 10 menit")
        lagi.tandai_sudah_minum(datetime(2026, 11, 12, 19, 12))
        self.db.ubah_riwayat(lagi)
        akhir = self.db.ambil_riwayat(r.id_riwayat)
        self.assertEqual(akhir.status, StatusKonsumsi.SUDAH_MINUM)
        self.assertEqual(akhir.waktu_aktual, datetime(2026, 11, 12, 19, 12))
        self.assertIsNone(akhir.ditunda_sampai)
        with self.assertRaises(ValueError):   # slot yang sama tidak boleh ganda
            self.db.tambah_riwayat(RiwayatKonsumsi(None, jadwal, waktu))

    def test_daftar_riwayat_filter_dan_kepatuhan(self):
        jadwal = self.jadwal(self.obat_rutin())
        for hari, status in [(10, "minum"), (11, "lewat"), (12, "minum")]:
            r = self.db.tambah_riwayat(RiwayatKonsumsi(
                None, jadwal, datetime(2026, 11, hari, 19, 0)))
            if status == "minum":
                r.tandai_sudah_minum(datetime(2026, 11, hari, 19, 1))
            else:
                r.tandai_terlewat(datetime(2026, 11, hari, 19, 40))
            self.db.ubah_riwayat(r)
        semua = self.db.daftar_riwayat(self.user.id_pengguna)
        self.assertEqual([r.waktu_terjadwal.day for r in semua], [12, 11, 10])
        sebagian = self.db.daftar_riwayat(
            self.user.id_pengguna, dari=datetime(2026, 11, 11, 0, 0),
            sampai=datetime(2026, 11, 11, 23, 59))
        self.assertEqual(len(sebagian), 1)
        self.assertEqual(RiwayatKonsumsi.hitung_kepatuhan(semua), 67)

    def test_hapus_obat_menghapus_jadwal_dan_riwayat(self):
        obat = self.obat_rutin()
        jadwal = self.jadwal(obat)
        r = self.db.tambah_riwayat(RiwayatKonsumsi(
            None, jadwal, datetime(2026, 11, 12, 19, 0)))
        self.db.hapus_obat(obat.id_obat)
        self.assertIsNone(self.db.ambil_jadwal(jadwal.id_jadwal))
        self.assertIsNone(self.db.ambil_riwayat(r.id_riwayat))


class TestPermanen(unittest.TestCase):
    def test_data_tetap_ada_setelah_ditutup(self):             # T-09
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "uji.db")
            db = DatabaseManager(path)
            user = db.tambah_pengguna(Pengguna.daftar("budi.s", "rahasia123"))
            obat = db.tambah_obat(user.id_pengguna,
                                  ObatRutin(None, "Iuvox", "50 mg", 1, "tablet", 30))
            db.tambah_jadwal(JadwalPengingat(None, obat, time(7, 0)))
            db.tutup()

            db2 = DatabaseManager(path)
            lagi = db2.ambil_pengguna_by_username("budi.s")
            self.assertEqual(lagi.daftar_obat[0].nama_lengkap(), "Iuvox 50 mg")
            self.assertEqual(len(db2.daftar_jadwal_pengguna(lagi.id_pengguna)), 1)
            db2.tutup()


if __name__ == "__main__":
    unittest.main()
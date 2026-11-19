import unittest
from datetime import date, datetime, time

from models.database_manager import DatabaseManager
from models.jadwal_pengingat import JadwalPengingat
from models.layanan_pengingat import LayananPengingat
from models.obat_rutin import ObatRutin
from models.obat_temporer import ObatTemporer
from models.pengguna import Pengguna
from models.status_konsumsi import StatusKonsumsi


def jam(h, m, s=0):
    return datetime(2026, 11, 12, h, m, s)


class DasarLayanan(unittest.TestCase):
    def setUp(self):
        self.db = DatabaseManager(":memory:")
        user = self.db.tambah_pengguna(Pengguna.daftar("budi.s", "rahasia123"))
        self.uid = user.id_pengguna
        self.amlodipin = self.db.tambah_obat(
            self.uid, ObatRutin(None, "Amlodipin", "5 mg", 1, "tablet", 4))
        self.amoksi = self.db.tambah_obat(
            self.uid, ObatTemporer(None, "Amoksisilin", "500 mg", 2, "kapsul", 21,
                                   date(2026, 11, 8), date(2026, 11, 14)))
        self.db.tambah_jadwal(JadwalPengingat(None, self.amlodipin, time(19, 0)))
        self.db.tambah_jadwal(JadwalPengingat(None, self.amoksi, time(13, 0)))
        self.layanan = LayananPengingat(self.db)

    def tearDown(self):
        self.db.tutup()

    def riwayat(self):
        return self.db.daftar_riwayat(self.uid)


class TestDering(DasarLayanan):
    def test_belum_waktunya_tidak_ada_pengingat(self):
        self.assertEqual(self.layanan.pengingat_aktif(self.uid, jam(12, 59)), [])
        self.assertEqual(self.riwayat(), [])

    def test_pengingat_muncul_dan_bunyi_bertambah(self):
        aktif = self.layanan.pengingat_aktif(self.uid, jam(13, 0, 10))
        self.assertEqual(len(aktif), 1)
        p = aktif[0]
        self.assertEqual(p.obat.nama_lengkap(), "Amoksisilin 500 mg")
        self.assertEqual((p.bunyi_ke, p.total_bunyi), (1, 4))
        self.assertEqual(p.detail_text(), "Dosis 2 kapsul · Jadwal 13:00")
        self.assertEqual(p.stok_text(), "Sisa stok 21 kapsul")
        p2 = self.layanan.pengingat_aktif(self.uid, jam(13, 1, 30))[0]
        self.assertEqual(p2.bunyi_ke, 2)
        self.assertEqual(
            p2.footer_text(),
            "Bunyi ke-2 dari 4 · otomatis Terlewat jika tidak ditanggapi")
        p4 = self.layanan.pengingat_aktif(self.uid, jam(13, 3, 59))[0]
        self.assertEqual(p4.bunyi_ke, 4)
        self.assertEqual(len(self.riwayat()), 1)      # tidak ganda

    def test_otomatis_terlewat_setelah_4_bunyi(self):
        self.layanan.pengingat_aktif(self.uid, jam(13, 0, 10))
        self.assertEqual(self.layanan.pengingat_aktif(self.uid, jam(13, 4)), [])
        r = self.riwayat()
        self.assertEqual(len(r), 1)
        self.assertEqual(r[0].status, StatusKonsumsi.TERLEWAT)
        self.assertEqual(r[0].keterangan, "Tidak ada respons")
        self.assertEqual(r[0].waktu_aktual, jam(13, 4))
        self.layanan.sinkronkan(self.uid, jam(13, 30))  # idempotent
        self.assertEqual(len(self.riwayat()), 1)

    def test_terlewat_dicatat_saat_halaman_dibuka_kembali(self):
        self.layanan.pengingat_aktif(self.uid, jam(13, 0, 10))
        self.layanan.sinkronkan(self.uid, jam(18, 0))   # tab ditutup lama
        r = self.riwayat()[0]
        self.assertEqual(r.status, StatusKonsumsi.TERLEWAT)
        self.assertEqual(r.waktu_aktual, jam(13, 4))     # batas siklus, bukan 18:00

    def test_pengingat_telat_dibuka_tidak_membuat_riwayat(self):
        self.assertEqual(self.layanan.pengingat_aktif(self.uid, jam(15, 0)), [])
        self.assertEqual(self.riwayat(), [])
        baris = self.layanan.jadwal_harian(self.uid, date(2026, 11, 12), jam(15, 0))
        self.assertEqual([b.status for b in baris],
                         [None, StatusKonsumsi.MENUNGGU])


class TestAksi(DasarLayanan):
    def test_sudah_minum_kurangi_stok(self):
        r = self.layanan.pengingat_aktif(self.uid, jam(13, 0, 10))[0].riwayat
        hasil = self.layanan.tandai_sudah_minum(self.uid, r.id_riwayat, jam(13, 1))
        self.assertEqual(hasil.status, StatusKonsumsi.SUDAH_MINUM)
        self.assertEqual(self.db.ambil_obat(self.amoksi.id_obat).stok, 19)
        self.assertEqual(self.layanan.pengingat_aktif(self.uid, jam(13, 2)), [])
        with self.assertRaises(ValueError):
            self.layanan.tandai_sudah_minum(self.uid, r.id_riwayat, jam(13, 3))
        self.assertEqual(self.db.ambil_obat(self.amoksi.id_obat).stok, 19)

    def test_tunda_lalu_bunyi_lagi_lalu_terlewat(self):
        r = self.layanan.pengingat_aktif(self.uid, jam(13, 0, 10))[0].riwayat
        hasil = self.layanan.tunda(self.uid, r.id_riwayat, jam(13, 1))
        self.assertEqual(hasil.status, StatusKonsumsi.DITUNDA)
        self.assertEqual(hasil.ditunda_sampai, jam(13, 11))
        self.assertEqual(hasil.keterangan, "Ditunda 10 menit")
        self.assertEqual(self.layanan.pengingat_aktif(self.uid, jam(13, 5)), [])
        lagi = self.layanan.pengingat_aktif(self.uid, jam(13, 11, 30))
        self.assertEqual(len(lagi), 1)
        self.assertEqual(lagi[0].bunyi_ke, 1)             # siklus baru
        self.assertEqual(self.layanan.pengingat_aktif(self.uid, jam(13, 15)), [])
        self.assertEqual(self.riwayat()[0].status, StatusKonsumsi.TERLEWAT)

    def test_ikut_pengaturan_jumlah_bunyi_dan_durasi_tunda(self):
        pengguna = self.db.ambil_pengguna(self.uid)
        pengguna.pengaturan.jumlah_bunyi = 2
        pengguna.pengaturan.durasi_tunda = 5
        self.db.simpan_pengaturan(self.uid, pengguna.pengaturan)
        p = self.layanan.pengingat_aktif(self.uid, jam(13, 0, 10))[0]
        self.assertEqual(p.total_bunyi, 2)
        hasil = self.layanan.tunda(self.uid, p.riwayat.id_riwayat, jam(13, 0, 30))
        self.assertEqual(hasil.ditunda_sampai, jam(13, 5, 30))
        self.assertEqual(self.layanan.pengingat_aktif(self.uid, jam(13, 8)), [])
        self.assertEqual(self.riwayat()[0].status, StatusKonsumsi.TERLEWAT)

    def test_stok_tidak_cukup_tetap_dicatat(self):
        obat = self.db.tambah_obat(
            self.uid, ObatRutin(None, "Vitamin C", "", 2, "tablet", 1))
        self.db.tambah_jadwal(JadwalPengingat(None, obat, time(21, 0)))
        p = self.layanan.pengingat_aktif(self.uid, jam(21, 0, 5))[0]
        self.layanan.tandai_sudah_minum(self.uid, p.riwayat.id_riwayat, jam(21, 1))
        self.assertEqual(self.db.ambil_obat(obat.id_obat).stok, 0)
        self.assertEqual(self.riwayat()[0].status, StatusKonsumsi.SUDAH_MINUM)

    def test_riwayat_pengguna_lain_ditolak(self):
        lain = self.db.tambah_pengguna(Pengguna.daftar("siti.n", "rahasia123"))
        r = self.layanan.pengingat_aktif(self.uid, jam(13, 0, 10))[0].riwayat
        with self.assertRaises(ValueError):
            self.layanan.tandai_sudah_minum(lain.id_pengguna, r.id_riwayat)
        with self.assertRaises(ValueError):
            self.layanan.tunda(lain.id_pengguna, r.id_riwayat)
        with self.assertRaises(ValueError):
            self.layanan.tunda(self.uid, 999)


class TestJadwalDanRingkasan(DasarLayanan):
    def test_ringkasan_beranda(self):
        p = self.layanan.pengingat_aktif(self.uid, jam(13, 0, 10))[0]
        self.layanan.tandai_sudah_minum(self.uid, p.riwayat.id_riwayat, jam(13, 1))
        ring = self.layanan.ringkasan_hari_ini(self.uid, jam(14, 0))
        self.assertEqual((ring.sudah_minum, ring.total), (1, 2))
        self.assertEqual(ring.berikutnya.jadwal.obat.nama, "Amlodipin")
        self.assertEqual(ring.berikutnya.waktu, jam(19, 0))
        self.assertEqual([o.nama for o in ring.obat_menipis], ["Amlodipin"])
        baris = self.layanan.jadwal_harian(self.uid, date(2026, 11, 12), jam(14, 0))
        self.assertEqual([b.status for b in baris],
                         [StatusKonsumsi.SUDAH_MINUM, StatusKonsumsi.MENUNGGU])

    def test_obat_nonaktif_tidak_muncul(self):
        self.amoksi.nonaktifkan()
        self.db.ubah_obat(self.amoksi)
        self.assertEqual(self.layanan.pengingat_aktif(self.uid, jam(13, 0, 10)), [])
        baris = self.layanan.jadwal_harian(self.uid, date(2026, 11, 12), jam(14, 0))
        self.assertEqual([b.jadwal.obat.nama for b in baris], ["Amlodipin"])
        self.amlodipin.nonaktifkan()
        self.db.ubah_obat(self.amlodipin)
        self.assertEqual(
            self.layanan.ringkasan_hari_ini(self.uid, jam(14, 0)).obat_menipis, [])

    def test_jadwal_hari_lalu(self):
        kemarin = datetime(2026, 11, 11, 13, 0, 10)
        self.layanan.pengingat_aktif(self.uid, kemarin)
        self.layanan.sinkronkan(self.uid, datetime(2026, 11, 11, 13, 5))
        baris = self.layanan.jadwal_harian(
            self.uid, date(2026, 11, 11), jam(9, 0))
        self.assertEqual([(b.jadwal.waktu_text(), b.status) for b in baris],
                         [("13:00", StatusKonsumsi.TERLEWAT), ("19:00", None)])


if __name__ == "__main__":
    unittest.main()
from collections import namedtuple
from datetime import datetime, time, timedelta

from models.pengingat_aktif import PengingatAktif
from models.riwayat_konsumsi import RiwayatKonsumsi
from models.status_konsumsi import StatusKonsumsi

# status bernilai None artinya: waktunya sudah lewat dan tidak pernah tercatat
BarisJadwal = namedtuple("BarisJadwal", "jadwal waktu status")
RingkasanHariIni = namedtuple(
    "RingkasanHariIni", "berikutnya sudah_minum total obat_menipis")


class LayananPengingat:
    """Logika inti pengingat (pengganti PenjadwalNotifikasi pada versi web).

    Aplikasi web tidak punya proses latar belakang, jadi halaman web memanggil
    pengingat_aktif() secara berkala (polling). Semua method menerima 'sekarang'
    supaya mudah diuji. sinkronkan() aman dipanggil berulang kali.

    Satu siklus dering: bunyi ke-1 pada saat jadwal tiba, lalu bunyi berikutnya
    setiap INTERVAL_BUNYI_MENIT menit. Setelah 'jumlah_bunyi' bunyi tanpa
    tanggapan, riwayat otomatis berstatus Terlewat. Menunda memulai siklus baru.
    """

    INTERVAL_BUNYI_MENIT = 1

    def __init__(self, db):
        self.__db = db

    # ================= pembantu internal =================
    def __durasi_siklus(self, pengaturan):
        return timedelta(
            minutes=pengaturan.jumlah_bunyi * self.INTERVAL_BUNYI_MENIT)

    @staticmethod
    def __mulai_dering(riwayat):
        if riwayat.status == StatusKonsumsi.DITUNDA and riwayat.ditunda_sampai:
            return riwayat.ditunda_sampai
        return riwayat.waktu_terjadwal

    def __riwayat_milik(self, id_pengguna, id_riwayat):
        riwayat = self.__db.ambil_riwayat(id_riwayat)
        milik = {o.id_obat for o in self.__db.daftar_obat(id_pengguna)}
        if riwayat is None or riwayat.jadwal.obat.id_obat not in milik:
            raise ValueError("Riwayat tidak ditemukan.")
        return riwayat

    # ================= sinkronisasi =================
    def sinkronkan(self, id_pengguna, sekarang=None):
        """1) Pengingat yang tidak ditanggapi sampai siklus habis -> Terlewat.
        2) Jadwal yang baru jatuh tempo hari ini -> buat riwayat Menunggu.

        Keterbatasan: slot yang waktunya sudah lewat dari siklus dering dan
        belum pernah tercatat (mis. halaman web tidak dibuka) tidak dicatat.
        """
        sekarang = sekarang or datetime.now()
        siklus = self.__durasi_siklus(self.__db.ambil_pengaturan(id_pengguna))

        for r in self.__db.daftar_riwayat_tertunda(id_pengguna):
            batas = self.__mulai_dering(r) + siklus
            if sekarang >= batas:
                r.tandai_terlewat(batas)
                self.__db.ubah_riwayat(r)

        hari = sekarang.date()
        sudah_ada = {
            (r.jadwal.id_jadwal, r.waktu_terjadwal)
            for r in self.__db.daftar_riwayat(
                id_pengguna,
                dari=datetime.combine(hari, time.min),
                sampai=datetime.combine(hari, time(23, 59, 59)))
        }
        for jadwal in self.__db.daftar_jadwal_pengguna(id_pengguna):
            if not jadwal.waktu_tiba(sekarang):
                continue
            slot = jadwal.waktu_terjadwal_pada(hari)
            if (jadwal.id_jadwal, slot) in sudah_ada:
                continue
            if sekarang >= slot + siklus:
                continue
            self.__db.tambah_riwayat(RiwayatKonsumsi(None, jadwal, slot))

    # ================= pop-up pengingat =================
    def pengingat_aktif(self, id_pengguna, sekarang=None):
        """Daftar pengingat yang sedang berbunyi (untuk pop-up)."""
        sekarang = sekarang or datetime.now()
        self.sinkronkan(id_pengguna, sekarang)
        total = self.__db.ambil_pengaturan(id_pengguna).jumlah_bunyi
        hasil = []
        for r in self.__db.daftar_riwayat_tertunda(id_pengguna):
            mulai = self.__mulai_dering(r)
            if mulai > sekarang:
                continue  # masih dalam masa tunda
            selisih = (sekarang - mulai).total_seconds()
            ke = int(selisih // (self.INTERVAL_BUNYI_MENIT * 60)) + 1
            hasil.append(PengingatAktif(r, min(ke, total), total))
        return hasil

    def tandai_sudah_minum(self, id_pengguna, id_riwayat, sekarang=None):
        """Tombol 'Sudah Minum': catat riwayat dan kurangi stok (FR-05)."""
        sekarang = sekarang or datetime.now()
        riwayat = self.__riwayat_milik(id_pengguna, id_riwayat)
        riwayat.tandai_sudah_minum(sekarang)  # ValueError jika sudah final
        obat = riwayat.jadwal.obat
        if obat.stok >= obat.jumlah_per_minum:
            obat.kurangi_stok()
        else:
            obat.stok = 0  # stok tercatat kurang; jangan blokir pencatatan
        self.__db.ubah_obat(obat)
        self.__db.ubah_riwayat(riwayat)
        return self.__db.ambil_riwayat(id_riwayat)

    def tunda(self, id_pengguna, id_riwayat, sekarang=None):
        """Tombol 'Tunda': durasi diambil dari Pengaturan (FR-06)."""
        sekarang = sekarang or datetime.now()
        riwayat = self.__riwayat_milik(id_pengguna, id_riwayat)
        menit = self.__db.ambil_pengaturan(id_pengguna).durasi_tunda
        riwayat.tunda(menit, sekarang)
        self.__db.ubah_riwayat(riwayat)
        return self.__db.ambil_riwayat(id_riwayat)

    # ================= jadwal harian & ringkasan =================
    def jadwal_harian(self, id_pengguna, tanggal, sekarang=None):
        """Baris tabel Jadwal/Beranda untuk satu tanggal, urut jam.

        Status: dari riwayat bila ada; Menunggu bila waktunya belum tiba;
        None bila waktunya sudah lewat tetapi tidak tercatat.
        """
        sekarang = sekarang or datetime.now()
        if tanggal == sekarang.date():
            self.sinkronkan(id_pengguna, sekarang)
        status_by_jadwal = {
            r.jadwal.id_jadwal: r.status
            for r in self.__db.daftar_riwayat(
                id_pengguna,
                dari=datetime.combine(tanggal, time.min),
                sampai=datetime.combine(tanggal, time(23, 59, 59)))
        }
        baris = []
        for jadwal in self.__db.daftar_jadwal_pengguna(id_pengguna):
            tercatat = status_by_jadwal.get(jadwal.id_jadwal)
            berjalan = jadwal.aktif and jadwal.obat.perlu_diingatkan(tanggal)
            if tercatat is None and not berjalan:
                continue
            waktu = jadwal.waktu_terjadwal_pada(tanggal)
            if tercatat is not None:
                status = tercatat
            elif waktu > sekarang:
                status = StatusKonsumsi.MENUNGGU
            else:
                status = None
            baris.append(BarisJadwal(jadwal, waktu, status))
        return baris

    def ringkasan_hari_ini(self, id_pengguna, sekarang=None):
        """Tiga kartu di Beranda: Berikutnya, Hari ini (x/y), dan Stok."""
        sekarang = sekarang or datetime.now()
        pengguna = self.__db.ambil_pengguna(id_pengguna)
        if pengguna is None:
            raise ValueError("Pengguna tidak ditemukan.")
        baris = self.jadwal_harian(id_pengguna, sekarang.date(), sekarang)
        berikutnya = next((b for b in baris
                           if b.status == StatusKonsumsi.MENUNGGU
                           and b.waktu > sekarang), None)
        sudah = sum(1 for b in baris if b.status == StatusKonsumsi.SUDAH_MINUM)
        return RingkasanHariIni(berikutnya, sudah, len(baris),
                                pengguna.obat_menipis())
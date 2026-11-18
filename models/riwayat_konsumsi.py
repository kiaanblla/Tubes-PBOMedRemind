from datetime import datetime, timedelta

from models.status_konsumsi import StatusKonsumsi


class RiwayatKonsumsi:
    """Catatan satu kejadian pengingat (waktu terjadwal, waktu aktual, status)."""

    def __init__(self, id_riwayat, jadwal, waktu_terjadwal,
                 status=StatusKonsumsi.MENUNGGU, waktu_aktual=None,
                 keterangan="", ditunda_sampai=None):
        self.__id_riwayat = id_riwayat
        self.__jadwal = jadwal
        self.__waktu_terjadwal = waktu_terjadwal
        self.__status = status
        self.__waktu_aktual = waktu_aktual
        self.__keterangan = keterangan
        self.__ditunda_sampai = ditunda_sampai

    @property
    def id_riwayat(self):
        return self.__id_riwayat

    @property
    def jadwal(self):
        return self.__jadwal

    @property
    def waktu_terjadwal(self):
        return self.__waktu_terjadwal

    @property
    def status(self):
        return self.__status

    @property
    def waktu_aktual(self):
        return self.__waktu_aktual

    @property
    def keterangan(self):
        return self.__keterangan

    @property
    def ditunda_sampai(self):
        return self.__ditunda_sampai

    def __pastikan_belum_final(self):
        if self.__status in (StatusKonsumsi.SUDAH_MINUM, StatusKonsumsi.TERLEWAT):
            raise ValueError(
                f"Riwayat sudah berstatus '{self.__status.value}' dan tidak bisa diubah."
            )

    def tandai_sudah_minum(self, waktu=None):
        self.__pastikan_belum_final()
        self.__status = StatusKonsumsi.SUDAH_MINUM
        self.__waktu_aktual = waktu or datetime.now()
        self.__keterangan = ""
        self.__ditunda_sampai = None

    def tunda(self, menit=10, sekarang=None):
        self.__pastikan_belum_final()
        if menit < 1:
            raise ValueError("Durasi tunda minimal 1 menit.")
        sekarang = sekarang or datetime.now()
        self.__status = StatusKonsumsi.DITUNDA
        self.__ditunda_sampai = sekarang + timedelta(minutes=menit)
        self.__keterangan = f"Ditunda {menit} menit"

    def tandai_terlewat(self, waktu=None):
        self.__pastikan_belum_final()
        self.__status = StatusKonsumsi.TERLEWAT
        self.__waktu_aktual = waktu or datetime.now()
        self.__keterangan = "Tidak ada respons"
        self.__ditunda_sampai = None

    @staticmethod
    def hitung_kepatuhan(daftar_riwayat):
        """Persentase kepatuhan = sudah minum / (sudah minum + terlewat) x 100.
        Yang masih Menunggu atau Ditunda belum dihitung."""
        sudah = sum(1 for r in daftar_riwayat
                    if r.status == StatusKonsumsi.SUDAH_MINUM)
        terlewat = sum(1 for r in daftar_riwayat
                       if r.status == StatusKonsumsi.TERLEWAT)
        total = sudah + terlewat
        if total == 0:
            return 0
        return round(sudah / total * 100)
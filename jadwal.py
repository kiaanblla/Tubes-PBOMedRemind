"""
jadwal.py - Jadwal pengingat dan riwayat konsumsi obat pada MedRemind.

Isi:
- StatusKonsumsi   : enum status (sudah minum / ditunda / dilewati)
- JadwalPengingat  : satu jam minum untuk satu obat
- RiwayatKonsumsi  : catatan setiap kejadian pengingat

Hubungan dengan kelas lain (lihat class diagram):
    Obat 1 --- * JadwalPengingat 1 --- * RiwayatKonsumsi
"""

from datetime import datetime, time
from enum import Enum


class StatusKonsumsi(Enum):
    """Status dari satu kejadian pengingat."""
    SUDAH_MINUM = "SUDAH_MINUM"
    DITUNDA = "DITUNDA"
    DILEWATI = "DILEWATI"


class JadwalPengingat:
    """Satu jam minum untuk satu obat (misalnya Amoksisilin jam 13.00)."""

    def __init__(self, id_jadwal: int, id_obat: int, waktu_minum: time,
                 aktif: bool = True):
        self.__id_jadwal = id_jadwal
        # id_obat menghubungkan jadwal ini ke obatnya (kolom FK di database).
        self.__id_obat = id_obat
        self.__waktu_minum = waktu_minum
        self.__aktif = aktif

    # ---------- Getter ----------
    def getIdJadwal(self) -> int:
        return self.__id_jadwal

    def getIdObat(self) -> int:
        return self.__id_obat

    def getWaktuMinum(self) -> time:
        return self.__waktu_minum

    def isAktif(self) -> bool:
        return self.__aktif

    # ---------- Perilaku ----------
    def setJadwal(self, waktu: time) -> None:
        """Mengubah jam minum."""
        self.__waktu_minum = waktu

    def aktifkan(self) -> None:
        self.__aktif = True

    def nonaktifkan(self) -> None:
        self.__aktif = False

    def waktuTiba(self, sekarang: time) -> bool:
        """
        True jika jadwal aktif dan jam:menit sekarang sama dengan jam minum.
        Detik diabaikan, karena pengecekan dilakukan berkala (bukan per detik).
        """
        return (self.__aktif
                and sekarang.hour == self.__waktu_minum.hour
                and sekarang.minute == self.__waktu_minum.minute)

    def __str__(self) -> str:
        status = "aktif" if self.__aktif else "nonaktif"
        return f"Jadwal #{self.__id_jadwal} (obat #{self.__id_obat}) " \
               f"{self.__waktu_minum:%H:%M} [{status}]"


class RiwayatKonsumsi:
    """Catatan satu kejadian pengingat: terjadwal jam berapa, hasilnya apa."""

    def __init__(self, id_riwayat: int, id_jadwal: int,
                 waktu_terjadwal: datetime,
                 status: StatusKonsumsi = StatusKonsumsi.DITUNDA,
                 waktu_aktual: datetime | None = None,
                 keterangan: str = ""):
        self.__id_riwayat = id_riwayat
        self.__id_jadwal = id_jadwal
        self.__waktu_terjadwal = waktu_terjadwal
        self.__status = status
        self.__waktu_aktual = waktu_aktual
        self.__keterangan = keterangan

    # ---------- Getter ----------
    def getIdRiwayat(self) -> int:
        return self.__id_riwayat

    def getIdJadwal(self) -> int:
        return self.__id_jadwal

    def getWaktuTerjadwal(self) -> datetime:
        return self.__waktu_terjadwal

    def getWaktuAktual(self) -> datetime | None:
        return self.__waktu_aktual

    def getStatus(self) -> StatusKonsumsi:
        return self.__status

    def getKeterangan(self) -> str:
        return self.__keterangan

    # ---------- Perilaku ----------
    def catatLog(self, status: StatusKonsumsi, keterangan: str = "",
                 waktu_aktual: datetime | None = None) -> None:
        """
        Mencatat hasil pengingat.
        - SUDAH_MINUM: waktu aktual diisi (bawaan: sekarang).
        - DITUNDA / DILEWATI: waktu aktual dikosongkan.
        """
        if not isinstance(status, StatusKonsumsi):
            raise ValueError("Status harus berupa StatusKonsumsi.")
        self.__status = status
        self.__keterangan = keterangan
        if status == StatusKonsumsi.SUDAH_MINUM:
            self.__waktu_aktual = waktu_aktual or datetime.now()
        else:
            self.__waktu_aktual = None

    @staticmethod
    def hitungKepatuhan(daftar_riwayat: list["RiwayatKonsumsi"]) -> float:
        """
        Persentase kepatuhan = SUDAH_MINUM / (SUDAH_MINUM + DILEWATI) x 100.
        Status DITUNDA tidak dihitung karena belum final: nanti berakhir
        sebagai SUDAH_MINUM atau DILEWATI. Hasil 0.0 jika belum ada data.
        """
        sudah = sum(1 for r in daftar_riwayat
                    if r.getStatus() == StatusKonsumsi.SUDAH_MINUM)
        lewat = sum(1 for r in daftar_riwayat
                    if r.getStatus() == StatusKonsumsi.DILEWATI)
        total = sudah + lewat
        return round(sudah / total * 100, 1) if total else 0.0

    def __str__(self) -> str:
        return (f"Riwayat #{self.__id_riwayat} | terjadwal "
                f"{self.__waktu_terjadwal:%d/%m %H:%M} | {self.__status.value}")


# ----------------------------------------------------------------------
# Demo singkat. Jalankan dengan:  python jadwal.py
# ----------------------------------------------------------------------
if __name__ == "__main__":
    jadwal = JadwalPengingat(1, id_obat=2, waktu_minum=time(13, 0))
    print(jadwal)
    print("13:00 sudah tiba?", jadwal.waktuTiba(time(13, 0, 25)))
    print("13:01 sudah tiba?", jadwal.waktuTiba(time(13, 1)))

    jadwal.nonaktifkan()
    print("Setelah dinonaktifkan, 13:00 tiba?", jadwal.waktuTiba(time(13, 0)))

    # Simulasi tiga hari pengingat
    riwayat = []
    for i, status in enumerate([StatusKonsumsi.SUDAH_MINUM,
                                StatusKonsumsi.SUDAH_MINUM,
                                StatusKonsumsi.DILEWATI], start=1):
        r = RiwayatKonsumsi(i, 1, datetime(2026, 11, 10 + i, 13, 0))
        r.catatLog(status)
        riwayat.append(r)
        print(r)

    print("Kepatuhan:", RiwayatKonsumsi.hitungKepatuhan(riwayat), "%")
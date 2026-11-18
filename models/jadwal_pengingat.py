from datetime import datetime, time


class JadwalPengingat:
    """Satu jam minum untuk satu obat."""

    def __init__(self, id_jadwal, obat, waktu_minum, aktif=True):
        self.__id_jadwal = id_jadwal
        self.__obat = obat
        self.waktu_minum = waktu_minum
        self.aktif = aktif

    @staticmethod
    def parse_jam(teks):
        """Ubah teks 'HH:MM' menjadi objek time. Salah format -> ValueError."""
        try:
            return datetime.strptime(teks.strip(), "%H:%M").time()
        except (ValueError, AttributeError):
            raise ValueError(
                f"Format jam tidak valid: '{teks}'. Gunakan HH:MM, contoh 07:00."
            )

    @property
    def id_jadwal(self):
        return self.__id_jadwal

    @property
    def obat(self):
        return self.__obat

    @property
    def waktu_minum(self):
        return self.__waktu_minum

    @waktu_minum.setter
    def waktu_minum(self, nilai):
        if not isinstance(nilai, time):
            raise ValueError("waktu_minum harus berupa objek datetime.time.")
        self.__waktu_minum = nilai

    @property
    def aktif(self):
        return self.__aktif

    @aktif.setter
    def aktif(self, nilai):
        self.__aktif = bool(nilai)

    def waktu_text(self):
        return self.__waktu_minum.strftime("%H:%M")

    def waktu_terjadwal_pada(self, tanggal):
        """Gabungkan tanggal dengan jam minum -> datetime."""
        return datetime.combine(tanggal, self.__waktu_minum)

    def waktu_tiba(self, sekarang):
        """True jika jadwal aktif, obatnya masih aktif hari itu,
        dan waktu sekarang sudah mencapai jam minum.

        Penjadwal (Langkah 4) yang memastikan pengingat tidak muncul dua kali
        dengan memeriksa riwayat hari ini.
        """
        if not self.__aktif:
            return False
        if not self.__obat.is_aktif(sekarang.date()):
            return False
        return sekarang >= self.waktu_terjadwal_pada(sekarang.date())
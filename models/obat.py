from abc import ABC, abstractmethod


class Obat(ABC):
    """Kelas induk abstrak untuk semua jenis obat."""

    def __init__(self, id_obat, nama, kekuatan_dosis, jumlah_per_minum,
                 satuan, stok, batas_stok_minimum=5):
        self.__id_obat = id_obat
        self.__kekuatan_dosis = kekuatan_dosis
        self.__satuan = satuan
        # lewat setter supaya langsung tervalidasi
        self.nama = nama
        self.jumlah_per_minum = jumlah_per_minum
        self.stok = stok
        self.batas_stok_minimum = batas_stok_minimum

    # ---- getter / setter (enkapsulasi) ----
    @property
    def id_obat(self):
        return self.__id_obat

    @property
    def kekuatan_dosis(self):
        return self.__kekuatan_dosis

    @property
    def satuan(self):
        return self.__satuan

    @property
    def nama(self):
        return self.__nama

    @nama.setter
    def nama(self, nilai):
        if not nilai or not nilai.strip():
            raise ValueError("Nama obat tidak boleh kosong.")
        self.__nama = nilai.strip()

    @property
    def jumlah_per_minum(self):
        return self.__jumlah_per_minum

    @jumlah_per_minum.setter
    def jumlah_per_minum(self, nilai):
        if nilai < 1:
            raise ValueError("Jumlah per minum minimal 1.")
        self.__jumlah_per_minum = nilai

    @property
    def stok(self):
        return self.__stok

    @stok.setter
    def stok(self, nilai):
        if nilai < 0:
            raise ValueError("Stok tidak boleh negatif.")
        self.__stok = nilai

    @property
    def batas_stok_minimum(self):
        return self.__batas_stok_minimum

    @batas_stok_minimum.setter
    def batas_stok_minimum(self, nilai):
        if nilai < 0:
            raise ValueError("Batas stok minimum tidak boleh negatif.")
        self.__batas_stok_minimum = nilai

    # ---- perilaku umum (diwariskan) ----
    def nama_lengkap(self):
        return f"{self.nama} {self.kekuatan_dosis}".strip()

    def dosis_text(self):
        return f"{self.jumlah_per_minum} {self.satuan}"

    def kurangi_stok(self):
        """Dipanggil saat pengguna menekan 'Sudah Minum' (FR-05)."""
        if self.stok < self.jumlah_per_minum:
            raise ValueError(f"Stok {self.nama_lengkap()} tidak cukup.")
        self.stok -= self.jumlah_per_minum

    def is_menipis(self, batas=None):
        """True jika stok <= batas (FR-07). Jika batas tidak diberikan,
        dipakai batas_stok_minimum milik obat ini."""
        if batas is None:
            batas = self.batas_stok_minimum
        return self.stok <= batas

    # ---- abstraksi: wajib di-override subkelas ----
    @abstractmethod
    def is_aktif(self, hari_ini=None):
        ...

    @abstractmethod
    def get_info(self):
        ...
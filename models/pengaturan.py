class Pengaturan:
    """Preferensi satu pengguna (halaman Pengaturan)."""

    JENIS_SUARA = ("Lonceng lembut", "Bip singkat", "Nada klasik")
    JUMLAH_BUNYI = (1, 2, 3, 4, 5)
    DURASI_TUNDA = (5, 10, 15, 30)  # menit
    PERIODE = ("7 hari terakhir", "30 hari terakhir")

    def __init__(self, pengingat_bersuara=True, jenis_suara="Lonceng lembut",
                 volume=70, jumlah_bunyi=4, durasi_tunda=10,
                 batas_stok_menipis=5, peringatan_beranda=True,
                 periode_bawaan="7 hari terakhir", sertakan_keterangan=True):
        # semua lewat setter supaya langsung tervalidasi
        self.pengingat_bersuara = pengingat_bersuara
        self.jenis_suara = jenis_suara
        self.volume = volume
        self.jumlah_bunyi = jumlah_bunyi
        self.durasi_tunda = durasi_tunda
        self.batas_stok_menipis = batas_stok_menipis
        self.peringatan_beranda = peringatan_beranda
        self.periode_bawaan = periode_bawaan
        self.sertakan_keterangan = sertakan_keterangan

    # ---- pembantu validasi ----
    @staticmethod
    def _pilih(nilai, pilihan, nama):
        if nilai not in pilihan:
            daftar = ", ".join(str(p) for p in pilihan)
            raise ValueError(f"{nama} harus salah satu dari: {daftar}.")
        return nilai

    @staticmethod
    def _int_antara(nilai, minimum, maksimum, nama):
        if (isinstance(nilai, bool) or not isinstance(nilai, int)
                or not minimum <= nilai <= maksimum):
            raise ValueError(f"{nama} harus bilangan bulat {minimum}-{maksimum}.")
        return nilai

    # ---- getter / setter ----
    @property
    def pengingat_bersuara(self):
        return self.__pengingat_bersuara

    @pengingat_bersuara.setter
    def pengingat_bersuara(self, nilai):
        self.__pengingat_bersuara = bool(nilai)

    @property
    def jenis_suara(self):
        return self.__jenis_suara

    @jenis_suara.setter
    def jenis_suara(self, nilai):
        self.__jenis_suara = self._pilih(nilai, self.JENIS_SUARA, "Jenis suara")

    @property
    def volume(self):
        return self.__volume

    @volume.setter
    def volume(self, nilai):
        self.__volume = self._int_antara(nilai, 0, 100, "Volume")

    @property
    def jumlah_bunyi(self):
        return self.__jumlah_bunyi

    @jumlah_bunyi.setter
    def jumlah_bunyi(self, nilai):
        self.__jumlah_bunyi = self._pilih(nilai, self.JUMLAH_BUNYI, "Jumlah bunyi")

    @property
    def durasi_tunda(self):
        return self.__durasi_tunda

    @durasi_tunda.setter
    def durasi_tunda(self, nilai):
        self.__durasi_tunda = self._pilih(nilai, self.DURASI_TUNDA, "Durasi tunda")

    @property
    def batas_stok_menipis(self):
        return self.__batas_stok_menipis

    @batas_stok_menipis.setter
    def batas_stok_menipis(self, nilai):
        self.__batas_stok_menipis = self._int_antara(
            nilai, 0, 1000, "Batas stok menipis")

    @property
    def peringatan_beranda(self):
        return self.__peringatan_beranda

    @peringatan_beranda.setter
    def peringatan_beranda(self, nilai):
        self.__peringatan_beranda = bool(nilai)

    @property
    def periode_bawaan(self):
        return self.__periode_bawaan

    @periode_bawaan.setter
    def periode_bawaan(self, nilai):
        self.__periode_bawaan = self._pilih(nilai, self.PERIODE, "Periode bawaan")

    @property
    def sertakan_keterangan(self):
        return self.__sertakan_keterangan

    @sertakan_keterangan.setter
    def sertakan_keterangan(self, nilai):
        self.__sertakan_keterangan = bool(nilai)

    # ---- konversi (dipakai nanti saat simpan/muat dari database) ----
    def to_dict(self):
        return {
            "pengingat_bersuara": self.pengingat_bersuara,
            "jenis_suara": self.jenis_suara,
            "volume": self.volume,
            "jumlah_bunyi": self.jumlah_bunyi,
            "durasi_tunda": self.durasi_tunda,
            "batas_stok_menipis": self.batas_stok_menipis,
            "peringatan_beranda": self.peringatan_beranda,
            "periode_bawaan": self.periode_bawaan,
            "sertakan_keterangan": self.sertakan_keterangan,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(**data)
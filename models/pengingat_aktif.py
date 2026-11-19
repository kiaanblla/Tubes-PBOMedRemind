class PengingatAktif:
    """Satu pengingat yang sedang berbunyi (isi pop-up 'Waktunya minum obat!')."""

    def __init__(self, riwayat, bunyi_ke, total_bunyi):
        self.__riwayat = riwayat
        self.__bunyi_ke = bunyi_ke
        self.__total_bunyi = total_bunyi

    @property
    def riwayat(self):
        return self.__riwayat

    @property
    def obat(self):
        return self.__riwayat.jadwal.obat

    @property
    def bunyi_ke(self):
        return self.__bunyi_ke

    @property
    def total_bunyi(self):
        return self.__total_bunyi

    def detail_text(self):
        """Contoh: 'Dosis 2 kapsul · Jadwal 13:00'."""
        return (f"Dosis {self.obat.dosis_text()} · "
                f"Jadwal {self.__riwayat.jadwal.waktu_text()}")

    def stok_text(self):
        """Contoh: 'Sisa stok 18 kapsul'."""
        return f"Sisa stok {self.obat.stok} {self.obat.satuan}"

    def footer_text(self):
        return (f"Bunyi ke-{self.__bunyi_ke} dari {self.__total_bunyi} · "
                "otomatis Terlewat jika tidak ditanggapi")
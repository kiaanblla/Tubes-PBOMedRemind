from datetime import date

from models.obat import Obat


class ObatTemporer(Obat):
    """Obat dengan masa terapi (tanggal mulai sampai tanggal selesai)."""

    def __init__(self, id_obat, nama, kekuatan_dosis, jumlah_per_minum,
                 satuan, stok, tanggal_mulai, tanggal_selesai,
                 batas_stok_minimum=5, dinonaktifkan=False):
        super().__init__(id_obat, nama, kekuatan_dosis, jumlah_per_minum,
                         satuan, stok, batas_stok_minimum, dinonaktifkan)
        if tanggal_selesai < tanggal_mulai:
            raise ValueError("Tanggal selesai tidak boleh lebih awal "
                             "dari tanggal mulai.")
        self.__tanggal_mulai = tanggal_mulai
        self.__tanggal_selesai = tanggal_selesai

    @property
    def tanggal_mulai(self):
        return self.__tanggal_mulai

    @property
    def tanggal_selesai(self):
        return self.__tanggal_selesai

    def is_aktif(self, hari_ini=None):
        hari_ini = hari_ini or date.today()
        return self.__tanggal_mulai <= hari_ini <= self.__tanggal_selesai

    def hitung_sisa_hari(self, hari_ini=None):
        hari_ini = hari_ini or date.today()
        return max(0, (self.__tanggal_selesai - hari_ini).days)

    def get_info(self):
        return (f"{self.nama_lengkap()} | Temporer | {self.dosis_text()} "
                f"| stok {self.stok} | sisa {self.hitung_sisa_hari()} hari")
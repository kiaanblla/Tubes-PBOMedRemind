from models.obat import Obat


class ObatRutin(Obat):
    """Obat jangka panjang tanpa tanggal selesai."""

    def is_aktif(self, hari_ini=None):
        return True

    def get_info(self):
        return (f"{self.nama_lengkap()} | Rutin | {self.dosis_text()} "
                f"| stok {self.stok}")
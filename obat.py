"""
obat.py - Kelas-kelas untuk data obat pada aplikasi MedRemind.

Struktur (sesuai class diagram di proposal):

    Obat (abstract)
     |-- ObatRutin
     |-- ObatTemporer

Penerapan prinsip PBO:
- Encapsulation : atribut diawali "__" (privat), diakses lewat getter/setter
                  yang memvalidasi nilai.
- Inheritance   : ObatRutin & ObatTemporer mewarisi atribut dan pengelolaan
                  stok dari Obat.
- Abstraction   : Obat adalah abstract class, tidak bisa dibuat langsung.
- Polymorphism  : isAktif() dan getInfo() di-override di tiap subkelas.
"""

from abc import ABC, abstractmethod
from datetime import date


class Obat(ABC):
    """Kelas induk abstrak untuk semua jenis obat."""

    def __init__(self, id_obat: int, nama_obat: str, kekuatan_dosis: str,
                 jumlah_per_minum: int, satuan: str, stok: int,
                 batas_stok_minimum: int = 5, foto: str = ""):
        # Semua atribut privat (diawali __). Pengisian awal lewat setter
        # supaya validasinya ikut berjalan.
        self.__id_obat = id_obat
        self.setNamaObat(nama_obat)
        self.__kekuatan_dosis = kekuatan_dosis
        self.setJumlahPerMinum(jumlah_per_minum)
        self.__satuan = satuan
        self.setStok(stok)
        self.setBatasStokMinimum(batas_stok_minimum)
        self.__foto = foto or ""          # path relatif foto obat ("" = belum ada)

    # ---------- Getter ----------
    def getIdObat(self) -> int:
        return self.__id_obat

    def getNamaObat(self) -> str:
        return self.__nama_obat

    def getKekuatanDosis(self) -> str:
        return self.__kekuatan_dosis

    def getJumlahPerMinum(self) -> int:
        return self.__jumlah_per_minum

    def getSatuan(self) -> str:
        return self.__satuan

    def getStok(self) -> int:
        return self.__stok

    def getBatasStokMinimum(self) -> int:
        return self.__batas_stok_minimum

    def getFoto(self) -> str:
        return self.__foto

    def setFoto(self, path: str) -> None:
        self.__foto = path or ""

    # ---------- Setter (dengan validasi) ----------
    def setNamaObat(self, nama: str) -> None:
        if not nama or not nama.strip():
            raise ValueError("Nama obat tidak boleh kosong.")
        self.__nama_obat = nama.strip()

    def setJumlahPerMinum(self, jumlah: int) -> None:
        if jumlah <= 0:
            raise ValueError("Jumlah per minum harus lebih dari 0.")
        self.__jumlah_per_minum = jumlah

    def setStok(self, nilai: int) -> None:
        if nilai < 0:
            raise ValueError("Stok tidak boleh negatif.")
        self.__stok = nilai

    def setBatasStokMinimum(self, batas: int) -> None:
        if batas < 0:
            raise ValueError("Batas stok minimum tidak boleh negatif.")
        self.__batas_stok_minimum = batas

    # ---------- Pengelolaan stok ----------
    def tambahStok(self, jumlah: int) -> None:
        """Menambah stok (misalnya setelah beli obat baru)."""
        if jumlah <= 0:
            raise ValueError("Jumlah tambahan stok harus lebih dari 0.")
        self.__stok += jumlah

    def kurangiStok(self) -> None:
        """
        Mengurangi stok sebanyak jumlah_per_minum.
        Dipanggil saat pengguna menekan "Sudah Minum".
        Stok tidak akan turun di bawah 0.
        """
        self.__stok = max(0, self.__stok - self.__jumlah_per_minum)

    def stokMenipis(self) -> bool:
        """True jika stok sudah sama dengan atau di bawah batas minimum."""
        return self.__stok <= self.__batas_stok_minimum

    # ---------- Method abstrak: wajib di-override subkelas ----------
    @abstractmethod
    def isAktif(self, tanggal: date) -> bool:
        """Apakah obat ini masih perlu diminum pada tanggal tersebut?"""

    @abstractmethod
    def getInfo(self) -> str:
        """Ringkasan teks tentang obat, untuk ditampilkan di antarmuka."""

    # ---------- Bagian info yang sama untuk semua obat ----------
    def _infoDasar(self) -> str:
        return (f"{self.__nama_obat} {self.__kekuatan_dosis} - "
                f"{self.__jumlah_per_minum} {self.__satuan} per minum "
                f"(stok: {self.__stok})")


class ObatRutin(Obat):
    """Obat jangka panjang tanpa tanggal selesai (misalnya obat darah tinggi)."""

    def __init__(self, id_obat: int, nama_obat: str, kekuatan_dosis: str,
                 jumlah_per_minum: int, satuan: str, stok: int,
                 batas_stok_minimum: int = 5, penyakit_kronis: str = "",
                 foto: str = ""):
        super().__init__(id_obat, nama_obat, kekuatan_dosis,
                         jumlah_per_minum, satuan, stok, batas_stok_minimum, foto)
        self.__penyakit_kronis = penyakit_kronis

    def getPenyakitKronis(self) -> str:
        return self.__penyakit_kronis

    def isAktif(self, tanggal: date) -> bool:
        # Obat rutin tidak punya tanggal selesai, jadi selalu aktif.
        return True

    def getInfo(self) -> str:
        info = f"[Rutin] {self._infoDasar()}"
        if self.__penyakit_kronis:
            info += f" | untuk: {self.__penyakit_kronis}"
        return info


class ObatTemporer(Obat):
    """Obat dengan masa terapi terbatas (misalnya antibiotik)."""

    def __init__(self, id_obat: int, nama_obat: str, kekuatan_dosis: str,
                 jumlah_per_minum: int, satuan: str, stok: int,
                 tanggal_mulai: date, tanggal_selesai: date,
                 batas_stok_minimum: int = 5, foto: str = ""):
        super().__init__(id_obat, nama_obat, kekuatan_dosis,
                         jumlah_per_minum, satuan, stok, batas_stok_minimum, foto)
        if tanggal_selesai < tanggal_mulai:
            raise ValueError("Tanggal selesai tidak boleh lebih awal dari tanggal mulai.")
        self.__tanggal_mulai = tanggal_mulai
        self.__tanggal_selesai = tanggal_selesai

    def getTanggalMulai(self) -> date:
        return self.__tanggal_mulai

    def getTanggalSelesai(self) -> date:
        return self.__tanggal_selesai

    def isAktif(self, tanggal: date) -> bool:
        # Aktif hanya selama masa terapi berlangsung.
        return self.__tanggal_mulai <= tanggal <= self.__tanggal_selesai

    def hitungSisaHari(self, tanggal: date | None = None) -> int:
        """Sisa hari terapi (0 jika masa terapi sudah lewat)."""
        tanggal = tanggal or date.today()
        return max(0, (self.__tanggal_selesai - tanggal).days)

    def getInfo(self) -> str:
        return (f"[Temporer] {self._infoDasar()} | "
                f"{self.__tanggal_mulai:%d/%m/%Y} - {self.__tanggal_selesai:%d/%m/%Y} "
                f"(sisa {self.hitungSisaHari()} hari)")


# ----------------------------------------------------------------------
# Demo singkat. Jalankan dengan:  python obat.py
# Bagian ini hanya jalan kalau file dijalankan langsung, bukan saat di-import.
# ----------------------------------------------------------------------
if __name__ == "__main__":
    hari_ini = date.today()

    daftar_obat = [
        ObatRutin(1, "Amlodipin", "5 mg", 1, "tablet", 30,
                  penyakit_kronis="Hipertensi"),
        ObatTemporer(2, "Amoksisilin", "500 mg", 1, "kapsul", 21,
                     tanggal_mulai=date(2026, 11, 10),
                     tanggal_selesai=date(2026, 11, 16)),
    ]

    # Polimorfisme: daftar diproses dengan cara yang sama, tapi hasilnya
    # menyesuaikan jenis obat masing-masing.
    for obat in daftar_obat:
        print(obat.getInfo())
        print("  Aktif hari ini?", obat.isAktif(hari_ini))

    # Simulasi pengguna menekan "Sudah Minum"
    amlodipin = daftar_obat[0]
    amlodipin.kurangiStok()
    print("\nSetelah minum, stok Amlodipin:", amlodipin.getStok())

    # Validasi (enkapsulasi): stok negatif ditolak
    try:
        amlodipin.setStok(-5)
    except ValueError as e:
        print("Ditolak:", e)

    # Abstraksi: Obat tidak bisa dibuat langsung
    try:
        Obat(3, "X", "1 mg", 1, "tablet", 10)
    except TypeError as e:
        print("Ditolak:", e)
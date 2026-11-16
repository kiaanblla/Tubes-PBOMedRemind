"""
pengaturan.py - Pengaturan tampilan (warna) dan penyimpanan foto obat MedRemind.

- PengaturanTampilan : warna aksen + mode gelap, disimpan di pengaturan.json.
                       Semua warna lain diturunkan dari aksen, jadi pengguna
                       cukup memilih satu warna.
- PenyimpanFoto      : menyalin foto obat ke folder foto_obat/ (diperkecil),
                       lalu memuatnya kembali untuk ditampilkan di Tkinter.

Foto memakai Pillow:  pip install pillow
"""

import json
import os
import re
import uuid

try:
    from PIL import Image, ImageTk
    PILLOW_ADA = True
except ImportError:
    PILLOW_ADA = False

FOLDER_APP = os.path.dirname(os.path.abspath(__file__))
_POLA_WARNA = re.compile(r"#[0-9a-fA-F]{6}")


def _rgb(kode: str) -> tuple:
    kode = kode.lstrip("#")
    return tuple(int(kode[i:i + 2], 16) for i in (0, 2, 4))


def campur(a: str, b: str, t: float) -> str:
    """Campuran dua warna hex. t=0 -> a, t=1 -> b."""
    r, g, bl = (round(x + (y - x) * t) for x, y in zip(_rgb(a), _rgb(b)))
    return f"#{r:02x}{g:02x}{bl:02x}"


class PengaturanTampilan:
    """Menyimpan pilihan warna dan menyediakan palet lengkap untuk tampilan."""

    PRESET = {"Teal": "#1f6f6b", "Biru": "#2f5fa8", "Ungu": "#6b4fa0",
              "Mawar": "#b04a6b", "Jingga": "#c2662d"}
    BAWAAN = "#1f6f6b"

    def __init__(self, nama_file: str = "pengaturan.json"):
        self.__file = os.path.join(FOLDER_APP, nama_file)
        self.__aksen = self.BAWAAN
        self.__gelap = False
        try:
            with open(self.__file, encoding="utf-8") as f:
                data = json.load(f)
            if _POLA_WARNA.fullmatch(str(data.get("aksen", ""))):
                self.__aksen = data["aksen"]
            self.__gelap = bool(data.get("gelap", False))
        except (OSError, ValueError, AttributeError):
            pass                      # file belum ada / rusak -> pakai bawaan
        self.__palet = self.__bangunPalet()

    @property
    def aksen(self) -> str:
        return self.__aksen

    @property
    def gelap(self) -> bool:
        return self.__gelap

    def warna(self, kunci: str) -> str:
        return self.__palet[kunci]

    def atur(self, aksen: str = None, gelap: bool = None) -> None:
        """Mengubah warna aksen dan/atau mode gelap, lalu menyimpannya."""
        if aksen is not None:
            if not _POLA_WARNA.fullmatch(aksen):
                raise ValueError("Warna harus berformat #RRGGBB.")
            self.__aksen = aksen
        if gelap is not None:
            self.__gelap = bool(gelap)
        self.__palet = self.__bangunPalet()
        try:
            with open(self.__file, "w", encoding="utf-8") as f:
                json.dump({"aksen": self.__aksen, "gelap": self.__gelap}, f)
        except OSError:
            pass                      # gagal menyimpan tidak boleh menutup aplikasi

    def kembalikan(self) -> None:
        self.atur(self.BAWAAN, False)

    @staticmethod
    def kontras(kode: str) -> str:
        """Warna teks (putih/hitam) yang terbaca di atas warna latar `kode`."""
        r, g, b = _rgb(kode)
        return "#ffffff" if 0.299 * r + 0.587 * g + 0.114 * b < 150 else "#111111"

    def __bangunPalet(self) -> dict:
        a = self.__aksen
        if self.__gelap:
            aksen = campur(a, "#ffffff", 0.2)      # dicerahkan agar terbaca di latar gelap
            p = {"bg": "#1c211f", "tabel": "#252b29", "fg": "#e7ece9",
                 "redup": "#9aa6a1", "header": "#313836", "garis": "#434b48",
                 "menunggu": "#252b29", "sudah_minum": "#24412f",
                 "ditunda": "#4a4121", "dilewati": "#4c2a2a",
                 "bahaya": "#ffb4ab", "bahaya_bg": "#4a2321"}
        else:
            aksen = a
            p = {"bg": campur(a, "#ffffff", 0.93), "tabel": "#ffffff", "fg": "#1f2523",
                 "redup": "#667070", "header": campur(a, "#ffffff", 0.82),
                 "garis": campur(a, "#ffffff", 0.70),
                 "menunggu": "#ffffff", "sudah_minum": "#dcf0e3",
                 "ditunda": "#fdf1cf", "dilewati": "#f6d9d9",
                 "bahaya": "#8c1d18", "bahaya_bg": "#fbe3e1"}
        p.update(aksen=aksen, aksen_tua=campur(aksen, "#000000", 0.2),
                 teks_aksen=self.kontras(aksen))
        return p


class PenyimpanFoto:
    """Mengelola file foto obat. Di database hanya path relatif yang disimpan."""

    def __init__(self, folder: str = "foto_obat", ukuran_maks: int = 480):
        self.__folder = folder
        self.__ukuran_maks = ukuran_maks

    @property
    def tersedia(self) -> bool:
        return PILLOW_ADA

    def simpan(self, sumber: str) -> str:
        """Menyalin (dan memperkecil) foto ke folder aplikasi. Mengembalikan path relatif."""
        if not PILLOW_ADA:
            raise RuntimeError("Pillow belum terpasang. Jalankan: pip install pillow")
        os.makedirs(os.path.join(FOLDER_APP, self.__folder), exist_ok=True)
        nama = f"{self.__folder}/{uuid.uuid4().hex[:12]}.png"
        with Image.open(sumber) as gambar:
            gambar = gambar.convert("RGBA")
            gambar.thumbnail((self.__ukuran_maks, self.__ukuran_maks))
            gambar.save(os.path.join(FOLDER_APP, nama))
        return nama

    def hapus(self, path: str) -> None:
        """Menghapus file foto, hanya jika berada di folder foto aplikasi."""
        if not path:
            return
        lengkap = os.path.abspath(os.path.join(FOLDER_APP, path))
        if os.path.dirname(lengkap) == os.path.join(FOLDER_APP, self.__folder):
            try:
                os.remove(lengkap)
            except OSError:
                pass

    def muat(self, path: str, ukuran: int):
        """PhotoImage untuk Tkinter (muat dalam kotak ukuran x ukuran), atau None."""
        if not (PILLOW_ADA and path):
            return None
        try:
            with Image.open(os.path.join(FOLDER_APP, path)) as gambar:
                gambar = gambar.convert("RGBA")
                gambar.thumbnail((ukuran, ukuran))
                return ImageTk.PhotoImage(gambar)
        except (OSError, ValueError):
            return None
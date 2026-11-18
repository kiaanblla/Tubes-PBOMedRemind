import re

from werkzeug.security import check_password_hash, generate_password_hash

from models.obat import Obat
from models.pengaturan import Pengaturan


class Pengguna:
    """Akun pengguna: kredensial, pengaturan, dan kumpulan obatnya."""

    PANJANG_PASSWORD_MIN = 8
    POLA_USERNAME = re.compile(r"^[a-z0-9._]{3,30}$")

    def __init__(self, id_pengguna, username, password_hash, pengaturan=None):
        self.__id_pengguna = id_pengguna
        self.__password_hash = password_hash
        self.__pengaturan = pengaturan or Pengaturan()
        self.__daftar_obat = []
        self.username = username

    # ---- pembuatan akun baru (halaman Daftar) ----
    @classmethod
    def daftar(cls, username, password, id_pengguna=None):
        cls.validasi_password(password)
        return cls(id_pengguna, username, generate_password_hash(password))

    @staticmethod
    def validasi_password(password):
        if (not isinstance(password, str)
                or len(password) < Pengguna.PANJANG_PASSWORD_MIN):
            raise ValueError(
                f"Kata sandi minimal {Pengguna.PANJANG_PASSWORD_MIN} karakter.")

    # ---- getter / setter ----
    @property
    def id_pengguna(self):
        return self.__id_pengguna

    @property
    def username(self):
        return self.__username

    @username.setter
    def username(self, nilai):
        bersih = nilai.strip().lower() if isinstance(nilai, str) else ""
        if not self.POLA_USERNAME.match(bersih):
            raise ValueError(
                "Nama pengguna 3-30 karakter: huruf, angka, titik, atau garis bawah.")
        self.__username = bersih

    @property
    def password_hash(self):
        return self.__password_hash

    @property
    def pengaturan(self):
        return self.__pengaturan

    @property
    def daftar_obat(self):
        return tuple(self.__daftar_obat)  # salinan, tidak bisa diubah dari luar

    # ---- kata sandi ----
    def verifikasi_password(self, password):
        return check_password_hash(self.__password_hash, password)

    def ubah_password(self, lama, baru):
        if not self.verifikasi_password(lama):
            raise ValueError("Kata sandi lama salah.")
        self.validasi_password(baru)
        self.__password_hash = generate_password_hash(baru)

    # ---- mengelola obat (agregasi) ----
    def tambah_obat(self, obat):
        if not isinstance(obat, Obat):
            raise TypeError("Yang ditambahkan harus objek Obat.")
        self.__daftar_obat.append(obat)

    def cari_obat(self, id_obat):
        for obat in self.__daftar_obat:
            if obat.id_obat == id_obat:
                return obat
        return None

    def hapus_obat(self, id_obat):
        obat = self.cari_obat(id_obat)
        if obat is None:
            raise ValueError(f"Obat dengan id {id_obat} tidak ditemukan.")
        self.__daftar_obat.remove(obat)

    def obat_aktif(self, hari_ini=None):
        """Polimorfisme: is_aktif() berbeda untuk ObatRutin dan ObatTemporer."""
        return [o for o in self.__daftar_obat if o.is_aktif(hari_ini)]

    def obat_menipis(self):
        """Obat dengan stok <= batas global di Pengaturan (UC-07)."""
        batas = self.__pengaturan.batas_stok_menipis
        return [o for o in self.__daftar_obat if o.is_menipis(batas)]
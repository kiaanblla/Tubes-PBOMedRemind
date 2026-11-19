import sqlite3
from datetime import date, datetime

from models.jadwal_pengingat import JadwalPengingat
from models.obat_rutin import ObatRutin
from models.obat_temporer import ObatTemporer
from models.pengaturan import Pengaturan
from models.pengguna import Pengguna
from models.riwayat_konsumsi import RiwayatKonsumsi
from models.status_konsumsi import StatusKonsumsi


class DatabaseManager:
    """Satu-satunya kelas yang berbicara langsung dengan SQLite.

    Kelas lain hanya memanggil method seperti tambah_obat() atau
    daftar_riwayat() tanpa perlu tahu SQL-nya (abstraksi).
    Method tambah_* mengembalikan objek baru yang sudah punya id dari database.
    """

    SKEMA = """
    CREATE TABLE IF NOT EXISTS pengguna (
        id_pengguna   INTEGER PRIMARY KEY AUTOINCREMENT,
        username      TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS pengaturan (
        id_pengguna         INTEGER PRIMARY KEY
                            REFERENCES pengguna(id_pengguna) ON DELETE CASCADE,
        pengingat_bersuara  INTEGER NOT NULL,
        jenis_suara         TEXT NOT NULL,
        volume              INTEGER NOT NULL,
        jumlah_bunyi        INTEGER NOT NULL,
        durasi_tunda        INTEGER NOT NULL,
        batas_stok_menipis  INTEGER NOT NULL,
        peringatan_beranda  INTEGER NOT NULL,
        periode_bawaan      TEXT NOT NULL,
        sertakan_keterangan INTEGER NOT NULL
    );
    CREATE TABLE IF NOT EXISTS obat (
        id_obat            INTEGER PRIMARY KEY AUTOINCREMENT,
        id_pengguna        INTEGER NOT NULL
                           REFERENCES pengguna(id_pengguna) ON DELETE CASCADE,
        nama_obat          TEXT NOT NULL,
        kekuatan_dosis     TEXT NOT NULL,
        jumlah_per_minum   INTEGER NOT NULL,
        satuan             TEXT NOT NULL,
        stok               INTEGER NOT NULL,
        batas_stok_minimum INTEGER NOT NULL,
        kategori           TEXT NOT NULL CHECK (kategori IN ('RUTIN', 'TEMPORER')),
        tanggal_mulai      TEXT,
        tanggal_selesai    TEXT,
        dinonaktifkan      INTEGER NOT NULL DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS jadwal (
        id_jadwal   INTEGER PRIMARY KEY AUTOINCREMENT,
        id_obat     INTEGER NOT NULL
                    REFERENCES obat(id_obat) ON DELETE CASCADE,
        waktu_minum TEXT NOT NULL,
        aktif       INTEGER NOT NULL
    );
    CREATE TABLE IF NOT EXISTS riwayat (
        id_riwayat      INTEGER PRIMARY KEY AUTOINCREMENT,
        id_jadwal       INTEGER NOT NULL
                        REFERENCES jadwal(id_jadwal) ON DELETE CASCADE,
        waktu_terjadwal TEXT NOT NULL,
        waktu_aktual    TEXT,
        status          TEXT NOT NULL,
        keterangan      TEXT NOT NULL DEFAULT '',
        ditunda_sampai  TEXT,
        UNIQUE (id_jadwal, waktu_terjadwal)
    );
    """

    def __init__(self, path="medremind.db"):
        self.__koneksi = sqlite3.connect(path)
        self.__koneksi.row_factory = sqlite3.Row
        self.__koneksi.execute("PRAGMA foreign_keys = ON")
        with self.__koneksi:
            self.__koneksi.executescript(self.SKEMA)

    def tutup(self):
        self.__koneksi.close()

    # ================= pembantu internal =================
    def __tulis(self, sql, params=()):
        """Jalankan INSERT/UPDATE/DELETE; commit jika sukses, rollback jika gagal."""
        with self.__koneksi:
            return self.__koneksi.execute(sql, params)

    def __satu(self, sql, params=()):
        return self.__koneksi.execute(sql, params).fetchone()

    def __semua(self, sql, params=()):
        return self.__koneksi.execute(sql, params).fetchall()

    @staticmethod
    def __iso(nilai):
        return None if nilai is None else nilai.isoformat(timespec="seconds")

    @staticmethod
    def __ke_datetime(teks):
        return None if teks is None else datetime.fromisoformat(teks)

    @staticmethod
    def __pastikan_ada(kursor, pesan):
        if kursor.rowcount == 0:
            raise ValueError(pesan)

    # ================= pengguna & pengaturan =================
    def __upsert_pengaturan(self, id_pengguna, pengaturan):
        data = pengaturan.to_dict()
        data["id_pengguna"] = id_pengguna
        self.__koneksi.execute(
            """INSERT OR REPLACE INTO pengaturan
               (id_pengguna, pengingat_bersuara, jenis_suara, volume,
                jumlah_bunyi, durasi_tunda, batas_stok_menipis,
                peringatan_beranda, periode_bawaan, sertakan_keterangan)
               VALUES (:id_pengguna, :pengingat_bersuara, :jenis_suara, :volume,
                :jumlah_bunyi, :durasi_tunda, :batas_stok_menipis,
                :peringatan_beranda, :periode_bawaan, :sertakan_keterangan)""",
            data)

    def tambah_pengguna(self, pengguna):
        try:
            with self.__koneksi:  # satu transaksi: pengguna + pengaturannya
                kursor = self.__koneksi.execute(
                    "INSERT INTO pengguna (username, password_hash) VALUES (?, ?)",
                    (pengguna.username, pengguna.password_hash))
                id_baru = kursor.lastrowid
                self.__upsert_pengaturan(id_baru, pengguna.pengaturan)
        except sqlite3.IntegrityError:
            raise ValueError("Nama pengguna sudah dipakai.")
        return self.ambil_pengguna(id_baru)

    def ambil_pengguna(self, id_pengguna):
        baris = self.__satu("SELECT * FROM pengguna WHERE id_pengguna = ?",
                            (id_pengguna,))
        if baris is None:
            return None
        pengaturan = self.ambil_pengaturan(id_pengguna)
        pengguna = Pengguna(baris["id_pengguna"], baris["username"],
                            baris["password_hash"], pengaturan)
        for obat in self.daftar_obat(id_pengguna):
            pengguna.tambah_obat(obat)
        return pengguna

    def ambil_pengguna_by_username(self, username):
        username = username.strip().lower() if isinstance(username, str) else ""
        baris = self.__satu("SELECT id_pengguna FROM pengguna WHERE username = ?",
                            (username,))
        return None if baris is None else self.ambil_pengguna(baris["id_pengguna"])

    def ubah_pengguna(self, pengguna):
        """Simpan username dan password_hash (mis. setelah ubah_password)."""
        try:
            kursor = self.__tulis(
                "UPDATE pengguna SET username = ?, password_hash = ? "
                "WHERE id_pengguna = ?",
                (pengguna.username, pengguna.password_hash, pengguna.id_pengguna))
        except sqlite3.IntegrityError:
            raise ValueError("Nama pengguna sudah dipakai.")
        self.__pastikan_ada(kursor, "Pengguna tidak ditemukan.")

    def hapus_pengguna(self, id_pengguna):
        kursor = self.__tulis("DELETE FROM pengguna WHERE id_pengguna = ?",
                              (id_pengguna,))
        self.__pastikan_ada(kursor, "Pengguna tidak ditemukan.")

    def ambil_pengaturan(self, id_pengguna):
        baris = self.__satu("SELECT * FROM pengaturan WHERE id_pengguna = ?",
                            (id_pengguna,))
        if baris is None:
            return Pengaturan()
        return Pengaturan(
            pengingat_bersuara=bool(baris["pengingat_bersuara"]),
            jenis_suara=baris["jenis_suara"],
            volume=baris["volume"],
            jumlah_bunyi=baris["jumlah_bunyi"],
            durasi_tunda=baris["durasi_tunda"],
            batas_stok_menipis=baris["batas_stok_menipis"],
            peringatan_beranda=bool(baris["peringatan_beranda"]),
            periode_bawaan=baris["periode_bawaan"],
            sertakan_keterangan=bool(baris["sertakan_keterangan"]))

    def simpan_pengaturan(self, id_pengguna, pengaturan):
        try:
            with self.__koneksi:
                self.__upsert_pengaturan(id_pengguna, pengaturan)
        except sqlite3.IntegrityError:
            raise ValueError("Pengguna tidak ditemukan.")

    # ================= obat =================
    @staticmethod
    def __kolom_kategori(obat):
        """Kategori dan kolom tanggal. Jika kelak ada jenis obat baru,
        cukup tambahkan cabangnya di sini dan di __bangun_obat()."""
        if isinstance(obat, ObatTemporer):
            return ("TEMPORER", obat.tanggal_mulai.isoformat(),
                    obat.tanggal_selesai.isoformat())
        return ("RUTIN", None, None)

    @staticmethod
    def __bangun_obat(baris):
        umum = (baris["id_obat"], baris["nama_obat"], baris["kekuatan_dosis"],
                baris["jumlah_per_minum"], baris["satuan"], baris["stok"])
        batas = baris["batas_stok_minimum"]
        nonaktif = bool(baris["dinonaktifkan"])
        if baris["kategori"] == "TEMPORER":
            return ObatTemporer(*umum,
                                date.fromisoformat(baris["tanggal_mulai"]),
                                date.fromisoformat(baris["tanggal_selesai"]),
                                batas, nonaktif)
        return ObatRutin(*umum, batas, nonaktif)
    

    def tambah_obat(self, id_pengguna, obat):
        kategori, mulai, selesai = self.__kolom_kategori(obat)
        try:
            kursor = self.__tulis(
                """INSERT INTO obat (id_pengguna, nama_obat, kekuatan_dosis,
                   jumlah_per_minum, satuan, stok, batas_stok_minimum,
                   kategori, tanggal_mulai, tanggal_selesai, dinonaktifkan)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (id_pengguna, obat.nama, obat.kekuatan_dosis,
                 obat.jumlah_per_minum, obat.satuan, obat.stok,
                 obat.batas_stok_minimum, kategori, mulai, selesai,
                 int(obat.dinonaktifkan)))
        except sqlite3.IntegrityError:
            raise ValueError("Pengguna tidak ditemukan.")
        return self.ambil_obat(kursor.lastrowid)

    def ambil_obat(self, id_obat):
        baris = self.__satu("SELECT * FROM obat WHERE id_obat = ?", (id_obat,))
        return None if baris is None else self.__bangun_obat(baris)

    def daftar_obat(self, id_pengguna, termasuk_nonaktif=True):
        sql = "SELECT * FROM obat WHERE id_pengguna = ?"
        if not termasuk_nonaktif:
            sql += " AND dinonaktifkan = 0"
        baris = self.__semua(sql + " ORDER BY id_obat", (id_pengguna,))
        return [self.__bangun_obat(b) for b in baris]

    def ubah_obat(self, obat):
        """Simpan seluruh isi objek. Untuk mengganti kategori, buat objek
        ObatRutin/ObatTemporer baru dengan id_obat yang sama."""
        kategori, mulai, selesai = self.__kolom_kategori(obat)
        kursor = self.__tulis(
            """UPDATE obat SET nama_obat = ?, kekuatan_dosis = ?,
               jumlah_per_minum = ?, satuan = ?, stok = ?,
               batas_stok_minimum = ?, kategori = ?,
               tanggal_mulai = ?, tanggal_selesai = ?, dinonaktifkan = ?
               WHERE id_obat = ?""",
            (obat.nama, obat.kekuatan_dosis, obat.jumlah_per_minum, obat.satuan,
             obat.stok, obat.batas_stok_minimum, kategori, mulai, selesai,
             int(obat.dinonaktifkan), obat.id_obat))
        self.__pastikan_ada(kursor, "Obat tidak ditemukan.")


    # ================= jadwal =================
    @staticmethod
    def __bangun_jadwal(baris, obat):
        return JadwalPengingat(baris["id_jadwal"], obat,
                               JadwalPengingat.parse_jam(baris["waktu_minum"]),
                               bool(baris["aktif"]))

    def tambah_jadwal(self, jadwal):
        try:
            kursor = self.__tulis(
                "INSERT INTO jadwal (id_obat, waktu_minum, aktif) VALUES (?, ?, ?)",
                (jadwal.obat.id_obat, jadwal.waktu_text(), int(jadwal.aktif)))
        except sqlite3.IntegrityError:
            raise ValueError("Obat tidak ditemukan.")
        return self.ambil_jadwal(kursor.lastrowid)

    def ambil_jadwal(self, id_jadwal):
        baris = self.__satu("SELECT * FROM jadwal WHERE id_jadwal = ?",
                            (id_jadwal,))
        if baris is None:
            return None
        return self.__bangun_jadwal(baris, self.ambil_obat(baris["id_obat"]))

    def daftar_jadwal(self, id_obat):
        obat = self.ambil_obat(id_obat)
        if obat is None:
            return []
        baris = self.__semua(
            "SELECT * FROM jadwal WHERE id_obat = ? ORDER BY waktu_minum",
            (id_obat,))
        return [self.__bangun_jadwal(b, obat) for b in baris]

    def daftar_jadwal_pengguna(self, id_pengguna):
        """Semua jadwal dari semua obat milik pengguna, urut jam."""
        obat_by_id = {o.id_obat: o for o in self.daftar_obat(id_pengguna)}
        baris = self.__semua(
            """SELECT j.* FROM jadwal j JOIN obat o ON o.id_obat = j.id_obat
               WHERE o.id_pengguna = ? ORDER BY j.waktu_minum, j.id_jadwal""",
            (id_pengguna,))
        return [self.__bangun_jadwal(b, obat_by_id[b["id_obat"]]) for b in baris]

    def ubah_jadwal(self, jadwal):
        kursor = self.__tulis(
            "UPDATE jadwal SET waktu_minum = ?, aktif = ? WHERE id_jadwal = ?",
            (jadwal.waktu_text(), int(jadwal.aktif), jadwal.id_jadwal))
        self.__pastikan_ada(kursor, "Jadwal tidak ditemukan.")

    def hapus_jadwal(self, id_jadwal):
        kursor = self.__tulis("DELETE FROM jadwal WHERE id_jadwal = ?",
                              (id_jadwal,))
        self.__pastikan_ada(kursor, "Jadwal tidak ditemukan.")

    # ================= riwayat =================
    def __bangun_riwayat(self, baris, jadwal):
        return RiwayatKonsumsi(
            baris["id_riwayat"], jadwal,
            datetime.fromisoformat(baris["waktu_terjadwal"]),
            StatusKonsumsi[baris["status"]],
            self.__ke_datetime(baris["waktu_aktual"]),
            baris["keterangan"],
            self.__ke_datetime(baris["ditunda_sampai"]))

    def tambah_riwayat(self, riwayat):
        try:
            kursor = self.__tulis(
                """INSERT INTO riwayat (id_jadwal, waktu_terjadwal, waktu_aktual,
                   status, keterangan, ditunda_sampai)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (riwayat.jadwal.id_jadwal, self.__iso(riwayat.waktu_terjadwal),
                 self.__iso(riwayat.waktu_aktual), riwayat.status.name,
                 riwayat.keterangan, self.__iso(riwayat.ditunda_sampai)))
        except sqlite3.IntegrityError as galat:
            if "UNIQUE" in str(galat):
                raise ValueError(
                    "Riwayat untuk jadwal dan waktu ini sudah ada.")
            raise ValueError("Jadwal tidak ditemukan.")
        return self.ambil_riwayat(kursor.lastrowid)

    def ambil_riwayat(self, id_riwayat):
        baris = self.__satu("SELECT * FROM riwayat WHERE id_riwayat = ?",
                            (id_riwayat,))
        if baris is None:
            return None
        return self.__bangun_riwayat(baris, self.ambil_jadwal(baris["id_jadwal"]))

    def ubah_riwayat(self, riwayat):
        kursor = self.__tulis(
            """UPDATE riwayat SET waktu_aktual = ?, status = ?, keterangan = ?,
               ditunda_sampai = ? WHERE id_riwayat = ?""",
            (self.__iso(riwayat.waktu_aktual), riwayat.status.name,
             riwayat.keterangan, self.__iso(riwayat.ditunda_sampai),
             riwayat.id_riwayat))
        self.__pastikan_ada(kursor, "Riwayat tidak ditemukan.")

    def daftar_riwayat(self, id_pengguna, dari=None, sampai=None):
        """Riwayat milik pengguna, terbaru dulu. dari/sampai (datetime) opsional
        dan bersifat inklusif."""
        sql = """SELECT r.* FROM riwayat r
                 JOIN jadwal j ON j.id_jadwal = r.id_jadwal
                 JOIN obat o ON o.id_obat = j.id_obat
                 WHERE o.id_pengguna = ?"""
        params = [id_pengguna]
        if dari is not None:
            sql += " AND r.waktu_terjadwal >= ?"
            params.append(self.__iso(dari))
        if sampai is not None:
            sql += " AND r.waktu_terjadwal <= ?"
            params.append(self.__iso(sampai))
        sql += " ORDER BY r.waktu_terjadwal DESC, r.id_riwayat DESC"
        jadwal_by_id = {j.id_jadwal: j
                        for j in self.daftar_jadwal_pengguna(id_pengguna)}
        return [self.__bangun_riwayat(b, jadwal_by_id[b["id_jadwal"]])
                for b in self.__semua(sql, params)]

    def daftar_riwayat_tertunda(self, id_pengguna):
        """Riwayat yang belum final (Menunggu atau Ditunda), terlama dulu."""
        jadwal_by_id = {j.id_jadwal: j
                        for j in self.daftar_jadwal_pengguna(id_pengguna)}
        baris = self.__semua(
            """SELECT r.* FROM riwayat r
               JOIN jadwal j ON j.id_jadwal = r.id_jadwal
               JOIN obat o ON o.id_obat = j.id_obat
               WHERE o.id_pengguna = ? AND r.status IN ('MENUNGGU', 'DITUNDA')
               ORDER BY r.waktu_terjadwal, r.id_riwayat""",
            (id_pengguna,))
        return [self.__bangun_riwayat(b, jadwal_by_id[b["id_jadwal"]])
                for b in baris]
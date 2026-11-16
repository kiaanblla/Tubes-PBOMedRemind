"""
database.py - Penyimpanan data MedRemind ke SQLite.

DatabaseManager adalah SATU-SATUNYA kelas yang bicara langsung dengan SQL.
Kelas lain (Obat, JadwalPengingat, dst.) tidak perlu tahu soal SQL. Itu
penerapan abstraksi: kalau database diganti, yang diubah cukup file ini.

Tabel (sesuai skema di proposal): pengguna, obat, jadwal, riwayat.
Pewarisan Obat disimpan dalam satu tabel, dibedakan oleh kolom `kategori`
(RUTIN / TEMPORER).
"""

import sqlite3
from datetime import date, datetime, time

from obat import Obat, ObatRutin, ObatTemporer
from jadwal import JadwalPengingat, RiwayatKonsumsi, StatusKonsumsi

# Nama tabel -> nama kolom id-nya. Dipakai juga sebagai daftar tabel yang
# diizinkan, supaya nama tabel dari luar tidak bisa disisipi perintah SQL.
_KOLOM_ID = {
    "obat": "id_obat",
    "jadwal": "id_jadwal",
    "riwayat": "id_riwayat",
}


class DatabaseManager:
    """Mengelola koneksi SQLite dan operasi simpan / ambil / ubah / hapus."""

    def __init__(self, nama_file: str = "medremind.db"):
        self.__nama_file = nama_file
        self.__koneksi = sqlite3.connect(nama_file)
        self.__koneksi.row_factory = sqlite3.Row
        # SQLite tidak mengaktifkan foreign key secara bawaan.
        self.__koneksi.execute("PRAGMA foreign_keys = ON")
        self.buatTabel()

    # ------------------------------------------------------------------
    # Pembuatan tabel
    # ------------------------------------------------------------------
    def buatTabel(self) -> None:
        """Membuat tabel jika belum ada (aman dipanggil berkali-kali)."""
        with self.__koneksi:
            self.__koneksi.executescript("""
                CREATE TABLE IF NOT EXISTS pengguna (
                    id_pengguna INTEGER PRIMARY KEY AUTOINCREMENT,
                    nama        TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS obat (
                    id_obat            INTEGER PRIMARY KEY AUTOINCREMENT,
                    id_pengguna        INTEGER NOT NULL DEFAULT 1
                                       REFERENCES pengguna(id_pengguna),
                    nama_obat          TEXT NOT NULL,
                    kekuatan_dosis     TEXT NOT NULL,
                    jumlah_per_minum   INTEGER NOT NULL,
                    satuan             TEXT NOT NULL,
                    stok               INTEGER NOT NULL,
                    batas_stok_minimum INTEGER NOT NULL,
                    kategori           TEXT NOT NULL
                                       CHECK (kategori IN ('RUTIN', 'TEMPORER')),
                    penyakit_kronis    TEXT,
                    tanggal_mulai      TEXT,
                    tanggal_selesai    TEXT,
                    foto               TEXT NOT NULL DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS jadwal (
                    id_jadwal   INTEGER PRIMARY KEY AUTOINCREMENT,
                    id_obat     INTEGER NOT NULL
                                REFERENCES obat(id_obat) ON DELETE CASCADE,
                    waktu_minum TEXT NOT NULL,
                    aktif       INTEGER NOT NULL DEFAULT 1
                );

                CREATE TABLE IF NOT EXISTS riwayat (
                    id_riwayat      INTEGER PRIMARY KEY AUTOINCREMENT,
                    id_jadwal       INTEGER NOT NULL
                                    REFERENCES jadwal(id_jadwal) ON DELETE CASCADE,
                    waktu_terjadwal TEXT NOT NULL,
                    waktu_aktual    TEXT,
                    status          TEXT NOT NULL
                                    CHECK (status IN ('SUDAH_MINUM', 'DITUNDA', 'DILEWATI')),
                    keterangan      TEXT NOT NULL DEFAULT ''
                );
            """)
            # Aplikasi ini untuk satu pengguna, jadi cukup satu baris bawaan.
            self.__koneksi.execute(
                "INSERT OR IGNORE INTO pengguna (id_pengguna, nama) VALUES (1, 'Pengguna')"
            )
            # Database lama (sebelum ada foto) ditambah kolom foto tanpa kehilangan data.
            kolom = [b["name"] for b in self.__koneksi.execute("PRAGMA table_info(obat)")]
            if "foto" not in kolom:
                self.__koneksi.execute(
                    "ALTER TABLE obat ADD COLUMN foto TEXT NOT NULL DEFAULT ''")

    # ------------------------------------------------------------------
    # Simpan (INSERT)
    # ------------------------------------------------------------------
    def simpan(self, objek) -> int:
        """
        Menyimpan objek baru dan mengembalikan id-nya.
        Kalau id objek None, id dibuatkan otomatis oleh database.
        Contoh: id_obat = db.simpan(obat), lalu pakai id_obat untuk jadwalnya.
        """
        with self.__koneksi:
            if isinstance(objek, Obat):
                kursor = self.__koneksi.execute(
                    """INSERT INTO obat (id_obat, nama_obat, kekuatan_dosis,
                           jumlah_per_minum, satuan, stok, batas_stok_minimum,
                           kategori, penyakit_kronis, tanggal_mulai, tanggal_selesai, foto)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (objek.getIdObat(), *self.__kolomObat(objek)),
                )
            elif isinstance(objek, JadwalPengingat):
                kursor = self.__koneksi.execute(
                    "INSERT INTO jadwal (id_jadwal, id_obat, waktu_minum, aktif) "
                    "VALUES (?, ?, ?, ?)",
                    (objek.getIdJadwal(), objek.getIdObat(),
                     objek.getWaktuMinum().strftime("%H:%M"),
                     int(objek.isAktif())),
                )
            elif isinstance(objek, RiwayatKonsumsi):
                kursor = self.__koneksi.execute(
                    """INSERT INTO riwayat (id_riwayat, id_jadwal, waktu_terjadwal,
                           waktu_aktual, status, keterangan)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (objek.getIdRiwayat(), objek.getIdJadwal(),
                     objek.getWaktuTerjadwal().isoformat(),
                     self.__isoAtauNone(objek.getWaktuAktual()),
                     objek.getStatus().value, objek.getKeterangan()),
                )
            else:
                raise TypeError(f"Tipe objek tidak dikenali: {type(objek).__name__}")
            return kursor.lastrowid

    # ------------------------------------------------------------------
    # Ambil (SELECT)
    # ------------------------------------------------------------------
    def ambilSemua(self, tabel: str) -> list:
        """Mengambil semua baris dari tabel sebagai daftar objek."""
        kolom_id = self.__cekTabel(tabel)
        baris = self.__koneksi.execute(
            f"SELECT * FROM {tabel} ORDER BY {kolom_id}"
        ).fetchall()
        return [self.__barisKeObjek(tabel, b) for b in baris]

    def ambilSatu(self, tabel: str, id_objek: int):
        """Mengambil satu objek berdasarkan id, atau None jika tidak ada."""
        kolom_id = self.__cekTabel(tabel)
        baris = self.__koneksi.execute(
            f"SELECT * FROM {tabel} WHERE {kolom_id} = ?", (id_objek,)
        ).fetchone()
        return self.__barisKeObjek(tabel, baris) if baris else None

    # ------------------------------------------------------------------
    # Ubah (UPDATE)
    # ------------------------------------------------------------------
    def ubah(self, objek) -> bool:
        """Memperbarui baris yang id-nya sama dengan objek. True jika ada yang berubah."""
        with self.__koneksi:
            if isinstance(objek, Obat):
                kursor = self.__koneksi.execute(
                    """UPDATE obat SET nama_obat=?, kekuatan_dosis=?,
                           jumlah_per_minum=?, satuan=?, stok=?, batas_stok_minimum=?,
                           kategori=?, penyakit_kronis=?, tanggal_mulai=?,
                           tanggal_selesai=?, foto=?
                       WHERE id_obat=?""",
                    (*self.__kolomObat(objek), objek.getIdObat()),
                )
            elif isinstance(objek, JadwalPengingat):
                kursor = self.__koneksi.execute(
                    "UPDATE jadwal SET id_obat=?, waktu_minum=?, aktif=? WHERE id_jadwal=?",
                    (objek.getIdObat(), objek.getWaktuMinum().strftime("%H:%M"),
                     int(objek.isAktif()), objek.getIdJadwal()),
                )
            elif isinstance(objek, RiwayatKonsumsi):
                kursor = self.__koneksi.execute(
                    """UPDATE riwayat SET id_jadwal=?, waktu_terjadwal=?,
                           waktu_aktual=?, status=?, keterangan=?
                       WHERE id_riwayat=?""",
                    (objek.getIdJadwal(), objek.getWaktuTerjadwal().isoformat(),
                     self.__isoAtauNone(objek.getWaktuAktual()),
                     objek.getStatus().value, objek.getKeterangan(),
                     objek.getIdRiwayat()),
                )
            else:
                raise TypeError(f"Tipe objek tidak dikenali: {type(objek).__name__}")
            return kursor.rowcount > 0

    # ------------------------------------------------------------------
    # Hapus (DELETE)
    # ------------------------------------------------------------------
    def hapus(self, tabel: str, id_objek: int) -> bool:
        """
        Menghapus satu baris. Menghapus obat ikut menghapus jadwalnya, dan
        menghapus jadwal ikut menghapus riwayatnya (ON DELETE CASCADE).
        """
        kolom_id = self.__cekTabel(tabel)
        with self.__koneksi:
            kursor = self.__koneksi.execute(
                f"DELETE FROM {tabel} WHERE {kolom_id} = ?", (id_objek,)
            )
            return kursor.rowcount > 0

    def tutup(self) -> None:
        """Menutup koneksi. Panggil saat aplikasi ditutup."""
        self.__koneksi.close()

    # ------------------------------------------------------------------
    # Fungsi bantu internal (diawali __ = privat)
    # ------------------------------------------------------------------
    @staticmethod
    def __cekTabel(tabel: str) -> str:
        if tabel not in _KOLOM_ID:
            raise ValueError(
                f"Tabel '{tabel}' tidak dikenal. Pilihan: {', '.join(_KOLOM_ID)}"
            )
        return _KOLOM_ID[tabel]

    @staticmethod
    def __isoAtauNone(nilai):
        return nilai.isoformat() if nilai else None

    @staticmethod
    def __kolomObat(obat: Obat) -> tuple:
        """Kolom obat (tanpa id) dalam urutan yang sama untuk INSERT dan UPDATE."""
        umum = (obat.getNamaObat(), obat.getKekuatanDosis(),
                obat.getJumlahPerMinum(), obat.getSatuan(),
                obat.getStok(), obat.getBatasStokMinimum())
        if isinstance(obat, ObatTemporer):
            return umum + ("TEMPORER", None,
                           obat.getTanggalMulai().isoformat(),
                           obat.getTanggalSelesai().isoformat(),
                           obat.getFoto())
        if isinstance(obat, ObatRutin):
            return umum + ("RUTIN", obat.getPenyakitKronis(), None, None, obat.getFoto())
        raise TypeError(f"Jenis obat tidak dikenali: {type(obat).__name__}")

    @staticmethod
    def __barisKeObjek(tabel: str, b: sqlite3.Row):
        """Mengubah satu baris database menjadi objek yang sesuai."""
        if tabel == "obat":
            umum = (b["id_obat"], b["nama_obat"], b["kekuatan_dosis"],
                    b["jumlah_per_minum"], b["satuan"], b["stok"])
            if b["kategori"] == "TEMPORER":
                return ObatTemporer(
                    *umum,
                    tanggal_mulai=date.fromisoformat(b["tanggal_mulai"]),
                    tanggal_selesai=date.fromisoformat(b["tanggal_selesai"]),
                    batas_stok_minimum=b["batas_stok_minimum"], foto=b["foto"])
            return ObatRutin(*umum, batas_stok_minimum=b["batas_stok_minimum"],
                             penyakit_kronis=b["penyakit_kronis"] or "",
                             foto=b["foto"])
        if tabel == "jadwal":
            return JadwalPengingat(b["id_jadwal"], b["id_obat"],
                                   time.fromisoformat(b["waktu_minum"]),
                                   bool(b["aktif"]))
        # tabel == "riwayat"
        aktual = b["waktu_aktual"]
        return RiwayatKonsumsi(
            b["id_riwayat"], b["id_jadwal"],
            datetime.fromisoformat(b["waktu_terjadwal"]),
            StatusKonsumsi(b["status"]),
            datetime.fromisoformat(aktual) if aktual else None,
            b["keterangan"])


# ----------------------------------------------------------------------
# Demo singkat. Jalankan dengan:  python database.py
# Memakai database sementara di memori, jadi tidak membuat file apa pun.
# Di aplikasi asli: db = DatabaseManager("medremind.db")
# ----------------------------------------------------------------------
if __name__ == "__main__":
    db = DatabaseManager(":memory:")

    # 1. Simpan dua jenis obat (id=None -> dibuatkan otomatis)
    id_amlo = db.simpan(ObatRutin(None, "Amlodipin", "5 mg", 1, "tablet", 30,
                                  penyakit_kronis="Hipertensi"))
    id_amox = db.simpan(ObatTemporer(None, "Amoksisilin", "500 mg", 1, "kapsul", 21,
                                     tanggal_mulai=date(2026, 11, 10),
                                     tanggal_selesai=date(2026, 11, 16)))

    # 2. Simpan jadwal & riwayat
    id_jadwal = db.simpan(JadwalPengingat(None, id_amox, time(13, 0)))
    r = RiwayatKonsumsi(None, id_jadwal, datetime(2026, 11, 11, 13, 0))
    r.catatLog(StatusKonsumsi.SUDAH_MINUM)
    db.simpan(r)

    # 3. Ambil kembali. Tiap baris jadi objek dengan jenis yang benar
    print("== Daftar obat ==")
    for obat in db.ambilSemua("obat"):
        print(type(obat).__name__, "->", obat.getInfo())

    # 4. Ubah: stok berkurang setelah "Sudah Minum", lalu simpan perubahan
    amlo = db.ambilSatu("obat", id_amlo)
    amlo.kurangiStok()
    db.ubah(amlo)
    print("\nStok Amlodipin sekarang:", db.ambilSatu("obat", id_amlo).getStok())

    # 5. Hapus obat -> jadwal & riwayatnya ikut terhapus
    db.hapus("obat", id_amox)
    print("Jadwal tersisa:", len(db.ambilSemua("jadwal")),
          "| Riwayat tersisa:", len(db.ambilSemua("riwayat")))
    db.tutup()
"""
penjadwal.py - Pemantau jadwal dan pemicu notifikasi pada MedRemind.

PenjadwalNotifikasi bertugas:
1. Mengecek jadwal secara berkala (bawaan: tiap 30 detik).
2. Saat waktu jadwal tiba dan obatnya masih aktif, memicu notifikasi.
3. Menangani respons pengguna: "Sudah Minum", "Tunda", atau tidak merespons
   (otomatis dicatat DILEWATI).

Kelas ini TIDAK membuat jendela pop-up sendiri. Tampilan disuplai dari luar
lewat parameter `tampilkan` (dibuat oleh bagian GUI). Dengan begitu:
- logika bisa dites tanpa tampilan,
- tampilan bisa diganti tanpa menyentuh logika.

Contoh pemakaian nanti di aplikasi (GUI):

    root = tk.Tk()
    db = DatabaseManager("medremind.db")

    def munculkan_popup(jadwal, obat):
        ...  # buat jendela dengan tombol "Sudah Minum" dan "Tunda"
        # tombol Sudah Minum -> penjadwal.konfirmasiMinum(jadwal)
        # tombol Tunda       -> penjadwal.tundaPengingat(jadwal)

    penjadwal = PenjadwalNotifikasi(db, root=root, tampilkan=munculkan_popup)
    penjadwal.mulaiPemantauan()
    root.mainloop()
"""

from datetime import datetime, timedelta

from database import DatabaseManager
from jadwal import JadwalPengingat, RiwayatKonsumsi, StatusKonsumsi

# Jika pengguna tidak merespons sampai 30 menit setelah jadwal,
# kejadian dicatat sebagai DILEWATI.
BATAS_LEWAT_MENIT = 30


class PenjadwalNotifikasi:
    """Memantau jadwal, memicu notifikasi, dan mencatat responsnya."""

    def __init__(self, db: DatabaseManager, root=None,
                 interval_cek: int = 30, menit_tunda: int = 10,
                 tampilkan=None, jam=datetime.now):
        """
        db           : DatabaseManager yang dipakai.
        root         : jendela utama Tkinter (hanya perlu untuk mulaiPemantauan()).
        interval_cek : seberapa sering jadwal dicek, dalam detik.
        menit_tunda  : lama penundaan saat pengguna menekan "Tunda".
        tampilkan    : fungsi(jadwal, obat) yang menampilkan notifikasi.
                       Jika kosong, notifikasi hanya dicetak di terminal.
        jam          : fungsi yang mengembalikan waktu sekarang (diganti saat
                       tes supaya waktu bisa "dipercepat").
        """
        if interval_cek <= 0 or menit_tunda <= 0:
            raise ValueError("interval_cek dan menit_tunda harus lebih dari 0.")
        self.__db = db
        self.__root = root
        self.__interval_cek = interval_cek
        self.__menit_tunda = menit_tunda
        self.__tampilkan = tampilkan or self.__tampilkanDiTerminal
        self.__jam = jam

        self.__id_after = None          # penanda timer Tkinter
        self.__sudah_dipicu = set()     # (id_jadwal, waktu_terjadwal): cegah notifikasi ganda
        self.__menunggu = {}            # id_jadwal -> data pengingat yang belum direspons

    # ------------------------------------------------------------------
    # Pemantauan berkala (memakai timer Tkinter, bukan thread terpisah)
    # ------------------------------------------------------------------
    def mulaiPemantauan(self) -> None:
        """Mulai mengecek jadwal setiap `interval_cek` detik."""
        if self.__root is None:
            raise RuntimeError("mulaiPemantauan() butuh root Tkinter. "
                               "Isi parameter root saat membuat PenjadwalNotifikasi.")
        if self.__id_after is None:
            self.__tik()

    def hentikanPemantauan(self) -> None:
        """Berhenti mengecek jadwal (panggil saat aplikasi ditutup)."""
        if self.__id_after is not None and self.__root is not None:
            self.__root.after_cancel(self.__id_after)
        self.__id_after = None

    def __tik(self) -> None:
        self.periksaJadwal(self.__jam())
        self.__id_after = self.__root.after(self.__interval_cek * 1000, self.__tik)

    # ------------------------------------------------------------------
    # Inti logika: dipanggil tiap tik (dan langsung dari tes)
    # ------------------------------------------------------------------
    def periksaJadwal(self, sekarang: datetime) -> None:
        """Satu putaran pengecekan pada waktu `sekarang`."""
        self.__bersihkanPenanda(sekarang)

        # 1. Pengingat yang sudah terlalu lama tidak direspons -> DILEWATI
        for id_jadwal, data in list(self.__menunggu.items()):
            if sekarang > data["terjadwal"] + timedelta(minutes=BATAS_LEWAT_MENIT):
                self.__catatRiwayat(id_jadwal, data["terjadwal"],
                                    StatusKonsumsi.DILEWATI,
                                    "Tidak ada respons")
                del self.__menunggu[id_jadwal]

        # 2. Jadwal yang waktunya tiba
        menit_ini = sekarang.replace(second=0, microsecond=0)
        for jadwal in self.__db.ambilSemua("jadwal"):
            kunci = (jadwal.getIdJadwal(), menit_ini)
            if kunci in self.__sudah_dipicu:
                continue                      # menit ini sudah dipicu (cek tiap 30 detik)
            if not jadwal.waktuTiba(sekarang.time()):
                continue
            obat = self.__db.ambilSatu("obat", jadwal.getIdObat())
            if obat is None or not obat.isAktif(sekarang.date()):
                continue                      # obat dihapus atau masa terapi selesai
            self.__sudah_dipicu.add(kunci)
            self.__menunggu[jadwal.getIdJadwal()] = {
                "terjadwal": menit_ini, "tunda_sampai": None}
            self.tampilkanNotifikasi(jadwal)

        # 3. Penundaan yang waktunya habis -> ingatkan lagi
        for id_jadwal, data in list(self.__menunggu.items()):
            if data["tunda_sampai"] and sekarang >= data["tunda_sampai"]:
                data["tunda_sampai"] = None
                jadwal = self.__db.ambilSatu("jadwal", id_jadwal)
                if jadwal is not None:
                    self.tampilkanNotifikasi(jadwal)

    # ------------------------------------------------------------------
    # Notifikasi dan respons pengguna
    # ------------------------------------------------------------------
    def tampilkanNotifikasi(self, jadwal: JadwalPengingat) -> None:
        """Meminta tampilan untuk memunculkan notifikasi jadwal ini."""
        obat = self.__db.ambilSatu("obat", jadwal.getIdObat())
        if obat is not None:
            self.__tampilkan(jadwal, obat)

    def konfirmasiMinum(self, jadwal: JadwalPengingat) -> None:
        """
        Pengguna menekan "Sudah Minum": stok berkurang dan riwayat tercatat.
        """
        data = self.__ambilMenunggu(jadwal)
        obat = self.__db.ambilSatu("obat", jadwal.getIdObat())
        if obat is not None:
            obat.kurangiStok()
            self.__db.ubah(obat)
        self.__catatRiwayat(jadwal.getIdJadwal(), data["terjadwal"],
                            StatusKonsumsi.SUDAH_MINUM)
        del self.__menunggu[jadwal.getIdJadwal()]

    def tundaPengingat(self, jadwal: JadwalPengingat) -> None:
        """
        Pengguna menekan "Tunda": diingatkan lagi setelah `menit_tunda` menit
        dan kejadian dicatat sebagai DITUNDA.
        """
        data = self.__ambilMenunggu(jadwal)
        sekarang = self.__jam()
        data["tunda_sampai"] = sekarang + timedelta(minutes=self.__menit_tunda)
        self.__catatRiwayat(jadwal.getIdJadwal(), data["terjadwal"],
                            StatusKonsumsi.DITUNDA,
                            f"Ditunda {self.__menit_tunda} menit")

    def lewatiPengingat(self, jadwal: JadwalPengingat) -> None:
        """
        Pengguna tidak merespons (popup habis waktu): langsung dicatat DILEWATI,
        tanpa menunggu batas BATAS_LEWAT_MENIT.
        """
        data = self.__ambilMenunggu(jadwal)
        self.__catatRiwayat(jadwal.getIdJadwal(), data["terjadwal"],
                            StatusKonsumsi.DILEWATI, "Tidak ada respons")
        del self.__menunggu[jadwal.getIdJadwal()]

    # ------------------------------------------------------------------
    # Fungsi bantu internal
    # ------------------------------------------------------------------
    def __ambilMenunggu(self, jadwal: JadwalPengingat) -> dict:
        data = self.__menunggu.get(jadwal.getIdJadwal())
        if data is None:
            raise LookupError("Tidak ada pengingat yang sedang menunggu untuk jadwal ini.")
        return data

    def __catatRiwayat(self, id_jadwal: int, terjadwal: datetime,
                       status: StatusKonsumsi, keterangan: str = "") -> None:
        # Jika obat/jadwal dihapus saat pengingat masih menunggu, jadwalnya
        # sudah tidak ada di database (ikut terhapus), jadi tidak ada yang dicatat.
        if self.__db.ambilSatu("jadwal", id_jadwal) is None:
            return
        riwayat = RiwayatKonsumsi(None, id_jadwal, terjadwal)
        riwayat.catatLog(status, keterangan, waktu_aktual=self.__jam())
        self.__db.simpan(riwayat)

    def __bersihkanPenanda(self, sekarang: datetime) -> None:
        """Menghapus penanda lama supaya himpunan tidak membesar terus."""
        batas = sekarang - timedelta(days=1)
        self.__sudah_dipicu = {k for k in self.__sudah_dipicu if k[1] > batas}

    @staticmethod
    def __tampilkanDiTerminal(jadwal: JadwalPengingat, obat) -> None:
        print(f"[PENGINGAT] Waktunya minum {obat.getNamaObat()} "
              f"{obat.getKekuatanDosis()} ({obat.getJumlahPerMinum()} "
              f"{obat.getSatuan()}) - jadwal {jadwal.getWaktuMinum():%H:%M}")


# ----------------------------------------------------------------------
# Demo tanpa tampilan. Jalankan dengan:  python penjadwal.py
# Waktu "dipercepat" dengan jam palsu, jadi hasilnya langsung terlihat.
# ----------------------------------------------------------------------
if __name__ == "__main__":
    from datetime import date, time
    from obat import ObatRutin, ObatTemporer

    waktu = {"kini": datetime(2026, 11, 11, 12, 59, 0)}
    db = DatabaseManager(":memory:")

    id_obat = db.simpan(ObatRutin(None, "Amlodipin", "5 mg", 1, "tablet", 30))
    id_temp = db.simpan(ObatTemporer(None, "Amoksisilin", "500 mg", 1, "kapsul", 21,
                                     date(2026, 11, 1), date(2026, 11, 5)))  # sudah lewat
    j_rutin = db.simpan(JadwalPengingat(None, id_obat, time(13, 0)))
    j_malam = db.simpan(JadwalPengingat(None, id_obat, time(19, 0)))
    db.simpan(JadwalPengingat(None, id_temp, time(13, 0)))  # tidak boleh memicu

    penjadwal = PenjadwalNotifikasi(db, jam=lambda: waktu["kini"])

    def maju(menit=0, detik=0):
        waktu["kini"] += timedelta(minutes=menit, seconds=detik)
        penjadwal.periksaJadwal(waktu["kini"])
        print(f"  ({waktu['kini']:%H:%M:%S})")

    print("12:59 -> belum ada pengingat")
    maju(0)
    print("13:00 -> pengingat Amlodipin (Amoksisilin tidak muncul: masa terapi lewat)")
    maju(1)
    print("13:00:30 -> tidak boleh muncul dua kali")
    maju(detik=30)

    jadwal = db.ambilSatu("jadwal", j_rutin)
    print("Pengguna menekan TUNDA")
    penjadwal.tundaPengingat(jadwal)
    print("13:10 -> diingatkan lagi")
    maju(9, 30)
    print("Pengguna menekan SUDAH MINUM")
    penjadwal.konfirmasiMinum(jadwal)
    print("Stok Amlodipin sekarang:", db.ambilSatu("obat", id_obat).getStok())

    print("19:00 -> pengingat malam, pengguna tidak merespons")
    waktu["kini"] = datetime(2026, 11, 11, 18, 59, 0)
    maju(1)
    print("19:31 -> lewat 30 menit, otomatis DILEWATI")
    maju(31)

    print("\nRiwayat tercatat:")
    for r in db.ambilSemua("riwayat"):
        print(" ", r, "|", r.getKeterangan())
    db.tutup()
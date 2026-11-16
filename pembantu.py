"""
pembantu.py - Fungsi bantu untuk tampilan MedRemind (tanpa Tkinter).

Semua logika yang tidak berhubungan dengan jendela ditaruh di sini:
membaca isian formulir, mengecek input, menyusun jadwal hari ini, dan
menyusun ringkasan riwayat. Dengan begitu, gui.py cukup mengurus tampilan
dan bagian ini bisa dites tanpa membuka jendela.
"""

import re
from datetime import date, datetime, time, timedelta

from obat import Obat, ObatRutin, ObatTemporer
from jadwal import JadwalPengingat, RiwayatKonsumsi, StatusKonsumsi

NAMA_HARI = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
NAMA_BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli",
              "Agustus", "September", "Oktober", "November", "Desember"]

LABEL_STATUS = {
    StatusKonsumsi.SUDAH_MINUM: "Sudah minum",
    StatusKonsumsi.DITUNDA: "Ditunda",
    StatusKonsumsi.DILEWATI: "Terlewat",
}


# ----------------------------------------------------------------------
# Membaca dan mengecek isian formulir
# ----------------------------------------------------------------------
def parseJam(teks: str) -> time:
    """'07:30' atau '7.30' -> time(7, 30)."""
    cocok = re.fullmatch(r"\s*(\d{1,2})[:.](\d{2})\s*", teks or "")
    if not cocok or int(cocok.group(1)) > 23 or int(cocok.group(2)) > 59:
        raise ValueError(f"Jam '{(teks or '').strip()}' tidak valid. "
                         "Gunakan format JJ:MM, contoh 07:30.")
    return time(int(cocok.group(1)), int(cocok.group(2)))


def parseDaftarJam(teks: str) -> list:
    """'07:00, 13:00, 19:00' -> [time(7,0), time(13,0), time(19,0)] (urut, tanpa dobel)."""
    bagian = [b for b in re.split(r"[,;\s]+", (teks or "").strip()) if b]
    if not bagian:
        raise ValueError("Isi minimal satu jam pengingat, contoh 07:00, 13:00.")
    return sorted({parseJam(b) for b in bagian})


def parseTanggal(teks: str, nama: str = "Tanggal") -> date:
    """'16/11/2026' -> date(2026, 11, 16)."""
    try:
        return datetime.strptime((teks or "").strip(), "%d/%m/%Y").date()
    except ValueError:
        raise ValueError(f"{nama} tidak valid. Gunakan format HH/BB/TTTT, "
                         "contoh 16/11/2026.") from None


def formatTanggal(tgl: date) -> str:
    return tgl.strftime("%d/%m/%Y")


def parseAngka(teks: str, nama: str, minimum: int) -> int:
    try:
        nilai = int((teks or "").strip())
    except ValueError:
        raise ValueError(f"{nama} harus berupa angka bulat.") from None
    if nilai < minimum:
        raise ValueError(f"{nama} minimal {minimum}.")
    return nilai


def bangunObat(id_obat, d: dict) -> Obat:
    """
    Membuat ObatRutin atau ObatTemporer dari isian formulir (semua teks).
    Kunci d: nama, kekuatan, jumlah, satuan, stok, batas, kategori,
             penyakit, mulai, selesai, foto (path foto, boleh kosong).
    Melempar ValueError dengan pesan yang bisa langsung ditampilkan.
    """
    nama = (d.get("nama") or "").strip()
    kekuatan = (d.get("kekuatan") or "").strip()
    satuan = (d.get("satuan") or "").strip()
    if not nama:
        raise ValueError("Nama obat tidak boleh kosong.")
    if not kekuatan:
        raise ValueError("Kekuatan dosis tidak boleh kosong, contoh 500 mg.")
    if not satuan:
        raise ValueError("Satuan tidak boleh kosong, contoh tablet.")
    jumlah = parseAngka(d.get("jumlah"), "Jumlah per minum", 1)
    stok = parseAngka(d.get("stok"), "Stok", 0)
    batas = parseAngka(d.get("batas"), "Batas stok minimum", 0)
    foto = (d.get("foto") or "").strip()

    if d.get("kategori") == "TEMPORER":
        mulai = parseTanggal(d.get("mulai"), "Tanggal mulai")
        selesai = parseTanggal(d.get("selesai"), "Tanggal selesai")
        return ObatTemporer(id_obat, nama, kekuatan, jumlah, satuan, stok,
                            tanggal_mulai=mulai, tanggal_selesai=selesai,
                            batas_stok_minimum=batas, foto=foto)
    return ObatRutin(id_obat, nama, kekuatan, jumlah, satuan, stok,
                     batas_stok_minimum=batas,
                     penyakit_kronis=(d.get("penyakit") or "").strip(), foto=foto)


# ----------------------------------------------------------------------
# Jadwal milik satu obat
# ----------------------------------------------------------------------
def jamAktif(db, id_obat: int) -> list:
    """Daftar jam (urut) dari jadwal AKTIF milik obat ini."""
    return sorted(j.getWaktuMinum() for j in db.ambilSemua("jadwal")
                  if j.getIdObat() == id_obat and j.isAktif())


def sinkronkanJadwal(db, id_obat: int, daftar_jam: list) -> None:
    """
    Menyamakan jadwal di database dengan daftar jam dari formulir.
    - Jam baru           -> dibuat.
    - Jam yang dihapus   -> DINONAKTIFKAN (bukan dihapus, supaya riwayatnya aman).
    - Jam lama muncul lagi -> diaktifkan kembali.
    """
    ada = {}
    for j in db.ambilSemua("jadwal"):
        if j.getIdObat() == id_obat:
            w = j.getWaktuMinum()
            ada[(w.hour, w.minute)] = j
    baru = {(t.hour, t.minute) for t in daftar_jam}

    for kunci, j in ada.items():
        if kunci in baru and not j.isAktif():
            j.aktifkan()
            db.ubah(j)
        elif kunci not in baru and j.isAktif():
            j.nonaktifkan()
            db.ubah(j)
    for kunci in sorted(baru - set(ada)):
        db.simpan(JadwalPengingat(None, id_obat, time(*kunci)))


# ----------------------------------------------------------------------
# Data untuk dashboard
# ----------------------------------------------------------------------
def judulHari(tgl: date) -> str:
    return f"{NAMA_HARI[tgl.weekday()]}, {tgl.day} {NAMA_BULAN[tgl.month - 1]} {tgl.year}"


def jadwalHariIni(db, hari: date) -> list:
    """
    Daftar baris untuk tabel dashboard, urut berdasarkan jam. Tiap baris:
    {"jam", "nama", "jumlah", "status", "kunci"}; kunci = kode warna baris.
    Hanya jadwal aktif milik obat yang masih aktif pada hari itu.
    """
    obat_by_id = {o.getIdObat(): o for o in db.ambilSemua("obat")}
    terakhir = {}                              # id_jadwal -> riwayat terakhir hari ini
    for r in db.ambilSemua("riwayat"):
        if r.getWaktuTerjadwal().date() == hari:
            terakhir[r.getIdJadwal()] = r      # urut id naik: yang terakhir menang

    baris = []
    for j in db.ambilSemua("jadwal"):
        obat = obat_by_id.get(j.getIdObat())
        if obat is None or not j.isAktif() or not obat.isAktif(hari):
            continue
        r = terakhir.get(j.getIdJadwal())
        status = LABEL_STATUS[r.getStatus()] if r else "Menunggu"
        kunci = r.getStatus().name.lower() if r else "menunggu"
        baris.append({
            "jam": j.getWaktuMinum(),
            "nama": f"{obat.getNamaObat()} {obat.getKekuatanDosis()}",
            "jumlah": f"{obat.getJumlahPerMinum()} {obat.getSatuan()}",
            "status": status,
            "kunci": kunci,
        })
    return sorted(baris, key=lambda b: (b["jam"], b["nama"]))


def peringatanStok(db, hari: date) -> list:
    """Teks peringatan untuk obat aktif yang stoknya sudah menipis."""
    return [f"{o.getNamaObat()} (sisa {o.getStok()} {o.getSatuan()})"
            for o in db.ambilSemua("obat")
            if o.isAktif(hari) and o.stokMenipis()]


# ----------------------------------------------------------------------
# Data untuk jendela riwayat
# ----------------------------------------------------------------------
def ringkasRiwayat(db, hari_ini: date, jumlah_hari) -> tuple:
    """
    Mengembalikan (baris, persen_kepatuhan).
    jumlah_hari: 7, 30, atau None untuk semua riwayat.
    Baris urut dari yang terbaru: (waktu, nama obat, status, keterangan).
    """
    sejak = hari_ini - timedelta(days=jumlah_hari - 1) if jumlah_hari else None
    obat_by_id = {o.getIdObat(): o for o in db.ambilSemua("obat")}
    jadwal_ke_obat = {j.getIdJadwal(): obat_by_id.get(j.getIdObat())
                      for j in db.ambilSemua("jadwal")}

    terpilih = [r for r in db.ambilSemua("riwayat")
                if sejak is None or r.getWaktuTerjadwal().date() >= sejak]
    terpilih.sort(key=lambda r: (r.getWaktuTerjadwal(), r.getIdRiwayat()), reverse=True)

    baris = []
    for r in terpilih:
        obat = jadwal_ke_obat.get(r.getIdJadwal())
        baris.append((r.getWaktuTerjadwal().strftime("%d/%m/%Y %H:%M"),
                      obat.getNamaObat() if obat else "(obat dihapus)",
                      LABEL_STATUS[r.getStatus()],
                      r.getKeterangan()))
    return baris, RiwayatKonsumsi.hitungKepatuhan(terpilih)
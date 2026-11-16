"""
popup.py - Jendela pengingat minum obat, lengkap dengan suara.

Dipanggil oleh pemantau.py saat jadwal tiba. Jendela muncul paling depan dan
bunyinya diulang 5 kali. Jika tidak dijawab dalam 20 detik, popup menutup sendiri
dan kejadian dicatat sebagai terlewat.
"""

import threading
import time
from tkinter import messagebox, ttk

from gui import Jendela, penyimpanFoto, tengahkan

JEDA_SUARA_MS = 4000      # jarak antar bunyi (milidetik)
ULANG_SUARA = 5           # jumlah bunyi tiap popup muncul
BATAS_DETIK = JEDA_SUARA_MS * ULANG_SUARA // 1000   # 20 detik, lalu otomatis terlewat
FREKUENSI_HZ = 1800       # nada tinggi supaya nyaring dan mudah terdengar
_terbuka = []                     # popup yang sedang tampil (agar tidak menumpuk persis)


def bunyi(jendela) -> None:
    """Tiga bunyi 'tit' nyaring (Windows). Di sistem lain memakai bel Tk."""
    try:
        import winsound
    except ImportError:
        jendela.bell()
        return

    def bunyikan():               # di thread sendiri karena Beep menahan program
        try:
            for _ in range(3):
                winsound.Beep(FREKUENSI_HZ, 220)
                time.sleep(0.07)
        except RuntimeError:
            pass

    threading.Thread(target=bunyikan, daemon=True).start()


def munculkanPopup(root, penjadwal, jadwal, obat) -> None:
    p = Jendela(root)
    p.title("Waktunya minum obat")
    p.attributes("-topmost", True)
    p.resizable(False, False)
    isi = ttk.Frame(p, padding=22)
    isi.pack()

    gambar = penyimpanFoto.muat(obat.getFoto(), 140)
    if gambar:
        foto = ttk.Label(isi, image=gambar)
        foto.image = gambar
        foto.pack(pady=(0, 12))
    ttk.Label(isi, text=f"Waktunya minum, {jadwal.getWaktuMinum():%H:%M}",
              font=("Segoe UI Semibold", 13), style="Aksen.TLabel").pack(anchor="w")
    ttk.Label(isi, text=f"{obat.getNamaObat()} {obat.getKekuatanDosis()}",
              font=("Segoe UI Semibold", 12)).pack(anchor="w", pady=(10, 0))
    ttk.Label(isi, text=f"{obat.getJumlahPerMinum()} {obat.getSatuan()}").pack(anchor="w")

    def jawab(aksi):
        try:
            aksi(jadwal)
        except LookupError:       # sudah otomatis tercatat "Terlewat"
            messagebox.showinfo("Pengingat berakhir",
                                "Pengingat ini sudah lewat 30 menit dan dicatat sebagai terlewat.",
                                parent=p)
        p.destroy()

    tombol = ttk.Frame(isi)
    tombol.pack(fill="x", pady=(18, 0))
    ttk.Button(tombol, text="Sudah Minum", style="Utama.TButton",
               command=lambda: jawab(penjadwal.konfirmasiMinum)).pack(side="left")
    ttk.Button(tombol, text="Tunda",
               command=lambda: jawab(penjadwal.tundaPengingat)).pack(side="left", padx=8)
    ttk.Label(isi, style="Redup.TLabel",
              text="Tunda: diingatkan lagi 10 menit kemudian").pack(anchor="w", pady=(10, 0))
    sisa = ttk.Label(isi, style="Redup.TLabel",
                     text=f"Tidak dijawab dalam {BATAS_DETIK} detik = dicatat terlewat")
    sisa.pack(anchor="w", pady=(2, 0))

    geser = 30 * len(_terbuka)
    _terbuka.append(p)
    p.bind("<Destroy>", lambda e: _terbuka.remove(p) if e.widget is p and p in _terbuka else None)
    tengahkan(p, geser=geser)
    p.lift()
    p.focus_force()

    hitung = {"n": 0}

    def ulangiSuara():
        if not p.winfo_exists() or hitung["n"] >= ULANG_SUARA:
            return
        bunyi(p)
        hitung["n"] += 1
        p.after(JEDA_SUARA_MS, ulangiSuara)

    detik = {"sisa": BATAS_DETIK}

    def hitungMundur():
        if not p.winfo_exists():
            return                # sudah dijawab pengguna
        if detik["sisa"] <= 0:    # waktu habis: catat terlewat dan tutup popup
            try:
                penjadwal.lewatiPengingat(jadwal)
            except LookupError:
                pass
            p.destroy()
            return
        sisa.config(text=f"Tidak dijawab dalam {detik['sisa']} detik = dicatat terlewat")
        detik["sisa"] -= 1
        p.after(1000, hitungMundur)

    ulangiSuara()
    hitungMundur()
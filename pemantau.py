"""
pemantau.py - Pemantau pengingat yang berjalan di latar belakang (tanpa jendela).

Berjalan terpisah dari gui.py, sehingga popup dan suara tetap muncul saat
jadwal tiba walaupun jendela utama sudah ditutup. Biasanya dinyalakan otomatis
oleh gui.py; bisa juga dijalankan manual:

    python pemantau.py                    jalankan pemantau
    python pemantau.py --berhenti         hentikan pemantau yang sedang berjalan
    python pemantau.py --pasang-autostart jalan otomatis saat Windows menyala
    python pemantau.py --lepas-autostart  batalkan jalan otomatis

Jika terjadi error, catatannya ada di pemantau.log.
"""

import os
import socket
import sys
import traceback
import tkinter as tk

import latar


def jalankan() -> None:
    pelayan = socket.socket()
    try:
        pelayan.bind(("127.0.0.1", latar.PORT))
    except OSError:
        return                    # pemantau lain sudah berjalan
    pelayan.listen(5)
    pelayan.setblocking(False)

    from database import DatabaseManager
    from penjadwal import PenjadwalNotifikasi
    from gui import terapkanTema
    from popup import munculkanPopup

    root = tk.Tk()
    root.withdraw()               # tidak ada jendela utama, hanya popup
    terapkanTema(root)
    db = DatabaseManager(os.path.join(latar.FOLDER_APP, "medremind.db"))
    penjadwal = PenjadwalNotifikasi(
        db, root=root, tampilkan=lambda j, o: munculkanPopup(root, penjadwal, j, o))
    penjadwal.mulaiPemantauan()

    def cekPerintah():
        try:
            konek, _ = pelayan.accept()
            konek.settimeout(0.5)
            with konek:
                if konek.recv(16) == b"berhenti":
                    penjadwal.hentikanPemantauan()
                    root.destroy()
                    return
        except (BlockingIOError, OSError):
            pass
        root.after(1000, cekPerintah)

    cekPerintah()
    root.mainloop()
    db.tutup()


if __name__ == "__main__":
    perintah = sys.argv[1] if len(sys.argv) > 1 else ""
    if perintah == "--berhenti":
        latar.hentikan()
    elif perintah == "--pasang-autostart":
        latar.pasangAutostart()
        print("Pemantau akan jalan otomatis saat Windows menyala.")
    elif perintah == "--lepas-autostart":
        latar.lepasAutostart()
        print("Jalan otomatis dibatalkan.")
    else:
        try:
            jalankan()
        except Exception:
            with open(os.path.join(latar.FOLDER_APP, "pemantau.log"), "a", encoding="utf-8") as f:
                f.write(traceback.format_exc() + "\n")
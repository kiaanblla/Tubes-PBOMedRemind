"""
latar.py - Kendali pemantau pengingat yang berjalan di latar belakang.

Pemantau (pemantau.py) adalah proses terpisah dari jendela utama, jadi popup
dan suara pengingat tetap muncul walaupun jendela utama ditutup.

File ini sengaja tanpa Tkinter supaya aman diimpor dari mana saja.
"""

import os
import socket
import subprocess
import sys

FOLDER_APP = os.path.dirname(os.path.abspath(__file__))
SKRIP = os.path.join(FOLDER_APP, "pemantau.py")
PORT = 47653                      # port lokal: penanda bahwa pemantau sedang berjalan
_WINDOWS = sys.platform == "win32"


def _hubungi(pesan: bytes = b"") -> bool:
    """Menyambung ke pemantau. True jika ada yang menjawab (pemantau berjalan)."""
    try:
        with socket.create_connection(("127.0.0.1", PORT), timeout=0.5) as s:
            if pesan:
                s.sendall(pesan)
        return True
    except OSError:
        return False


def berjalan() -> bool:
    return _hubungi()


def hentikan() -> None:
    _hubungi(b"berhenti")


def jalankan() -> None:
    """Menyalakan pemantau di latar belakang (tanpa jendela) jika belum berjalan."""
    if berjalan():
        return
    if _WINDOWS:
        opsi = {"creationflags": 0x00000008 | 0x00000200}   # DETACHED_PROCESS | NEW_PROCESS_GROUP
    else:
        opsi = {"start_new_session": True}
    subprocess.Popen([sys.executable, SKRIP], cwd=FOLDER_APP,
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, close_fds=True, **opsi)


# ----------------------------------------------------------------------
# Jalankan otomatis saat Windows menyala (lewat folder Startup)
# ----------------------------------------------------------------------
def _fileAutostart() -> str:
    return os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows",
                        "Start Menu", "Programs", "Startup", "MedRemindPemantau.vbs")


def autostartTersedia() -> bool:
    return _WINDOWS and bool(os.environ.get("APPDATA"))


def autostartAktif() -> bool:
    return autostartTersedia() and os.path.exists(_fileAutostart())


def pasangAutostart() -> None:
    if not autostartTersedia():
        return
    # Gaya jendela 0 = tersembunyi, jadi tidak ada jendela hitam saat Windows menyala.
    isi = ('CreateObject("Wscript.Shell").Run """' + sys.executable + '"" ""'
           + SKRIP + '""", 0, False\n')
    with open(_fileAutostart(), "w", encoding="utf-16") as f:
        f.write(isi)


def lepasAutostart() -> None:
    if autostartAktif():
        os.remove(_fileAutostart())
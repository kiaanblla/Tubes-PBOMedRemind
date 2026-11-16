"""
main.py - Titik masuk aplikasi MedRemind.

Jalankan dengan:  python main.py

Urutan kerjanya:
1. Membuka jendela utama (gui.py).
2. gui.py menyalakan pemantau latar belakang (pemantau.py), sehingga popup
   dan suara pengingat tetap muncul walaupun jendela utama ditutup.
"""

from gui import main

if __name__ == "__main__":
    main()
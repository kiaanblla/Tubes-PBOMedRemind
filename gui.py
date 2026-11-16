"""
gui.py - Tampilan Tkinter untuk MedRemind.

File ini hanya mengurus jendela. Logika ada di pembantu.py (isian & data
tabel), penjadwal.py (pengingat), dan database.py (penyimpanan).

Jalankan dengan:  python gui.py
"""

import os
import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox, simpledialog, ttk
from datetime import date, timedelta

from database import DatabaseManager
from obat import ObatTemporer
import latar
from pengaturan import FOLDER_APP, PengaturanTampilan, PenyimpanFoto
import pembantu as pb

tampilan = PengaturanTampilan()      # warna aktif (disimpan di pengaturan.json)
penyimpanFoto = PenyimpanFoto()      # foto obat (disimpan di folder foto_obat/)
FONT = ("Segoe UI", 10)
FONT_JUDUL = ("Segoe UI Semibold", 16)


def pasangGaris(tabel, warna="#c3c7bf"):
    """
    Menggambar garis pemisah baris dan kolom di atas Treeview, karena Treeview
    tidak punya garis kisi bawaan. Garis digambar ulang lewat tabel.gambarGaris().
    """
    pool = []
    sekarang = {"w": warna}

    def garis(i):
        while len(pool) <= i:
            pool.append(tk.Frame(tabel, bg=sekarang["w"]))
        return pool[i]

    def gambar(*_):
        n = 0
        lebar, tinggi = tabel.winfo_width(), tabel.winfo_height()
        tampak = [(i, tabel.bbox(i)) for i in tabel.get_children()]
        tampak = [b for _, b in tampak if b]
        y0 = tampak[0][1] if tampak else 30           # batas bawah judul kolom
        for _, y, _, h in tampak:                     # garis antar baris
            garis(n).place(x=0, y=y + h - 1, width=lebar, height=1)
            n += 1
        x = 0
        for kol in tabel["columns"][:-1]:             # garis antar kolom
            x += int(tabel.column(kol, "width"))
            garis(n).place(x=x - 1, y=y0, width=1, height=max(0, tinggi - y0))
            n += 1
        for sisa in pool[n:]:
            sisa.place_forget()

    def warnai(w):
        sekarang["w"] = w
        for f in pool:
            f.config(bg=w)

    tabel.warnaiGaris = warnai
    tabel.gambarGaris = lambda: tabel.after_idle(gambar)
    tabel.bind("<Configure>", gambar, add="+")
    tabel.bind("<B1-Motion>", gambar, add="+")        # saat lebar kolom diseret
    tabel.bind("<ButtonRelease-1>", gambar, add="+")
    return gambar


def buatTabel(induk, kolom: dict, tinggi: int = 4) -> ttk.Treeview:
    """Treeview dengan scrollbar. kolom: {nama_kolom: (judul, lebar)}."""
    bingkai = ttk.Frame(induk)
    bingkai.pack(fill="both", expand=True)
    tabel = ttk.Treeview(bingkai, columns=list(kolom), show="headings",
                         height=tinggi, selectmode="browse")
    for nama, (judul, lebar) in kolom.items():
        tabel.heading(nama, text=judul)
        tabel.column(nama, width=lebar, anchor="w")
    gulir = ttk.Scrollbar(bingkai, orient="vertical", command=tabel.yview)
    gambar = pasangGaris(tabel)
    tabel.configure(yscrollcommand=lambda a, b: (gulir.set(a, b), tabel.after_idle(gambar)))
    tabel.pack(side="left", fill="both", expand=True)
    gulir.pack(side="right", fill="y")

    def warnai():
        for kunci in ("menunggu", "sudah_minum", "ditunda", "dilewati"):
            tabel.tag_configure(kunci, background=tampilan.warna(kunci))
        tabel.tag_configure("menipis", foreground=tampilan.warna("bahaya"))
        tabel.warnaiGaris(tampilan.warna("garis"))

    tabel.warnai = warnai
    warnai()
    return tabel


def terapkanTema(root):
    """Menerapkan warna tema aktif ke semua widget yang sudah ada."""
    w = tampilan.warna
    g = ttk.Style()
    g.theme_use("clam")      # tema ini mendukung warna latar baris tabel
    g.configure(".", font=FONT, background=w("bg"), foreground=w("fg"),
                fieldbackground=w("tabel"), bordercolor=w("garis"),
                lightcolor=w("bg"), darkcolor=w("bg"), troughcolor=w("bg"),
                insertcolor=w("fg"))
    g.configure("Redup.TLabel", foreground=w("redup"))
    g.configure("Aksen.TLabel", foreground=w("aksen"))
    g.configure("Treeview", background=w("tabel"), foreground=w("fg"),
                fieldbackground=w("tabel"), rowheight=28)
    g.map("Treeview", background=[("selected", w("aksen"))],
          foreground=[("selected", w("teks_aksen"))])
    g.configure("Treeview.Heading", background=w("header"), foreground=w("fg"),
                font=("Segoe UI Semibold", 10),
                lightcolor=w("header"), darkcolor=w("header"))
    g.configure("TButton", background=w("header"), foreground=w("fg"), padding=(10, 4),
                lightcolor=w("header"), darkcolor=w("header"))
    g.map("TButton", background=[("active", w("garis"))])
    g.configure("Utama.TButton", background=w("aksen"), foreground=w("teks_aksen"),
                padding=(12, 5), lightcolor=w("aksen"), darkcolor=w("aksen"))
    g.map("Utama.TButton", background=[("active", w("aksen_tua"))])
    g.configure("Vertical.TScrollbar", background=w("header"), arrowcolor=w("fg"))
    g.map("TCombobox", fieldbackground=[("readonly", w("tabel"))])
    root.option_add("*TCombobox*Listbox.background", w("tabel"))
    root.option_add("*TCombobox*Listbox.foreground", w("fg"))
    root.configure(bg=w("bg"))

    def jalan(induk):
        for anak in induk.winfo_children():
            if isinstance(anak, tk.Toplevel):
                anak.configure(bg=w("bg"))
            if hasattr(anak, "warnai"):
                anak.warnai()
            jalan(anak)
    jalan(root)


class Jendela(tk.Toplevel):
    """Toplevel yang otomatis memakai warna tema aktif."""
    def __init__(self, induk):
        super().__init__(induk, bg=tampilan.warna("bg"))


def tengahkan(jendela, lebar=None, tinggi=None, geser=0):
    """Menaruh jendela di tengah layar (ukuran diambil dari isi bila tidak diberikan)."""
    jendela.update_idletasks()
    lebar = lebar or jendela.winfo_reqwidth()
    tinggi = tinggi or jendela.winfo_reqheight()
    x = (jendela.winfo_screenwidth() - lebar) // 2 + geser
    y = (jendela.winfo_screenheight() - tinggi) // 3 + geser
    jendela.geometry(f"{lebar}x{tinggi}+{x}+{y}")


# ======================================================================
# Formulir tambah / ubah obat
# ======================================================================
class FormObat(Jendela):
    def __init__(self, induk, db, obat=None, setelahSimpan=None):
        super().__init__(induk)
        self.__db, self.__obat, self.__setelah = db, obat, setelahSimpan
        self.title("Ubah obat" if obat else "Tambah obat")
        self.resizable(False, False)
        self.transient(induk)

        hari = date.today()
        v = {k: tk.StringVar() for k in
             ("nama", "kekuatan", "jumlah", "satuan", "stok", "batas",
              "kategori", "penyakit", "mulai", "selesai", "jam")}
        v["jumlah"].set("1"); v["batas"].set("5"); v["kategori"].set("RUTIN")
        v["mulai"].set(pb.formatTanggal(hari))
        v["selesai"].set(pb.formatTanggal(hari + timedelta(days=7)))
        if obat:
            v["nama"].set(obat.getNamaObat()); v["kekuatan"].set(obat.getKekuatanDosis())
            v["jumlah"].set(obat.getJumlahPerMinum()); v["satuan"].set(obat.getSatuan())
            v["stok"].set(obat.getStok()); v["batas"].set(obat.getBatasStokMinimum())
            v["jam"].set(", ".join(f"{t:%H:%M}" for t in pb.jamAktif(db, obat.getIdObat())))
            if isinstance(obat, ObatTemporer):
                v["kategori"].set("TEMPORER")
                v["mulai"].set(pb.formatTanggal(obat.getTanggalMulai()))
                v["selesai"].set(pb.formatTanggal(obat.getTanggalSelesai()))
            else:
                v["penyakit"].set(obat.getPenyakitKronis())
        self.__v = v
        self.__fotoLama = obat.getFoto() if obat else ""
        self.__fotoBaru = None            # path foto pilihan pengguna (disalin saat Simpan)
        self.__fotoHapus = False

        isi = ttk.Frame(self, padding=16)
        isi.pack()
        baris = [("Nama obat", "nama", ""), ("Kekuatan dosis", "kekuatan", "contoh 500 mg"),
                 ("Jumlah per minum", "jumlah", ""), ("Satuan", "satuan", "contoh tablet"),
                 ("Stok saat ini", "stok", ""), ("Ingatkan bila stok tinggal", "batas", "")]
        for i, (label, kunci, bantu) in enumerate(baris):
            ttk.Label(isi, text=label).grid(row=i, column=0, sticky="w", pady=3)
            ttk.Entry(isi, textvariable=v[kunci], width=26).grid(row=i, column=1, pady=3, padx=8)
            ttk.Label(isi, text=bantu, style="Redup.TLabel").grid(row=i, column=2, sticky="w")

        kotak = ttk.Frame(isi)
        kotak.grid(row=0, column=3, rowspan=7, sticky="n", padx=(18, 0))
        self.__pratinjau = ttk.Label(kotak, anchor="center", justify="center",
                                     style="Redup.TLabel")
        self.__pratinjau.pack(pady=(3, 8))
        ttk.Button(kotak, text="Pilih foto...", command=self.__pilihFoto).pack(fill="x")
        ttk.Button(kotak, text="Hapus foto", command=self.__buangFoto).pack(fill="x", pady=(6, 0))
        self.__tampilkanFoto()

        ttk.Label(isi, text="Jenis obat").grid(row=6, column=0, sticky="w", pady=(10, 3))
        jenis = ttk.Frame(isi)
        jenis.grid(row=6, column=1, columnspan=2, sticky="w", pady=(10, 3), padx=8)
        ttk.Radiobutton(jenis, text="Rutin (jangka panjang)", value="RUTIN",
                        variable=v["kategori"], command=self.__aturBagian).pack(side="left")
        ttk.Radiobutton(jenis, text="Temporer (ada masa terapi)", value="TEMPORER",
                        variable=v["kategori"], command=self.__aturBagian).pack(side="left", padx=10)

        self.__rutin = ttk.Frame(isi)
        ttk.Label(self.__rutin, text="Untuk penyakit").grid(row=0, column=0, sticky="w", padx=(0, 31))
        ttk.Entry(self.__rutin, textvariable=v["penyakit"], width=26).grid(row=0, column=1, padx=8)
        ttk.Label(self.__rutin, text="boleh dikosongkan", style="Redup.TLabel").grid(row=0, column=2)

        self.__temporer = ttk.Frame(isi)
        for i, (label, kunci) in enumerate([("Tanggal mulai", "mulai"), ("Tanggal selesai", "selesai")]):
            ttk.Label(self.__temporer, text=label).grid(row=i, column=0, sticky="w", pady=3, padx=(0, 47))
            ttk.Entry(self.__temporer, textvariable=v[kunci], width=26).grid(row=i, column=1, pady=3, padx=8)
            ttk.Label(self.__temporer, text="HH/BB/TTTT", style="Redup.TLabel").grid(row=i, column=2)

        self.__bagianJenis = (self.__rutin, self.__temporer)
        ttk.Label(isi, text="Jam minum").grid(row=9, column=0, sticky="w", pady=(10, 3))
        ttk.Entry(isi, textvariable=v["jam"], width=26).grid(row=9, column=1, pady=(10, 3), padx=8)
        ttk.Label(isi, text="pisahkan dengan koma, contoh 07:00, 19:00",
                  style="Redup.TLabel").grid(row=9, column=2, sticky="w", pady=(10, 3))

        tombol = ttk.Frame(isi)
        tombol.grid(row=10, column=0, columnspan=3, sticky="e", pady=(16, 0))
        ttk.Button(tombol, text="Batal", command=self.destroy).pack(side="right")
        ttk.Button(tombol, text="Simpan", style="Utama.TButton",
                   command=self.__simpan).pack(side="right", padx=8)

        self.__aturBagian()
        self.bind("<Escape>", lambda e: self.destroy())
        self.bind("<Return>", lambda e: self.__simpan())
        self.grab_set()
        self.focus_set()

    def __tampilkanFoto(self):
        sumber = self.__fotoBaru or ("" if self.__fotoHapus else self.__fotoLama)
        gambar = penyimpanFoto.muat(sumber, 150)
        self.__pratinjau.config(image=gambar or "",
                                text="" if gambar else "Belum ada foto\n\n\n")
        self.__pratinjau.image = gambar

    def __pilihFoto(self):
        if not penyimpanFoto.tersedia:
            messagebox.showinfo("Pillow belum terpasang",
                                "Untuk memakai foto, jalankan di terminal:\npip install pillow",
                                parent=self)
            return
        berkas = filedialog.askopenfilename(
            parent=self, title="Pilih foto obat",
            filetypes=[("Gambar", "*.png *.jpg *.jpeg *.gif *.bmp *.webp")])
        if berkas:
            self.__fotoBaru = berkas
            self.__tampilkanFoto()

    def __buangFoto(self):
        self.__fotoBaru, self.__fotoHapus = None, True
        self.__tampilkanFoto()

    def __aturBagian(self):
        for b in self.__bagianJenis:
            b.grid_forget()
        aktif = self.__rutin if self.__v["kategori"].get() == "RUTIN" else self.__temporer
        aktif.grid(row=7, column=0, columnspan=3, sticky="w", rowspan=2)

    def __simpan(self):
        d = {k: x.get() for k, x in self.__v.items()}
        d["foto"] = "" if self.__fotoHapus else self.__fotoLama
        try:
            daftar_jam = pb.parseDaftarJam(d["jam"])
            id_obat = self.__obat.getIdObat() if self.__obat else None
            obat = pb.bangunObat(id_obat, d)
        except ValueError as e:
            messagebox.showerror("Data belum benar", str(e), parent=self)
            return
        if self.__fotoBaru or self.__fotoHapus:
            try:
                if self.__fotoBaru:
                    obat.setFoto(penyimpanFoto.simpan(self.__fotoBaru))
            except Exception as e:
                messagebox.showerror("Foto gagal disimpan", str(e), parent=self)
                return
            penyimpanFoto.hapus(self.__fotoLama)
        if self.__obat:
            self.__db.ubah(obat)
        else:
            id_obat = self.__db.simpan(obat)
        pb.sinkronkanJadwal(self.__db, id_obat, daftar_jam)
        if self.__setelah:
            self.__setelah()
        self.destroy()


# ======================================================================
# Jendela daftar obat
# ======================================================================
class JendelaObat(Jendela):
    def __init__(self, induk, db, setelahUbah):
        super().__init__(induk)
        self.__db, self.__setelahUbah = db, setelahUbah
        self.title("Daftar obat")
        self.geometry("1020x470")
        isi = ttk.Frame(self, padding=14)
        isi.pack(fill="both", expand=True)

        tengah = ttk.Frame(isi)
        tengah.pack(fill="both", expand=True)
        panel = ttk.Frame(tengah, width=190)
        panel.pack(side="right", fill="y", padx=(12, 0))
        self.__foto = ttk.Label(panel, anchor="center", justify="center",
                                style="Redup.TLabel", text="Pilih obat untuk\nmelihat fotonya")
        self.__foto.pack(pady=(4, 8))
        self.__namaFoto = ttk.Label(panel, wraplength=180, justify="center",
                                    font=("Segoe UI Semibold", 10))
        self.__namaFoto.pack()
        self.__tabel = buatTabel(tengah, {
            "nama": ("Obat", 190), "jenis": ("Jenis", 80), "dosis": ("Per minum", 90),
            "stok": ("Stok", 60), "jam": ("Jam minum", 130), "ket": ("Keterangan", 210)})
        self.__tabel.bind("<Double-1>", lambda e: self.__ubah())
        self.__tabel.bind("<<TreeviewSelect>>", lambda e: self.__tampilFoto())

        tombol = ttk.Frame(isi)
        tombol.pack(fill="x", pady=(12, 0))
        ttk.Button(tombol, text="Tambah obat", style="Utama.TButton",
                   command=self.__tambah).pack(side="left")
        ttk.Button(tombol, text="Ubah", command=self.__ubah).pack(side="left", padx=6)
        ttk.Button(tombol, text="Tambah stok", command=self.__tambahStok).pack(side="left")
        ttk.Button(tombol, text="Hapus", command=self.__hapus).pack(side="left", padx=6)
        ttk.Button(tombol, text="Tutup", command=self.destroy).pack(side="right")
        self.muat()

    def muat(self):
        self.__tabel.delete(*self.__tabel.get_children())
        for o in self.__db.ambilSemua("obat"):
            temporer = isinstance(o, ObatTemporer)
            ket = (f"{pb.formatTanggal(o.getTanggalMulai())} - {pb.formatTanggal(o.getTanggalSelesai())}"
                   if temporer else o.getPenyakitKronis())
            jam = ", ".join(f"{t:%H:%M}" for t in pb.jamAktif(self.__db, o.getIdObat()))
            self.__tabel.insert("", "end", iid=str(o.getIdObat()),
                                tags=("menipis",) if o.stokMenipis() else (),
                                values=(f"{o.getNamaObat()} {o.getKekuatanDosis()}",
                                        "Temporer" if temporer else "Rutin",
                                        f"{o.getJumlahPerMinum()} {o.getSatuan()}",
                                        o.getStok(), jam or "-", ket))
        self.__tabel.gambarGaris()

    def __tampilFoto(self):
        pilihan = self.__tabel.selection()
        obat = self.__db.ambilSatu("obat", int(pilihan[0])) if pilihan else None
        gambar = penyimpanFoto.muat(obat.getFoto(), 170) if obat else None
        if obat:
            teks = "" if gambar else "Belum ada foto\n\n"
        else:
            teks = "Pilih obat untuk\nmelihat fotonya"
        self.__foto.config(image=gambar or "", text=teks)
        self.__foto.image = gambar
        self.__namaFoto.config(text=obat.getNamaObat() if obat else "")

    def __dipilih(self):
        pilihan = self.__tabel.selection()
        if not pilihan:
            messagebox.showinfo("Pilih obat", "Klik satu obat di daftar dulu.", parent=self)
            return None
        return self.__db.ambilSatu("obat", int(pilihan[0]))

    def __selesai(self):
        self.muat()
        self.__setelahUbah()

    def __tambah(self):
        FormObat(self, self.__db, setelahSimpan=self.__selesai)

    def __ubah(self):
        obat = self.__dipilih()
        if obat:
            FormObat(self, self.__db, obat, self.__selesai)

    def __tambahStok(self):
        obat = self.__dipilih()
        if not obat:
            return
        jumlah = simpledialog.askinteger(
            "Tambah stok", f"Tambah berapa {obat.getSatuan()} {obat.getNamaObat()}?",
            parent=self, minvalue=1)
        if jumlah:
            obat.tambahStok(jumlah)
            self.__db.ubah(obat)
            self.__selesai()

    def __hapus(self):
        obat = self.__dipilih()
        if obat and messagebox.askyesno(
                "Hapus obat",
                f"Hapus {obat.getNamaObat()}?\nJadwal dan riwayat minumnya ikut terhapus "
                "dan tidak bisa dikembalikan.",
                icon="warning", parent=self):
            penyimpanFoto.hapus(obat.getFoto())
            self.__db.hapus("obat", obat.getIdObat())
            self.__selesai()


# ======================================================================
# Jendela riwayat
# ======================================================================
class JendelaRiwayat(Jendela):
    PILIHAN = {"7 hari terakhir": 7, "30 hari terakhir": 30, "Semua riwayat": None}

    def __init__(self, induk, db):
        super().__init__(induk)
        self.__db = db
        self.title("Riwayat minum obat")
        self.geometry("760x460")
        isi = ttk.Frame(self, padding=14)
        isi.pack(fill="both", expand=True)

        atas = ttk.Frame(isi)
        atas.pack(fill="x", pady=(0, 10))
        self.__rentang = ttk.Combobox(atas, values=list(self.PILIHAN), state="readonly", width=18)
        self.__rentang.current(0)
        self.__rentang.pack(side="left")
        self.__rentang.bind("<<ComboboxSelected>>", lambda e: self.muat())
        self.__kepatuhan = ttk.Label(atas, font=("Segoe UI Semibold", 11), style="Aksen.TLabel")
        self.__kepatuhan.pack(side="right")

        self.__tabel = buatTabel(isi, {"waktu": ("Jadwal", 130), "obat": ("Obat", 200),
                                       "status": ("Status", 100), "ket": ("Keterangan", 270)})
        self.__kosong = ttk.Label(isi, style="Redup.TLabel",
                                  text="Belum ada riwayat pada rentang ini.")
        ttk.Button(isi, text="Tutup", command=self.destroy).pack(anchor="e", pady=(12, 0))
        self.muat()

    def muat(self):
        baris, persen = pb.ringkasRiwayat(self.__db, date.today(),
                                          self.PILIHAN[self.__rentang.get()])
        self.__tabel.delete(*self.__tabel.get_children())
        peta = {"Sudah minum": "sudah_minum", "Ditunda": "ditunda", "Terlewat": "dilewati"}
        for b in baris:
            self.__tabel.insert("", "end", values=b, tags=(peta[b[2]],))
        self.__kepatuhan.config(text=f"Kepatuhan: {persen:g}%" if baris else "")
        self.__tabel.gambarGaris()
        if baris:
            self.__kosong.pack_forget()
        else:
            self.__kosong.pack(before=self.__tabel.master)


# ======================================================================
# Jendela pengaturan tampilan (warna)
# ======================================================================
class JendelaTampilan(Jendela):
    def __init__(self, induk, setelahUbah):
        super().__init__(induk)
        self.__setelah = setelahUbah
        self.title("Tampilan")
        self.resizable(False, False)
        isi = ttk.Frame(self, padding=18)
        isi.pack()
        ttk.Label(isi, text="Warna aksen", font=("Segoe UI Semibold", 11)).pack(anchor="w")
        baris = ttk.Frame(isi)
        baris.pack(anchor="w", pady=(8, 4))
        for nama, kode in PengaturanTampilan.PRESET.items():
            tk.Button(baris, text=nama, bg=kode, fg=PengaturanTampilan.kontras(kode),
                      activebackground=kode, relief="flat", padx=10, pady=6, cursor="hand2",
                      command=lambda k=kode: self.__ubah(aksen=k)).pack(side="left", padx=(0, 6))
        ttk.Button(isi, text="Pilih warna sendiri...",
                   command=self.__pilihSendiri).pack(anchor="w", pady=(8, 0))
        self.__gelap = tk.BooleanVar(value=tampilan.gelap)
        ttk.Checkbutton(isi, text="Mode gelap", variable=self.__gelap,
                        command=lambda: self.__ubah(gelap=self.__gelap.get())
                        ).pack(anchor="w", pady=(14, 0))
        tombol = ttk.Frame(isi)
        tombol.pack(fill="x", pady=(18, 0))
        ttk.Button(tombol, text="Kembalikan bawaan", command=self.__reset).pack(side="left")
        ttk.Button(tombol, text="Tutup", command=self.destroy).pack(side="right")
        self.bind("<Escape>", lambda e: self.destroy())

    def __ubah(self, **pilihan):
        tampilan.atur(**pilihan)
        self.__setelah()

    def __pilihSendiri(self):
        _, kode = colorchooser.askcolor(color=tampilan.aksen, parent=self,
                                        title="Pilih warna aksen")
        if kode:
            self.__ubah(aksen=kode)

    def __reset(self):
        tampilan.kembalikan()
        self.__gelap.set(False)
        self.__setelah()


# ======================================================================
# Jendela utama (dashboard)
# ======================================================================
class AplikasiMedRemind:
    def __init__(self, root: tk.Tk, db: DatabaseManager):
        self.__root, self.__db = root, db
        self.__jendela = {}
        self.__id_segar = None
        root.title("MedRemind")
        tengahkan(root, 760, 540)
        root.minsize(620, 400)
        self.__aturGaya()

        isi = ttk.Frame(root, padding=18)
        isi.pack(fill="both", expand=True)
        ttk.Label(isi, text="Jadwal hari ini", font=FONT_JUDUL,
                  style="Aksen.TLabel").pack(anchor="w")
        self.__tanggal = ttk.Label(isi, style="Redup.TLabel")
        self.__tanggal.pack(anchor="w", pady=(0, 10))

        self.__stok = tk.Label(isi, anchor="w",
                               justify="left", padx=10, pady=6, font=FONT)
        self.__stok.warnai = lambda: self.__stok.config(
            bg=tampilan.warna("bahaya_bg"), fg=tampilan.warna("bahaya"))
        self.__tabel = buatTabel(isi, {"jam": ("Jam", 70), "nama": ("Obat", 240),
                                       "jumlah": ("Jumlah", 110), "status": ("Status", 110)})
        self.__kosong = ttk.Label(isi, style="Redup.TLabel", justify="center",
                                  text="Belum ada jadwal untuk hari ini.\n"
                                       "Klik \"Tambah obat\" untuk memasukkan obat dan jam minumnya.")

        tombol = ttk.Frame(isi)
        tombol.pack(fill="x", pady=(12, 0))
        ttk.Button(tombol, text="Tambah obat", style="Utama.TButton",
                   command=self.__tambahObat).pack(side="left")
        ttk.Button(tombol, text="Daftar obat",
                   command=lambda: self.__buka("obat")).pack(side="left", padx=6)
        ttk.Button(tombol, text="Riwayat", command=lambda: self.__buka("riwayat")).pack(side="left")
        ttk.Button(tombol, text="Tampilan", command=lambda: self.__buka("tampilan")).pack(side="left", padx=6)
        self.__otomatis = tk.BooleanVar(value=latar.autostartAktif())
        if latar.autostartTersedia():
            ttk.Checkbutton(tombol, text="Pengingat aktif saat Windows menyala",
                            variable=self.__otomatis,
                            command=self.__aturOtomatis).pack(side="right")
        root.bind("<Control-n>", lambda e: self.__tambahObat())
        root.bind("<Control-r>", lambda e: self.__buka("riwayat"))

        # Popup dan suara ditangani pemantau.py (proses terpisah), supaya tetap
        # muncul walaupun jendela ini ditutup.
        latar.jalankan()
        terapkanTema(root)
        self.segarkan()
        root.protocol("WM_DELETE_WINDOW", self.__tutup)

    def __aturGaya(self):
        terapkanTema(self.__root)

    def segarkan(self):
        """Memuat ulang tabel dan peringatan stok. Dipanggil tiap 30 detik dan setelah perubahan."""
        hari = date.today()
        self.__tanggal.config(text=pb.judulHari(hari))
        self.__tabel.delete(*self.__tabel.get_children())
        baris = pb.jadwalHariIni(self.__db, hari)
        for b in baris:
            self.__tabel.insert("", "end", tags=(b["kunci"],),
                                values=(f"{b['jam']:%H:%M}", b["nama"], b["jumlah"], b["status"]))
        self.__tabel.gambarGaris()
        if baris:
            self.__kosong.pack_forget()
        else:
            self.__kosong.pack(before=self.__tabel.master, pady=30)

        peringatan = pb.peringatanStok(self.__db, hari)
        if peringatan:
            self.__stok.config(text="Stok menipis: " + "; ".join(peringatan))
            self.__stok.pack(fill="x", pady=(0, 10), before=self.__tabel.master)
        else:
            self.__stok.pack_forget()
        if self.__id_segar:
            self.__root.after_cancel(self.__id_segar)
        self.__id_segar = self.__root.after(30000, self.segarkan)

    def __tambahObat(self):
        FormObat(self.__root, self.__db, setelahSimpan=self.segarkan)

    def __buka(self, nama):
        jendela = self.__jendela.get(nama)
        if jendela is not None and jendela.winfo_exists():
            jendela.lift()
            return
        if nama == "obat":
            self.__jendela[nama] = JendelaObat(self.__root, self.__db, self.segarkan)
        elif nama == "tampilan":
            self.__jendela[nama] = JendelaTampilan(self.__root, lambda: terapkanTema(self.__root))
        else:
            self.__jendela[nama] = JendelaRiwayat(self.__root, self.__db)

    def __aturOtomatis(self):
        if self.__otomatis.get():
            latar.pasangAutostart()
        else:
            latar.lepasAutostart()

    def __tutup(self):
        if latar.berjalan():
            jawab = messagebox.askyesnocancel(
                "Tutup MedRemind",
                "Pengingat tetap berjalan di latar belakang agar popup dan suara "
                "tetap muncul.\n\nHentikan pengingat juga?", parent=self.__root)
            if jawab is None:
                return                      # batal menutup
            if jawab:
                latar.hentikan()
        self.__db.tutup()
        self.__root.destroy()


def main():
    root = tk.Tk()
    AplikasiMedRemind(root, DatabaseManager(os.path.join(FOLDER_APP, "medremind.db")))
    root.mainloop()


if __name__ == "__main__":
    main()
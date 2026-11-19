import hmac
import os
import secrets
from datetime import datetime
from functools import wraps

from flask import (Flask, abort, current_app, g, redirect, render_template,
                   request, session, url_for)

from models.database_manager import DatabaseManager
from models.pengguna import Pengguna

HARI = ("Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu")
BULAN = ("Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli",
         "Agustus", "September", "Oktober", "November", "Desember")

# (nama fungsi route, teks menu). Menu hanya menampilkan route yang sudah ada.
MENU = (("beranda", "Beranda"), ("jadwal", "Jadwal"), ("obat", "Obat"),
        ("riwayat", "Riwayat"), ("pengaturan", "Pengaturan"))


def tanggal_indonesia(tanggal):
    """Contoh: 'Kamis, 12 November 2026'."""
    return (f"{HARI[tanggal.weekday()]}, {tanggal.day} "
            f"{BULAN[tanggal.month - 1]} {tanggal.year}")


def ambil_db():
    """Satu DatabaseManager per request (koneksi SQLite tidak dibagi antar-thread)."""
    if "db" not in g:
        g.db = DatabaseManager(current_app.config["DATABASE"])
    return g.db


def wajib_login(fungsi):
    @wraps(fungsi)
    def pembungkus(*args, **kwargs):
        id_pengguna = session.get("id_pengguna")
        pengguna = ambil_db().ambil_pengguna(id_pengguna) if id_pengguna else None
        if pengguna is None:
            session.clear()
            return redirect(url_for("masuk"))
        g.pengguna = pengguna
        return fungsi(*args, **kwargs)
    return pembungkus


def csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return session["csrf_token"]


def buat_app(konfigurasi=None):
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.environ.get("MEDREMIND_SECRET", "kunci-dev-ganti-di-produksi"),
        DATABASE=os.path.join(app.root_path, "medremind.db"),
        SESSION_COOKIE_SAMESITE="Lax",
    )
    if konfigurasi:
        app.config.update(konfigurasi)

    app.jinja_env.globals["csrf_token"] = csrf_token
    app.jinja_env.filters["tanggal_id"] = tanggal_indonesia
    app.jinja_env.filters["inisial"] = lambda nama: nama[:2].upper()

    @app.context_processor
    def sisipkan_konteks():
        menu = [(e, label) for e, label in MENU if e in app.view_functions]
        return {"menu": menu, "pengguna": g.get("pengguna")}

    @app.teardown_appcontext
    def tutup_db(_galat):
        db = g.pop("db", None)
        if db is not None:
            db.tutup()

    @app.before_request
    def periksa_csrf():
        if request.method == "POST":
            token = session.get("csrf_token")
            kiriman = (request.form.get("csrf_token")
                       or request.headers.get("X-CSRF-Token"))
            if not token or not kiriman or not hmac.compare_digest(token, kiriman):
                abort(400, "Permintaan tidak valid. Muat ulang halaman lalu coba lagi.")

    # ================= autentikasi =================
    @app.route("/")
    def indeks():
        if "id_pengguna" in session:
            return redirect(url_for("beranda"))
        return redirect(url_for("masuk"))

    @app.route("/masuk", methods=["GET", "POST"])
    def masuk():
        if "id_pengguna" in session:
            return redirect(url_for("beranda"))
        if request.method == "POST":
            username = request.form.get("username", "")
            password = request.form.get("password", "")
            pengguna = ambil_db().ambil_pengguna_by_username(username)
            if pengguna is None or not pengguna.verifikasi_password(password):
                return render_template(
                    "auth.html", mode="masuk", username=username,
                    galat="Nama pengguna atau kata sandi salah."), 401
            session.clear()
            session["id_pengguna"] = pengguna.id_pengguna
            return redirect(url_for("beranda"))
        return render_template("auth.html", mode="masuk", username="")

    @app.route("/daftar", methods=["GET", "POST"])
    def daftar():
        if "id_pengguna" in session:
            return redirect(url_for("beranda"))
        if request.method == "POST":
            username = request.form.get("username", "")
            password = request.form.get("password", "")
            try:
                baru = ambil_db().tambah_pengguna(
                    Pengguna.daftar(username, password))
            except ValueError as galat:
                return render_template(
                    "auth.html", mode="daftar", username=username,
                    galat=str(galat)), 400
            session.clear()
            session["id_pengguna"] = baru.id_pengguna
            return redirect(url_for("beranda"))
        return render_template("auth.html", mode="daftar", username="")

    @app.route("/keluar", methods=["POST"])
    def keluar():
        session.clear()
        return redirect(url_for("masuk"))

    # ================= halaman utama =================
    @app.route("/beranda")
    @wajib_login
    def beranda():
        return render_template("beranda.html", hari_ini=datetime.now().date())

    return app


if __name__ == "__main__":
    buat_app().run(debug=True)
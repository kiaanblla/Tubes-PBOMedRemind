from enum import Enum


class StatusKonsumsi(Enum):
    """Status satu kejadian pengingat. Nilainya dipakai sebagai teks tampilan."""
    MENUNGGU = "Menunggu"
    SUDAH_MINUM = "Sudah minum"
    DITUNDA = "Ditunda"
    TERLEWAT = "Terlewat"
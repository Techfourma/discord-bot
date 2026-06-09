import re
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple, List

WIB = timezone(timedelta(hours=7))


def parse_date_from_prompt(prompt: str) -> Optional[datetime]:
    month_map = {
        'januari': 1, 'februari': 2, 'maret': 3, 'april': 4, 'mei': 5, 'juni': 6,
        'juli': 7, 'agustus': 8, 'september': 9, 'oktober': 10, 'november': 11, 'desember': 12,
        'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6,
        'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12
    }

    # Search for number + month name + optional year
    match = re.search(r"(\d{1,2})\s+([A-Za-z]+)(?:\s+(\d{4}))?", prompt)
    if not match:
        return None

    day = int(match.group(1))
    month_str = match.group(2).lower()
    month = month_map.get(month_str)
    year = int(match.group(3)) if match.group(3) else datetime.now(WIB).year

    if not month:
        return None

    try:
        return datetime(year, month, day, tzinfo=WIB).date()
    except ValueError:
        return None


def parse_month_year_from_prompt(prompt: str) -> Optional[Tuple[int, Optional[int]]]:
    month_map = {
        'januari': 1, 'februari': 2, 'maret': 3, 'april': 4, 'mei': 5, 'juni': 6,
        'juli': 7, 'agustus': 8, 'september': 9, 'oktober': 10, 'november': 11, 'desember': 12,
        'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6,
        'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12
    }

    for name, num in month_map.items():
        if re.search(r"\b" + re.escape(name) + r"\b", prompt.lower()):
            year_match = re.search(r"(\d{4})", prompt)
            year = int(year_match.group(1)) if year_match else datetime.now(WIB).year
            return num, year
    return None


def extract_student_name(prompt: str) -> Optional[str]:
    prompt_lower = prompt.lower()

    name_patterns = [
        r"apakah\s+(.+?)\s+(?:sudah|udah|udh|blm|belum)\s+bayar",
        r"(.+?)\s+apakah\s+(?:sudah|udah|udh)\s+bayar",
        r"(.+?)\s+(?:sudah|udah|udh|blm|belum)\s+bayar\s+(?:uang\s*)?kas",
        r"cek\s+(.+?)(?:\s+uang\s*kas|\s+kas)?$",
        r"status\s+(.+?)(?:\s+uang\s*kas|\s+kas)?$",
        r"mahasiswa\dengan\s+nama\s+(.+?)\s+nunggak",
        r"(.+?)\s+nunggak\s+(?:uang\s*)?kas",
    ]

    skip_words = {
        "uang", "kas", "siapa", "semua", "yang", "aja", "saja",
        "belum", "sudah", "udah", "bayar", "nunggak", "mahasiswa",
        "dengan", "nama", "berapa", "kali"
    }

    detected_name = None
    for pattern in name_patterns:
        m = re.search(pattern, prompt_lower)
        if m:
            candidate = m.group(1).strip()
            tokens = [t for t in candidate.split() if t not in skip_words]
            candidate = " ".join(tokens)
            if candidate and len(candidate) > 2:
                detected_name = candidate
                break

    return detected_name
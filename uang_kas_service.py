import os
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import aiohttp

logger = logging.getLogger(__name__)


class UangKasService:
    """Service untuk mengelola data uang kas dari Google Spreadsheet via Apps Script."""

    def __init__(self):
        self.api_url = None
        self._initialized = False
        self._cache: Dict = {}
        self._cache_duration = 60  # detik

    # INIT & CORE

    async def initialize(self) -> bool:
        try:
            api_url = os.getenv("GOOGLE_APPS_SCRIPT_URL")
            if not api_url:
                logger.error("❌ GOOGLE_APPS_SCRIPT_URL tidak ditemukan")
                return False

            self.api_url = api_url.rstrip("/")
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_url}?action=test", timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        logger.info(f"📦 Test result: {result}")
                        self._initialized = True
                        logger.info("✅ UangKasService initialized")
                        return True
                    logger.error(f"❌ API error: {resp.status}")
                    return False
        except Exception as e:
            logger.error(f"❌ Error initializing: {e}")
            return False

    def _get_cached(self, key: str):
        if key in self._cache:
            data, ts = self._cache[key]
            if datetime.now().timestamp() - ts < self._cache_duration:
                return data
        return None

    def _set_cached(self, key: str, data):
        self._cache[key] = (data, datetime.now().timestamp())

    async def _fetch_api(self, action: str, extra_params: str = ""):
        if not self.api_url:
            return None
        try:
            url = f"{self.api_url}?action={action}{extra_params}"
            logger.info(f"🔍 Fetching: {url}")
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        if result.get("success"):
                            return result.get("data")
                        logger.error(f"❌ API error: {result}")
                    else:
                        logger.error(f"❌ HTTP error: {resp.status}")
        except Exception as e:
            logger.error(f"❌ Fetch error: {e}")
        return None

    # DATA FETCHERS

    async def _get_all_students(self) -> List[Dict]:
        cached = self._get_cached("all_students")
        if cached:
            return cached
        data = await self._fetch_api("getStudents")
        if not data:
            return []
        students = data.get("students", [])
        logger.info(f"✅ Loaded {len(students)} students")
        self._set_cached("all_students", students)
        return students

    async def _get_dashboard(self) -> Dict:
        cached = self._get_cached("dashboard")
        if cached:
            return cached
        data = await self._fetch_api("getDashboard")
        if not data:
            return {"total_pemasukan": 0, "total_pengeluaran": 0, "sisa_uang_kas": 0, "status": "UNKNOWN"}
        self._set_cached("dashboard", data)
        return data

    async def find_student_by_name(self, query: str) -> Optional[Dict]:
        """Cari satu mahasiswa berdasarkan nama (fuzzy)."""
        # Coba via endpoint khusus dulu
        data = await self._fetch_api("getStudent", f"&name={query.replace(' ', '+')}")
        if data:
            return data

        # Fallback: cari dari list lokal
        students = await self._get_all_students()
        query_lower = query.lower()
        for s in students:
            if query_lower in s["name"].lower():
                return s
        return None

    # QUERY HELPERS

    async def get_all_unpaid_detailed(self) -> List[Dict]:
        """Semua mahasiswa yang memiliki setidaknya satu tanggal belum bayar."""
        students = await self._get_all_students()
        result = []
        for s in students:
            unpaid = s.get("unpaid_dates", [])
            if unpaid:
                result.append({
                    "no": s["no"],
                    "name": s["name"],
                    "unpaid_dates": unpaid,
                    "paid_dates": s.get("paid_dates", []),
                    "total_unpaid": len(unpaid),
                    "total_paid": len(s.get("paid_dates", [])),
                    "total_owed": len(unpaid) * 10_000,
                })
        result.sort(key=lambda x: x["total_unpaid"], reverse=True)
        return result

    async def get_nunggak_summary(self) -> List[Dict]:
        """Ringkasan tunggakan: total belum bayar per mahasiswa (termasuk yg 0)."""
        students = await self._get_all_students()
        result = []
        for s in students:
            unpaid_count = len(s.get("unpaid_dates", []))
            if unpaid_count > 0:
                result.append({
                    "no": s["no"],
                    "name": s["name"],
                    "total_unpaid": unpaid_count,
                    "total_owed": unpaid_count * 10_000,
                })
        result.sort(key=lambda x: x["total_unpaid"], reverse=True)
        return result

    async def get_current_balance(self) -> Dict:
        d = await self._get_dashboard()
        return {
            "total_pemasukan": d.get("total_pemasukan", 0),
            "total_pengeluaran": d.get("total_pengeluaran", 0),
            "sisa_uang_kas": d.get("sisa_uang_kas", 0),
            "status": d.get("status", "UNKNOWN"),
        }

    async def get_total_expenditure(self) -> int:
        d = await self._get_dashboard()
        return d.get("total_pengeluaran", 0)

    async def get_total_income(self) -> int:
        d = await self._get_dashboard()
        return d.get("total_pemasukan", 0)

    # FORMATTERS

    @staticmethod
    def _fmt_date(date_str: str) -> str:
        """yyyy-MM-dd → DD/MM/YYYY"""
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").strftime("%d/%m/%Y")
        except Exception:
            return date_str

    def format_all_unpaid(self, detail_list: List[Dict]) -> str:
        """
        Format respons 'siapa yang belum bayar uang kas?'
        Tampilkan semua mahasiswa dengan daftar tanggal belum bayar.
        """
        if not detail_list:
            return "✅ Semua mahasiswa sudah lunas. Tidak ada yang belum bayar! 🎉"

        total_tagihan = sum(s["total_owed"] for s in detail_list)
        lines = [
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "📋  **DAFTAR BELUM BAYAR UANG KAS**",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"👥 Total mahasiswa  : **{len(detail_list)} orang**",
            f"💸 Total tagihan    : **Rp {total_tagihan:,.0f}**",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "",
        ]

        for i, s in enumerate(detail_list, 1):
            dates_fmt = ", ".join(self._fmt_date(d) for d in s["unpaid_dates"])
            lines.append(
                f"**{i}. {s['name']}**\n"
                f"   └ Belum bayar  : {dates_fmt}\n"
                f"   └ Jumlah belum : {s['total_unpaid']}x  |  Tagihan: Rp {s['total_owed']:,.0f}"
            )
            lines.append("")

        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        return "\n".join(lines)

    def format_nunggak_summary(self, summary_list: List[Dict]) -> str:
        """
        Format respons 'siapa aja yang nunggak uang kas?'
        Tampilkan total tunggakan masing-masing mahasiswa.
        """
        if not summary_list:
            return "✅ Tidak ada mahasiswa yang nunggak. Semua sudah lunas! 🎉"

        lines = [
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "🔴  **REKAP TUNGGAKAN UANG KAS**",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"{'No':<4} {'Nama':<30} {'Nunggak':>8} {'Total Hutang':>14}",
            "─" * 60,
        ]

        for i, s in enumerate(summary_list, 1):
            lines.append(
                f"{i:<4} {s['name']:<30} {s['total_unpaid']:>6}x    Rp {s['total_owed']:>10,.0f}"
            )

        total_orang  = len(summary_list)
        total_semua  = sum(s["total_owed"] for s in summary_list)
        lines += [
            "─" * 60,
            f"{'Total':>4} {total_orang} mahasiswa nunggak  |  Total: Rp {total_semua:,.0f}",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        ]
        return "\n".join(lines)

    def format_single_student(self, student: Dict) -> str:
        """
        Format respons cek satu mahasiswa: 'Jundulloh apakah sudah bayar?'
        """
        name         = student["name"]
        paid_dates   = student.get("paid_dates", [])
        unpaid_dates = student.get("unpaid_dates", [])
        total_paid   = len(paid_dates)
        total_unpaid = len(unpaid_dates)

        lines = [
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"👤  **STATUS UAS KAS — {name}**",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        ]

        if total_unpaid == 0:
            lines += [
                "✅ **LUNAS** — Semua sudah dibayar!",
                f"   └ Total lunas : {total_paid}x pembayaran",
            ]
        else:
            unpaid_str = ", ".join(self._fmt_date(d) for d in unpaid_dates)
            paid_str   = (", ".join(self._fmt_date(d) for d in paid_dates)
                          if paid_dates else "—")
            lines += [
                f"⚠️ **BELUM LUNAS** — masih punya tunggakan!",
                "",
                f"❌ Belum bayar ({total_unpaid}x):",
                f"   └ {unpaid_str}",
                "",
                f"✅ Sudah bayar ({total_paid}x):",
                f"   └ {paid_str}",
                "",
                f"💸 Total tagihan  : **Rp {total_unpaid * 10_000:,.0f}**",
            ]

        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        return "\n".join(lines)

    def format_balance(self, balance: Dict) -> str:
        status_icon = {"AMAN": "✅", "WARNING": "⚠️", "BAHAYA": "🚨", "UNKNOWN": "❓"}
        icon = status_icon.get(balance["status"], "❓")
        return (
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "💰  **STATUS UANG KAS**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📥 Pemasukan    : **Rp {balance['total_pemasukan']:,.0f}**\n"
            f"📤 Pengeluaran  : **Rp {balance['total_pengeluaran']:,.0f}**\n"
            f"💵 Sisa Kas     : **Rp {balance['sisa_uang_kas']:,.0f}**\n"
            f"🏷️ Status        : {icon} **{balance['status']}**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )

    def format_expenditure(self, val: int) -> str:
        return f"📤 **Total Pengeluaran Uang Kas**\n━━━━━━━━━━━━━━━━━━━━━\n**Rp {val:,.0f}**"

    def format_income(self, val: int) -> str:
        return f"📥 **Total Pemasukan Uang Kas**\n━━━━━━━━━━━━━━━━━━━━━\n**Rp {val:,.0f}**"


uang_kas_service = UangKasService()
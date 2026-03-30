import os
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import aiohttp

logger = logging.getLogger(__name__)

class UangKasService:
    """Service for managing cash data from Google Spreadsheet via Apps Script."""
    
    def __init__(self):
        self.api_url = None
        self._initialized = False
        self._cache = {}
        self._cache_duration = 60
        
    async def initialize(self) -> bool:
        """Inisialisasi koneksi ke Google Apps Script API"""
        try:
            api_url = os.getenv("GOOGLE_APPS_SCRIPT_URL")
            if not api_url:
                logger.error("❌ GOOGLE_APPS_SCRIPT_URL tidak ditemukan")
                return False
            
            self.api_url = api_url.rstrip('/')
            
            async with aiohttp.ClientSession() as session:
                test_url = f"{self.api_url}?action=test"
                logger.info(f"🔍 Testing API: {test_url}")
                async with session.get(test_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    logger.info(f"📡 Response status: {resp.status}")
                    if resp.status == 200:
                        result = await resp.json()
                        logger.info(f"📦 Test result: {result}")
                        self._initialized = True
                        logger.info("✅ UangKasService initialized (Google Apps Script)")
                        return True
                    else:
                        logger.error(f"❌ Apps Script API error: {resp.status}")
                        return False
        except Exception as e:
            logger.error(f"❌ Error initializing UangKasService: {e}")
            return False
    
    def _get_cached(self, key: str):
        if key in self._cache:
            data, timestamp = self._cache[key]
            if datetime.now().timestamp() - timestamp < self._cache_duration:
                return data
        return None
    
    def _set_cached(self, key: str, data):
        self._cache[key] = (data, datetime.now().timestamp())
    
    async def _fetch_api(self, action: str, extra_params: str = ""):
        """Fetch data dari Google Apps Script API"""
        if not self.api_url:
            return None
        try:
            url = f"{self.api_url}?action={action}{extra_params}"
            logger.info(f"🔍 Fetching: {url}")
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    logger.info(f"📡 Response status: {resp.status}")
                    if resp.status == 200:
                        result = await resp.json()
                        if result.get("success"):
                            return result.get("data")
                        else:
                            logger.error(f"❌ API error: {result}")
                    else:
                        logger.error(f"❌ HTTP error: {resp.status}")
        except Exception as e:
            logger.error(f"❌ Fetch error: {e}")
        return None
    
    async def _get_all_students_data(self) -> List[Dict]:
        """Ambil semua data mahasiswa"""
        cached = self._get_cached("all_students")
        if cached:
            logger.info(f"📦 Using cached students data ({len(cached)} students)")
            return cached
        
        data = await self._fetch_api("getStudents")
        if not data:
            logger.warning("⚠️ No students data from API")
            return []
        
        students = data.get("students", [])
        logger.info(f"✅ Loaded {len(students)} students from API")
        
        if students:
            s = students[0]
            logger.info(f"📊 Sample: {s['name']} | paid={s.get('total_paid',0)} unpaid={s.get('total_unpaid',0)}")
            logger.info(f"📊 paid_dates sample: {s.get('paid_dates', [])[:3]}")
            logger.info(f"📊 unpaid_dates sample: {s.get('unpaid_dates', [])[:3]}")
        
        self._set_cached("all_students", students)
        return students
    
    async def _get_dashboard_data(self) -> Dict:
        """Ambil data dashboard"""
        cached = self._get_cached("dashboard")
        if cached:
            return cached
        data = await self._fetch_api("getDashboard")
        if not data:
            return {'total_pemasukan': 0, 'total_pengeluaran': 0, 'sisa_uang_kas': 0, 'status': 'UNKNOWN'}
        self._set_cached("dashboard", data)
        return data

    # HELPER: Filter past dates
    @staticmethod
    def _get_past_dates(date_list: List[str]) -> List[str]:
        """
        Dari list tanggal yyyy-MM-dd, kembalikan hanya yang SUDAH LEWAT
        (sebelum hari ini). Tanggal hari ini dan masa depan dibuang.
        """
        today = datetime.now().date()
        past = []
        for d in date_list:
            try:
                dt = datetime.strptime(d, "%Y-%m-%d").date()
                if dt < today:
                    past.append(d)
            except Exception:
                pass
        return sorted(past)

    @staticmethod
    def _fmt_date(date_str: str) -> str:
        """yyyy-MM-dd → DD/MM/YYYY"""
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").strftime("%d/%m/%Y")
        except Exception:
            return date_str

    # FIND STUDENT BY NAME
    async def find_student_by_name(self, query: str) -> Optional[Dict]:
        """Cari satu mahasiswa berdasarkan nama (fuzzy match)."""
        students = await self._get_all_students_data()
        q = query.lower().strip()
        for s in students:
            if s['name'].lower() == q:
                return s
        for s in students:
            if q in s['name'].lower():
                return s
        q_first = q.split()[0] if q.split() else ""
        for s in students:
            if q_first and q_first in s['name'].lower():
                return s
        return None

    # QUERY METHODS
    
    async def get_unpaid_this_week(self) -> List[Dict]:
        """Dapatkan mahasiswa yang belum bayar untuk minggu ini (sabtu terakhir)"""
        students = await self._get_all_students_data()
        logger.info(f"🔍 Total students: {len(students)}")
        if not students:
            return []
        
        today = datetime.now()
        days_since_saturday = (today.weekday() + 2) % 7
        if days_since_saturday == 0:
            days_since_saturday = 7
        last_saturday = today - timedelta(days=days_since_saturday)
        target_date = last_saturday.strftime("%Y-%m-%d")
        logger.info(f"📅 Looking for unpaid on: {target_date} (last Saturday)")
        
        unpaid_students = []
        for student in students:
            unpaid_dates = student.get('unpaid_dates', [])
            if target_date in unpaid_dates:
                unpaid_students.append({
                    'name': student['name'],
                    'no': student['no'],
                    'unpaid_date': target_date
                })
        logger.info(f"⚠️ Found {len(unpaid_students)} unpaid for {target_date}")
        return unpaid_students
    
    async def get_unpaid_last_week(self) -> List[Dict]:
        """Dapatkan mahasiswa yang belum bayar untuk minggu lalu"""
        students = await self._get_all_students_data()
        if not students:
            return []
        
        today = datetime.now()
        days_since_saturday = (today.weekday() + 2) % 7
        if days_since_saturday == 0:
            days_since_saturday = 7
        last_saturday = today - timedelta(days=days_since_saturday + 7)
        target_date = last_saturday.strftime("%Y-%m-%d")
        
        unpaid_students = []
        for student in students:
            if target_date in student.get('unpaid_dates', []):
                unpaid_students.append({
                    'name': student['name'],
                    'no': student['no'],
                    'unpaid_date': target_date
                })
        return unpaid_students
    
    async def get_all_unpaid_detailed(self) -> List[Dict]:
        """
        Dapatkan semua mahasiswa yang belum bayar, HANYA untuk tanggal
        yang sudah lewat (< hari ini). Tanggal masa depan diabaikan.
        """
        students = await self._get_all_students_data()
        logger.info(f"📊 Total students for detailed check: {len(students)}")
        if not students:
            return []

        today_str = datetime.now().date().strftime("%Y-%m-%d")
        logger.info(f"📅 Today: {today_str} — hanya tanggal sebelum ini yang dihitung")

        detailed_unpaid = []
        
        for student in students:
            all_unpaid = student.get('unpaid_dates', [])
            past_unpaid = self._get_past_dates(all_unpaid)
            
            logger.debug(f"  {student['name']}: total_unpaid={len(all_unpaid)}, past_unpaid={len(past_unpaid)}")
            
            if past_unpaid:
                total_owed = len(past_unpaid) * 10_000
                detailed_unpaid.append({
                    'name': student['name'],
                    'no': student['no'],
                    'unpaid_dates': past_unpaid,
                    'paid_dates': student.get('paid_dates', []),
                    'total_unpaid_count': len(past_unpaid),
                    'total_paid_count': len(student.get('paid_dates', [])),
                    'total_owed': total_owed
                })
        
        detailed_unpaid.sort(key=lambda x: x['total_unpaid_count'], reverse=True)
        logger.info(f"⚠️ Found {len(detailed_unpaid)} students with past unpaid records")
        return detailed_unpaid

    async def get_current_balance(self) -> Dict:
        dashboard = await self._get_dashboard_data()
        return {
            'total_pemasukan': dashboard.get('total_pemasukan', 0),
            'total_pengeluaran': dashboard.get('total_pengeluaran', 0),
            'sisa_uang_kas': dashboard.get('sisa_uang_kas', 0),
            'status': dashboard.get('status', 'UNKNOWN')
        }
    
    async def get_total_expenditure(self) -> int:
        dashboard = await self._get_dashboard_data()
        return dashboard.get('total_pengeluaran', 0)
    
    async def get_total_income(self) -> int:
        dashboard = await self._get_dashboard_data()
        return dashboard.get('total_pemasukan', 0)

    # FORMAT METHODS
    
    def format_unpaid_weekly_response(self, unpaid_list: List[Dict], week_label: str) -> str:
        if not unpaid_list:
            return f"✅ Tidak ada yang belum bayar uang kas {week_label}!"
        
        lines = [
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"⚠️ **BELUM BAYAR UANG KAS {week_label}**",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"👥 Total: **{len(unpaid_list)} mahasiswa**",
            "",
        ]
        for i, student in enumerate(unpaid_list[:20], 1):
            date_str = self._fmt_date(student.get('unpaid_date', 'N/A'))
            lines.append(f"**{i}. {student['name']}**")
            lines.append(f"   └ Tanggal: {date_str}")
            lines.append("")
        if len(unpaid_list) > 20:
            lines.append(f"_... dan {len(unpaid_list) - 20} lainnya_")
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        return "\n".join(lines)
    
    def format_unpaid_detailed_response(self, detailed_list: List[Dict]) -> str:
        """
        Format semua mahasiswa belum bayar + tanggal-tanggal yang sudah lewat
        dan belum dicentang. Dipanggil bot.py — nama method TIDAK diubah.
        """
        if not detailed_list:
            return "✅ Tidak ada yang belum bayar uang kas! Semua sudah lunas 🎉"
        
        today = datetime.now().date()
        total_owed_all = sum(s['total_owed'] for s in detailed_list)
        
        lines = [
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "📋 **DAFTAR BELUM BAYAR UANG KAS**",
            f"📅 Per tanggal: {today.strftime('%d/%m/%Y')}",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"👥 Total mahasiswa : **{len(detailed_list)} orang**",
            f"💸 Total tagihan   : **Rp {total_owed_all:,.0f}**",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "",
        ]
        
        for i, student in enumerate(detailed_list, 1):
            # Tampilkan SEMUA tanggal yang belum bayar (sudah difilter past saja)
            dates_fmt = [self._fmt_date(d) for d in student['unpaid_dates']]
            dates_str = ", ".join(dates_fmt)
            
            lines.append(f"**{i}. {student['name']}**")
            lines.append(f"   └ Belum bayar : {dates_str}")
            lines.append(f"   └ Tagihan     : **Rp {student['total_owed']:,.0f}** ({student['total_unpaid_count']}x)")
            lines.append("")
        
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        return "\n".join(lines)

    def format_single_student_response(self, student: Dict) -> str:
        """
        Format cek status satu mahasiswa.
        Hanya hitung unpaid_dates yang sudah lewat.
        """
        name = student['name']
        paid_dates   = student.get('paid_dates', [])
        all_unpaid   = student.get('unpaid_dates', [])
        
        # Filter
        past_unpaid  = self._get_past_dates(all_unpaid)
        total_paid   = len(paid_dates)
        total_unpaid = len(past_unpaid)

        today = datetime.now().date()
        lines = [
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"👤 **STATUS UANG KAS — {name}**",
            f"📅 Per tanggal: {today.strftime('%d/%m/%Y')}",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        ]

        if total_unpaid == 0:
            lines += [
                "✅ **LUNAS** — Semua sudah dibayar!",
                f"   └ Total bayar: {total_paid}x pembayaran",
            ]
        else:
            unpaid_fmt = ", ".join(self._fmt_date(d) for d in past_unpaid)
            paid_fmt   = ", ".join(self._fmt_date(d) for d in paid_dates) if paid_dates else "—"
            lines += [
                "⚠️ **BELUM LUNAS**",
                "",
                f"❌ Belum bayar ({total_unpaid}x):",
                f"   └ {unpaid_fmt}",
                "",
                f"✅ Sudah bayar ({total_paid}x):",
                f"   └ {paid_fmt}",
                "",
                f"💸 Total tagihan: **Rp {total_unpaid * 10_000:,.0f}**",
            ]

        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        return "\n".join(lines)

    def format_nunggak_summary_response(self, detailed_list: List[Dict]) -> str:
        """
        Format rekap total tunggakan per mahasiswa.
        detailed_list sudah difilter past-only oleh get_all_unpaid_detailed().
        """
        if not detailed_list:
            return "✅ Tidak ada mahasiswa yang nunggak. Semua sudah lunas! 🎉"

        today = datetime.now().date()
        lines = [
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "🔴 **REKAP TUNGGAKAN UANG KAS**",
            f"📅 Per tanggal: {today.strftime('%d/%m/%Y')}",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "",
        ]
        for i, s in enumerate(detailed_list, 1):
            lines.append(f"**{i}. {s['name']}**")
            lines.append(f"   └ Nunggak: {s['total_unpaid_count']}x  |  Tagihan: Rp {s['total_owed']:,.0f}")
            lines.append("")

        total_tagihan = sum(s['total_owed'] for s in detailed_list)
        lines += [
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"👥 {len(detailed_list)} mahasiswa nunggak",
            f"💸 Total semua: **Rp {total_tagihan:,.0f}**",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        ]
        return "\n".join(lines)

    def format_balance_response(self, balance: Dict) -> str:
        status_emoji = {'AMAN': '✅', 'HABIS': '⚠️', 'MINUS': '🚨', 'UNKNOWN': '❓'}
        emoji = status_emoji.get(balance['status'], '❓')
        return (
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "💰 **STATUS UANG KAS SAAT INI**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📥 Total Pemasukan  : **Rp {balance['total_pemasukan']:,.0f}**\n"
            f"📤 Total Pengeluaran: **Rp {balance['total_pengeluaran']:,.0f}**\n"
            f"💵 Sisa Uang Kas    : **Rp {balance['sisa_uang_kas']:,.0f}**\n"
            f"🏷️ Status            : {emoji} **{balance['status']}**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
    
    def format_expenditure_response(self, expenditure: int) -> str:
        return (
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "📤 **TOTAL PENGELUARAN UANG KAS**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"**Rp {expenditure:,.0f}**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
    
    def format_income_response(self, income: int) -> str:
        return (
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "📥 **TOTAL PEMASUKAN UANG KAS**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"**Rp {income:,.0f}**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )

uang_kas_service = UangKasService()
import os
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
import aiohttp

logger = logging.getLogger(__name__)

WIB_TIMEZONE = 7

class UangKasService:
    """
    Service untuk mengelola data uang kas dari Google Spreadsheet.
    Menggunakan Google Apps Script API (GRATIS, tanpa Google Cloud).
    """
    
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
                logger.error("❌ GOOGLE_APPS_SCRIPT_URL tidak ditemukan di environment")
                return False
            
            self.api_url = api_url
            
            # Test koneksi
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_url}?action=test", timeout=10) as resp:
                    if resp.status == 200:
                        self._initialized = True
                        logger.info("✅ UangKasService initialized (Google Apps Script)")
                        return True
                    else:
                        logger.error(f"❌ Apps Script API tidak responsif: {resp.status}")
                        return False
            
        except Exception as e:
            logger.error(f"❌ Error initializing UangKasService: {e}")
            return False
    
    def _get_cached(self, key: str) -> Optional[any]:
        """Ambil data dari cache jika masih valid"""
        if key in self._cache:
            data, timestamp = self._cache[key]
            if datetime.now().timestamp() - timestamp < self._cache_duration:
                return data
        return None
    
    def _set_cached(self, key: str, data: any):
        """Simpan data ke cache"""
        self._cache[key] = (data, datetime.now().timestamp())
    
    async def _fetch_api(self, action: str) -> Optional[Dict]:
        """Fetch data dari Google Apps Script API"""
        if not self.api_url:
            return None
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_url}?action={action}", timeout=15) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        if result.get("success"):
                            return result.get("data")
                        else:
                            logger.error(f"❌ API error: {result.get('error')}")
                    else:
                        logger.error(f"❌ HTTP error: {resp.status}")
        except Exception as e:
            logger.error(f"❌ Fetch error: {e}")
        
        return None
    
    async def _get_all_students_data(self) -> List[Dict]:
        """Ambil semua data mahasiswa dan status pembayaran"""
        cached = self._get_cached("all_students")
        if cached:
            return cached
        
        data = await self._fetch_api("getStudents")
        if not data:
            return []
        
        students = data.get("students", [])
        self._set_cached("all_students", students)
        logger.info(f"✅ Loaded {len(students)} students data")
        return students
    
    async def _get_dashboard_data(self) -> Dict:
        """Ambil data dari dashboard"""
        cached = self._get_cached("dashboard")
        if cached:
            return cached
        
        data = await self._fetch_api("getDashboard")
        if not data:
            return {
                'total_pemasukan': 0,
                'total_pengeluaran': 0,
                'sisa_uang_kas': 0,
                'status': 'UNKNOWN'
            }
        
        self._set_cached("dashboard", data)
        return data
    
    async def get_unpaid_this_week(self) -> List[Dict]:
        """Dapatkan mahasiswa yang belum bayar untuk minggu ini"""
        students = await self._get_all_students_data()
        if not students:
            return []
        
        today = datetime.now()
        days_since_saturday = (today.weekday() + 2) % 7
        if days_since_saturday == 0:
            days_since_saturday = 7
        last_saturday = today - timedelta(days=days_since_saturday)
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
        """Dapatkan SEMUA mahasiswa yang belum bayar dengan detail lengkap"""
        students = await self._get_all_students_data()
        if not students:
            return []
        
        detailed_unpaid = []
        
        for student in students:
            unpaid_dates = student.get('unpaid_dates', [])
            if unpaid_dates:
                payment_amount = 10000
                total_owed = len(unpaid_dates) * payment_amount
                
                detailed_unpaid.append({
                    'name': student['name'],
                    'no': student['no'],
                    'unpaid_dates': unpaid_dates,
                    'total_unpaid_count': len(unpaid_dates),
                    'total_owed': total_owed
                })
        
        detailed_unpaid.sort(key=lambda x: x['total_unpaid_count'], reverse=True)
        return detailed_unpaid
    
    async def get_current_balance(self) -> Dict:
        """Dapatkan saldo uang kas saat ini"""
        dashboard = await self._get_dashboard_data()
        return {
            'total_pemasukan': dashboard.get('total_pemasukan', 0),
            'total_pengeluaran': dashboard.get('total_pengeluaran', 0),
            'sisa_uang_kas': dashboard.get('sisa_uang_kas', 0),
            'status': dashboard.get('status', 'UNKNOWN')
        }
    
    async def get_total_expenditure(self) -> int:
        """Dapatkan total pengeluaran uang kas"""
        dashboard = await self._get_dashboard_data()
        return dashboard.get('total_pengeluaran', 0)
    
    async def get_total_income(self) -> int:
        """Dapatkan total pemasukan uang kas"""
        dashboard = await self._get_dashboard_data()
        return dashboard.get('total_pemasukan', 0)
    
    def format_unpaid_weekly_response(self, unpaid_list: List[Dict], week_label: str) -> str:
        """Format response untuk belum bayar mingguan"""
        if not unpaid_list:
            return f"✅ Tidak ada yang belum bayar uang kas {week_label}!"
        
        response = f"⚠️ **DAFTAR BELUM BAYAR UANG KAS {week_label}**\n\n"
        response += f"Total: **{len(unpaid_list)} mahasiswa**\n\n"
        
        for i, student in enumerate(unpaid_list[:20], 1):
            date_str = student.get('unpaid_date', 'N/A')
            response += f"{i}. **{student['name']}** (No: {student['no']})\n"
            response += f"   └ Tanggal: {date_str}\n\n"
        
        if len(unpaid_list) > 20:
            response += f"... dan {len(unpaid_list) - 20} lainnya\n"
        
        return response
    
    def format_unpaid_detailed_response(self, detailed_list: List[Dict]) -> str:
        """Format response untuk detail semua yang belum bayar"""
        if not detailed_list:
            return "✅ Tidak ada yang belum bayar uang kas! Semua sudah lunas 🎉"
        
        total_owed_all = sum(s['total_owed'] for s in detailed_list)
        
        response = f"⚠️ **DAFTAR LENGKAP BELUM BAYAR UANG KAS**\n\n"
        response += f"Total Mahasiswa: **{len(detailed_list)} orang**\n"
        response += f"Total Tagihan: **Rp {total_owed_all:,}**\n\n"
        response += "─" * 50 + "\n\n"
        
        for i, student in enumerate(detailed_list[:15], 1):
            dates_str = ", ".join([d[:10] if isinstance(d, str) else d.strftime('%d/%m') for d in student['unpaid_dates'][:5]])
            if len(student['unpaid_dates']) > 5:
                dates_str += f" ... (+{len(student['unpaid_dates']) - 5} lainnya)"
            
            response += f"{i}. **{student['name']}** (No: {student['no']})\n"
            response += f"   └ Belum bayar: {dates_str}\n"
            response += f"   └ Total: **Rp {student['total_owed']:,}** ({student['total_unpaid_count']}x)\n\n"
        
        if len(detailed_list) > 15:
            response += f"... dan {len(detailed_list) - 15} lainnya\n"
        
        return response
    
    def format_balance_response(self, balance: Dict) -> str:
        """Format response untuk saldo uang kas"""
        response = "💰 **STATUS UANG KAS SAAT INI**\n\n"
        response += f"📥 Total Pemasukan: **Rp {balance['total_pemasukan']:,}**\n"
        response += f"📤 Total Pengeluaran: **Rp {balance['total_pengeluaran']:,}**\n"
        response += f"💵 Sisa Uang Kas: **Rp {balance['sisa_uang_kas']:,}**\n\n"
        
        status_emoji = {
            'AMAN': '✅',
            'WARNING': '⚠️',
            'BAHAYA': '🚨',
            'UNKNOWN': '❓'
        }
        emoji = status_emoji.get(balance['status'], '❓')
        response += f"Status: {emoji} **{balance['status']}**"
        
        return response
    
    def format_expenditure_response(self, expenditure: int) -> str:
        """Format response untuk total pengeluaran"""
        return f"📤 **TOTAL PENGELUARAN UANG KAS**\n\n**Rp {expenditure:,}**"
    
    def format_income_response(self, income: int) -> str:
        """Format response untuk total pemasukan"""
        return f"📥 **TOTAL PEMASUKAN UANG KAS**\n\n**Rp {income:,}**"


# Singleton instance
uang_kas_service = UangKasService()
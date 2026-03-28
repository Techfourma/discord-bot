import re
import os
import time
import asyncio
import logging
import requests
import hashlib
import google.generativeai as genai
from typing import Optional
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)

class SmartAIService:
    def __init__(self):
        self.wolfram_id = os.getenv("WOLFRAM_APP_ID")
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        self.hf_token = os.getenv("HF_TOKEN")
        self.response_cache = {}
        self.CACHE_DURATION = 300

        if self.gemini_key:
            genai.configure(api_key=self.gemini_key)
            logger.info("✅ Gemini API configured")
        else:
            logger.warning("⚠️ GEMINI_API_KEY not set")

        if self.wolfram_id:
            logger.info("✅ Wolfram Alpha configured")
        else:
            logger.warning("⚠️ WOLFRAM_APP_ID not set")

        if self.hf_token:
            logger.info("✅ Hugging Face token configured")
        else:
            logger.warning("⚠️ HF_TOKEN not set")

    async def get_response(self, user_prompt: str, user_id: int, image_bytes: Optional[bytes] = None):
        """
        Smart Router: Choose context-sensitive AI with fallback to Gemini
        """
        cache_key = self._generate_cache_key(user_prompt, user_id, image_bytes)
        cached = self._get_cached_response(cache_key)
        if cached:
            return cached

        prompt_lower = (user_prompt or "").lower()

        try:
            # Priority 1: OCR for images
            if image_bytes and self._is_ocr_request(user_prompt):
                result = await asyncio.to_thread(self._ocr_with_gemini, image_bytes, user_prompt)
            
            # Priority 2: Mathematics and Complex Calculations
            elif self._is_math_physics_query(prompt_lower):
                logger.info("🔢 Routing to Wolfram Alpha")
                result = await asyncio.to_thread(self._wolfram_query, user_prompt)
                
                # Fallback to Gemini if ​​Wolfram fails
                if result.startswith("❌"):
                    logger.warning("⚠️ Wolfram failed, falling back to Gemini")
                    result = await asyncio.to_thread(self._gemini_query, user_prompt)
            
            # Priority 3: Code gemma
            elif self._is_code_query(prompt_lower):
                logger.info("💻 Routing to CodeGemma")
                result = await asyncio.to_thread(self._codegemma_query, user_prompt)
                
                # Fallback to Gemini if ​​CodeGemma fails
                if result.startswith("❌"):
                    logger.warning("⚠️ CodeGemma failed, falling back to Gemini")
                    result = await asyncio.to_thread(self._gemini_query, user_prompt)
            
            # Priority 4: General queries to Gemini
            else:
                logger.info("🤖 Routing to Gemini (general)")
                result = await asyncio.to_thread(self._gemini_query, user_prompt)

        except Exception as e:
            logger.exception("❌ Routing error")
            result = f"❌ Terjadi kesalahan sistem: {str(e)[:100]}"

        self._cache_response(cache_key, result)
        return result

    def _generate_cache_key(self, prompt: str, user_id: int, image_bytes: Optional[bytes]) -> str:
        """Generate cache key untuk response"""
        cache_key_prompt = (prompt or "")[:50]
        if image_bytes:
            image_hash = hashlib.md5(image_bytes).hexdigest()[:8]
            cache_key_prompt += f"_img_{image_hash}"
        return f"{user_id}_{cache_key_prompt}"

    def _get_cached_response(self, key: str) -> Optional[str]:
        """Ambil cached response jika masih valid"""
        cached = self.response_cache.get(key)
        if cached and time.time() - cached['t'] < self.CACHE_DURATION:
            logger.info("📦 Using cached response")
            return cached['r']
        return None

    def _cache_response(self, key: str, response: str):
        """Simpan response ke cache"""
        self.response_cache[key] = {'r': response, 't': time.time()}

    def _is_math_physics_query(self, prompt: str) -> bool:
        # Detect calculator style
        if re.search(r'\d+\s*[\+\-\*/]\s*\d+', prompt):
            return True

        math_keywords = [
            "integral", "diferensial", "turunan", "limit", "matrix", "matriks",
            "persamaan", "fungsi", "kalkulus", "aljabar", "trigonometri",
            "sin", "cos", "tan", "log", "ln", "akar", "pangkat",
            "hitung", "solve", "calculate", "compute", "equation",
            "derivative", "physics", "fisika", "velocity", "kecepatan",
            "acceleration", "percepatan", "force", "gaya", "energy", "energi"
        ]
        return any(keyword in prompt for keyword in math_keywords)


    def _is_code_query(self, prompt: str) -> bool:
        # intent eksplisit bikin / minta code
        if re.search(r'\b(buatkan|buat|generate|perbaiki|fix|debug|refactor)\b', prompt):
            return True

        # bahasa pemrograman
        if re.search(r'\b(c\+\+|cpp|python|java|javascript|js|php|go|rust|c#|typescript)\b', prompt):
            return True

        # ciri struktur kode
        if any(token in prompt for token in [
            "{", "}", ";", "#include", "def ", "class ", "import ", "main("
        ]):
            return True

        return False

    def _is_ocr_request(self, prompt: str) -> bool:
        """Deteksi permintaan OCR"""
        ocr_keywords = [
            "text dari gambar", "baca teks", "teks di gambar", "ocr",
            "extract text", "text extraction", "baca gambar", "scan text"
        ]
        return any(keyword in (prompt or "").lower() for keyword in ocr_keywords)

    def _ocr_with_gemini(self, image_bytes: bytes, prompt: str) -> str:
        """OCR menggunakan Gemini Flash """
        try:
            model = genai.GenerativeModel("gemini-2.5-flash")

            if not prompt or self._is_ocr_request(prompt):
                prompt = "Ekstrak semua teks yang terlihat di gambar ini dengan rapi dan terstruktur."

            result = model.generate_content(
                [prompt, {"mime_type": "image/jpeg", "data": image_bytes}],
                generation_config=genai.types.GenerationConfig(
                    candidate_count=1,
                    max_output_tokens=2048,
                    temperature=0.4,
                ),
            )
            
            text = getattr(result, "text", str(result))
            logger.info("✅ OCR successful")
            return text
            
        except Exception as e:
            logger.exception("❌ OCR (Gemini) failure")
            return f"❌ OCR Error: {str(e)[:100]}"

    def _wolfram_query(self, query: str) -> str:
        """Query ke Wolfram Alpha API"""
        try:
            if not self.wolfram_id:
                return "❌ Wolfram App ID tidak diset di environment variables."

            encoded = quote_plus(query)
            url = f"https://api.wolframalpha.com/v2/query?input={encoded}&appid={self.wolfram_id}&output=json&format=plaintext"
            
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            pods = data.get("queryresult", {}).get("pods", [])
            
            if not pods:
                return "❌ Wolfram tidak menemukan hasil untuk query ini."

            output = []
            for pod in pods:
                title = pod.get("title", "")
                subpods = pod.get("subpods", [])
                
                for subpod in subpods:
                    plaintext = subpod.get("plaintext")
                    if plaintext and plaintext.strip():
                        output.append(f"**{title}:**\n{plaintext}\n")

            result = "\n".join(output) if output else "❌ Wolfram tidak mengembalikan hasil yang dapat dibaca."
            logger.info("✅ Wolfram query successful")
            return result
            
        except requests.exceptions.Timeout:
            logger.error("⏱️ Wolfram timeout")
            return "❌ Wolfram timeout - mencoba dengan Gemini..."
        except Exception as e:
            logger.exception("❌ Wolfram query failure")
            return f"❌ Wolfram Error: {str(e)[:100]}"

    def _codegemma_query(self, prompt: str) -> str:
        """Query ke CodeGemma via Hugging Face"""
        try:
            if not self.hf_token:
                return "❌ Hugging Face token tidak diset di environment variables."

            #CodeGemma 7B Instruct
            url = "https://api-inference.huggingface.co/models/google/codegemma-7b-it"
            headers = {
                "Authorization": f"Bearer {self.hf_token}",
                "Content-Type": "application/json"
            }
            
            #Prompt format for model instructions
            formatted_prompt = f"<start_of_turn>user\n{prompt}<end_of_turn>\n<start_of_turn>model\n"
            
            payload = {
                "inputs": formatted_prompt,
                "parameters": {
                    "max_new_tokens": 1024,
                    "temperature": 0.7,
                    "top_p": 0.95,
                    "do_sample": True,
                    "return_full_text": False
                },
                "options": {
                    "wait_for_model": True
                }
            }

            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Handle various response formats
            if isinstance(data, list) and len(data) > 0:
                result = data[0].get("generated_text", "")
            elif isinstance(data, dict):
                result = data.get("generated_text") or data.get("text", "")
            else:
                result = str(data)

            if not result or result.strip() == "":
                return "❌ CodeGemma tidak mengembalikan hasil."

            logger.info("✅ CodeGemma query successful")
            return result.strip()
            
        except requests.exceptions.Timeout:
            logger.error("⏱️ CodeGemma timeout")
            return "❌ CodeGemma timeout - mencoba dengan Gemini..."
        except Exception as e:
            logger.exception("❌ CodeGemma query failure")
            return f"❌ CodeGemma Error: {str(e)[:100]}"

    def _gemini_query(self, text: str) -> str:
        """Query to Gemini API"""
        try:
            if not self.gemini_key:
                return "❌ Gemini API key tidak diset di environment variables."

            model = genai.GenerativeModel("gemini-2.5-flash")
            
            response = model.generate_content(text)
            result = getattr(response, "text", str(response))
            logger.info("✅ Gemini query successful")
            return result
            
        except Exception as e:
            logger.exception("❌ Gemini query failure")
            return f"❌ Gemini Error: {str(e)[:100]}"


# Singleton instance
ai_bot_service = SmartAIService()
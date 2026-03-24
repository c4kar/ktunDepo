"""
ktunDepo Intake Agent — LLM Analyzer
Claude API ile materyal analizi — metin ve vision destekli.

Bu modül sistemin kalbidir. LLM birincil yargıçtır.
Her dosya (teknik olarak bozuk olanlar hariç) LLM tarafından görülür.
"""

import os
import json
import logging
import httpx
import time
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List

# import anthropic  # ← Anthropic API commented out, using OpenRouter instead

from agent.intake.file_scanner import ScanResult
from agent.intake.content_preparer import PreparedContent, ContentMode
from agent.intake.hint_loader import IntakeHint

logger = logging.getLogger(__name__)


# OpenRouter API Configuration
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "anthropic/claude-3-haiku"  # Vision-capable, affordable. Diğerleri olmadı. İleride Mistral OCR araya koyup daha ucuza halledebilriiz
MAX_TOKENS = 600

# System prompt — ktunDepo baş editörü
SYSTEM_PROMPT = """You are a content screener for ktunDepo, a course material repository for Electrical-Electronics Engineering students at Konya Technical University (Turkey).

Evaluate the submitted material and return ONLY a JSON object. No explanation, no markdown.

OUTPUT SCHEMA:
{
  "decision": "ACCEPT" | "REVIEW" | "REJECT",
  "quality_score": 1 | 2 | 3 | 4 | 5,
  "category": "<semester>/<course>/<type>",
  "reason": "<max 10 words in Turkish>",
  "flags": []
}

SEMESTERS: EEM-1 through EEM-8
COURSES: Fizik I/II, Matematik I/II, Lineer Cebir, Kimya, Devre Analizi, Elektronik, Lojik Devreler, Mühendislik Mekaniği, Diferansiyel Denklemler, Bilgisayar Programlama, Sinyal ve Sistemler, Elektromanyetik
TYPES: Sınav Sorusu, Ders Notu, Formül Özeti, Lab Föyü, Sunum
FLAGS: el_yazisi, dusuk_cozunurluk, baska_universite, telif_riski

DECISION RULES:
- REJECT: completely irrelevant (ads, personal photos, blank), or technically unreadable
- REVIEW: score 1-2, or genuinely ambiguous content
- ACCEPT: score 3-5 and clearly class related

QUALITY SCORE:
5 = solved exam, clean notes, official slides
4 = unsolved exam, legible handwritten notes, formula sheet
3 = partial content, low-res but readable, other-university material with transfer value
2 = mostly unreadable or highly incomplete
1 = nearly unusable

RULES:
- Page count does not affect score. A single handwritten exam page can score 5.
- Low image quality alone is not grounds for REJECT if content is understandable.
- When in doubt, choose REVIEW. Wrong rejection is worse than wrong acceptance.
- Add "el_yazisi" flag for handwritten or scanned content.
- Add "dusuk_cozunurluk" flag for low-res images.
- reason field must be in Turkish."""


@dataclass
class AnalysisResult:
    """LLM analiz sonucu."""

    # Karar
    decision: str = "REVIEW"  # ACCEPTED | REJECTED | REVIEW
    confidence: float = 0.5
    decision_reason: str = ""
    quality_score: int = 3  # 1-5 yildiz/puan sistemi

    # Materyal bilgisi
    material_type: str = "diger"  # ders_notu, lms_sunumu, sinav_sorusu, sinav_cozumu, laboratuvar_foyu, ozet, video_ders, diger
    course_name: str = ""
    semester_guess: str = "belirsiz"  # EEM-1, EEM-2, ..., belirsiz
    topics: List[str] = field(default_factory=list)
    year_guess: Optional[str] = None
    has_solutions: bool = False
    language: str = "tr"  # tr, en, mixed

    # Teknik bilgi
    needs_ocr: bool = False
    legibility: str = "good"  # good, medium, poor (vision için)

    # Dosya adı ipucu
    suggested_filename_hint: str = ""

    # Token kullanımı
    tokens_used: Dict[str, int] = field(default_factory=dict)
    model_used: str = ""

    # Hata
    error: Optional[str] = None


class LLMAnalyzer:
    """
    OpenRouter API ile materyal analizi (OpenAI GPT OSS modeli).

    Tek LLM çağrısı ile:
    - Materyalin ne olduğunu anlar
    - Kabul/Red/Review kararını verir
    - Dosya adı ve yol için ipuçları üretir
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        LLMAnalyzer başlat.

        Args:
            api_key: OpenRouter API key (None ise env'den alınır: OPENROUTER_API_KEY)
        """
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")

    def _call_openrouter(
        self, messages: List[Dict[str, Any]], max_tokens: int = MAX_TOKENS
    ) -> dict:
        """
        OpenRouter API'ye httpx ile çağrı yap.

        Args:
            messages: Messages array (system + user)
            max_tokens: Max token sayısı

        Returns:
            API yanıtı dict
        """
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY ayarlanmamış")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/c4kar/ktunDepo",
            "X-Title": "ktunDepo Intake Agent",
        }

        payload = {
            "model": MODEL,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.1,
        }

        with httpx.Client(timeout=60) as client:
            response = client.post(OPENROUTER_API_URL, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()

    def analyze(
        self,
        scan_result: ScanResult,
        prepared_content: PreparedContent,
        hint: Optional[IntakeHint] = None,
    ) -> AnalysisResult:
        """
        Materyali analiz et.

        Args:
            scan_result: Teknik tarama sonucu
            prepared_content: Hazırlanmış içerik

        Returns:
            AnalysisResult objesi
        """
        if not self.api_key:
            return AnalysisResult(
                decision="REVIEW",
                decision_reason="OPENROUTER_API_KEY ayarlanmamış",
                error="API key missing",
            )

        try:
            # Vision modu için payload boyutu kontrolü
            if prepared_content.mode == ContentMode.VISION:
                total_b64_size = sum(len(img) for img in prepared_content.images_base64)
                # Base64 verisi yaklaşık 3MB'dan büyükse, OpenRouter API sorun yaşayabilir
                if total_b64_size > 15_000_000:  # 15MB base64 = ~11MB binary
                    logger.warning(
                        f"Vision payload too large: {total_b64_size:,} bytes for {scan_result.filename_original}. "
                        f"This may cause API errors."
                    )
                    return AnalysisResult(
                        decision="REVIEW",
                        decision_reason=(
                            f"Görüntü dosyası çok büyük ({total_b64_size / 1_000_000:.1f}MB base64). "
                            "API limitleri nedeniyle manuel inceleme gerekli."
                        ),
                        error=f"Payload size: {total_b64_size} bytes",
                    )

            if prepared_content.mode == ContentMode.TEXT:
                return self._analyze_text(scan_result, prepared_content, hint)
            elif prepared_content.mode == ContentMode.VISION:
                return self._analyze_vision(scan_result, prepared_content, hint)
            else:  # METADATA_ONLY
                return self._analyze_metadata(scan_result, prepared_content, hint)

        except httpx.HTTPStatusError as e:
            # HTTP hataları
            logger.error(
                f"OpenRouter API HTTP error {e.response.status_code} for {scan_result.filename_original}",
                exc_info=True,
            )

            # 404 hatası vision mode'da ise text mode'a geç
            if (
                e.response.status_code == 404
                and prepared_content.mode == ContentMode.VISION
            ):
                logger.warning(
                    f"Vision mode failed with 404 for {scan_result.filename_original}. "
                    "Falling back to text mode."
                )
                # Metin moduna geçiş yap
                if prepared_content.text_content:
                    return self._analyze_text(scan_result, prepared_content, hint)
                else:
                    # Text içeriği yok ise metadata moduna geç
                    return self._analyze_metadata(scan_result, prepared_content, hint)

            return AnalysisResult(
                decision="REVIEW",
                decision_reason=f"LLM API hatası ({e.response.status_code}): {str(e)[:150]}",
                error=f"HTTP {e.response.status_code}: {str(e)[:500]}",
            )
        except Exception as e:
            logger.error(
                f"Unexpected error analyzing {scan_result.filename_original}: {e}",
                exc_info=True,
            )
            return AnalysisResult(
                decision="REVIEW",
                decision_reason=f"LLM analiz hatası: {str(e)[:200]}",
                error=str(e),
            )

    def _get_hint_prompt(self, hint: Optional[IntakeHint]) -> str:
        if not hint or (not hint.semester and not hint.course):
            return ""

        hint_str = "\nÖNEMLİ KESİN BİLGİ (HINT):\nBu materyalin nereye ait olduğu kullanıcı tarafından KESİN olarak belirtilmiştir:\n"
        if hint.semester:
            hint_str += f"- Dönem: {hint.semester}\n"
        if hint.course:
            hint_str += f"- Ders: {hint.course}\n"
        hint_str += "Lütfen JSON çıktısında semester_guess ve course_name alanlarını BURADAKİ bilgilere göre doldur.\n"
        return hint_str

    def _analyze_text(
        self,
        scan: ScanResult,
        content: PreparedContent,
        hint: Optional[IntakeHint] = None,
    ) -> AnalysisResult:
        """Metin modu analizi."""
        hint_prompt = self._get_hint_prompt(hint)

        user_prompt = f"""{hint_prompt}
Dosya Bilgisi:
- Orijinal adı: {scan.filename_original}
- Boyut: {scan.size_kb:.0f} KB
- Sayfa sayısı: {scan.page_count or "bilinmiyor"}
- Format: {scan.extension}

İlk {content.pages_sampled} Sayfanın İçeriği:
{content.text_content}

Lütfen şunları belirle ve SADECE JSON döndür:

{{
  "material_type": "ders_notu | lms_sunumu | sinav_sorusu | sinav_cozumu | laboratuvar_foyu | ozet | video_ders | diger",
  "course_name": "Ders adı (Türkçe, klasördeki gibi)",
  "semester_guess": "EEM-1 | EEM-2 | EEM-3 | EEM-4 | EEM-5 | EEM-6 | EEM-7 | EEM-8 | belirsiz",
  "topics": ["konu1", "konu2"],
  "year_guess": "2022 veya null",
  "has_solutions": true/false,
  "language": "tr | en | mixed",
  "needs_ocr": true/false,
  "decision": "ACCEPTED | REJECTED | REVIEW",
  "decision_reason": "Kararın 1-2 cümle Türkçe gerekçesi",
  "confidence": 0.0-1.0,
  "quality_score": 1, 2, 3, 4 veya 5,
  "suggested_filename_hint": "kısa dosya adı ipucu (maks 3 kelime, tireli)"
}}
"""

        response_data = self._call_openrouter(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ]
        )

        return self._parse_response(response_data, MODEL, hint)

    def _analyze_vision(
        self,
        scan: ScanResult,
        content: PreparedContent,
        hint: Optional[IntakeHint] = None,
    ) -> AnalysisResult:
        """Vision modu analizi."""
        hint_prompt = self._get_hint_prompt(hint)

        # Görüntüleri OpenAI format'ına dönüştür (base64 data URL)
        image_content = []
        for img_b64 in content.images_base64:
            image_content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{content.media_type};base64,{img_b64}"},
                }
            )

        text_prompt = f"""{hint_prompt}
Bu görüntüler bir ders materyalinin ilk sayfalarıdır (metin katmanı yok,
taranmış veya fotoğraflanmış).

Dosya bilgisi:
- Orijinal adı: {scan.filename_original}
- Boyut: {scan.size_kb:.0f} KB
- Toplam sayfa: {scan.page_count or "bilinmiyor"}

Görüntüye bakarak şunları belirle ve SADECE JSON döndür:

{{
  "material_type": "ders_notu | lms_sunumu | sinav_sorusu | sinav_cozumu | laboratuvar_foyu | ozet | video_ders | diger",
  "course_name": "Ders adı",
  "semester_guess": "EEM-1 | EEM-2 | EEM-3 | EEM-4 | EEM-5 | EEM-6 | EEM-7 | EEM-8 | belirsiz",
  "topics": ["konu1", "konu2"],
  "year_guess": "2022 veya null",
  "has_solutions": true/false,
  "language": "tr | en | mixed",
  "needs_ocr": true,
  "legibility": "good | medium | poor",
  "decision": "ACCEPTED | REJECTED | REVIEW",
  "decision_reason": "Gerekçe",
  "confidence": 0.0-1.0,
  "quality_score": 1, 2, 3, 4 veya 5,
  "suggested_filename_hint": "kısa dosya adı ipucu (maks 3 kelime, tireli)"
}}
"""

        image_content.append({"type": "text", "text": text_prompt})

        response_data = self._call_openrouter(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": image_content},
            ]
        )

        return self._parse_response(response_data, MODEL, hint)

    def _analyze_metadata(
        self,
        scan: ScanResult,
        content: PreparedContent,
        hint: Optional[IntakeHint] = None,
    ) -> AnalysisResult:
        """Sadece metadata ile analiz (video dosyaları)."""
        hint_prompt = self._get_hint_prompt(hint)

        user_prompt = f"""{hint_prompt}
Video dosyası hakkında karar ver:

Dosya bilgisi:
- Orijinal adı: {scan.filename_original}
- Boyut: {scan.size_mb:.1f} MB
- Format: {scan.extension}

Sadece dosya adına ve boyutuna bakarak şunları belirle ve SADECE JSON döndür:

{{
  "material_type": "video_ders",
  "course_name": "Ders adı (dosya adından tahmin et)",
  "semester_guess": "EEM-1 | EEM-2 | ... | belirsiz",
  "topics": ["konu1"],
  "year_guess": null,
  "has_solutions": false,
  "language": "tr",
  "needs_ocr": false,
  "decision": "ACCEPTED | REJECTED | REVIEW",
  "decision_reason": "Gerekçe",
  "confidence": 0.0-1.0,
  "quality_score": 1, 2, 3, 4 veya 5,
  "suggested_filename_hint": "kısa dosya adı ipucu (maks 3 kelime, tireli)"
}}

NOT: Video içeriğini göremiyorum, sadece dosya adı ve boyutuna göre karar ver.
Şüphe varsa REVIEW seç.
"""

        response_data = self._call_openrouter(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=400,
        )

        return self._parse_response(response_data, MODEL, hint)

    def _parse_response(
        self, data: dict, model: str, hint: Optional[IntakeHint] = None
    ) -> AnalysisResult:
        """OpenRouter API yanıtını parse et."""
        # OpenRouter format: data["usage"]["prompt_tokens"] ve data["usage"]["completion_tokens"]
        usage = data.get("usage", {})
        tokens_used = {
            "input": usage.get("prompt_tokens", 0),
            "output": usage.get("completion_tokens", 0),
        }

        # OpenRouter format: data["choices"][0]["message"]["content"]
        content = data.get("choices", [{}])[0].get("message", {}).get("content")
        if content is None:
            return AnalysisResult(
                decision="REVIEW",
                decision_reason="LLM boş yanıt döndürdü",
                tokens_used=tokens_used,
                model_used=model,
                error="API returned null content",
            )

        raw = content.strip()

        # JSON bloğunu çıkar
        raw = raw.replace("```json", "").replace("```", "").strip()

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            return AnalysisResult(
                decision="REVIEW",
                decision_reason=f"JSON parse hatası: {e}",
                tokens_used=tokens_used,
                model_used=model,
                error=f"JSON parse error: {raw[:200]}",
            )

        # Karar yorumlama — düşük güvenli kararları REVIEW'a al
        decision = data.get("decision", "REVIEW").upper()
        confidence = float(data.get("confidence", 0.5))

        # Hatalı red önleme: RED ama düşük güven → REVIEW
        if decision == "REJECTED" and confidence < 0.75:
            decision = "REVIEW"
            data["decision_reason"] = (
                f"Düşük güvenle red → review'a alındı. Orijinal: {data.get('decision_reason', '')}"
            )

        # Düşük güvenli kabul → REVIEW
        if decision == "ACCEPTED" and confidence < 0.6:
            decision = "REVIEW"
            data["decision_reason"] = (
                f"Düşük güvenle kabul → review'a alındı. Orijinal: {data.get('decision_reason', '')}"
            )

        # Override with hint if available
        final_semester = data.get("semester_guess", "belirsiz")
        final_course = data.get("course_name", "")

        if hint:
            if hint.semester:
                final_semester = hint.semester
            if hint.course:
                final_course = hint.course

        return AnalysisResult(
            decision=decision,
            confidence=confidence,
            decision_reason=data.get("decision_reason", ""),
            material_type=data.get("material_type", "diger"),
            course_name=final_course,
            semester_guess=final_semester,
            topics=data.get("topics", []),
            year_guess=data.get("year_guess"),
            has_solutions=data.get("has_solutions", False),
            language=data.get("language", "tr"),
            needs_ocr=data.get("needs_ocr", False),
            legibility=data.get("legibility", "good"),
            suggested_filename_hint=data.get("suggested_filename_hint", ""),
            quality_score=data.get("quality_score", 3),
            tokens_used=tokens_used,
            model_used=model,
        )

"""
ktunDepo Intake Agent — LLM Analyzer
Claude API ile materyal analizi — metin ve vision destekli.

Bu modül sistemin kalbidir. LLM birincil yargıçtır.
Her dosya (teknik olarak bozuk olanlar hariç) LLM tarafından görülür.
"""

import os
import json
import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List

import anthropic

from agent.intake.file_scanner import ScanResult
from agent.intake.content_preparer import PreparedContent, ContentMode
from agent.intake.hint_loader import IntakeHint

logger = logging.getLogger(__name__)


# System prompt — ktunDepo baş editörü
SYSTEM_PROMPT = """Sen ktunDepo'nun baş editörüsün. Konya Teknik Üniversitesi Mühendislik
Fakültesi'nin dijital ders materyali deposunu yönetiyorsun.

Görevin: Sana gönderilen materyali inceleyip depoya alınmaya değer olup
olmadığına karar vermek.

DEPO HAKKINDA:
- Dönem bazlı organize: EEM-1, EEM-2, EEM-3, EEM-4 (8 dönem)
- Her dönemde: Fizik I/II, Matematik I/II, Lineer Cebir, Kimya, Devre Analizi,
  Elektronik, Lojik Devreler, Mühendislik Mekaniği, Diferansiyel Denklemler,
  Bilgisayar Programlama, Sinyal ve Sistemler, Elektromanyetik, vb.
- Hedef kitle: Elektrik-Elektronik Mühendisliği öğrencileri
- Değer verilen materyaller: Sınav soruları (çözümlü veya çözümsüz),
  ders notları (el yazısı dahil), formül özetleri, LMS sunumları,
  laboratuvar föyleri

KRİTİK KARAR KURALLARI:
1. Tek sayfalık bir materyal bile değerli olabilir. Sayfa sayısına göre
   karar verme. El yazısıyla yazılmış tek sayfa sınav sorusu paha biçilmezdir.

2. Metin okunamıyor olsa bile (taranmış, el yazısı, düşük çözünürlük)
   içerik anlaşılabiliyorsa kabul et. OCR sonradan yapılacak.

3. Dil Türkçe veya İngilizce olabilir. İkisi de kabul edilir.

4. Red kararı için güçlü gerekçe lazım:
   - Tamamen alakasız içerik (reklam, kişisel fotoğraf, boş sayfa)
   - Başka üniversiteye ait ve hiç transfer değeri olmayan materyal
   - Teknik olarak okunamaz düzeyde bozuk görüntü

5. Emin olamıyorsan REVIEW seç. Hatalı red, hatalı kabulden daha kötüdür.

SADECE JSON döndür. Hiçbir açıklama ekleme."""


@dataclass
class AnalysisResult:
    """LLM analiz sonucu."""

    # Karar
    decision: str = "REVIEW"  # ACCEPTED | REJECTED | REVIEW
    confidence: float = 0.5
    decision_reason: str = ""

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
    Claude API ile materyal analizi.

    Tek LLM çağrısı ile:
    - Materyalin ne olduğunu anlar
    - Kabul/Red/Review kararını verir
    - Dosya adı ve yol için ipuçları üretir
    """

    # Model seçimi
    MODEL_TEXT = "claude-sonnet-4-20250514"  # Metin analizi
    MODEL_VISION = "claude-sonnet-4-20250514"  # Vision analizi
    MODEL_METADATA = "claude-haiku-3-5-20241022"  # Sadece metadata (video)

    MAX_TOKENS = 600

    def __init__(self, api_key: Optional[str] = None):
        """
        LLMAnalyzer başlat.

        Args:
            api_key: Anthropic API key (None ise env'den alınır)
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self._client = None

    def _get_client(self):
        """Anthropic client'ı lazy load et."""
        if self._client is None:
            try:
                import anthropic

                self._client = anthropic.Anthropic(api_key=self.api_key)
            except ImportError:
                raise ImportError(
                    "anthropic kütüphanesi yüklü değil: pip install anthropic"
                )
        return self._client

    def analyze(
        self, scan_result: ScanResult, prepared_content: PreparedContent, hint: Optional[IntakeHint] = None
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
                decision_reason="ANTHROPIC_API_KEY ayarlanmamış",
                error="API key missing",
            )

        try:
            # Vision modu için payload boyutu kontrolü
            if prepared_content.mode == ContentMode.VISION:
                total_b64_size = sum(len(img) for img in prepared_content.images_base64)
                # Base64 verisi yaklaşık 3MB'dan büyükse, Anthropic API sorun yaşayabilir
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

        except anthropic.BadRequestError as e:
            # 400 Bad Request hatasını ayrıntılı logla
            logger.error(
                f"API 400 Bad Request for {scan_result.filename_original}: {e.message}",
                exc_info=True
            )
            return AnalysisResult(
                decision="REVIEW",
                decision_reason=(
                    f"LLM API hatası (400): Dosya yapısı veya boyutu uygun olmayabilir. "
                    f"Hata: {str(e.message)[:200]}"
                ),
                error=f"BadRequestError: {str(e.message)[:500]}",
            )
        except anthropic.APIStatusError as e:
            # Diğer API hataları
            logger.error(
                f"API error {e.status_code} for {scan_result.filename_original}: {e.message}",
                exc_info=True
            )
            return AnalysisResult(
                decision="REVIEW",
                decision_reason=f"LLM API hatası ({e.status_code}): {str(e.message)[:150]}",
                error=f"APIStatusError {e.status_code}: {str(e.message)[:500]}",
            )
        except Exception as e:
            logger.error(
                f"Unexpected error analyzing {scan_result.filename_original}: {e}",
                exc_info=True
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
        self, scan: ScanResult, content: PreparedContent, hint: Optional[IntakeHint] = None
    ) -> AnalysisResult:
        """Metin modu analizi."""
        client = self._get_client()

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
  "suggested_filename_hint": "kısa dosya adı ipucu (maks 3 kelime, tireli)"
}}
"""

        response = client.messages.create(
            model=self.MODEL_TEXT,
            max_tokens=self.MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

        return self._parse_response(response, self.MODEL_TEXT, hint)

    def _analyze_vision(
        self, scan: ScanResult, content: PreparedContent, hint: Optional[IntakeHint] = None
    ) -> AnalysisResult:
        """Vision modu analizi."""
        client = self._get_client()

        hint_prompt = self._get_hint_prompt(hint)

        # Görüntüleri messages array'ine ekle
        image_content = []
        for img_b64 in content.images_base64:
            image_content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": content.media_type,
                        "data": img_b64,
                    },
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
  "suggested_filename_hint": "kısa dosya adı ipucu (maks 3 kelime, tireli)"
}}
"""

        image_content.append({"type": "text", "text": text_prompt})

        response = client.messages.create(
            model=self.MODEL_VISION,
            max_tokens=self.MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": image_content}],
        )

        return self._parse_response(response, self.MODEL_VISION, hint)

    def _analyze_metadata(
        self, scan: ScanResult, content: PreparedContent, hint: Optional[IntakeHint] = None
    ) -> AnalysisResult:
        """Sadece metadata ile analiz (video dosyaları)."""
        client = self._get_client()

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
  "suggested_filename_hint": "kısa dosya adı ipucu (maks 3 kelime, tireli)"
}}

NOT: Video içeriğini göremiyorum, sadece dosya adı ve boyutuna göre karar ver.
Şüphe varsa REVIEW seç.
"""

        response = client.messages.create(
            model=self.MODEL_METADATA,
            max_tokens=400,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

        return self._parse_response(response, self.MODEL_METADATA, hint)

    def _parse_response(self, response, model: str, hint: Optional[IntakeHint] = None) -> AnalysisResult:
        """API yanıtını parse et."""
        tokens_used = {
            "input": response.usage.input_tokens,
            "output": response.usage.output_tokens,
        }

        raw = response.content[0].text.strip()

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
            tokens_used=tokens_used,
            model_used=model,
        )

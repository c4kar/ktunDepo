"""
ktunDepo Agent — Duplicate Detector
Vektör veritabanı kullanarak duplicate materyal tespiti.

Embedding stratejisi:
- Yeni materyal geldiğinde: İlk 3 sayfa embed edilir
- Qdrant'ta cosine similarity ile arama yapılır
- Benzerlik > 0.92 → kesin duplicate → red
- 0.75 < benzerlik < 0.92 → LLM'e sor
"""

import os
import uuid
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json

# Lazy imports
try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import (
        VectorParams,
        Distance,
        PointStruct,
        Filter,
        FieldCondition,
        MatchValue,
        PointIdsList,
    )

    HAS_QDRANT = True
except ImportError:
    HAS_QDRANT = False

try:
    from sentence_transformers import SentenceTransformer

    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False

from agent.logging_config import get_logger

logger = get_logger("duplicate_detector")


class DuplicateDecision(Enum):
    """Duplicate tespit kararları."""

    UNIQUE = "unique"  # Benzersiz, depoya eklenebilir
    DUPLICATE = "duplicate"  # Kesin duplicate, reddet
    SIMILAR = "similar"  # Benzer var, LLM'e sor
    ERROR = "error"  # Hata oluştu


@dataclass
class DuplicateResult:
    """Duplicate tespit sonucu."""

    decision: DuplicateDecision
    similarity: float = 0.0
    similar_documents: List[Dict[str, Any]] = field(default_factory=list)
    reason: str = ""
    content_hash: Optional[str] = None


@dataclass
class DocumentChunk:
    """Vektör veritabanına kaydedilecek doküman parçası."""

    id: str  # Unique ID (hash)
    text: str  # Metin içeriği
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class DuplicateDetector:
    """
    Vektör veritabanı tabanlı duplicate tespit sistemi.

    Embedding modeli olarak multilingual-e5-large kullanılır.
    Qdrant lokal instance ile çalışır.
    """

    COLLECTION_NAME = "ktundepo_materials"
    VECTOR_SIZE = 1024  # multilingual-e5-large boyutu

    DEFAULT_CONFIG = {
        "reject_similarity": 0.92,
        "warn_similarity": 0.75,
        "check_pages": 3,
        "embedding_model": "intfloat/multilingual-e5-large",
        "qdrant_host": "localhost",
        "qdrant_port": 6333,
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        DuplicateDetector başlat.

        Args:
            config: Yapılandırma dict'i
        """
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}
        self._client: Optional[QdrantClient] = None
        self._model: Optional[SentenceTransformer] = None
        self._initialized = False

    def _ensure_initialized(self) -> bool:
        """Qdrant ve embedding modeli başlat."""
        if self._initialized:
            return True

        if not HAS_QDRANT:
            return False

        if not HAS_SENTENCE_TRANSFORMERS:
            return False

        try:
            # Qdrant client
            self._client = QdrantClient(
                host=self.config["qdrant_host"], port=self.config["qdrant_port"]
            )

            # Collection var mı kontrol et, yoksa oluştur
            collections = self._client.get_collections().collections
            collection_names = [c.name for c in collections]

            if self.COLLECTION_NAME not in collection_names:
                self._client.create_collection(
                    collection_name=self.COLLECTION_NAME,
                    vectors_config=VectorParams(
                        size=self.VECTOR_SIZE, distance=Distance.COSINE
                    ),
                )

            # Embedding modeli (ilk kullanımda indirir)
            self._model = SentenceTransformer(self.config["embedding_model"])

            self._initialized = True
            return True

        except Exception as e:
            logger.error(f"DuplicateDetector başlatma hatası: {e}")
            return False

    def _compute_hash(self, text: str) -> str:
        """Metin için MD5 hash hesapla."""
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    def _embed_text(self, text: str) -> Optional[List[float]]:
        """Metni vektöre dönüştür."""
        if not self._ensure_initialized():
            return None

        try:
            # E5 modeli için query prefix
            query_text = f"query: {text}"
            embedding = self._model.encode(query_text, normalize_embeddings=True)
            return embedding.tolist()
        except Exception:
            return None

    def check_duplicate(
        self,
        text: str,
        semester: Optional[str] = None,
        course: Optional[str] = None,
        top_k: int = 5,
    ) -> DuplicateResult:
        """
        Metin için duplicate kontrolü yap.

        Args:
            text: Kontrol edilecek metin (genelde ilk 3 sayfanın metni)
            semester: Filtreleme için dönem
            course: Filtreleme için ders adı
            top_k: Döndürülecek benzer doküman sayısı

        Returns:
            DuplicateResult objesi
        """
        if not self._ensure_initialized():
            return DuplicateResult(
                decision=DuplicateDecision.ERROR,
                reason="Vektör veritabanı başlatılamadı",
            )

        # Hash hesapla (exact match için)
        content_hash = self._compute_hash(text)

        # Embedding oluştur
        embedding = self._embed_text(text)
        if embedding is None:
            return DuplicateResult(
                decision=DuplicateDecision.ERROR, reason="Embedding oluşturulamadı"
            )

        # Filter oluştur
        filters = []
        if semester:
            filters.append(
                FieldCondition(key="semester", match=MatchValue(value=semester))
            )
        if course:
            filters.append(FieldCondition(key="course", match=MatchValue(value=course)))

        query_filter = Filter(must=filters) if filters else None

        try:
            # Qdrant'ta ara
            response = self._client.query_points(
                collection_name=self.COLLECTION_NAME,
                query=embedding,
                query_filter=query_filter,
                limit=top_k,
                with_payload=True,
            )

            # QueryResponse.points listesini al
            results = (
                response.points if response and hasattr(response, "points") else []
            )

            if not results:
                return DuplicateResult(
                    decision=DuplicateDecision.UNIQUE,
                    similarity=0.0,
                    reason="Benzer doküman bulunamadı",
                    content_hash=content_hash,
                )

            # En yüksek benzerlik
            top_result = results[0]
            max_similarity = top_result.score

            # Benzer dokümanları listele
            similar_docs = []
            for r in results:
                if r.score >= self.config["warn_similarity"]:
                    similar_docs.append(
                        {
                            "id": r.id,
                            "similarity": r.score,
                            "semester": r.payload.get("semester"),
                            "course": r.payload.get("course"),
                            "filename": r.payload.get("filename"),
                            "path": r.payload.get("path"),
                            "material_type": r.payload.get("material_type"),
                            "year": r.payload.get("year"),
                        }
                    )

            # Karar ver
            if max_similarity >= self.config["reject_similarity"]:
                return DuplicateResult(
                    decision=DuplicateDecision.DUPLICATE,
                    similarity=max_similarity,
                    similar_documents=similar_docs,
                    reason=f"Kesin duplicate tespit edildi (benzerlik: {max_similarity:.2%})",
                    content_hash=content_hash,
                )
            elif max_similarity >= self.config["warn_similarity"]:
                return DuplicateResult(
                    decision=DuplicateDecision.SIMILAR,
                    similarity=max_similarity,
                    similar_documents=similar_docs,
                    reason=f"Benzer doküman mevcut (benzerlik: {max_similarity:.2%})",
                    content_hash=content_hash,
                )
            else:
                return DuplicateResult(
                    decision=DuplicateDecision.UNIQUE,
                    similarity=max_similarity,
                    reason="Benzersiz doküman",
                    content_hash=content_hash,
                )

        except Exception as e:
            return DuplicateResult(
                decision=DuplicateDecision.ERROR, reason=f"Arama hatası: {str(e)}"
            )

    def add_document(self, text: str, metadata: Dict[str, Any]) -> bool:
        """
        Yeni dokümanı vektör veritabanına ekle.

        Args:
            text: Doküman metni
            metadata: Metadata (semester, course, filename, path, vb.)

        Returns:
            Başarılı mı
        """
        if not self._ensure_initialized():
            return False

        try:
            # Hash ve embedding
            content_hash = self._compute_hash(text)
            embedding = self._embed_text(text)

            if embedding is None:
                return False

            # Point oluştur — Qdrant UUID veya integer ID gerektirir
            # MD5 hex (32 karakter) doğrudan UUID formatına dönüştürülür
            point_id = str(uuid.UUID(content_hash))
            point = PointStruct(
                id=point_id,
                vector=embedding,
                payload={
                    **metadata,
                    "content_hash": content_hash,
                    "text_preview": text[:500],  # İlk 500 karakter
                },
            )

            # Qdrant'a ekle
            self._client.upsert(collection_name=self.COLLECTION_NAME, points=[point])

            return True

        except Exception:
            return False

    def delete_document(self, document_id: str) -> bool:
        """Dokümanı vektör veritabanından sil."""
        if not self._ensure_initialized():
            return False

        try:
            self._client.delete(
                collection_name=self.COLLECTION_NAME,
                points_selector=PointIdsList(points=[document_id]),
            )
            return True
        except Exception:
            return False

    def get_collection_stats(self) -> Dict[str, Any]:
        """Collection istatistiklerini döndür."""
        if not self._ensure_initialized():
            return {"error": "Not initialized"}

        try:
            info = self._client.get_collection(self.COLLECTION_NAME)
            return {
                "total_points": info.points_count,
                "indexed_points": info.indexed_vectors_count,
                "status": info.status.value,
            }
        except Exception as e:
            return {"error": str(e)}

    def search_similar(
        self,
        text: str,
        semester: Optional[str] = None,
        course: Optional[str] = None,
        limit: int = 10,
        min_score: float = 0.5,
    ) -> List[Dict[str, Any]]:
        """
        Benzer dokümanları ara (RAG için).

        Args:
            text: Arama metni
            semester: Filtreleme için dönem
            course: Filtreleme için ders
            limit: Maksimum sonuç sayısı
            min_score: Minimum benzerlik skoru

        Returns:
            Benzer dokümanların listesi
        """
        if not self._ensure_initialized():
            return []

        embedding = self._embed_text(text)
        if embedding is None:
            return []

        # Filter oluştur
        filters = []
        if semester:
            filters.append(
                FieldCondition(key="semester", match=MatchValue(value=semester))
            )
        if course:
            filters.append(FieldCondition(key="course", match=MatchValue(value=course)))

        query_filter = Filter(must=filters) if filters else None

        try:
            response = self._client.query_points(
                collection_name=self.COLLECTION_NAME,
                query=embedding,
                query_filter=query_filter,
                limit=limit,
                score_threshold=min_score,
                with_payload=True,
            )

            # QueryResponse.points listesini al
            results = (
                response.points if response and hasattr(response, "points") else []
            )

            return [
                {
                    "id": r.id,
                    "score": r.score,
                    "semester": r.payload.get("semester"),
                    "course": r.payload.get("course"),
                    "filename": r.payload.get("filename"),
                    "path": r.payload.get("path"),
                    "material_type": r.payload.get("material_type"),
                    "year": r.payload.get("year"),
                    "text_preview": r.payload.get("text_preview", ""),
                }
                for r in results
            ]

        except Exception:
            return []


# Singleton instance
_detector: Optional[DuplicateDetector] = None


def get_duplicate_detector(
    config: Optional[Dict[str, Any]] = None,
) -> DuplicateDetector:
    """Global DuplicateDetector instance döndür."""
    global _detector
    if _detector is None:
        _detector = DuplicateDetector(config)
    return _detector

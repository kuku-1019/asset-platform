from __future__ import annotations

import hashlib
import json
import logging
from typing import ClassVar, Dict, List, Optional

from django.conf import settings
from django.core.cache import cache
from django.db.models import Sum, Count, Avg
from openai import OpenAI

from assets.models import Asset

logger = logging.getLogger(__name__)


class AIAnalysisService:
    """DeepSeek AI analysis with RAG integration and local SQL aggregation."""

    _client: ClassVar[Optional[OpenAI]] = None

    MODEL = "deepseek-chat"
    MAX_ASSETS = 200

    @classmethod
    def get_client(cls) -> OpenAI:
        if cls._client is None:
            cls._client = OpenAI(
                api_key=settings.DEEPSEEK_API_KEY,
                base_url=settings.DEEPSEEK_BASE_URL,
                timeout=30.0,
            )
        return cls._client

    # ------------------------------------------------------------------
    # New: RAG-driven structured analysis
    # ------------------------------------------------------------------

    @classmethod
    def analyze(cls, user_query: str, queryset) -> dict:
        """RAG-driven financial analysis.

        Returns: {"stats": {...}, "analysis": "...", "sources": [...]}
        """
        assets = list(queryset[: cls.MAX_ASSETS])

        # ── 1. Local SQL-style aggregation (硬数据，零误差) ──────────
        stats = cls._compute_stats(queryset)

        # ── 2. RAG 语义检索 ─────────────────────────────────────────
        from assets.services.vector_store import AssetVectorStore

        store = AssetVectorStore.instance()
        rag_results: dict = store.search(user_query, n_results=10)
        rag_docs: List[str] = rag_results.get("documents", [[]])[0]
        sources: List[dict] = rag_results.get("metadatas", [[]])[0]

        # ── 3. 构建 prompt，发给 DeepSeek ────────────────────────────
        docs_text = "\n".join(rag_docs) if rag_docs else "（无额外匹配资产）"
        prompt = f"""你是一个资深财务分析师。请根据以下数据回答用户的问题。

## 硬数据统计
{json.dumps(stats, ensure_ascii=False, indent=2)}

## 语义检索到的相关资产
{docs_text}

## 用户问题
{user_query}

请按以下格式回答：
1. **数据摘要**：关键指标概述
2. **分析洞察**：趋势、异常、分布特点
3. **处置建议**：具体可操作的建议，尽可能点名具体资产"""

        cache_key = _build_cache_key("structured_report", user_query)
        cached = cache.get(cache_key)
        if cached is not None:
            logger.info("Returning cached structured report")
            return cached

        client = cls.get_client()
        try:
            response = client.chat.completions.create(
                model=cls.MODEL,
                messages=[{"role": "user", "content": prompt}],
                stream=False,
            )
            analysis = response.choices[0].message.content or ""
            result = {"stats": stats, "analysis": analysis, "sources": sources}
            cache.set(cache_key, result, timeout=settings.AI_REPORT_CACHE_TTL)
            logger.info("Generated and cached structured report")
            return result
        except Exception:
            logger.exception("DeepSeek API call failed")
            raise

    # ------------------------------------------------------------------
    # Legacy: plain-text report (kept for backward compatibility)
    # ------------------------------------------------------------------

    @classmethod
    def generate_report(cls, assets_queryset) -> str:
        if not assets_queryset.exists():
            return "仓库是空的，没法分析"

        data_lines: List[str] = []
        for asset in assets_queryset[: cls.MAX_ASSETS]:
            data_lines.append(
                f"资产:{asset.name},编号:{asset.sn},状态:{asset.status},价格:{asset.price}"
            )
        data = "\n".join(data_lines)

        cache_key = _build_cache_key("asset_report", data)
        cached = cache.get(cache_key)
        if cached is not None:
            logger.info("Returning cached AI report")
            return cached

        prompt = f"""你是一个财务分析师。请分析以下数据：
{data}

要求：
1. 统计总金额(Total Amount)
2. 给出简短的运营建议"""

        client = cls.get_client()
        try:
            response = client.chat.completions.create(
                model=cls.MODEL,
                messages=[{"role": "user", "content": prompt}],
                stream=False,
            )
            result = response.choices[0].message.content or ""
            cache.set(cache_key, result, timeout=settings.AI_REPORT_CACHE_TTL)
            logger.info("Generated and cached AI report")
            return result
        except Exception:
            logger.exception("DeepSeek API call failed")
            raise

    # ------------------------------------------------------------------
    # RAG query (kept for standalone use)
    # ------------------------------------------------------------------

    @classmethod
    def rag_query(cls, user_query: str, context_documents: List[str]) -> str:
        context = "\n".join(context_documents)
        prompt = f"""基于以下资产数据回答用户问题：

资产数据：
{context}

用户问题：{user_query}

请用中文回答，简洁明了。如果数据不足以回答，请说明。"""

        client = cls.get_client()
        response = client.chat.completions.create(
            model=cls.MODEL,
            messages=[{"role": "user", "content": prompt}],
            stream=False,
        )
        return response.choices[0].message.content or ""

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_stats(queryset) -> dict:
        """Compute hard stats with SQL aggregation."""
        agg = queryset.aggregate(
            total_value=Sum("price"),
            total_count=Count("id"),
            avg_price=Avg("price"),
        )
        total_count = agg["total_count"] or 0
        total_value = round(float(agg["total_value"] or 0), 2)
        avg_price = round(float(agg["avg_price"] or 0), 2)

        # 按状态分布
        by_status: Dict[str, int] = {}
        for row in (
            queryset.values("status")
            .annotate(cnt=Count("id"))
            .order_by("status")
        ):
            by_status[row["status"]] = row["cnt"]

        # 按分类分布
        by_category: Dict[str, int] = {}
        for row in (
            queryset.values("category__name")
            .annotate(cnt=Count("id"))
            .order_by("category__name")
        ):
            name = row["category__name"] or "未分类"
            by_category[name] = row["cnt"]

        # 按部门分布
        by_department: Dict[str, int] = {}
        for row in (
            queryset.values("department__name")
            .annotate(cnt=Count("id"))
            .order_by("department__name")
        ):
            name = row["department__name"] or "未分配"
            by_department[name] = row["cnt"]

        return {
            "total_count": total_count,
            "total_value": total_value,
            "avg_price": avg_price,
            "by_status": by_status,
            "by_category": by_category,
            "by_department": by_department,
        }


def _build_cache_key(prefix: str, data: str) -> str:
    digest = hashlib.sha256(data.encode()).hexdigest()
    return f"{prefix}_{digest}"

from __future__ import annotations

import logging

from django.shortcuts import render
from rest_framework import filters, permissions, viewsets
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response

from assets.models import Asset, Category, Department
from assets.serializers import AssetSerializer, CategorySerializer, DepartmentSerializer
from assets.services.ai_analysis import AIAnalysisService
from assets.services.vector_store import AssetVectorStore

logger = logging.getLogger(__name__)


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.order_by("id")
    serializer_class = CategorySerializer
    pagination_class = None
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


class DepartmentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Department.objects.order_by("id")
    serializer_class = DepartmentSerializer
    pagination_class = None
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


class AssetViewSet(viewsets.ModelViewSet):
    queryset = Asset.objects.select_related("category", "department", "owner").order_by("-id")
    serializer_class = AssetSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "sn", "department__name", "category__name", "status"]
    ordering_fields = ["price", "purchase_date", "name", "id"]
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


def index(request: Request) -> Response:
    return render(request, "index.html")


@api_view(["POST"])
def ai_report(request: Request) -> Response:
    """RAG-driven structured financial analysis.

    Accepts optional ``query`` in POST body.  When omitted, generates a
    default overview of all assets.
    """
    user_query = (request.data.get("query") or "").strip()
    if not user_query:
        user_query = "请全面分析当前资产状况，包括各状态/部门/分类的分布，并给出运营建议"

    try:
        qs = Asset.objects.select_related("category", "department", "owner").all()
        result = AIAnalysisService.analyze(user_query, qs)
        return Response(result)
    except Exception:
        logger.exception("Failed to generate AI report")
        return Response(
            {"error": "AI 服务暂时不可用，请稍后重试"},
            status=503,
        )


@api_view(["POST"])
def reindex_assets(request: Request) -> Response:
    """Rebuild the vector store index for all assets."""
    try:
        count = AssetVectorStore.instance().index_all()
        return Response({"message": f"已完成 {count} 条资产的向量索引重建"})
    except Exception:
        logger.exception("Vector reindex failed")
        return Response({"error": "向量索引重建失败"}, status=500)


@api_view(["POST"])
def rag_query(request: Request) -> Response:
    """RAG endpoint: semantic search + AI answer.

    Expects: {"query": "user question here"}
    """
    query = request.data.get("query")
    if not query:
        return Response({"error": "请提供 query 参数"}, status=400)

    try:
        store = AssetVectorStore.instance()
        results = store.search(query, n_results=10)
        documents: list[str] = results.get("documents", [[]])[0]

        if not documents:
            return Response({"answer": "没有找到相关资产数据，请检查资产库是否已索引。"})

        answer = AIAnalysisService.rag_query(query, documents)
        return Response(
            {
                "answer": answer,
                "sources": results.get("metadatas", [[]])[0],
            }
        )
    except Exception:
        logger.exception("RAG query failed")
        return Response({"error": "RAG 查询失败，请稍后重试"}, status=500)

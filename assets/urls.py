from django.urls import include, path
from rest_framework.routers import DefaultRouter

from assets.views import (
    AssetViewSet,
    CategoryViewSet,
    DepartmentViewSet,
    ai_report,
    rag_query,
    reindex_assets,
)

router = DefaultRouter()
router.register(r"assets", AssetViewSet)
router.register(r"categories", CategoryViewSet)
router.register(r"departments", DepartmentViewSet)

urlpatterns = [
    path("", include(router.urls)),
    path("ai-report/", ai_report, name="ai_report"),
    path("rag-query/", rag_query, name="rag_query"),
    path("reindex/", reindex_assets, name="reindex"),
]

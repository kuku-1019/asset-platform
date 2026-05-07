from __future__ import annotations

from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from assets.models import Asset, Category, Department


# ══════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════

def _mock_deepseek(text: str = "AI 分析结果"):
    """Return a fake chat completion object."""

    class FakeChoice:
        message = type("msg", (), {"content": text})()

    class FakeResponse:
        choices = [FakeChoice()]

    return FakeResponse()


# ══════════════════════════════════════════════════════════════════
# Model tests
# ══════════════════════════════════════════════════════════════════

class ModelTests(TestCase):
    def test_category_str(self):
        c = Category.objects.create(name="电子设备")
        self.assertEqual(str(c), "电子设备")

    def test_department_str(self):
        d = Department.objects.create(name="技术部")
        self.assertEqual(str(d), "技术部")

    def test_department_parent(self):
        parent = Department.objects.create(name="总公司")
        child = Department.objects.create(name="研发部", parent=parent)
        self.assertEqual(child.parent, parent)

    def test_asset_str(self):
        cat = Category.objects.create(name="家具")
        dept = Department.objects.create(name="行政")
        asset = Asset.objects.create(
            name="办公桌", sn="SN-001", price=1500,
            status="使用中", category=cat, department=dept,
            purchase_date="2025-01-01",
        )
        self.assertEqual(str(asset), "办公桌 (SN-001)")

    def test_asset_unique_sn(self):
        cat = Category.objects.create(name="家具")
        dept = Department.objects.create(name="行政")
        Asset.objects.create(
            name="A", sn="SN-UNIQUE", price=100, status="闲置中",
            category=cat, department=dept, purchase_date="2025-01-01",
        )
        with self.assertRaises(Exception):
            Asset.objects.create(
                name="B", sn="SN-UNIQUE", price=200, status="使用中",
                category=cat, department=dept, purchase_date="2025-01-02",
            )


# ══════════════════════════════════════════════════════════════════
# API tests
# ══════════════════════════════════════════════════════════════════

class APITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="testuser", password="testpass")
        cls.cat = Category.objects.create(name="电子设备")
        cls.cat2 = Category.objects.create(name="办公家具")
        cls.dept = Department.objects.create(name="技术部")
        cls.dept2 = Department.objects.create(name="人事部")

        cls.asset1 = Asset.objects.create(
            name="MacBook", sn="SN-001", price=15000,
            status="使用中", category=cls.cat, department=cls.dept,
            purchase_date="2025-06-01",
        )
        cls.asset2 = Asset.objects.create(
            name="打印机", sn="SN-002", price=3000,
            status="维修中", category=cls.cat, department=cls.dept2,
            purchase_date="2024-03-15",
        )
        cls.asset3 = Asset.objects.create(
            name="办公椅", sn="SN-003", price=800,
            status="闲置中", category=cls.cat2, department=cls.dept,
            purchase_date="2025-01-10",
        )

    # ── GET /api/assets/ ──────────────────────────────────────────

    def test_list_assets(self):
        resp = self.client.get("/api/assets/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["count"], 3)

    def test_list_assets_default_ordering(self):
        resp = self.client.get("/api/assets/")
        # Default ordering is -id, so newest first
        self.assertEqual(resp.data["results"][0]["sn"], "SN-003")

    def test_search_assets(self):
        resp = self.client.get("/api/assets/?search=MacBook")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["count"], 1)
        self.assertEqual(resp.data["results"][0]["name"], "MacBook")

    def test_search_by_status(self):
        resp = self.client.get("/api/assets/?search=维修中")
        self.assertEqual(resp.data["count"], 1)
        self.assertEqual(resp.data["results"][0]["sn"], "SN-002")

    def test_order_by_price(self):
        resp = self.client.get("/api/assets/?ordering=price")
        results = resp.data["results"]
        self.assertEqual(results[0]["price"], "800.00")

    def test_order_by_price_desc(self):
        resp = self.client.get("/api/assets/?ordering=-price")
        results = resp.data["results"]
        self.assertEqual(results[0]["price"], "15000.00")

    # ── POST /api/assets/ ─────────────────────────────────────────

    def test_create_asset(self):
        resp = self.client.post("/api/assets/", {
            "name": "服务器", "sn": "SN-NEW", "price": 50000,
            "status": "使用中", "category": self.cat.id,
            "department": self.dept.id, "purchase_date": "2025-08-01",
        }, format="json")
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(Asset.objects.count(), 4)

    def test_create_asset_missing_fields(self):
        resp = self.client.post("/api/assets/", {
            "name": "X", "sn": "SN-X",
        }, format="json")
        self.assertEqual(resp.status_code, 400)

    # ── GET /api/assets/<id>/ ─────────────────────────────────────

    def test_retrieve_asset(self):
        resp = self.client.get(f"/api/assets/{self.asset1.id}/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["name"], "MacBook")
        self.assertIn("category", resp.data)
        self.assertIn("department", resp.data)

    # ── DELETE /api/assets/<id>/ ──────────────────────────────────

    def test_delete_asset(self):
        resp = self.client.delete(f"/api/assets/{self.asset3.id}/")
        self.assertEqual(resp.status_code, 204)
        self.assertEqual(Asset.objects.count(), 2)

    # ── Categories & Departments ──────────────────────────────────

    def test_list_categories(self):
        resp = self.client.get("/api/categories/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 2)

    def test_list_departments(self):
        resp = self.client.get("/api/departments/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 2)

    # ── AI Report ─────────────────────────────────────────────────

    @patch("assets.services.ai_analysis.OpenAI")
    def test_ai_report_with_query(self, mock_openai):
        mock_openai.return_value.chat.completions.create.return_value = (
            _mock_deepseek("分析结果")
        )
        resp = self.client.post("/api/ai-report/", {
            "query": "分析闲置资产",
        }, format="json")
        self.assertEqual(resp.status_code, 200)
        data = resp.data
        self.assertIn("stats", data)
        self.assertIn("analysis", data)
        self.assertIn("sources", data)
        stats = data["stats"]
        self.assertEqual(stats["total_count"], 3)

    @patch("assets.services.ai_analysis.OpenAI")
    def test_ai_report_no_query_uses_default(self, mock_openai):
        mock_openai.return_value.chat.completions.create.return_value = (
            _mock_deepseek("默认分析")
        )
        resp = self.client.post("/api/ai-report/", {}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("stats", resp.data)

    # ── RAG Query ─────────────────────────────────────────────────

    @patch("assets.services.ai_analysis.OpenAI")
    def test_rag_query(self, mock_openai):
        mock_openai.return_value.chat.completions.create.return_value = (
            _mock_deepseek("RAG 回答")
        )
        resp = self.client.post("/api/rag-query/", {
            "query": "哪些资产在维修？",
        }, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("answer", resp.data)

    def test_rag_query_missing_query(self):
        resp = self.client.post("/api/rag-query/", {}, format="json")
        self.assertEqual(resp.status_code, 400)

    # ── Reindex ───────────────────────────────────────────────────

    def test_reindex(self):
        resp = self.client.post("/api/reindex/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("message", resp.data)

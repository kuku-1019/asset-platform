"""Lightweight vector store for asset semantic search.

Uses sentence-transformers for embeddings and numpy for in-memory vector
storage with json-based persistence.  No external vector DB required.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import ClassVar, Dict, List, Optional

import numpy as np
from django.conf import settings

from assets.models import Asset

logger = logging.getLogger(__name__)


class AssetVectorStore:
    """In-memory vector index with disk persistence.

    Stores asset embeddings as numpy arrays and uses cosine similarity
    for semantic search.  Vectors persist to a json file on disk.
    """

    _instance: ClassVar[Optional["AssetVectorStore"]] = None

    def __init__(self) -> None:
        self._model = None  # lazy load
        self._ids: List[str] = []
        self._documents: List[str] = []
        self._metadatas: List[dict] = []
        self._embeddings: np.ndarray | None = None
        self._persist_path = Path(settings.CHROMA_PERSIST_DIR) / "vectors.json"

    @classmethod
    def instance(cls) -> "AssetVectorStore":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def _embed_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer("BAAI/bge-small-zh-v1.5")
        return self._model

    # ------------------------------------------------------------------
    # indexing
    # ------------------------------------------------------------------

    @staticmethod
    def _asset_to_document(asset: Asset) -> str:
        department_name = asset.department.name if asset.department else ""
        category_name = asset.category.name if asset.category else ""
        owner_name = asset.owner.username if asset.owner else ""
        return (
            f"资产名称: {asset.name}, 编号: {asset.sn}, "
            f"状态: {asset.status}, 价格: {asset.price}元, "
            f"部门: {department_name}, 分类: {category_name}, "
            f"使用人: {owner_name}, 购买日期: {asset.purchase_date}"
        )

    @staticmethod
    def _asset_metadata(asset: Asset) -> dict:
        return {
            "name": asset.name,
            "sn": asset.sn,
            "status": asset.status,
            "price": str(asset.price),
            "department": asset.department.name if asset.department else "",
            "category": asset.category.name if asset.category else "",
            "purchase_date": str(asset.purchase_date),
        }

    def index_asset(self, asset: Asset) -> None:
        doc = self._asset_to_document(asset)
        vec = self._embed_model.encode([doc], normalize_embeddings=True)[0]

        asset_id = str(asset.id)

        if self._embeddings is not None:
            try:
                idx = self._ids.index(asset_id)
                self._documents[idx] = doc
                self._metadatas[idx] = self._asset_metadata(asset)
                self._embeddings[idx] = vec
                return
            except ValueError:
                pass

        self._ids.append(asset_id)
        self._documents.append(doc)
        self._metadatas.append(self._asset_metadata(asset))
        if self._embeddings is None:
            self._embeddings = np.array([vec])
        else:
            self._embeddings = np.vstack([self._embeddings, vec])

    def delete_asset(self, asset_id: int) -> None:
        asset_id = str(asset_id)
        if asset_id not in self._ids:
            return
        idx = self._ids.index(asset_id)
        self._ids.pop(idx)
        self._documents.pop(idx)
        self._metadatas.pop(idx)
        if self._embeddings is not None:
            self._embeddings = np.delete(self._embeddings, idx, axis=0)

    def index_all(self, queryset=None) -> int:
        if queryset is None:
            queryset = Asset.objects.select_related("department", "category", "owner").all()

        if not queryset.exists():
            self.clear()
            return 0

        ids: List[str] = []
        docs: List[str] = []
        metas: List[dict] = []

        for asset in queryset:
            ids.append(str(asset.id))
            docs.append(self._asset_to_document(asset))
            metas.append(self._asset_metadata(asset))

        embeddings = self._embed_model.encode(docs, normalize_embeddings=True, show_progress_bar=True)

        self._ids = ids
        self._documents = docs
        self._metadatas = metas
        self._embeddings = np.array(embeddings)

        self._save()
        logger.info("Indexed %d assets", len(ids))
        return len(ids)

    def clear(self) -> None:
        self._ids = []
        self._documents = []
        self._metadatas = []
        self._embeddings = None

    # ------------------------------------------------------------------
    # search
    # ------------------------------------------------------------------

    def search(self, query: str, n_results: int = 10) -> dict:
        if self._embeddings is None or len(self._ids) == 0:
            self._load()
        if self._embeddings is None or len(self._ids) == 0:
            return {"ids": [[]], "documents": [[]], "metadatas": [[]]}

        query_vec = self._embed_model.encode([query], normalize_embeddings=True)[0]
        scores = np.dot(self._embeddings, query_vec)

        n = min(n_results, len(scores))
        top_indices = np.argsort(scores)[::-1][:n]

        return {
            "ids": [[self._ids[i] for i in top_indices]],
            "documents": [[self._documents[i] for i in top_indices]],
            "metadatas": [[self._metadatas[i] for i in top_indices]],
        }

    def count(self) -> int:
        return len(self._ids)

    # ------------------------------------------------------------------
    # persistence
    # ------------------------------------------------------------------

    def _save(self) -> None:
        self._persist_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "ids": self._ids,
            "documents": self._documents,
            "metadatas": self._metadatas,
            "embeddings": self._embeddings.tolist() if self._embeddings is not None else [],
        }
        self._persist_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    def _load(self) -> None:
        if not self._persist_path.exists():
            return
        try:
            payload = json.loads(self._persist_path.read_text(encoding="utf-8"))
            self._ids = payload.get("ids", [])
            self._documents = payload.get("documents", [])
            self._metadatas = payload.get("metadatas", [])
            emb_list = payload.get("embeddings", [])
            if emb_list:
                self._embeddings = np.array(emb_list)
            logger.info("Loaded %d vectors from disk", len(self._ids))
        except Exception:
            logger.exception("Failed to load vectors from disk")

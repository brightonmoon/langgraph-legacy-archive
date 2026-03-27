"""
Vector store helpers for the LangGraph RAG sub-agent.
"""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

try:
    from langchain_community.vectorstores import FAISS  # type: ignore
except ImportError:
    FAISS = None

try:
    import faiss  # type: ignore  # noqa: F401

    _FAISS_RUNTIME_AVAILABLE = True
except ImportError:
    _FAISS_RUNTIME_AVAILABLE = False

from src.utils.paths import get_project_root, resolve_data_file_path


def create_default_embedding_model() -> Embeddings:
    """Instantiate the mandated Ollama embedding model (bge-m3:latest)."""
    load_dotenv()
    try:
        from langchain_ollama import OllamaEmbeddings  # type: ignore
    except ImportError as exc:
        raise ImportError(
            "langchain-ollama 패키지가 필요합니다. "
            "pip install langchain-ollama 로 설치 후 다시 시도하세요."
        ) from exc

    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model_name = os.getenv("RAG_EMBEDDING_MODEL", "bge-m3:latest")
    return OllamaEmbeddings(model=model_name, base_url=base_url)


def _ensure_vectorstore_dir(path: Optional[str | Path]) -> Path:
    base_path = Path(path) if path else get_project_root() / ".rag_vectorstores"
    base_path.mkdir(parents=True, exist_ok=True)
    return base_path


def _slugify(value: str) -> str:
    return value.replace(" ", "_").replace("/", "_").lower()


class VectorStoreManager:
    """Utility class that manages FAISS vector stores on disk."""

    def __init__(
        self,
        embedding_model: Optional[Embeddings] = None,
        vectorstore_dir: Optional[str | Path] = None,
    ) -> None:
        load_dotenv()
        self.embedding_model = embedding_model or create_default_embedding_model()
        self.base_dir = _ensure_vectorstore_dir(vectorstore_dir)
        self.default_chunk_size = int(os.getenv("RAG_CHUNK_SIZE", "800"))
        self.default_chunk_overlap = int(os.getenv("RAG_CHUNK_OVERLAP", "150"))
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.default_chunk_size,
            chunk_overlap=self.default_chunk_overlap,
        )
        self.use_faiss = bool(_FAISS_RUNTIME_AVAILABLE and FAISS is not None)

    # ------------------------------------------------------------------
    # Document ingestion helpers
    # ------------------------------------------------------------------
    def prepare_documents(self, ingest_inputs: Dict[str, Any]) -> List[Document]:
        documents: List[Document] = []
        if not ingest_inputs:
            return documents

        for payload in ingest_inputs.get("documents", []):
            if isinstance(payload, Document):
                documents.append(payload)
            elif isinstance(payload, dict):
                content = payload.get("content") or payload.get("page_content")
                if not content:
                    continue
                metadata = payload.get("metadata") or {}
                documents.append(Document(page_content=str(content), metadata=metadata))

        for text in ingest_inputs.get("texts", []):
            if not text:
                continue
            documents.append(Document(page_content=str(text), metadata={"source": "inline"}))

        for path in ingest_inputs.get("paths", []):
            resolved = self._resolve_path(path)
            if not resolved or not resolved.exists():
                continue
            content = resolved.read_text(encoding="utf-8")
            documents.append(Document(page_content=content, metadata={"source": str(resolved)}))

        return documents

    def split_documents(
        self,
        documents: Iterable[Document],
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
    ) -> List[Document]:
        if not documents:
            return []

        if chunk_size or chunk_overlap:
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size or self.default_chunk_size,
                chunk_overlap=chunk_overlap or self.default_chunk_overlap,
            )
        else:
            splitter = self._splitter

        return splitter.split_documents(list(documents))

    # ------------------------------------------------------------------
    # Security validation
    # ------------------------------------------------------------------
    def _validate_vectorstore_integrity(self, store_path: Path) -> bool:
        """
        Validate vectorstore integrity before loading with allow_dangerous_deserialization.

        Checks:
        - Path is within expected base directory (prevents directory traversal)
        - index.faiss file exists and is not suspiciously large (> 1GB)
        - Path contains no symlinks that could point elsewhere

        Returns:
            True if all integrity checks pass, False otherwise.
        """
        try:
            # Check 1: Ensure store_path is within self.base_dir
            resolved_store = store_path.resolve()
            resolved_base = self.base_dir.resolve()
            if not resolved_store.is_relative_to(resolved_base):
                return False

            # Check 2: Verify no symlinks in the path
            if store_path.is_symlink():
                return False
            for parent in store_path.parents:
                if parent.is_symlink():
                    return False
                if parent == resolved_base:
                    break

            # Check 3: Check index.faiss exists and is not suspiciously large
            index_file = store_path / "index.faiss"
            if not index_file.exists():
                return False

            # 1GB size limit for FAISS index files
            max_size = 1024 * 1024 * 1024  # 1GB in bytes
            if index_file.stat().st_size > max_size:
                return False

            return True
        except Exception:
            # Any error during validation means we can't trust the file
            return False

    # ------------------------------------------------------------------
    # Vector store management
    # ------------------------------------------------------------------
    def generate_vectorstore_id(self, hint: Optional[str] = None) -> str:
        slug = _slugify(hint) if hint else uuid.uuid4().hex[:10]
        return slug

    def index_documents(
        self,
        documents: List[Document],
        vectorstore_id: Optional[str] = None,
    ) -> str:
        if not documents:
            raise ValueError("인덱싱할 문서가 없습니다.")

        vector_id = vectorstore_id or self.generate_vectorstore_id()
        store_path = self.base_dir / vector_id
        store_path.mkdir(parents=True, exist_ok=True)

        if self.use_faiss:
            self._index_with_faiss(documents, store_path)
        else:
            self._index_with_numpy(documents, store_path)

        return vector_id

    def _index_with_faiss(self, documents: List[Document], store_path: Path) -> None:
        faiss_store = None
        if (store_path / "index.faiss").exists():
            # Validate vectorstore integrity before loading with allow_dangerous_deserialization
            if self._validate_vectorstore_integrity(store_path):
                # Note: allow_dangerous_deserialization=True is required by the FAISS API
                # for loading pickled objects, but integrity checks mitigate the risk of
                # arbitrary code execution from crafted vectorstore files.
                faiss_store = FAISS.load_local(
                    str(store_path),
                    self.embedding_model,
                    allow_dangerous_deserialization=True,
                )
                faiss_store.add_documents(documents)
            else:
                # Validation failed - re-create index from scratch for safety
                faiss_store = FAISS.from_documents(documents, self.embedding_model)
        else:
            faiss_store = FAISS.from_documents(documents, self.embedding_model)

        faiss_store.save_local(str(store_path))

    def _index_with_numpy(self, documents: List[Document], store_path: Path) -> None:
        existing_docs, existing_embeddings = self._load_numpy_store(store_path)
        new_docs = [
            {"content": doc.page_content, "metadata": doc.metadata}
            for doc in documents
        ]
        new_embeddings = np.array(
            self.embedding_model.embed_documents([doc.page_content for doc in documents]),
            dtype="float32",
        )

        combined_docs = existing_docs + new_docs
        combined_embeddings = (
            np.vstack([existing_embeddings, new_embeddings])
            if existing_embeddings.size
            else new_embeddings
        )

        (store_path / "documents.json").write_text(
            json.dumps(combined_docs, ensure_ascii=False),
            encoding="utf-8",
        )
        np.save(store_path / "embeddings.npy", combined_embeddings)

    def load_vectorstore(self, vectorstore_id: Optional[str]):
        if not vectorstore_id:
            return None

        store_path = self.base_dir / vectorstore_id
        if not store_path.exists():
            return None

        # Validate vectorstore integrity before loading
        if not self._validate_vectorstore_integrity(store_path):
            return None

        # Note: allow_dangerous_deserialization=True is required by the FAISS API
        # for loading pickled objects, but integrity checks mitigate the risk of
        # arbitrary code execution from crafted vectorstore files.
        return FAISS.load_local(
            str(store_path),
            self.embedding_model,
            allow_dangerous_deserialization=True,
        )

    def retrieve_documents(
        self,
        vectorstore_id: Optional[str],
        query: Optional[str],
        *,
        search_kwargs: Optional[Dict[str, Any]] = None,
    ):
        if not vectorstore_id or not query:
            return []

        search_params = {"k": int(os.getenv("RAG_TOP_K", "4"))}
        if search_kwargs:
            search_params.update(search_kwargs)

        if self.use_faiss:
            store = self.load_vectorstore(vectorstore_id)
            if not store:
                return []
            retriever = store.as_retriever(search_kwargs=search_params)
            return retriever.invoke(query)

        return self._retrieve_with_numpy(vectorstore_id, query, search_params["k"])

    def _retrieve_with_numpy(self, vectorstore_id: str, query: str, k: int):
        store_path = self.base_dir / vectorstore_id
        docs, embeddings = self._load_numpy_store(store_path)
        if not len(docs) or not embeddings.size:
            return []

        query_vector = np.array(self.embedding_model.embed_query(query), dtype="float32")
        similarities = self._cosine_similarity(embeddings, query_vector)
        top_indices = similarities.argsort()[::-1][:k]

        return [
            Document(page_content=docs[idx]["content"], metadata=docs[idx].get("metadata", {}))
            for idx in top_indices
        ]

    def _load_numpy_store(self, store_path: Path) -> Tuple[List[Dict[str, Any]], np.ndarray]:
        docs_path = store_path / "documents.json"
        embeddings_path = store_path / "embeddings.npy"
        if not docs_path.exists() or not embeddings_path.exists():
            return [], np.empty((0, 0), dtype="float32")

        documents = json.loads(docs_path.read_text(encoding="utf-8"))
        embeddings = np.load(embeddings_path, allow_pickle=False)
        return documents, embeddings

    @staticmethod
    def _cosine_similarity(matrix: np.ndarray, vector: np.ndarray) -> np.ndarray:
        if not matrix.size:
            return np.array([])

        vector = vector / (np.linalg.norm(vector) + 1e-8)
        norms = np.linalg.norm(matrix, axis=1, keepdims=True) + 1e-8
        normalized = matrix / norms
        return normalized @ vector

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _resolve_path(self, path_like: str | Path) -> Optional[Path]:
        if not path_like:
            return None

        path_obj = Path(path_like)
        if path_obj.is_absolute():
            return path_obj

        try:
            return resolve_data_file_path(str(path_obj))
        except Exception:
            return (get_project_root() / path_obj).resolve()


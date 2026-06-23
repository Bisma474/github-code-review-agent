from typing import Optional
from chromadb import Collection
from app.rag.chroma import get_or_create_collection
from app.core.logging import get_logger

logger = get_logger(__name__)


class PatternRepository:
    def __init__(self, collection: Optional[Collection] = None):
        self.collection = collection or get_or_create_collection()

    def add_pattern(
        self,
        pattern_id: str,
        code_snippet: str,
        issue_type: str,
        severity: str,
        message: str,
        suggestion: str,
        repo_full_name: str,
        file_path: str,
        metadata: Optional[dict] = None,
    ):
        doc = f"Issue: {message}\nSuggestion: {suggestion}\nCode: {code_snippet}"
        meta = {
            "issue_type": issue_type,
            "severity": severity,
            "repo": repo_full_name,
            "file": file_path,
            ** (metadata or {}),
        }
        self.collection.add(documents=[doc], metadatas=[meta], ids=[pattern_id])
        logger.debug(f"Pattern '{pattern_id}' stored")
        return pattern_id

    def search_similar(self, query: str, n_results: int = 5) -> list[dict]:
        results = self.collection.query(query_texts=[query], n_results=n_results)
        items = []
        for i in range(len(results["ids"][0])):
            items.append({
                "id": results["ids"][0][i],
                "document": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i] if results.get("distances") else None,
            })
        return items

    def count(self) -> int:
        return self.collection.count()

    def delete_pattern(self, pattern_id: str):
        self.collection.delete(ids=[pattern_id])


pattern_repo = PatternRepository()

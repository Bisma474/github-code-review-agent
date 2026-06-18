from functools import lru_cache
from typing import Optional
import chromadb
from chromadb import ClientAPI, Collection
from chromadb.errors import NotFoundError
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def get_embedding_function():
    settings = get_settings()
    if settings.EMBEDDING_PROVIDER == "ollama":
        from chromadb.utils.embedding_functions import OllamaEmbeddingFunction
        return OllamaEmbeddingFunction(
            model_name=settings.LLM_MODEL,
            url=f"{settings.OLLAMA_BASE_URL}/api/embeddings",
        )
    return DefaultEmbeddingFunction()


@lru_cache
def get_chroma_client() -> ClientAPI:
    settings = get_settings()
    if settings.APP_ENV == "production":
        client = chromadb.HttpClient(host=settings.CHROMA_HOST, port=settings.CHROMA_PORT)
    else:
        client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
    logger.info(f"ChromaDB client created (mode={'http' if settings.APP_ENV == 'production' else 'persistent'})")
    return client


def get_or_create_collection(name: Optional[str] = None) -> Collection:
    client = get_chroma_client()
    settings = get_settings()
    collection_name = name or settings.CHROMA_COLLECTION_NAME
    try:
        collection = client.get_collection(collection_name, embedding_function=get_embedding_function())
        logger.info(f"ChromaDB collection '{collection_name}' loaded ({collection.count()} docs)")
    except (ValueError, NotFoundError):
        collection = client.create_collection(collection_name, embedding_function=get_embedding_function())
        logger.info(f"ChromaDB collection '{collection_name}' created")
    return collection

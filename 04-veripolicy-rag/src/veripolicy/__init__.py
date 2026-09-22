"""VeriPolicy-RAG: version-, scope-, and conflict-aware retrieval."""

from .pipeline import VeriPolicyRAG
from .schemas import QueryContext, RAGResponse

__all__ = ["VeriPolicyRAG", "QueryContext", "RAGResponse"]
__version__ = "0.1.0"


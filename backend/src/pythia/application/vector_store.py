"""
Modulo per l'integrazione di Vector DB.
Supporta ChromaDB per ambiente locale e Weaviate Cloud per la produzione.
"""
import os
from typing import List, Dict, Any, Optional
import chromadb
import weaviate
from weaviate.classes.init import Auth
from pydantic import BaseModel

class SearchResult(BaseModel):
    chunk: str
    metadata: Dict[str, Any]
    score: float

class VectorStoreService:
    """Gestisce il DB vettoriale (ChromaDB locale, Weaviate Cloud prod)."""

    def __init__(self, mode: str='local'):
        self.mode = mode
        self.similarity_threshold = 0.85
        if self.mode == 'production':
            weaviate_url = os.environ.get('WEAVIATE_URL', '')
            weaviate_api_key = os.environ.get('WEAVIATE_API_KEY', '')
            if weaviate_url and weaviate_api_key:
                self.client = weaviate.connect_to_weaviate_cloud(cluster_url=weaviate_url, auth_credentials=Auth.api_key(weaviate_api_key))
            self.collection_name = 'NewsSentiment'
        else:
            self.client = chromadb.PersistentClient(path='./chroma_db')
            self.collection = self.client.get_or_create_collection(name='news_sentiment', metadata={'hnsw:space': 'cosine'})

    async def add_texts(self, texts: List[str], metadatas: List[Dict[str, Any]], ids: List[str]) -> None:
        """Aggiunge documenti al Vector Store."""
        if self.mode == 'production':
            collection = self.client.collections.get(self.collection_name)
            with collection.batch.dynamic() as batch:
                for idx, text in enumerate(texts):
                    batch.add_object(properties={'text': text, **metadatas[idx]}, uuid=ids[idx])
        else:
            self.collection.add(documents=texts, metadatas=metadatas, ids=ids)

    async def similarity_search(self, query: str, limit: int=5) -> List[SearchResult]:
        """Esegue semantic search con threshold cosine > 0.85."""
        results = []
        if self.mode == 'production':
            collection = self.client.collections.get(self.collection_name)
            response = collection.query.near_text(query=query, limit=limit, return_metadata=['distance'])
            for obj in response.objects:
                distance = obj.metadata.distance if obj.metadata.distance is not None else 1.0
                score = 1.0 - distance
                if score >= self.similarity_threshold:
                    results.append(SearchResult(chunk=obj.properties.get('text', ''), metadata={k: v for k, v in obj.properties.items() if k != 'text'}, score=score))
        else:
            response = self.collection.query(query_texts=[query], n_results=limit, include=['documents', 'metadatas', 'distances'])
            if not response['documents']:
                return []
            docs = response['documents'][0]
            metas = response['metadatas'][0]
            dists = response['distances'][0]
            for doc, meta, distance in zip(docs, metas, dists):
                score = 1.0 - distance
                if score >= self.similarity_threshold:
                    results.append(SearchResult(chunk=doc, metadata=meta, score=score))
        return sorted(results, key=lambda x: x.score, reverse=True)

    def close(self):
        if self.mode == 'production':
            self.client.close()
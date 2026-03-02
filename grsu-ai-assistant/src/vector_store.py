"""
Модуль векторного хранилища для ИИ-ассистента инженерного факультета ГрГУ
Использует ChromaDB для хранения и поиска векторных представлений документов
"""
import os
from typing import List, Optional, Dict, Any
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
from langchain_community.embeddings import HuggingFaceEmbeddings
import chromadb
from chromadb.config import Settings


class VectorStore:
    """Класс для работы с векторным хранилищем документов"""
    
    def __init__(self, collection_name: str = "engineering_docs", persist_dir: str = "./db_storage"):
        self.collection_name = collection_name
        self.persist_dir = persist_dir
        
        # Создаем директорию для хранения данных, если она не существует
        os.makedirs(persist_dir, exist_ok=True)
        
        # Инициализируем клиент ChromaDB
        self.client = chromadb.PersistentClient(path=persist_dir)
        
        # Настройка эмбеддингов (можно использовать OpenAI или локальные)
        self._setup_embeddings()
        
        # Создаем коллекцию
        self.collection = self.client.get_or_create_collection(name=collection_name)
        
        # Инициализируем LangChain wrapper для Chroma
        self.chroma_db = Chroma(
            client=self.client,
            collection_name=collection_name,
            embedding_function=self.embeddings
        )
    
    def _setup_embeddings(self):
        """Настройка функции эмбеддингов"""
        # Проверяем наличие OPENAI_API_KEY в переменных окружения
        if os.getenv("OPENAI_API_KEY"):
            # Используем OpenAI embeddings
            self.embeddings = OpenAIEmbeddings(disallowed_special=())
            self.embedding_model = "openai"
        else:
            # Используем локальные эмбеддинги
            self.embeddings = HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2"
            )
            self.embedding_model = "huggingface"
    
    def add_documents(self, documents: List[Document]):
        """Добавление документов в векторное хранилище"""
        if not documents:
            return
        
        # Добавляем документы в ChromaDB
        self.chroma_db.add_documents(documents)
    
    def similarity_search(self, query: str, k: int = 5, filter_dict: Optional[Dict] = None) -> List[Document]:
        """Поиск похожих документов"""
        if filter_dict:
            # Поиск с фильтрацией по метаданным
            results = self.chroma_db.similarity_search(
                query, 
                k=k, 
                filter=filter_dict
            )
        else:
            # Обычный поиск
            results = self.chroma_db.similarity_search(query, k=k)
        
        return results
    
    def hybrid_search(self, query: str, k: int = 5, filter_dict: Optional[Dict] = None) -> List[Document]:
        """Гибридный поиск (семантический + ключевой)"""
        # Сначала делаем семантический поиск
        semantic_results = self.similarity_search(query, k=k*2, filter_dict=filter_dict)
        
        # Затем можем дополнительно обработать результаты
        # для улучшения релевантности
        
        return semantic_results[:k]
    
    def search_by_metadata(self, metadata_filters: Dict[str, Any], query: str = "", k: int = 5) -> List[Document]:
        """Поиск документов по метаданным"""
        # Если указан текст запроса, выполняем поиск с фильтрацией по метаданным
        if query:
            return self.similarity_search(query, k=k, filter_dict=metadata_filters)
        else:
            # Если запрос пустой, возвращаем документы только по фильтрам
            results = self.client.get_collection(self.collection_name).get(
                where=metadata_filters,
                limit=k
            )
            
            # Преобразуем результаты в формат Document
            documents = []
            for i in range(len(results['ids'])):
                doc = Document(
                    page_content=results['documents'][i],
                    metadata=results['metadatas'][i] if results['metadatas'] else {}
                )
                documents.append(doc)
            
            return documents
    
    def get_document_count(self) -> int:
        """Возвращает количество документов в коллекции"""
        return self.client.get_collection(self.collection_name).count()
    
    def delete_collection(self):
        """Удаляет всю коллекцию"""
        self.client.delete_collection(self.collection_name)
        # Пересоздаем коллекцию
        self.collection = self.client.get_or_create_collection(name=self.collection_name)
        self.chroma_db = Chroma(
            client=self.client,
            collection_name=self.collection_name,
            embedding_function=self.embeddings
        )
    
    def update_document(self, doc_id: str, document: Document):
        """Обновление конкретного документа"""
        # ChromaDB не поддерживает прямое обновление, поэтому удаляем и добавляем заново
        self.delete_documents([doc_id])
        self.add_documents([document])
    
    def delete_documents(self, doc_ids: List[str]):
        """Удаление документов по ID"""
        self.client.get_collection(self.collection_name).delete(ids=doc_ids)


class AdvancedVectorStore(VectorStore):
    """Расширенный класс векторного хранилища с дополнительными возможностями"""
    
    def __init__(self, collection_name: str = "engineering_docs", persist_dir: str = "./db_storage"):
        super().__init__(collection_name, persist_dir)
        
        # Добавляем возможность работы с несколькими коллекциями
        self.collections = {collection_name: self.chroma_db}
    
    def create_collection(self, name: str):
        """Создание новой коллекции"""
        if name not in self.collections:
            self.collections[name] = Chroma(
                client=self.client,
                collection_name=name,
                embedding_function=self.embeddings
            )
    
    def switch_collection(self, name: str):
        """Переключение на другую коллекцию"""
        if name not in self.collections:
            self.create_collection(name)
        
        # Обновляем активную коллекцию
        self.collection_name = name
        self.chroma_db = self.collections[name]
    
    def get_collections_stats(self) -> Dict[str, int]:
        """Получение статистики по всем коллекциям"""
        stats = {}
        for name, collection in self.client.list_collections():
            stats[name] = collection.count()
        return stats
    
    def search_in_all_collections(self, query: str, k: int = 5) -> List[Document]:
        """Поиск по всем коллекциям"""
        all_results = []
        for collection_name in self.collections.keys():
            self.switch_collection(collection_name)
            results = self.similarity_search(query, k=k//len(self.collections))
            for doc in results:
                doc.metadata['collection'] = collection_name
                all_results.append(doc)
        
        # Сортируем по релевантности (пока просто возвращаем все)
        return all_results[:k]


# Пример использования
if __name__ == "__main__":
    # Пример создания векторного хранилища
    vector_store = VectorStore(collection_name="test_docs")
    
    # Пример добавления документов
    # docs = [Document(page_content="Пример содержимого", metadata={"type": "GOST"})]
    # vector_store.add_documents(docs)
    
    print("Векторное хранилище готово к использованию")
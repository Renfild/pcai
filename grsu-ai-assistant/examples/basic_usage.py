"""
Примеры использования API ИИ-ассистента инженерного факультета ГрГУ
"""
from src.document_loader import EngineeringDocumentLoader
from src.chunker import SmartEngineeringChunker
from src.vector_store import VectorStore
from src.rag_engine import RAGEngine


def example_basic_usage():
    """Пример базового использования системы"""
    print("🚀 Пример базового использования ИИ-ассистента")
    print("-" * 50)
    
    # 1. Загрузка документов
    print("1. Загрузка документов...")
    loader = EngineeringDocumentLoader()
    
    # Загрузка из директории (в примере будет ошибка, если директория не существует)
    # docs = loader.load_directory("./data/documents")
    
    # Для примера создадим тестовые документы
    from langchain.schema import Document
    test_docs = [
        Document(
            page_content="ГОСТ 21.1101-2020 устанавливает требования к оформлению чертежей. Пункт 5.2.1: Все размеры должны быть проставлены в миллиметрах.",
            metadata={'filename': 'gost_21.1101.pdf', 'document_type': 'GOST', 'standard_number': '21.1101', 'year': '2020'}
        ),
        Document(
            page_content="СНиП 2.01.07-2020 определяет нормы нагрузок для строительства. Таблица 3.1: Временные нагрузки на перекрытия жилых зданий составляют 1.5 кПа.",
            metadata={'filename': 'snip_2.01.07.pdf', 'document_type': 'SNIP', 'standard_number': '2.01.07', 'year': '2020'}
        ),
        Document(
            page_content="СТБ 1111-2019: Пункт 4.3.2 - Бетон класса В25 должен иметь прочность на сжатие не менее 25 МПа.",
            metadata={'filename': 'stb_1111.pdf', 'document_type': 'STB', 'standard_number': '1111', 'year': '2019'}
        )
    ]
    
    print(f"   Загружено {len(test_docs)} тестовых документов")
    
    # 2. Разбиение на чанки
    print("2. Разбиение на чанки...")
    chunker = SmartEngineeringChunker(chunk_size=1000, chunk_overlap=200)
    chunks = chunker.split_documents(test_docs)
    print(f"   Создано {len(chunks)} чанков")
    
    # 3. Создание векторного хранилища
    print("3. Создание векторного хранилища...")
    vector_store = VectorStore(collection_name="example_docs")
    vector_store.add_documents(chunks)
    print(f"   Документов в базе: {vector_store.get_document_count()}")
    
    # 4. Создание RAG-движка
    print("4. Создание RAG-движка...")
    rag_engine = RAGEngine(vector_store)
    print("   RAG-движок готов к использованию")
    
    # 5. Выполнение запросов
    print("\n5. Выполнение тестовых запросов:")
    print("-" * 30)
    
    queries = [
        "Какие требования к оформлению чертежей по ГОСТ 21.1101?",
        "Какова норма нагрузки на перекрытия по СНиП?",
        "Какая прочность бетона В25 по СТБ?"
    ]
    
    for query in queries:
        print(f"\n❓ Вопрос: {query}")
        response = rag_engine.query(query)
        
        print(f"✅ Ответ: {response.answer}")
        print(f"📊 Уверенность: {response.confidence:.2f}")
        print(f"🏷️ Тип запроса: {response.query_type}")
        
        if response.citations:
            print("📝 Источники:")
            for citation in response.citations[:2]:  # Показываем первые 2 источника
                print(f"   - {citation.source} (релевантность: {citation.relevance_score:.2f})")
        
        print("-" * 30)


def example_advanced_usage():
    """Пример расширенного использования системы"""
    print("\n🚀 Пример расширенного использования ИИ-ассистента")
    print("-" * 50)
    
    # Использование расширенных возможностей
    from src.rag_engine import AdvancedRAGEngine
    
    # Создаем компоненты как в базовом примере
    from langchain.schema import Document
    test_docs = [
        Document(
            page_content="ГОСТ 21.1101-2020 устанавливает требования к оформлению чертежей. Пункт 5.2.1: Все размеры должны быть проставлены в миллиметрах. Пункт 5.3: Шрифт должен быть не менее 3.5 мм.",
            metadata={'filename': 'gost_21.1101.pdf', 'document_type': 'GOST', 'standard_number': '21.1101', 'year': '2020'}
        ),
        Document(
            page_content="ГОСТ 2.304-2011 определяет типы шрифтов для технических чертежей. Тип Arial допускается для компьютерных чертежей.",
            metadata={'filename': 'gost_2.304.pdf', 'document_type': 'GOST', 'standard_number': '2.304', 'year': '2011'}
        )
    ]
    
    from src.chunker import SmartEngineeringChunker
    from src.vector_store import VectorStore
    from src.rag_engine import RAGEngine
    
    chunker = SmartEngineeringChunker(chunk_size=1000, chunk_overlap=200)
    chunks = chunker.split_documents(test_docs)
    
    vector_store = VectorStore(collection_name="advanced_example")
    vector_store.add_documents(chunks)
    
    advanced_rag_engine = AdvancedRAGEngine(vector_store)
    
    # Пример многоходового запроса
    query = "Какие требования к шрифту для чертежей по ГОСТ?"
    print(f"❓ Вопрос: {query}")
    
    response = advanced_rag_engine.multi_hop_query(query)
    print(f"✅ Ответ: {response.answer}")
    print(f"📊 Уверенность: {response.confidence:.2f}")
    
    # Пример запроса с разным уровнем детализации
    print(f"\n📝 Ответ с разным уровнем детализации:")
    
    detail_responses = {
        'brief': advanced_rag_engine.query_with_detail_level(query, 'brief'),
        'normal': advanced_rag_engine.query_with_detail_level(query, 'normal'),
        'detailed': advanced_rag_engine.query_with_detail_level(query, 'detailed')
    }
    
    for level, resp in detail_responses.items():
        print(f"   {level.upper()}: {resp.answer[:100]}...")


def example_filtering_and_search():
    """Пример использования фильтрации и поиска"""
    print("\n🚀 Пример использования фильтрации и поиска")
    print("-" * 50)
    
    # Создаем тестовые документы с разными метаданными
    from langchain.schema import Document
    test_docs = [
        Document(
            page_content="ГОСТ 21.1101-2020: Требования к оформлению чертежей строительных объектов.",
            metadata={'document_type': 'GOST', 'standard_number': '21.1101', 'year': '2020', 'category': 'construction'}
        ),
        Document(
            page_content="СТБ 1111-2019: Параметры бетона класса В25.",
            metadata={'document_type': 'STB', 'standard_number': '1111', 'year': '2019', 'category': 'materials'}
        ),
        Document(
            page_content="СНиП 2.01.07-2020: Нагрузки и воздействия.",
            metadata={'document_type': 'SNIP', 'standard_number': '2.01.07', 'year': '2020', 'category': 'construction'}
        )
    ]
    
    from src.chunker import SmartEngineeringChunker
    from src.vector_store import VectorStore
    
    chunker = SmartEngineeringChunker(chunk_size=1000, chunk_overlap=200)
    chunks = chunker.split_documents(test_docs)
    
    vector_store = VectorStore(collection_name="filtering_example")
    vector_store.add_documents(chunks)
    
    # Поиск с фильтрацией по типу документа
    print("🔍 Поиск документов по категории 'construction':")
    construction_docs = vector_store.search_by_metadata({'category': 'construction'}, "", k=5)
    for doc in construction_docs:
        print(f"   - {doc.metadata['document_type']} {doc.metadata['standard_number']}: {doc.page_content[:50]}...")
    
    # Поиск с фильтрацией по году
    print(f"\n🔍 Поиск документов за 2020 год:")
    year_docs = vector_store.search_by_metadata({'year': '2020'}, "", k=5)
    for doc in year_docs:
        print(f"   - {doc.metadata['document_type']} {doc.metadata['standard_number']}: {doc.page_content[:50]}...")


if __name__ == "__main__":
    example_basic_usage()
    example_advanced_usage()
    example_filtering_and_search()
    
    print("\n🎉 Все примеры выполнены успешно!")
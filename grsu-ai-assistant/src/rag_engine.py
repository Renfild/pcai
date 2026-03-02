"""
Модуль RAG-движка для ИИ-ассистента инженерного факультета ГрГУ
Обеспечивает генерацию ответов с цитированием источников
"""
from typing import List, Dict, Any, Optional, NamedTuple
from langchain.chains import RetrievalQA
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory
from pydantic import BaseModel, Field
from src.vector_store import VectorStore
import re


class Citation(BaseModel):
    """Модель для цитирования источника"""
    source: str = Field(description="Источник документа")
    page: Optional[int] = Field(description="Номер страницы")
    content: str = Field(description="Фрагмент исходного документа")
    relevance_score: float = Field(description="Оценка релевантности (0-1)")
    section: Optional[str] = Field(description="Раздел документа")


class RAGResponse(BaseModel):
    """Модель ответа RAG-движка"""
    answer: str = Field(description="Сгенерированный ответ")
    citations: List[Citation] = Field(description="Список цитирований")
    confidence: float = Field(description="Уверенность в ответе (0-1)")
    query_type: str = Field(description="Тип запроса (normative/calculation/formatting/other)")


class QueryClassifier:
    """Классификация типа запроса пользователя"""
    
    @staticmethod
    def classify_query(query: str) -> str:
        """Определяет тип запроса"""
        query_lower = query.lower()
        
        # Паттерны для различных типов запросов
        patterns = {
            'normative': [
                r'(гост|стб|снип|стандарт|норм[аи][ае][тм][иы][вр][ае][нн][иы][её][мн]\s*|требовани[яеё])',
                r'(должн[аои]|необходимо|следует|допускается|запрещено)',
                r'(материалы|размеры|параметры|характеристики|свойства)'
            ],
            'calculation': [
                r'(расчет|рассчитать|вычислить|определить\s+.+?\s+по\s+формул)',
                r'(формула|коэффициент|методика)',
                r'(нагрузка|прочность|деформация|устойчивость)'
            ],
            'formatting': [
                r'(оформлен|шрифт|размер|вид|чертеж|график|таблица|схема)',
                r'(формат|рамка|графа|подпись|маркировка)',
                r'(визуальн|представлен|изображен)'
            ]
        }
        
        scores = {'normative': 0, 'calculation': 0, 'formatting': 0, 'other': 0}
        
        for qtype, type_patterns in patterns.items():
            for pattern in type_patterns:
                if re.search(pattern, query_lower):
                    scores[qtype] += 1
        
        # Возвращаем тип с наибольшим счетом
        return max(scores, key=scores.get)


class RAGEngine:
    """Основной RAG-движок с поддержкой цитирования"""
    
    def __init__(self, vector_store: VectorStore, model_name: str = "gpt-3.5-turbo"):
        self.vector_store = vector_store
        self.query_classifier = QueryClassifier()
        
        # Инициализируем модель
        if model_name.startswith("gpt"):
            self.llm = ChatOpenAI(model_name=model_name, temperature=0.1)
        else:
            # Здесь можно добавить поддержку других моделей
            self.llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0.1)
        
        # Создаем цепочку RetrievalQA
        self.qa_chain = RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=self.vector_store.chroma_db.as_retriever(search_kwargs={"k": 5}),
            return_source_documents=True
        )
        
        # Память для диалога
        self.memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
    
    def query(self, user_query: str, include_citations: bool = True) -> RAGResponse:
        """Выполнение запроса к RAG-движку"""
        # Классифицируем запрос
        query_type = self.query_classifier.classify_query(user_query)
        
        # Получаем релевантные документы
        docs = self.vector_store.similarity_search(user_query, k=5)
        
        # Формируем контекст из релевантных документов
        context_parts = []
        citations = []
        
        for i, doc in enumerate(docs):
            content = doc.page_content
            source = doc.metadata.get('filename', 'unknown')
            page = doc.metadata.get('page', None)
            section = doc.metadata.get('section_number', None)
            
            context_parts.append(f"Документ {i+1}: {content}")
            
            # Создаем цитирование
            citation = Citation(
                source=source,
                page=page,
                content=content[:200] + "..." if len(content) > 200 else content,  # Обрезаем для краткости
                relevance_score=1.0 - (i * 0.1),  # Уменьшаем оценку для менее релевантных документов
                section=section
            )
            citations.append(citation)
        
        context = "\n\n".join(context_parts)
        
        # Проверяем актуальность документов
        outdated_docs = self._check_document_currency(docs)
        
        # Формируем промпт в зависимости от типа запроса
        prompt_template = self._get_prompt_template(query_type)
        
        # Если есть устаревшие документы, добавляем информацию об этом
        if outdated_docs:
            outdated_msg = f"\n\nВНИМАНИЕ: Обнаружены устаревшие документы: {', '.join(outdated_docs)}. Рекомендуется проверить актуальность информации."
            context += outdated_msg
        
        # Заполняем промпт
        prompt = prompt_template.format(
            context=context,
            question=user_query
        )
        
        # Получаем ответ от модели
        response = self.llm.invoke(prompt)
        answer = response.content
        
        # Определяем уверенность (упрощенно)
        confidence = self._calculate_confidence(answer, docs)
        
        return RAGResponse(
            answer=answer,
            citations=citations if include_citations else [],
            confidence=confidence,
            query_type=query_type
        )
    
    def _get_prompt_template(self, query_type: str) -> str:
        """Возвращает подходящий шаблон промпта для типа запроса"""
        templates = {
            'normative': """Вы являетесь экспертом в области инженерных стандартов (ГОСТ, СТБ, СНиП).
Отвечайте на вопросы строго на основе предоставленного контекста. 
Если в контексте нет информации для ответа, скажите: "Информация в предоставленных документах отсутствует".
Формируйте ответ в соответствии с инженерными стандартами, ссылаясь на конкретные пункты, таблицы или рисунки если они есть.

Контекст: {context}

Вопрос: {question}

Ответ:""",
            
            'calculation': """Вы являетесь экспертом в области инженерных расчетов.
На основе предоставленного контекста дайте ответ с указанием формул, методик расчета и параметров.
Обязательно ссылайтесь на конкретные источники информации (номера ГОСТ, СТБ, СНиП и пункты).
Если в контексте недостаточно данных для расчета, укажите это.

Контекст: {context}

Вопрос: {question}

Ответ:""",
            
            'formatting': """Вы являетесь экспертом в области оформления инженерной документации.
На основе предоставленного контекста дайте ответ о требованиях к оформлению чертежей, таблиц, схем и другой документации.
Обязательно укажите конкретные стандарты и пункты, в которых описаны эти требования.

Контекст: {context}

Вопрос: {question}

Ответ:""",
            
            'other': """Ответьте на вопрос на основе предоставленного контекста.
Если в контексте нет информации для ответа, скажите: "Информация в предоставленных документах отсутствует".
Старайтесь давать точные ответы с ссылками на источники.

Контекст: {context}

Вопрос: {question}

Ответ:"""
        }
        
        return templates.get(query_type, templates['other'])
    
    def _check_document_currency(self, documents: List[Any]) -> List[str]:
        """Проверяет актуальность документов"""
        outdated_docs = []
        
        for doc in documents:
            year = doc.metadata.get('year')
            doc_type = doc.metadata.get('document_type')
            standard_number = doc.metadata.get('standard_number')
            
            # Простая проверка: если год старше 10 лет, считаем документ потенциально устаревшим
            if year and isinstance(year, str) and year.isdigit():
                year_int = int(year)
                if 2026 - year_int > 10:  # Предполагаем текущий год 2026
                    doc_identifier = f"{doc_type} {standard_number}" if standard_number else doc.metadata.get('filename', 'unknown')
                    outdated_docs.append(doc_identifier)
        
        return outdated_docs
    
    def _calculate_confidence(self, answer: str, documents: List[Any]) -> float:
        """Вычисляет уверенность в ответе"""
        # Если в ответе есть фраза об отсутствии информации, уверенность минимальна
        if "информация в предоставленных документах отсутствует" in answer.lower():
            return 0.1
        
        # Уверенность зависит от количества и качества источников
        num_docs = len(documents)
        if num_docs == 0:
            return 0.1
        elif num_docs == 1:
            return 0.6
        elif num_docs >= 2:
            return min(0.9, 0.5 + (num_docs * 0.15))  # Максимум 0.9
        
        return 0.5  # По умолчанию средняя уверенность


class AdvancedRAGEngine(RAGEngine):
    """Расширенный RAG-движок с дополнительными возможностями"""
    
    def __init__(self, vector_store: VectorStore, model_name: str = "gpt-3.5-turbo"):
        super().__init__(vector_store, model_name)
        
        # Добавляем возможности для работы с разными уровнями детализации
        self.detail_levels = {
            'brief': 0.3,   # Краткий ответ
            'normal': 0.6,  # Стандартный ответ
            'detailed': 0.9 # Подробный ответ
        }
    
    def query_with_detail_level(self, user_query: str, detail_level: str = 'normal') -> RAGResponse:
        """Выполнение запроса с заданным уровнем детализации"""
        base_response = self.query(user_query)
        
        # Регулируем уровень детализации ответа
        if detail_level == 'brief':
            # Краткий ответ
            sentences = base_response.answer.split('.')
            if len(sentences) > 3:
                base_response.answer = '.'.join(sentences[:3]) + '.'
        elif detail_level == 'detailed':
            # Можно расширить ответ, запросив дополнительную информацию
            # Пока просто возвращаем оригинальный ответ
            pass
        
        return base_response
    
    def multi_hop_query(self, user_query: str) -> RAGResponse:
        """Выполнение многоходового запроса"""
        # Сначала определяем основной запрос
        primary_query = user_query
        
        # Извлекаем ключевые сущности для дополнительного поиска
        entities = self._extract_entities(user_query)
        
        # Делаем первичный поиск
        initial_docs = self.vector_store.similarity_search(primary_query, k=3)
        
        # Если нашли мало информации, пытаемся найти больше через связанные сущности
        if len(initial_docs) < 2:
            for entity in entities:
                related_docs = self.vector_store.similarity_search(entity, k=2)
                initial_docs.extend(related_docs)
        
        # Ограничиваем количество документов
        docs = initial_docs[:5]
        
        # Формируем контекст и генерируем ответ как в основном методе
        context_parts = []
        citations = []
        
        for i, doc in enumerate(docs):
            content = doc.page_content
            source = doc.metadata.get('filename', 'unknown')
            page = doc.metadata.get('page', None)
            section = doc.metadata.get('section_number', None)
            
            context_parts.append(f"Документ {i+1}: {content}")
            
            citation = Citation(
                source=source,
                page=page,
                content=content[:200] + "..." if len(content) > 200 else content,
                relevance_score=1.0 - (i * 0.1),
                section=section
            )
            citations.append(citation)
        
        context = "\n\n".join(context_parts)
        
        prompt_template = self._get_prompt_template(
            self.query_classifier.classify_query(user_query)
        )
        
        prompt = prompt_template.format(
            context=context,
            question=user_query
        )
        
        response = self.llm.invoke(prompt)
        answer = response.content
        confidence = self._calculate_confidence(answer, docs)
        
        return RAGResponse(
            answer=answer,
            citations=citations,
            confidence=confidence,
            query_type=self.query_classifier.classify_query(user_query)
        )
    
    def _extract_entities(self, text: str) -> List[str]:
        """Извлечение ключевых сущностей из текста"""
        # Простое извлечение сущностей с помощью регулярных выражений
        # В реальной системе можно использовать NER модели
        
        # Паттерны для поиска стандартов, чисел, технических терминов
        patterns = [
            r'(гост|стб|снип)\s*[\d\.-]+',  # Названия стандартов
            r'\b\d+\.\d+\.?\d*\b',         # Числовые значения
            r'\b(?:мм|см|м|кг|т|мпа|кн)\b', # Единицы измерения
            r'\b(?:бетон|сталь|дерево|кирпич|железобетон)\b', # Материалы
            r'\b(?:температура|влажность|давление|нагрузка)\b' # Параметры
        ]
        
        entities = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            entities.extend(matches)
        
        # Убираем дубликаты и возвращаем уникальные сущности
        return list(set(entities))


# Пример использования
if __name__ == "__main__":
    # Пример использования RAG-движка
    # vector_store = VectorStore(collection_name="test_docs")
    # rag_engine = RAGEngine(vector_store)
    # response = rag_engine.query("Какие требования к оформлению чертежей по ГОСТ 21.1101?")
    # print(response.answer)
    
    print("RAG-движок готов к использованию")
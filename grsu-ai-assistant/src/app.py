"""
Веб-интерфейс для ИИ-ассистента инженерного факультета ГрГУ
Streamlit приложение для работы с инженерными стандартами
"""
import streamlit as st
import os
from pathlib import Path
from typing import List
import tempfile

# Импорты наших модулей
from src.document_loader import EngineeringDocumentLoader
from src.chunker import SmartEngineeringChunker
from src.vector_store import VectorStore
from src.rag_engine import RAGEngine, RAGResponse


# Настройка страницы
st.set_page_config(
    page_title="ИИ-ассистент инженерного факультета ГрГУ",
    page_icon="🏗️",
    layout="wide"
)

# Заголовок приложения
st.title("🏗️ ИИ-ассистент инженерного факультета ГрГУ")
st.markdown("""
Это приложение позволяет осуществлять поиск по инженерным стандартам (ГОСТ, СТБ, СНиП) 
с возможностью цитирования источников. Загрузите документы и задавайте вопросы по инженерной тематике.
""")

# Инициализация сессии
if 'vector_store' not in st.session_state:
    st.session_state.vector_store = None
if 'rag_engine' not in st.session_state:
    st.session_state.rag_engine = None
if 'uploaded_files' not in st.session_state:
    st.session_state.uploaded_files = []
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

# Боковая панель
with st.sidebar:
    st.header("⚙️ Настройки")
    
    # Выбор модели
    model_option = st.selectbox(
        "Выберите модель ИИ:",
        ["gpt-3.5-turbo", "gpt-4"],
        index=0
    )
    
    # Настройки загрузки документов
    st.subheader("📥 Загрузка документов")
    
    uploaded_files = st.file_uploader(
        "Выберите файлы (PDF, DOCX, TXT)",
        type=['pdf', 'docx', 'txt'],
        accept_multiple_files=True
    )
    
    if uploaded_files:
        # Временная директория для загрузки
        upload_dir = Path("./uploads")
        upload_dir.mkdir(exist_ok=True)
        
        new_files = []
        for uploaded_file in uploaded_files:
            if uploaded_file.name not in [f.name for f in st.session_state.uploaded_files]:
                # Сохраняем файл во временной директории
                file_path = upload_dir / uploaded_file.name
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                new_files.append(uploaded_file)
        
        st.session_state.uploaded_files.extend(new_files)
        
        if new_files:
            st.success(f"Загружено {len(new_files)} новых файлов")
    
    # Отображение загруженных файлов
    if st.session_state.uploaded_files:
        st.subheader("📚 Загруженные файлы")
        for file in st.session_state.uploaded_files:
            st.write(f"- {file.name}")
    
    # Кнопка индексации
    if st.button("🔄 Индексировать документы"):
        if st.session_state.uploaded_files:
            with st.spinner("Индексация документов..."):
                try:
                    # Инициализируем компоненты
                    loader = EngineeringDocumentLoader()
                    chunker = SmartEngineeringChunker(chunk_size=1000, chunk_overlap=200)
                    
                    # Загружаем документы
                    docs = []
                    for file in st.session_state.uploaded_files:
                        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.name).suffix) as tmp_file:
                            tmp_file.write(file.getbuffer())
                            docs.extend(loader.load_file(tmp_file.name))
                            os.unlink(tmp_file.name)
                    
                    # Разбиваем на чанки
                    chunks = chunker.split_documents(docs)
                    
                    # Создаем векторное хранилище
                    vector_store = VectorStore(collection_name="engineering_docs")
                    vector_store.add_documents(chunks)
                    
                    # Создаем RAG-движок
                    rag_engine = RAGEngine(vector_store, model_name=model_option)
                    
                    # Сохраняем в сессию
                    st.session_state.vector_store = vector_store
                    st.session_state.rag_engine = rag_engine
                    
                    st.success(f"Проиндексировано {len(chunks)} фрагментов из {len(docs)} документов")
                    
                except Exception as e:
                    st.error(f"Ошибка индексации: {str(e)}")
        else:
            st.warning("Сначала загрузите документы")

# Основная область
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("💬 Чат с ассистентом")
    
    # Отображение истории чата
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.write(message["content"])
    
    # Поле ввода запроса
    user_input = st.chat_input("Задайте вопрос по инженерным стандартам...")

    if user_input and st.session_state.rag_engine:
        # Добавляем сообщение пользователя в историю
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        
        with st.chat_message("user"):
            st.write(user_input)
        
        # Получаем ответ от RAG-движка
        with st.chat_message("assistant"):
            with st.spinner("Ассистент думает..."):
                try:
                    response: RAGResponse = st.session_state.rag_engine.query(user_input)
                    
                    # Отображаем ответ
                    st.write(response.answer)
                    
                    # Отображаем информацию о достоверности
                    st.caption(f"Уверенность: {response.confidence:.2f}, Тип запроса: {response.query_type}")
                    
                    # Отображаем цитаты
                    if response.citations:
                        with st.expander("📝 Источники (цитаты)"):
                            for i, citation in enumerate(response.citations):
                                st.write(f"**Источник {i+1}**: {citation.source}")
                                if citation.page:
                                    st.write(f"*Страница: {citation.page}*")
                                if citation.section:
                                    st.write(f"*Раздел: {citation.section}*")
                                st.write(f"*Фрагмент:* {citation.content}")
                                st.write(f"*Оценка релевантности: {citation.relevance_score:.2f}*")
                                st.divider()
                
                except Exception as e:
                    st.error(f"Ошибка при обработке запроса: {str(e)}")
    
    elif user_input and not st.session_state.rag_engine:
        st.warning("Сначала проиндексируйте документы")

with col2:
    st.subheader("📊 Статистика")
    
    if st.session_state.vector_store:
        doc_count = st.session_state.vector_store.get_document_count()
        st.metric("Документов в базе", doc_count)
        
        # Показываем информацию о коллекциях
        try:
            stats = st.session_state.vector_store.get_collections_stats()
            st.write("**Коллекции:**")
            for name, count in stats.items():
                st.write(f"- {name}: {count} документов")
        except:
            pass
    else:
        st.info("Индексация не выполнена")
    
    st.divider()
    
    st.subheader("ℹ️ Как пользоваться")
    st.write("""
    1. Загрузите документы (PDF, DOCX, TXT)
    2. Нажмите "Индексировать документы"
    3. Задавайте вопросы по инженерным стандартам
    4. Получайте ответы с цитированием источников
    """)
    
    st.write("**Примеры запросов:**")
    st.code("Какие требования к оформлению чертежей по ГОСТ 21.1101?")
    st.code("Как рассчитать нагрузку на перекрытие по СНиП?")
    st.code("Какие параметры бетона указаны в СТБ 1111?")


# Футер
st.divider()
st.caption("ИИ-ассистент инженерного факультета ГрГУ | Создано с использованием LangChain и OpenAI")
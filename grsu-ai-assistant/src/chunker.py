"""
Модуль разбиения документов на чанки для ИИ-ассистента инженерного факультета ГрГУ
Учитывает специфику инженерной документации (ГОСТ, СТБ, СНиП)
"""
from typing import List, Dict, Any
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
import re


class EngineeringDocumentChunker:
    """Класс для разбиения инженерных документов на чанки с учетом структуры"""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # Определяем разделители для инженерной документации
        self.separators = [
            # Разделы и подразделы
            r'\n\d+\.\s+',  # 1., 2., 3. и т.д.
            r'\n\d+\.\d+\s+',  # 1.1, 1.2 и т.д.
            r'\n\d+\.\d+\.\d+\s+',  # 1.1.1, 1.1.2 и т.д.
            r'\nПриложение\s+[А-Яа-яA-Za-z0-9]',  # Приложение А, Б и т.д.
            r'\nРаздел\s+[IVXLCDM\d]+',  # Раздел I, II, 1, 2 и т.д.
            
            # Заголовки таблиц и рисунков
            r'\nТаблица\s+\d+',  # Таблица 1, 2 и т.д.
            r'\nРисунок\s+\d+',  # Рисунок 1, 2 и т.д.
            
            # Общие разделители
            '\n\n',  # Параграф
            '\n',   # Новая строка
            ' ',    # Пробел
            ''      # Любой символ
        ]
        
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=self.separators,
            keep_separator=True,
            length_function=len,
            is_separator_regex=True
        )
    
    def split_documents(self, documents: List[Document]) -> List[Document]:
        """Разбивает список документов на чанки с сохранением метаданных"""
        chunks = []
        
        for doc in documents:
            # Проверяем, содержит ли документ таблицу
            is_table = doc.metadata.get('element_type') == 'table'
            
            # Если это таблица, не разбиваем её на части
            if is_table:
                # Увеличиваем размер чанка для таблиц
                temp_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=max(self.chunk_size * 2, 2000),
                    chunk_overlap=0,
                    separators=[''],
                    keep_separator=True
                )
                table_chunks = temp_splitter.split_documents([doc])
                chunks.extend(table_chunks)
            else:
                # Обычное разбиение для текстовых документов
                doc_chunks = self.text_splitter.split_documents([doc])
                chunks.extend(doc_chunks)
        
        # Обогащаем чанки дополнительными метаданными
        enhanced_chunks = []
        for chunk in chunks:
            enhanced_chunk = self._enrich_metadata(chunk)
            enhanced_chunks.append(enhanced_chunk)
        
        return enhanced_chunks
    
    def _enrich_metadata(self, chunk: Document) -> Document:
        """Добавляет дополнительные метаданные к чанку"""
        # Определяем тип содержимого в чанке
        content = chunk.page_content.lower()
        
        # Проверяем наличие специфических элементов
        metadata = chunk.metadata.copy()
        metadata['has_formulas'] = bool(re.search(r'[αβγδεζηθικλμνξοπρστυφχψω∑∏∫∂∇∞]', content))
        metadata['has_numbers'] = bool(re.search(r'\b\d+\.?\d*\b', content))
        metadata['has_section_header'] = bool(
            re.search(r'(\n|^)(\d+\.\d*\.?\d*)\s+', content)
        )
        metadata['has_table_ref'] = bool(
            re.search(r'(таблиц[аыи]|табл\.|рисунк[ауеи]|рис\.)', content)
        )
        
        # Определяем уровень раздела
        section_match = re.search(r'^(\d+(?:\.\d+)*)', chunk.page_content.strip())
        if section_match:
            section_number = section_match.group(1)
            level = len(section_number.split('.'))
            metadata['section_level'] = level
            metadata['section_number'] = section_number
        
        chunk.metadata = metadata
        return chunk


class SmartEngineeringChunker(EngineeringDocumentChunker):
    """Улучшенный класс чанкеринга с более сложной логикой"""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        super().__init__(chunk_size, chunk_overlap)
        
        # Дополнительные правила для разных типов документов
        self.special_rules = {
            'GOST': self._apply_gost_rules,
            'STB': self._apply_stb_rules,
            'SNIP': self._apply_snip_rules
        }
    
    def split_documents(self, documents: List[Document]) -> List[Document]:
        """Разбивает документы с учетом специфики каждого типа"""
        chunks = []
        
        for doc in documents:
            doc_type = doc.metadata.get('document_type', 'OTHER')
            
            # Применяем специфические правила для типа документа
            if doc_type in self.special_rules:
                processed_docs = self.special_rules[doc_type]([doc])
            else:
                processed_docs = [doc]
            
            # Разбиваем обработанные документы
            for proc_doc in processed_docs:
                doc_chunks = super().split_documents([proc_doc])
                chunks.extend(doc_chunks)
        
        return chunks
    
    def _apply_gost_rules(self, documents: List[Document]) -> List[Document]:
        """Применяет правила разбиения для ГОСТ"""
        processed_docs = []
        
        for doc in documents:
            content = doc.page_content
            
            # Разделяем по ключевым элементам ГОСТ
            sections = re.split(r'\n(?=\d+\.|\nПриложение)', content)
            
            if len(sections) > 1:
                # Если нашли разделы, создаем отдельные документы для каждого
                for i, section in enumerate(sections):
                    if section.strip():
                        new_doc = Document(
                            page_content=section,
                            metadata={
                                **doc.metadata,
                                'sub_element': f'section_{i}',
                                'original_section_count': len(sections)
                            }
                        )
                        processed_docs.append(new_doc)
            else:
                processed_docs.append(doc)
        
        return processed_docs
    
    def _apply_stb_rules(self, documents: List[Document]) -> List[Document]:
        """Применяет правила разбиения для СТБ"""
        # Для СТБ применяем те же правила, что и для ГОСТ
        return self._apply_gost_rules(documents)
    
    def _apply_snip_rules(self, documents: List[Document]) -> List[Document]:
        """Применяет правила разбиения для СНиП"""
        processed_docs = []
        
        for doc in documents:
            content = doc.page_content
            
            # Разделяем по главам и разделам СНиП
            sections = re.split(r'\n(?=Глава\s+\w+|Раздел\s+\d+)', content)
            
            if len(sections) > 1:
                for i, section in enumerate(sections):
                    if section.strip():
                        new_doc = Document(
                            page_content=section,
                            metadata={
                                **doc.metadata,
                                'sub_element': f'snip_section_{i}',
                                'original_section_count': len(sections)
                            }
                        )
                        processed_docs.append(new_doc)
            else:
                processed_docs.append(doc)
        
        return processed_docs


# Пример использования
if __name__ == "__main__":
    # Пример создания чанкеров
    basic_chunker = EngineeringDocumentChunker(chunk_size=1000, chunk_overlap=200)
    smart_chunker = SmartEngineeringChunker(chunk_size=1000, chunk_overlap=200)
    
    print("Чанкеры готовы к использованию")
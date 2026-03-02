"""
Модуль загрузки документов для ИИ-ассистента инженерного факультета ГрГУ
Поддерживает PDF, DOCX, TXT с OCR и извлечением таблиц
"""
import os
import re
from typing import List, Dict, Any
from pathlib import Path
from langchain.schema import Document
from langchain_community.document_loaders import (
    PyPDFLoader, 
    TextLoader, 
    Docx2txtLoader,
    UnstructuredPDFLoader
)
import pdfplumber
import pytesseract
from PIL import Image
import io


class DocumentTypeClassifier:
    """Классификатор типов документов (ГОСТ, СТБ, СНиП)"""
    
    @staticmethod
    def classify_document_type(filename: str) -> Dict[str, Any]:
        """Определяет тип документа по названию файла"""
        filename_lower = filename.lower()
        
        # Регулярные выражения для определения типа документа
        patterns = {
            'GOST': r'(?:^|[^a-z])гост[\s_-]?(\d+)[\s_-]?(\d{4})?',
            'STB': r'(?:^|[^a-z])стб[\s_-]?(\d+)',
            'SNIP': r'(?:^|[^a-z])снип[\s_-]?([\d\.-]+)',
            'TU': r'(?:^|[^a-z])ту[\s_-]?([\d\.-]+)',
            'DSTU': r'(?:^|[^a-z])дсту[\s_-]?(\d+)'
        }
        
        metadata = {
            'filename': filename,
            'document_type': 'OTHER',
            'standard_number': None,
            'year': None,
            'status': 'active'  # по умолчанию считаем действующим
        }
        
        for doc_type, pattern in patterns.items():
            match = re.search(pattern, filename_lower)
            if match:
                metadata['document_type'] = doc_type
                metadata['standard_number'] = match.group(1)
                
                # Пытаемся извлечь год, если он есть
                if match.groups() and len(match.groups()) > 1 and match.group(2):
                    metadata['year'] = match.group(2)
                
                break
        
        return metadata


class EngineeringDocumentLoader:
    """Загрузчик инженерных документов с поддержкой различных форматов"""
    
    def __init__(self):
        self.classifier = DocumentTypeClassifier()
    
    def load_file(self, file_path: str) -> List[Document]:
        """Загружает один файл"""
        file_ext = Path(file_path).suffix.lower()
        docs = []
        
        # Определяем тип документа
        doc_metadata = self.classifier.classify_document_type(Path(file_path).name)
        
        if file_ext == '.pdf':
            docs = self._load_pdf(file_path, doc_metadata)
        elif file_ext == '.docx':
            docs = self._load_docx(file_path, doc_metadata)
        elif file_ext in ['.txt', '.text']:
            docs = self._load_txt(file_path, doc_metadata)
        else:
            raise ValueError(f"Неподдерживаемый формат файла: {file_ext}")
        
        # Добавляем метаданные ко всем документам
        for doc in docs:
            doc.metadata.update(doc_metadata)
        
        return docs
    
    def load_directory(self, directory_path: str) -> List[Document]:
        """Загружает все поддерживаемые файлы из директории"""
        docs = []
        supported_extensions = {'.pdf', '.docx', '.txt', '.text'}
        
        for root, _, files in os.walk(directory_path):
            for file in files:
                file_path = os.path.join(root, file)
                if Path(file_path).suffix.lower() in supported_extensions:
                    try:
                        docs.extend(self.load_file(file_path))
                    except Exception as e:
                        print(f"Ошибка загрузки файла {file_path}: {e}")
        
        return docs
    
    def _load_pdf(self, file_path: str, metadata: Dict[str, Any]) -> List[Document]:
        """Загрузка PDF файла с поддержкой OCR и таблиц"""
        docs = []
        
        # Попробуем сначала загрузить с помощью PyPDFLoader
        try:
            loader = PyPDFLoader(file_path)
            docs = loader.load()
        except:
            # Если обычный способ не работает, пробуем с OCR
            docs = self._load_pdf_with_ocr(file_path, metadata)
        
        # Извлекаем таблицы и добавляем их как отдельные документы
        table_docs = self._extract_tables_from_pdf(file_path, metadata)
        docs.extend(table_docs)
        
        return docs
    
    def _load_pdf_with_ocr(self, file_path: str, metadata: Dict[str, Any]) -> List[Document]:
        """Загрузка PDF с OCR для сканированных документов"""
        docs = []
        
        try:
            # Используем UnstructuredPDFLoader с режимом OCR
            loader = UnstructuredPDFLoader(
                file_path, 
                mode="single", 
                strategy="ocr_only"
            )
            docs = loader.load()
        except:
            # Альтернативный метод OCR
            docs = self._ocr_pdf_pages(file_path, metadata)
        
        return docs
    
    def _ocr_pdf_pages(self, file_path: str, metadata: Dict[str, Any]) -> List[Document]:
        """Выполняет OCR для каждой страницы PDF"""
        docs = []
        
        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                # Получаем изображение страницы
                pil_image = page.to_pil()
                
                # Конвертируем в bytesIO для OCR
                img_byte_arr = io.BytesIO()
                pil_image.save(img_byte_arr, format='PNG')
                img_byte_arr = img_byte_arr.getvalue()
                
                # Выполняем OCR
                image = Image.open(io.BytesIO(img_byte_arr))
                text = pytesseract.image_to_string(image, lang='rus+eng')
                
                if text.strip():
                    doc = Document(
                        page_content=text,
                        metadata={
                            **metadata,
                            'page': page_num + 1,
                            'source': file_path
                        }
                    )
                    docs.append(doc)
        
        return docs
    
    def _extract_tables_from_pdf(self, file_path: str, metadata: Dict[str, Any]) -> List[Document]:
        """Извлечение таблиц из PDF файла"""
        docs = []
        
        try:
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    tables = page.extract_tables()
                    
                    for table_idx, table in enumerate(tables):
                        if table and len(table) > 1:  # Убедимся, что это действительно таблица
                            # Преобразуем таблицу в текстовый формат
                            table_text = self._format_table_as_text(table)
                            
                            doc = Document(
                                page_content=table_text,
                                metadata={
                                    **metadata,
                                    'page': page_num + 1,
                                    'source': file_path,
                                    'element_type': 'table',
                                    'table_index': table_idx
                                }
                            )
                            docs.append(doc)
        except:
            pass  # Если не удалось извлечь таблицы, продолжаем без них
        
        return docs
    
    def _format_table_as_text(self, table: List[List[str]]) -> str:
        """Форматирует таблицу как текст"""
        formatted_lines = ["ТАБЛИЦА:", ""]
        
        for row_idx, row in enumerate(table):
            formatted_row = " | ".join(str(cell) if cell else "" for cell in row)
            formatted_lines.append(formatted_row)
            
            # Добавляем разделитель после заголовка
            if row_idx == 0:
                separator = "-|-".join("-" * max(3, len(str(cell))) if cell else "---" for cell in row)
                formatted_lines.append(separator)
        
        return "\n".join(formatted_lines)
    
    def _load_docx(self, file_path: str, metadata: Dict[str, Any]) -> List[Document]:
        """Загрузка DOCX файла"""
        loader = Docx2txtLoader(file_path)
        docs = loader.load()
        
        # Обновляем метаданные для всех документов
        for doc in docs:
            doc.metadata.update(metadata)
            doc.metadata['source'] = file_path
        
        return docs
    
    def _load_txt(self, file_path: str, metadata: Dict[str, Any]) -> List[Document]:
        """Загрузка TXT файла"""
        loader = TextLoader(file_path, encoding='utf-8')
        docs = loader.load()
        
        # Обновляем метаданные для всех документов
        for doc in docs:
            doc.metadata.update(metadata)
            doc.metadata['source'] = file_path
        
        return docs


# Пример использования
if __name__ == "__main__":
    loader = EngineeringDocumentLoader()
    
    # Загрузка одного файла
    # docs = loader.load_file("./examples/sample_gost.pdf")
    
    # Загрузка всех файлов из директории
    # docs = loader.load_directory("./documents")
    
    print("Загрузчик документов готов к использованию")
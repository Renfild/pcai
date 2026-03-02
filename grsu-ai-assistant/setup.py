from setuptools import setup, find_packages

setup(
    name="grsu-ai-assistant",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "langchain>=0.0.352",
        "langchain-community>=0.0.31",
        "langchain-openai>=0.0.8",
        "chromadb>=0.4.22",
        "tiktoken>=0.5.2",
        "pypdf>=4.0.1",
        "pdfplumber>=0.10.3",
        "pytesseract>=0.3.10",
        "pillow>=10.1.0",
        "python-docx>=0.8.11",
        "pandas>=2.1.4",
        "numpy>=1.26.3",
        "openai>=1.3.5",
        "streamlit>=1.29.0",
        "python-dotenv>=1.0.0",
        "unstructured>=0.12.5",
        "lxml>=4.9.3",
        "beautifulsoup4>=4.12.2",
        "requests>=2.31.0",
        "langchain-chroma>=0.1.0"
    ],
    author="GRSU AI Assistant Team",
    description="ИИ-ассистент для инженерного факультета ГрГУ",
    python_requires=">=3.9",
)
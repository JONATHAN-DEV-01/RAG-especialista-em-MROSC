"""
src/ingest.py
=============
Pipeline de ingestão de documentos jurídicos para o RAG MROSC.

Fluxo:
  1. Carrega os documentos (DOCX e PDF) separadamente
  2. Parseia por artigo usando regex sensível à estrutura legal brasileira
  3. Gera metadados por chunk: fonte, tipo, artigo, status (vigente/alterado/revogado)
  4. Aplica fallback de split por tamanho para artigos muito longos
  5. Gera embeddings e persiste no Chroma

Uso:
  python src/ingest.py
"""

import os
import re
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from tqdm import tqdm

# Carrega variáveis de ambiente do .env (se existir)
load_dotenv()

# ---------------------------------------------------------------------------
# Configurações (lidas do .env ou valores padrão)
# ---------------------------------------------------------------------------
DATA_DIR = Path(__file__).parent.parent / "data"
LEI_FILE = DATA_DIR / "lei_mrosc.docx"
DECRETO_FILE = DATA_DIR / "decreto_57575_2016.pdf"

CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))         # TODO(usuário): ajuste se necessário
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "150"))    # TODO(usuário): ajuste se necessário

# ---------------------------------------------------------------------------
# Padrões de regex para textos jurídicos brasileiros
# ---------------------------------------------------------------------------

# Detecta início de artigo: "Art. 1º", "Art. 22.", "Art. 35-A", "Artigo 10"
ARTICLE_PATTERN = re.compile(
    r"(?:^|\n)\s*"
    r"(Art(?:igo)?\.?\s*\d+[\w-]*\s*[°º]?\.?)"
    r"(?=\s)",
    re.MULTILINE | re.IGNORECASE,
)

# Detecta artigos revogados (ex: "Revogado pelo Decreto nº 61.615/2022")
REVOCATION_PATTERN = re.compile(
    r"(Revogad[ao]|Suprimid[ao])\s+(?:pelo|pela|por)\s+(?:Decreto|Lei|Portaria|Resolução)",
    re.IGNORECASE,
)

# Detecta artigos com redação alterada (ex: "Redação dada pelo Decreto nº 63.541/2024")
AMENDMENT_PATTERN = re.compile(
    r"(Redação\s+dada|Nova\s+redação|Alterado)\s+(?:pelo|pela|por)\s+(?:Decreto|Lei|Portaria)",
    re.IGNORECASE,
)

# Extrai número do artigo para metadado (ex: "Art. 22" → "22")
ARTICLE_NUMBER_PATTERN = re.compile(
    r"Art(?:igo)?\.?\s*(\d+[\w-]*)\s*[°º]?\.?",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Funções de carregamento
# ---------------------------------------------------------------------------

def load_docx(file_path: Path) -> str:
    """Carrega texto de arquivo DOCX preservando parágrafos."""
    try:
        import docx  # python-docx
    except ImportError:
        print("❌ Instale python-docx: pip install python-docx")
        sys.exit(1)

    doc = docx.Document(str(file_path))
    paragraphs = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            paragraphs.append(text)
    return "\n".join(paragraphs)


def load_pdf(file_path: Path) -> str:
    """Carrega texto de arquivo PDF, página por página."""
    try:
        from pypdf import PdfReader
    except ImportError:
        print("❌ Instale pypdf: pip install pypdf")
        sys.exit(1)

    reader = PdfReader(str(file_path))
    pages_text = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages_text.append(text.strip())
    return "\n".join(pages_text)


# ---------------------------------------------------------------------------
# Chunking sensível à estrutura jurídica
# ---------------------------------------------------------------------------

def detect_article_status(article_text: str) -> str:
    """
    Detecta o status de vigor de um artigo com base no próprio texto.
    Retorna: 'revogado', 'alterado' ou 'vigente'.
    """
    if REVOCATION_PATTERN.search(article_text):
        return "revogado"
    if AMENDMENT_PATTERN.search(article_text):
        return "alterado"
    return "vigente"


def extract_article_number(article_header: str) -> str:
    """Extrai o número do artigo do cabeçalho detectado pelo regex."""
    match = ARTICLE_NUMBER_PATTERN.search(article_header)
    if match:
        return match.group(1)
    return "?"


def split_by_articles(
    full_text: str,
    fonte: str,
    tipo: str,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> list[Document]:
    """
    Divide o texto jurídico em chunks por artigo.

    Para cada artigo encontrado:
    - Se couber no chunk_size: um único Document com metadados completos.
    - Se for muito longo: subdividido pelo RecursiveCharacterTextSplitter,
      mantendo os metadados do artigo em todos os sub-chunks.

    Retorna lista de Document com metadados: fonte, tipo, artigo, status.
    """
    # Localiza todas as ocorrências de "Art. X..." no texto
    matches = list(ARTICLE_PATTERN.finditer(full_text))

    documents: list[Document] = []

    # Texto antes do primeiro artigo (preâmbulo/cabeçalho)
    if matches:
        preamble = full_text[: matches[0].start()].strip()
        if preamble:
            documents.append(
                Document(
                    page_content=preamble,
                    metadata={
                        "fonte": fonte,
                        "tipo": tipo,
                        "artigo": "preâmbulo",
                        "status": "vigente",
                        "secao": "preâmbulo",
                    },
                )
            )

    fallback_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", " ", ""],
    )

    for i, match in enumerate(matches):
        # Delimitação do artigo: do início deste match até o início do próximo
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)

        article_text = full_text[start:end].strip()
        article_header = match.group(1)
        article_number = extract_article_number(article_header)
        status = detect_article_status(article_text)

        base_metadata = {
            "fonte": fonte,
            "tipo": tipo,
            "artigo": article_number,
            "artigo_header": article_header.strip(),
            "status": status,
        }

        # Se o artigo couber no limite de chunk, não subdividir
        if len(article_text) <= chunk_size:
            documents.append(
                Document(page_content=article_text, metadata=base_metadata)
            )
        else:
            # Artigo muito longo: subdividir, preservando metadados
            sub_chunks = fallback_splitter.split_text(article_text)
            for j, sub_chunk in enumerate(sub_chunks):
                sub_metadata = {**base_metadata, "sub_chunk": j + 1}
                documents.append(
                    Document(page_content=sub_chunk, metadata=sub_metadata)
                )

    return documents


# ---------------------------------------------------------------------------
# Pipeline principal de ingestão
# ---------------------------------------------------------------------------

def ingest_documents(
    lei_path: Optional[Path] = None,
    decreto_path: Optional[Path] = None,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> list[Document]:
    """
    Carrega, parseia e gera chunks dos dois documentos jurídicos.
    Retorna lista de Documents prontos para indexação.
    """
    lei_path = lei_path or LEI_FILE
    decreto_path = decreto_path or DECRETO_FILE

    all_documents: list[Document] = []

    # --- Lei Federal 13.019/2014 (DOCX) ---
    if not lei_path.exists():
        print(f"⚠️  Arquivo da Lei não encontrado: {lei_path}")
        print(
            "   Coloque 'lei_mrosc.docx' na pasta 'data/' antes de rodar a ingestão."
        )
    else:
        print(f"\n📄 Carregando Lei 13.019/2014: {lei_path.name} ...")
        lei_text = load_docx(lei_path)
        lei_docs = split_by_articles(
            full_text=lei_text,
            fonte="Lei 13.019/2014",
            tipo="lei_federal",
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        all_documents.extend(lei_docs)
        print(f"   ✅ {len(lei_docs)} chunks gerados da Lei 13.019/2014")

        # Relatório de status dos artigos
        revogados = [d for d in lei_docs if d.metadata["status"] == "revogado"]
        alterados = [d for d in lei_docs if d.metadata["status"] == "alterado"]
        if revogados:
            print(
                f"   ⚠️  Artigos detectados como revogados: "
                f"{', '.join(d.metadata['artigo'] for d in revogados)}"
            )
        if alterados:
            print(
                f"   ℹ️  Artigos com redação alterada: "
                f"{', '.join(d.metadata['artigo'] for d in alterados)}"
            )

    # --- Decreto Municipal 57.575/2016 (PDF) ---
    if not decreto_path.exists():
        print(f"\n⚠️  Arquivo do Decreto não encontrado: {decreto_path}")
        print(
            "   Coloque 'decreto_57575_2016.pdf' na pasta 'data/' antes de rodar a ingestão."
        )
    else:
        print(f"\n📄 Carregando Decreto 57.575/2016: {decreto_path.name} ...")
        decreto_text = load_pdf(decreto_path)
        decreto_docs = split_by_articles(
            full_text=decreto_text,
            fonte="Decreto 57.575/2016",
            tipo="decreto_municipal",
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        all_documents.extend(decreto_docs)
        print(f"   ✅ {len(decreto_docs)} chunks gerados do Decreto 57.575/2016")

        revogados = [d for d in decreto_docs if d.metadata["status"] == "revogado"]
        alterados = [d for d in decreto_docs if d.metadata["status"] == "alterado"]
        if revogados:
            print(
                f"   ⚠️  Artigos detectados como revogados: "
                f"{', '.join(d.metadata['artigo'] for d in revogados)}"
            )
        if alterados:
            print(
                f"   ℹ️  Artigos com redação alterada: "
                f"{', '.join(d.metadata['artigo'] for d in alterados)}"
            )

    return all_documents


def run_ingest_pipeline():
    """Executa o pipeline completo: ingestão + embeddings + Chroma."""
    from src.vectorstore import build_vectorstore  # importação local para evitar circular

    print("=" * 60)
    print("  RAG Jurídico MROSC — Pipeline de Ingestão")
    print("=" * 60)

    docs = ingest_documents()

    if not docs:
        print(
            "\n❌ Nenhum documento encontrado. "
            "Certifique-se de que os arquivos estão em 'data/'."
        )
        sys.exit(1)

    print(f"\n📊 Total de chunks a indexar: {len(docs)}")
    print("\n🔢 Gerando embeddings e indexando no Chroma ...")
    print(
        "   (O download do modelo de embeddings pode levar alguns minutos na 1ª execução)\n"
    )

    vectorstore = build_vectorstore(docs)

    print(f"\n✅ Ingestão concluída! Vector store salvo em: {os.getenv('CHROMA_PERSIST_DIR', './chroma_db')}")
    print("\nAgora você pode rodar:")
    print("  streamlit run app_streamlit.py    # interface principal")
    print("  python src/cli.py                 # debug via terminal")
    print("=" * 60)


if __name__ == "__main__":
    # Permite rodar como: python src/ingest.py
    # Adiciona o diretório raiz ao path para imports absolutos
    sys.path.insert(0, str(Path(__file__).parent.parent))
    run_ingest_pipeline()

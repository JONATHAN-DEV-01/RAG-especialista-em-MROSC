"""
src/vectorstore.py
==================
Criação e carregamento do vector store Chroma persistente.

- Embeddings: intfloat/multilingual-e5-large (padrão) ou configurável via .env
- Vector store: Chroma (local, sem custo, persistente entre sessões)
- Coleção: "mrosc_juridico" (configurável via .env)

Uso:
  from src.vectorstore import build_vectorstore, load_vectorstore
"""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from langchain.schema import Document
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

load_dotenv()

# ---------------------------------------------------------------------------
# Configurações (lidas do .env ou valores padrão)
# ---------------------------------------------------------------------------
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")  # TODO(usuário): ajuste se necessário
CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION", "mrosc_juridico")  # TODO(usuário): ajuste se necessário
EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL",
    "intfloat/multilingual-e5-large",
    # Alternativa menor e mais rápida: "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
)

# Normaliza o caminho relativo ao diretório raiz do projeto
_PROJECT_ROOT = Path(__file__).parent.parent
_CHROMA_PATH = str(_PROJECT_ROOT / CHROMA_PERSIST_DIR.lstrip("./\\"))


def get_embeddings() -> HuggingFaceEmbeddings:
    """
    Cria o objeto de embeddings com o modelo multilíngue selecionado.
    O modelo é baixado e cacheado localmente na 1ª execução.
    """
    print(f"   Modelo de embeddings: {EMBEDDING_MODEL}")
    return HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},  # TODO(usuário): mude para "cuda" se tiver GPU
        encode_kwargs={"normalize_embeddings": True},
    )


def build_vectorstore(
    documents: list[Document],
    persist_dir: Optional[str] = None,
    collection_name: Optional[str] = None,
) -> Chroma:
    """
    Cria (ou recria) o vector store Chroma a partir dos documentos fornecidos.

    ATENÇÃO: Apaga a coleção existente antes de recriar para garantir
    consistência com os documentos mais recentes.

    Args:
        documents: Lista de Document com metadados (gerada pelo ingest.py).
        persist_dir: Diretório de persistência (padrão: CHROMA_PERSIST_DIR).
        collection_name: Nome da coleção Chroma (padrão: CHROMA_COLLECTION).

    Returns:
        Instância do Chroma vector store persistido.
    """
    persist_dir = persist_dir or _CHROMA_PATH
    collection_name = collection_name or CHROMA_COLLECTION

    embeddings = get_embeddings()

    # Cria o Chroma com os documentos (substitui se já existir)
    vectorstore = Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        collection_name=collection_name,
        persist_directory=persist_dir,
    )

    return vectorstore


def load_vectorstore(
    persist_dir: Optional[str] = None,
    collection_name: Optional[str] = None,
) -> Chroma:
    """
    Carrega um vector store Chroma já existente do disco.
    Levanta RuntimeError se o diretório não existir.

    Args:
        persist_dir: Diretório de persistência (padrão: CHROMA_PERSIST_DIR).
        collection_name: Nome da coleção Chroma (padrão: CHROMA_COLLECTION).

    Returns:
        Instância do Chroma vector store carregada do disco.
    """
    persist_dir = persist_dir or _CHROMA_PATH
    collection_name = collection_name or CHROMA_COLLECTION

    if not Path(persist_dir).exists():
        raise RuntimeError(
            f"Vector store não encontrado em: {persist_dir}\n"
            "Execute primeiro: python src/ingest.py"
        )

    embeddings = get_embeddings()

    vectorstore = Chroma(
        collection_name=collection_name,
        embedding_function=embeddings,
        persist_directory=persist_dir,
    )

    return vectorstore


def get_retriever(
    persist_dir: Optional[str] = None,
    collection_name: Optional[str] = None,
    k: int = 6,
):
    """
    Retorna um retriever configurado para buscar os k chunks mais relevantes.

    Args:
        k: Número de chunks a recuperar por consulta (padrão: 6).
           Aumentar melhora recall mas pode piorar precisão/custo de tokens.

    Returns:
        Retriever LangChain pronto para uso na chain.
    """
    vectorstore = load_vectorstore(persist_dir, collection_name)
    return vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": k},
    )

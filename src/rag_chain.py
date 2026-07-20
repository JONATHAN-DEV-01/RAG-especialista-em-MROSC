"""
src/rag_chain.py
================
Montagem da chain de RAG jurídico via LCEL (LangChain Expression Language).

Pipeline:
  pergunta do usuário
    → retriever (busca semântica no Chroma)
    → formata contexto com metadados (artigo, fonte)
    → prompt jurídico especializado
    → LLM
    → resposta com citações

Retorna tanto a resposta textual quanto os documentos-fonte recuperados,
para exibição destacada na interface Streamlit.

Uso:
  from src.rag_chain import build_rag_chain, ask

  chain = build_rag_chain()
  result = ask(chain, "O que é um termo de fomento?")
  print(result["answer"])
  print(result["source_documents"])
"""

import os
from typing import Any, Optional

from dotenv import load_dotenv
from langchain.schema import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableParallel, RunnablePassthrough

load_dotenv()

# ---------------------------------------------------------------------------
# Prompt do sistema — instrui o LLM como se comportar em contexto jurídico
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """Você é um assistente jurídico especializado no Marco Regulatório das Organizações da Sociedade Civil (MROSC) brasileiro. Sua base de conhecimento é composta por dois documentos:

1. **Lei Federal nº 13.019/2014** (Lei MROSC), que estabelece as normas gerais de parcerias entre poder público e organizações da sociedade civil.
2. **Decreto Municipal nº 57.575/2016** (Prefeitura de São Paulo), que regulamenta a aplicação da Lei MROSC no âmbito do Município de São Paulo.

**Regras que você DEVE seguir:**

1. **Responda SOMENTE com base nos trechos fornecidos abaixo** como contexto. Não invente dispositivos legais, artigos, prazos ou definições que não estejam explicitamente presentes no contexto.

2. **Sempre cite a fonte exata** ao usar uma informação: indique se é da Lei 13.019/2014 ou do Decreto 57.575/2016, e o número do artigo/parágrafo/inciso correspondente. Use o formato: *"conforme o art. X da Lei 13.019/2014"* ou *"nos termos do art. Y do Decreto 57.575/2016"*.

3. **Quando a pergunta envolver comparação** entre o que a Lei estabelece geralmente e como o Decreto Municipal de SP regulamenta especificamente, **explicite a relação entre os dois**. Por exemplo: "A Lei Federal, no art. X, prevê Y de forma geral; o Decreto Municipal, no art. Z, detalha isso especificamente para São Paulo da seguinte forma..."

4. **Se a informação não estiver nos trechos fornecidos**, diga claramente: "Não encontrei base nos documentos fornecidos para responder a esta pergunta." Não complemente com conhecimento genérico do modelo.

5. **Ao final de toda resposta**, inclua obrigatoriamente o seguinte aviso:
   "⚠️ *Esta resposta é uma organização informativa dos textos legais fornecidos e não substitui análise jurídica profissional. Para casos concretos, consulte um advogado especializado.*"

**Contexto recuperado dos documentos:**

{context}

---

**Pergunta:** {question}

**Resposta:**"""

HUMAN_TEMPLATE = "{question}"


# ---------------------------------------------------------------------------
# Formatação do contexto com metadados
# ---------------------------------------------------------------------------

def format_documents_with_metadata(docs: list[Document]) -> str:
    """
    Formata os documentos recuperados incluindo metadados de fonte e artigo,
    para que o LLM possa citá-los corretamente na resposta.
    """
    formatted_parts = []
    for i, doc in enumerate(docs, 1):
        meta = doc.metadata
        fonte = meta.get("fonte", "Fonte desconhecida")
        artigo = meta.get("artigo", "?")
        status = meta.get("status", "vigente")

        # Aviso se o artigo estiver revogado ou alterado
        status_note = ""
        if status == "revogado":
            status_note = " [⚠️ ARTIGO REVOGADO — verifique a versão vigente]"
        elif status == "alterado":
            status_note = " [ℹ️ Artigo com redação alterada]"

        header = f"[Trecho {i}] {fonte} — Art. {artigo}{status_note}"
        formatted_parts.append(f"{header}\n{doc.page_content}")

    return "\n\n" + "\n\n---\n\n".join(formatted_parts) + "\n"


# ---------------------------------------------------------------------------
# Construção da chain via LCEL
# ---------------------------------------------------------------------------

def build_rag_chain(provider: Optional[str] = None, k: int = 6):
    """
    Monta a chain de RAG usando LCEL (LangChain Expression Language).

    A chain retorna um dict com:
      - "answer": str — a resposta gerada pelo LLM
      - "source_documents": list[Document] — chunks usados como contexto

    Args:
        provider: Provedor de LLM ("ollama" | "groq" | "gemini").
                  None = lê do .env (padrão: "ollama").
        k: Número de chunks a recuperar por consulta.

    Returns:
        Chain LCEL que aceita {"question": str} e retorna {"answer": str, "source_documents": list}.
    """
    from src.llm_provider import get_llm
    from src.vectorstore import get_retriever

    print("\n🔧 Inicializando RAG chain...")

    # 1. Retriever
    retriever = get_retriever(k=k)

    # 2. LLM
    llm = get_llm(provider)

    # 3. Prompt
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
        ]
    )

    # 4. Chain LCEL
    # Passo 1: recupera documentos e passa a questão adiante em paralelo
    retrieve_and_passthrough = RunnableParallel(
        {
            "source_documents": retriever,
            "question": RunnablePassthrough(),
        }
    )

    # Passo 2: formata contexto + monta prompt + chama LLM + parseia
    def build_prompt_input(inputs: dict) -> dict:
        return {
            "context": format_documents_with_metadata(inputs["source_documents"]),
            "question": inputs["question"],
        }

    answer_chain = (
        {
            "context": lambda x: format_documents_with_metadata(x["source_documents"]),
            "question": lambda x: x["question"],
        }
        | prompt
        | llm
        | StrOutputParser()
    )

    # Chain completa: retorna answer + source_documents
    full_chain = retrieve_and_passthrough | RunnableParallel(
        {
            "answer": answer_chain,
            "source_documents": lambda x: x["source_documents"],
        }
    )

    print("   ✅ Chain inicializada com sucesso!")
    return full_chain


def ask(
    chain,
    question: str,
) -> dict[str, Any]:
    """
    Faz uma pergunta à chain e retorna a resposta com metadados de fonte.

    Args:
        chain: Chain LCEL construída por build_rag_chain().
        question: Pergunta do usuário em linguagem natural.

    Returns:
        Dict com:
          - "answer": str — resposta gerada
          - "source_documents": list[Document] — documentos-fonte
          - "question": str — pergunta original
    """
    result = chain.invoke(question)
    result["question"] = question
    return result


def has_base_in_documents(answer: str) -> bool:
    """
    Verifica se a resposta indica que não há base nos documentos.
    Usado pela interface Streamlit para exibir alerta visual.
    """
    no_base_indicators = [
        "não encontrei base nos documentos",
        "não há base nos textos",
        "não encontrado nos documentos",
        "fora do escopo dos documentos",
        "não está presente nos documentos",
        "não consta nos documentos",
    ]
    answer_lower = answer.lower()
    return not any(indicator in answer_lower for indicator in no_base_indicators)

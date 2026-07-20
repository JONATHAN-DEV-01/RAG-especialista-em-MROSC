"""
app_streamlit.py
================
Interface principal do RAG Jurídico MROSC.

Paleta de cores inspirada na identidade visual da Prefeitura de São Paulo.
TODO(usuário): confirmar hex oficial no manual de marca da PMSP antes de publicar.

Uso:
  streamlit run app_streamlit.py
  streamlit run app_streamlit.py -- --provider groq
"""

import sys
from pathlib import Path

# Garante que o diretório raiz está no path para imports absolutos
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Configuração da página (deve ser o PRIMEIRO comando Streamlit)
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="RAG Jurídico MROSC — Prefeitura de São Paulo",
    page_icon="⚖️",
    layout="centered",
    initial_sidebar_state="expanded",
    menu_items={
        "About": (
            "**RAG Jurídico MROSC**\n\n"
            "Sistema de consulta à Lei Federal 13.019/2014 e ao "
            "Decreto Municipal SP 57.575/2016.\n\n"
            "⚠️ Esta é uma ferramenta informativa, **não um canal oficial da Prefeitura de São Paulo**."
        )
    },
)

# ---------------------------------------------------------------------------
# CSS customizado — identidade visual da Prefeitura de SP
# TODO(usuário): confirmar hex oficial no manual de marca da PMSP antes de publicar
# ---------------------------------------------------------------------------
PMSP_RED = "#ED1C24"         # TODO(usuário): confirmar hex oficial no manual de marca da PMSP antes de publicar
PMSP_RED_DARK = "#B8151B"    # TODO(usuário): ajuste após confirmar o hex oficial
PMSP_RED_LIGHT = "#FDECEA"

st.markdown(
    f"""
    <style>
    /* ---------- Fonte ---------- */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; }}

    /* ---------- Cabeçalho da página ---------- */
    .main-header {{
        background: linear-gradient(135deg, {PMSP_RED} 0%, {PMSP_RED_DARK} 100%);
        color: white;
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 15px rgba(237, 28, 36, 0.25);
    }}
    .main-header h1 {{
        margin: 0;
        font-size: 1.6rem;
        font-weight: 700;
        letter-spacing: -0.5px;
    }}
    .main-header p {{
        margin: 0.3rem 0 0 0;
        font-size: 0.85rem;
        opacity: 0.9;
    }}

    /* ---------- Badges de fonte ---------- */
    .badge-lei {{
        background: #1565C0;
        color: white;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 0.72rem;
        font-weight: 600;
        display: inline-block;
        margin-right: 6px;
        letter-spacing: 0.3px;
    }}
    .badge-decreto {{
        background: {PMSP_RED};
        color: white;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 0.72rem;
        font-weight: 600;
        display: inline-block;
        margin-right: 6px;
        letter-spacing: 0.3px;
    }}
    .badge-artigo {{
        background: #424242;
        color: white;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 0.72rem;
        font-weight: 600;
        display: inline-block;
        margin-right: 6px;
    }}
    .badge-revogado {{
        background: #F57F17;
        color: white;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 0.72rem;
        font-weight: 600;
        display: inline-block;
    }}

    /* ---------- Card de fonte citada ---------- */
    .source-card {{
        border: 1px solid #e0e0e0;
        border-left: 4px solid {PMSP_RED};
        border-radius: 8px;
        padding: 0.75rem 1rem;
        margin: 0.4rem 0;
        background: #FAFAFA;
        font-size: 0.82rem;
        color: #424242;
    }}
    .source-card-lei {{
        border-left-color: #1565C0;
    }}
    .source-card-revogado {{
        border-left-color: #F57F17;
        background: #FFFDE7;
    }}

    /* ---------- Alerta sem base ---------- */
    .no-base-alert {{
        background: #FFF8E1;
        border: 1px solid #FFD600;
        border-left: 4px solid #F9A825;
        border-radius: 8px;
        padding: 1rem 1.25rem;
        margin: 0.75rem 0;
        color: #5D4037;
        font-size: 0.92rem;
    }}
    .no-base-alert strong {{
        color: #E65100;
    }}

    /* ---------- Rodapé jurídico ---------- */
    .legal-footer {{
        background: #F5F5F5;
        border-top: 2px solid {PMSP_RED};
        border-radius: 0 0 8px 8px;
        padding: 0.75rem 1.25rem;
        font-size: 0.78rem;
        color: #757575;
        margin-top: 2rem;
        text-align: center;
    }}

    /* ---------- Mensagens de chat ---------- */
    .chat-message-user {{
        background: #E3F2FD;
        border-radius: 12px 12px 2px 12px;
        padding: 0.85rem 1.1rem;
        margin: 0.5rem 0;
        font-size: 0.92rem;
    }}
    .chat-message-assistant {{
        background: white;
        border: 1px solid #EEEEEE;
        border-radius: 2px 12px 12px 12px;
        padding: 0.85rem 1.1rem;
        margin: 0.5rem 0;
        font-size: 0.92rem;
    }}

    /* ---------- Botão de envio ---------- */
    .stButton > button {{
        background: {PMSP_RED} !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        transition: background 0.2s;
    }}
    .stButton > button:hover {{
        background: {PMSP_RED_DARK} !important;
    }}

    /* ---------- Sidebar ---------- */
    .css-1d391kg, [data-testid="stSidebar"] {{
        background: #F8F8F8;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Cabeçalho
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div class="main-header">
        <h1>⚖️ RAG Jurídico MROSC</h1>
        <p>Consulta inteligente à Lei Federal 13.019/2014 e ao Decreto Municipal SP 57.575/2016</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Sidebar — configurações e instruções
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### ⚙️ Configurações")

    provider_options = {
        "🦙 Ollama (local, padrão)": "ollama",
        "⚡ Groq (API gratuita)": "groq",
        "✨ Google Gemini (API gratuita)": "gemini",
    }
    selected_label = st.selectbox(
        "Provedor de LLM",
        options=list(provider_options.keys()),
        index=0,
        help="Ollama é 100% local e não precisa de chave. Groq e Gemini precisam de GROQ_API_KEY / GOOGLE_API_KEY no .env",
    )
    selected_provider = provider_options[selected_label]

    k_chunks = st.slider(
        "Chunks recuperados por consulta",
        min_value=2,
        max_value=12,
        value=6,
        step=1,
        help="Mais chunks = mais contexto, mas respostas podem ficar mais longas",
    )

    st.divider()
    st.markdown("### 📚 Base de conhecimento")
    st.markdown(
        """
        - 🔵 **Lei Federal 13.019/2014** (MROSC)
        - 🔴 **Decreto Municipal 57.575/2016** (SP)
        """
    )

    st.divider()
    st.markdown("### 💡 Perguntas de exemplo")
    example_questions = [
        "O que é um termo de fomento?",
        "Quando é obrigatório o chamamento público e quais são as exceções?",
        "Qual o prazo de vigência de uma parceria de natureza continuada?",
        "Quais são as hipóteses de dispensa de chamamento público?",
        "O que é uma organização da sociedade civil para fins do MROSC?",
    ]
    for q in example_questions:
        if st.button(q, use_container_width=True, key=f"example_{q[:20]}"):
            st.session_state["input_question"] = q
            st.rerun()

    st.divider()
    st.caption(
        "⚠️ Esta ferramenta é informativa e **não é um canal oficial** da Prefeitura de São Paulo."
    )

# ---------------------------------------------------------------------------
# Inicialização da sessão
# ---------------------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state["messages"] = []

if "chain" not in st.session_state:
    st.session_state["chain"] = None

if "chain_provider" not in st.session_state:
    st.session_state["chain_provider"] = None

if "chain_k" not in st.session_state:
    st.session_state["chain_k"] = None


def get_or_init_chain(provider: str, k: int):
    """Carrega ou reutiliza a chain (evita reinicializar a cada mensagem)."""
    if (
        st.session_state["chain"] is None
        or st.session_state["chain_provider"] != provider
        or st.session_state["chain_k"] != k
    ):
        with st.spinner(
            "🔧 Inicializando modelo de embeddings e chain... (pode levar alguns segundos na 1ª vez)"
        ):
            try:
                from src.rag_chain import build_rag_chain
                st.session_state["chain"] = build_rag_chain(provider=provider, k=k)
                st.session_state["chain_provider"] = provider
                st.session_state["chain_k"] = k
            except RuntimeError as e:
                st.error(
                    f"❌ **Vector store não encontrado.**\n\n"
                    f"Execute primeiro no terminal:\n```\npython src/ingest.py\n```\n\n"
                    f"Detalhes: {e}"
                )
                return None
            except Exception as e:
                st.error(f"❌ Erro ao inicializar a chain: {e}")
                return None

    return st.session_state["chain"]


# ---------------------------------------------------------------------------
# Helpers de renderização
# ---------------------------------------------------------------------------

def render_source_badges(meta: dict) -> str:
    """Gera HTML de badges para exibição das fontes."""
    fonte = meta.get("fonte", "?")
    artigo = meta.get("artigo", "?")
    status = meta.get("status", "vigente")

    badge_class = "badge-decreto" if "Decreto" in fonte else "badge-lei"
    badge_html = f'<span class="{badge_class}">{fonte}</span>'
    badge_html += f'<span class="badge-artigo">Art. {artigo}</span>'

    if status == "revogado":
        badge_html += '<span class="badge-revogado">⚠️ REVOGADO</span>'
    elif status == "alterado":
        badge_html += '<span class="badge-revogado">ℹ️ Alterado</span>'

    return badge_html


def render_source_cards(source_docs: list) -> None:
    """Renderiza os cards de fontes citadas abaixo da resposta."""
    if not source_docs:
        return

    # Remove duplicatas de artigos (pode haver sub-chunks do mesmo artigo)
    seen = set()
    unique_docs = []
    for doc in source_docs:
        key = (doc.metadata.get("fonte", ""), doc.metadata.get("artigo", ""))
        if key not in seen:
            seen.add(key)
            unique_docs.append(doc)

    with st.expander(f"📚 **Fontes consultadas** ({len(unique_docs)} artigos)", expanded=True):
        for doc in unique_docs:
            meta = doc.metadata
            fonte = meta.get("fonte", "?")
            artigo = meta.get("artigo", "?")
            status = meta.get("status", "vigente")

            card_class = "source-card"
            if "Lei" in fonte:
                card_class += " source-card-lei"
            if status == "revogado":
                card_class += " source-card-revogado"

            badges = render_source_badges(meta)
            trecho = doc.page_content[:300].replace("\n", " ") + (
                "..." if len(doc.page_content) > 300 else ""
            )

            st.markdown(
                f"""
                <div class="{card_class}">
                    {badges}<br/>
                    <span style="color: #616161; font-size: 0.8rem; margin-top: 4px; display: block;">
                        {trecho}
                    </span>
                </div>
                """,
                unsafe_allow_html=True,
            )


# ---------------------------------------------------------------------------
# Histórico do chat
# ---------------------------------------------------------------------------
def render_chat_history():
    """Renderiza o histórico completo da conversa."""
    for message in st.session_state["messages"]:
        role = message["role"]
        content = message["content"]
        source_docs = message.get("source_documents", [])

        if role == "user":
            with st.chat_message("user", avatar="👤"):
                st.markdown(content)
        else:
            with st.chat_message("assistant", avatar="⚖️"):
                # Verifica se a resposta indica falta de base nos documentos
                from src.rag_chain import has_base_in_documents

                if not has_base_in_documents(content):
                    st.markdown(
                        f"""
                        <div class="no-base-alert">
                            <strong>⚠️ Informação não encontrada nos documentos</strong><br/>
                            O sistema não localizou base legal nos documentos fornecidos para responder a esta pergunta.
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                st.markdown(content)

                if source_docs:
                    render_source_cards(source_docs)


# ---------------------------------------------------------------------------
# Área principal do chat
# ---------------------------------------------------------------------------
render_chat_history()

# Campo de input (com suporte a perguntas de exemplo da sidebar)
input_value = st.session_state.pop("input_question", "")

if question := st.chat_input(
    "Digite sua pergunta sobre a Lei MROSC ou o Decreto Municipal...",
):
    # Obtém (ou inicializa) a chain
    chain = get_or_init_chain(selected_provider, k_chunks)

    if chain is None:
        st.stop()

    # Adiciona pergunta do usuário ao histórico
    st.session_state["messages"].append({"role": "user", "content": question})

    with st.chat_message("user", avatar="👤"):
        st.markdown(question)

    # Gera resposta
    with st.chat_message("assistant", avatar="⚖️"):
        with st.spinner("🔍 Consultando os documentos jurídicos..."):
            try:
                from src.rag_chain import ask, has_base_in_documents

                result = ask(chain, question)
                answer = result["answer"]
                source_docs = result.get("source_documents", [])

            except Exception as e:
                answer = f"❌ Erro ao processar a pergunta: {e}"
                source_docs = []

        # Alerta visual se não há base nos documentos
        if not has_base_in_documents(answer):
            st.markdown(
                """
                <div class="no-base-alert">
                    <strong>⚠️ Informação não encontrada nos documentos</strong><br/>
                    O sistema não localizou base legal nos documentos fornecidos para responder a esta pergunta.
                    A resposta abaixo informa o que foi possível encontrar.
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown(answer)

        if source_docs:
            render_source_cards(source_docs)

    # Salva resposta no histórico
    st.session_state["messages"].append(
        {
            "role": "assistant",
            "content": answer,
            "source_documents": source_docs,
        }
    )

# Suporte a pergunta via botão da sidebar (exemplo)
if input_value and input_value not in [
    m["content"] for m in st.session_state["messages"] if m["role"] == "user"
]:
    st.session_state["messages"].append({"role": "user", "content": input_value})
    st.rerun()

# ---------------------------------------------------------------------------
# Botão de limpar conversa
# ---------------------------------------------------------------------------
col1, col2, col3 = st.columns([4, 2, 4])
with col2:
    if st.button("🗑️ Limpar conversa"):
        st.session_state["messages"] = []
        st.rerun()

# ---------------------------------------------------------------------------
# Rodapé fixo
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div class="legal-footer">
        ⚠️ <strong>Aviso Legal:</strong> Este sistema é uma ferramenta informativa de consulta a textos jurídicos e
        <strong>não substitui análise jurídica profissional</strong>. As respostas são geradas automaticamente
        com base nos documentos indexados (Lei 13.019/2014 e Decreto 57.575/2016) e podem conter imprecisões.
        Para casos concretos, consulte um advogado especializado. Esta ferramenta <strong>não é um canal oficial
        da Prefeitura de São Paulo</strong>.
    </div>
    """,
    unsafe_allow_html=True,
)

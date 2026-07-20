# ⚖️ RAG Jurídico MROSC

> Sistema de **Recuperação Aumentada por Geração (RAG)** especializado no **Marco Regulatório das Organizações da Sociedade Civil (MROSC)** — Lei Federal nº 13.019/2014 e Decreto Municipal SP nº 57.575/2016.

**Pipeline 100% gratuito**: embeddings locais (HuggingFace) + vector store local (Chroma) + LLM local (Ollama) ou API gratuita (Groq / Google Gemini).

---

## O que preciso configurar antes de rodar

> **Checklist obrigatório antes da primeira execução:**

- [ ] **Documentos jurídicos** — coloque os dois arquivos na pasta `data/`:
  - `data/lei_mrosc.docx` — Lei Federal 13.019/2014 (com a redação dada pela Lei 13.204/2015)
  - `data/decreto_57575_2016.pdf` — Decreto Municipal SP 57.575/2016

- [ ] **Ollama instalado** (se usar o provedor padrão):
  - Baixe em: https://ollama.com
  - Execute: `ollama pull llama3.1:8b` (ou o modelo da sua preferência — veja `.env.example`)
  - Confirme que o serviço está rodando: `ollama serve`

- [ ] **Arquivo `.env` criado** (copie de `.env.example`):
  ```bash
  cp .env.example .env
  ```
  E edite conforme necessário (especialmente `OLLAMA_MODEL` se usar um modelo diferente).

- [ ] **Paleta de cores** — o valor `#ED1C24` em `.streamlit/config.toml` e em `app_streamlit.py` é uma **aproximação** do vermelho institucional da Prefeitura de São Paulo. Antes de publicar ou apresentar oficialmente, verifique o hexadecimal correto no **Manual de Aplicação da Marca da PMSP** e substitua os valores marcados com `# TODO(usuário): confirmar hex oficial`.

---

## Pré-requisitos

| Ferramenta | Versão mínima | Uso |
|---|---|---|
| Python | 3.10+ | Runtime |
| pip | qualquer | Instalação de pacotes |
| Ollama | qualquer | LLM local (opcional se usar Groq/Gemini) |

---

## Instalação

### 1. Clone o repositório

```bash
git clone <url-do-repositorio>
cd rag-mrosc
```

### 2. Crie e ative o ambiente virtual

**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Linux / macOS:**
```bash
python -m venv venv
source venv/bin/activate
```

### 3. Instale as dependências

```bash
pip install -r requirements.txt
```

> **Nota sobre PyTorch**: a instalação padrão inclui PyTorch com suporte CUDA. Se quiser apenas CPU (instalação menor e mais rápida):
> ```bash
> pip install torch --index-url https://download.pytorch.org/whl/cpu
> pip install -r requirements.txt
> ```

### 4. Configure o ambiente

```bash
cp .env.example .env
```

Edite o arquivo `.env` com suas configurações. **Apenas o `OLLAMA_MODEL` precisa ser ajustado** se usar Ollama com um modelo diferente de `llama3.1:8b`.

### 5. Instale o Ollama (se for usar o provedor padrão)

```bash
# Baixe e instale o Ollama em: https://ollama.com
# Depois, baixe o modelo desejado:
ollama pull llama3.1:8b

# Modelos alternativos gratuitos:
# ollama pull qwen2.5:7b      # bom multilíngue
# ollama pull mistral          # alternativa clássica
# ollama pull llama3.2:3b     # mais leve, para máquinas com pouca RAM
```

### 6. Coloque os documentos jurídicos em `data/`

```
data/
├── lei_mrosc.docx           ← Lei Federal 13.019/2014
└── decreto_57575_2016.pdf   ← Decreto Municipal SP 57.575/2016
```

---

## Execução

### Passo 1 — Ingestão (obrigatório, apenas uma vez)

```bash
python src/ingest.py
```

Isso vai:
1. Carregar e parsear os dois documentos por artigo
2. Gerar embeddings com `intfloat/multilingual-e5-large` (download automático na 1ª vez, ~1.2 GB)
3. Indexar os chunks no Chroma e persistir em `chroma_db/`

O progresso é exibido no terminal. Execute novamente sempre que os documentos forem atualizados.

### Passo 2 — Interface principal (Streamlit)

```bash
streamlit run app_streamlit.py
```

Abre no navegador em `http://localhost:8501`

### Alternativa — CLI de debug (terminal)

```bash
python src/cli.py

# Com opções:
python src/cli.py --provider groq    # usa Groq em vez de Ollama
python src/cli.py --k 8              # recupera 8 chunks por consulta
```

---

## Usando Groq ou Google Gemini (opcional)

Se preferir usar uma API gratuita em vez do Ollama local:

### Groq (free tier generoso)
1. Crie conta em https://console.groq.com
2. Gere uma API key gratuita
3. No `.env`: `GROQ_API_KEY=sua_chave_aqui` e `LLM_PROVIDER=groq`

### Google Gemini (free tier)
1. Acesse https://aistudio.google.com/app/apikey
2. Gere uma API key gratuita
3. No `.env`: `GOOGLE_API_KEY=sua_chave_aqui` e `LLM_PROVIDER=gemini`

---

## Estrutura do projeto

```
rag-mrosc/
├── data/
│   ├── lei_mrosc.docx              ← Lei Federal 13.019/2014 (você coloca aqui)
│   └── decreto_57575_2016.pdf      ← Decreto Municipal SP 57.575/2016 (você coloca aqui)
├── src/
│   ├── __init__.py
│   ├── ingest.py          # carregamento, parsing por artigo, chunking, embeddings
│   ├── vectorstore.py     # criação/carregamento do Chroma persistente
│   ├── llm_provider.py    # fábrica de LLM: ollama | groq | gemini
│   ├── rag_chain.py       # montagem da chain LCEL + prompt jurídico especializado
│   └── cli.py             # interface CLI para debug/teste rápido
├── .streamlit/
│   └── config.toml        # tema visual (paleta inspirada na Prefeitura de SP)
├── app_streamlit.py        # interface principal do sistema (chat)
├── chroma_db/              # vector store persistido (gerado, git-ignored)
├── requirements.txt
├── .env.example            # modelo de configuração (nunca contém chaves reais)
├── .gitignore
└── README.md
```

---

## Arquitetura do pipeline

```
Documentos (DOCX + PDF)
    │
    ▼ src/ingest.py
Parsing por artigo (regex)  ──────────────────────┐
    │                                              │
    ▼                                    Metadados: fonte, artigo, status
Chunks (1 chunk ≈ 1 artigo, fallback por tamanho)
    │
    ▼ src/vectorstore.py
Embeddings multilíngues (HuggingFace — local)
    │
    ▼
Chroma (vector store persistente local)
    │
    ▼ src/rag_chain.py (via LCEL)
Pergunta do usuário ──→ Retriever (top-k chunks) ──→ Prompt jurídico ──→ LLM
                                                                         │
                                                                         ▼
                                              Resposta com citação de artigo/fonte
```

---

## Exemplos de perguntas de teste

| Pergunta | Artigo esperado |
|---|---|
| "O que é um termo de fomento?" | Art. 12 do Decreto / Art. 2º da Lei |
| "Quando é obrigatório o chamamento público e quais são as exceções?" | Arts. 23, 30, 31 do Decreto |
| "Qual o prazo de vigência de uma parceria de natureza continuada?" | Art. 36 do Decreto (5 anos, prorrogável até 20 anos) |
| "O que é uma organização da sociedade civil para fins do MROSC?" | Art. 2º da Lei |
| "Qual município aplica esse decreto?" | Município de São Paulo |
| "Que regras valem para parcerias no Rio de Janeiro?" | → sistema deve informar que não há base nos documentos |

---

## Solução de problemas

| Problema | Solução |
|---|---|
| `RuntimeError: Vector store não encontrado` | Execute `python src/ingest.py` primeiro |
| `Connection refused` (Ollama) | Execute `ollama serve` em outro terminal |
| Modelo não encontrado (Ollama) | Execute `ollama pull <nome-do-modelo>` |
| Download lento do modelo de embeddings | Normal na 1ª execução (~1.2 GB). Aguarde. |
| `GROQ_API_KEY não configurada` | Edite o `.env` com sua chave ou use `LLM_PROVIDER=ollama` |
| Memória insuficiente (embeddings) | Troque o modelo no `.env`: `EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-mpnet-base-v2` |
| Respostas muito genéricas | Aumente `k` no slider da sidebar ou em `--k` no CLI |

---

## Placeholders a confirmar antes de publicar

- [ ] **Hex oficial da paleta PMSP**: substituir `#ED1C24` e `#B8151B` (procure por `TODO(usuário): confirmar hex oficial` nos arquivos `app_streamlit.py` e `.streamlit/config.toml`) após consultar o Manual de Aplicação da Marca da Prefeitura de São Paulo.
- [ ] **Modelo Ollama**: verificar se o modelo configurado em `OLLAMA_MODEL` está disponível na sua máquina (`ollama list`).
- [ ] **Modelo de embeddings**: se a máquina tiver GPU, mudar `device: "cpu"` para `"cuda"` em `src/vectorstore.py`.

---

## Aviso legal

> Este sistema é uma ferramenta informativa de consulta a textos jurídicos e **não substitui análise jurídica profissional**. As respostas são geradas automaticamente com base nos documentos indexados e podem conter imprecisões. Para casos concretos, consulte um advogado especializado. **Esta ferramenta não é um canal oficial da Prefeitura de São Paulo.**

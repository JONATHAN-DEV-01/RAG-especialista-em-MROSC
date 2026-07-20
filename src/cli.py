"""
src/cli.py
==========
Interface de linha de comando para debug e teste rápido do RAG MROSC.

Exibe:
  - Resposta gerada pelo LLM
  - Artigos e fontes usados como contexto (com metadados completos)
  - Aviso visual quando não há base nos documentos

Uso:
  python src/cli.py
  python src/cli.py --provider groq    # usa Groq em vez de Ollama
  python src/cli.py --k 8              # recupera 8 chunks em vez de 6
"""

import argparse
import sys
from pathlib import Path

# Garante que o diretório raiz está no path para imports absolutos
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from rich import print as rprint
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

load_dotenv()

console = Console()


def print_banner():
    """Exibe banner de boas-vindas."""
    console.print()
    console.print(
        Panel.fit(
            "[bold red]RAG Jurídico MROSC[/bold red]\n"
            "[dim]Lei Federal 13.019/2014 + Decreto Municipal SP 57.575/2016[/dim]\n"
            "[dim]Interface de debug — use Ctrl+C ou digite 'sair' para encerrar[/dim]",
            border_style="red",
        )
    )
    console.print()


def print_sources(source_docs: list) -> None:
    """Exibe os documentos-fonte recuperados em formato tabular."""
    if not source_docs:
        console.print("[yellow]⚠️  Nenhum documento-fonte recuperado.[/yellow]")
        return

    table = Table(
        title="📚 Fontes recuperadas",
        show_header=True,
        header_style="bold",
        border_style="dim",
    )
    table.add_column("#", style="dim", width=3)
    table.add_column("Fonte", style="bold cyan", min_width=20)
    table.add_column("Art.", style="bold yellow", width=6)
    table.add_column("Status", width=12)
    table.add_column("Trecho", style="dim", max_width=60)

    for i, doc in enumerate(source_docs, 1):
        meta = doc.metadata
        fonte = meta.get("fonte", "?")
        artigo = meta.get("artigo", "?")
        status = meta.get("status", "vigente")
        trecho = doc.page_content[:120].replace("\n", " ") + "..."

        status_color = {
            "vigente": "green",
            "alterado": "yellow",
            "revogado": "red",
        }.get(status, "white")

        table.add_row(
            str(i),
            fonte,
            artigo,
            f"[{status_color}]{status}[/{status_color}]",
            trecho,
        )

    console.print()
    console.print(table)
    console.print()


def run_cli(provider: str = None, k: int = 6):
    """Loop principal do CLI de debug."""
    from src.rag_chain import ask, build_rag_chain, has_base_in_documents

    print_banner()

    try:
        chain = build_rag_chain(provider=provider, k=k)
    except RuntimeError as e:
        console.print(f"\n[bold red]❌ Erro ao carregar vector store:[/bold red]\n{e}")
        console.print(
            "\n[yellow]➡️  Execute primeiro:[/yellow] [bold]python src/ingest.py[/bold]"
        )
        sys.exit(1)

    console.print(
        "[dim]Dica: experimente perguntar sobre termos de fomento, "
        "chamamento público, prazos de vigência...[/dim]\n"
    )

    while True:
        try:
            console.print(Rule(style="dim"))
            pergunta = console.input("[bold green]❓ Sua pergunta:[/bold green] ").strip()

            if not pergunta:
                continue

            if pergunta.lower() in {"sair", "exit", "quit", "q"}:
                console.print("\n[dim]Até logo! 👋[/dim]\n")
                break

            console.print("\n[dim]🔍 Buscando nos documentos...[/dim]")

            result = ask(chain, pergunta)
            answer = result["answer"]
            source_docs = result.get("source_documents", [])

            # Exibe resposta
            console.print()
            if has_base_in_documents(answer):
                console.print(
                    Panel(
                        Markdown(answer),
                        title="[bold]📋 Resposta[/bold]",
                        border_style="green",
                    )
                )
            else:
                console.print(
                    Panel(
                        Markdown(answer),
                        title="[bold yellow]⚠️  Sem base nos documentos[/bold yellow]",
                        border_style="yellow",
                    )
                )

            # Exibe fontes
            print_sources(source_docs)

        except KeyboardInterrupt:
            console.print("\n\n[dim]Interrompido pelo usuário. Até logo! 👋[/dim]\n")
            break
        except Exception as e:
            console.print(f"\n[bold red]❌ Erro:[/bold red] {e}\n")


def main():
    parser = argparse.ArgumentParser(
        description="CLI de debug para o RAG Jurídico MROSC",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python src/cli.py
  python src/cli.py --provider groq
  python src/cli.py --provider gemini --k 8
        """,
    )
    parser.add_argument(
        "--provider",
        type=str,
        default=None,
        choices=["ollama", "groq", "gemini"],
        help="Provedor de LLM (padrão: lê do .env, fallback: ollama)",
    )
    parser.add_argument(
        "--k",
        type=int,
        default=6,
        help="Número de chunks a recuperar por consulta (padrão: 6)",
    )
    args = parser.parse_args()
    run_cli(provider=args.provider, k=args.k)


if __name__ == "__main__":
    main()

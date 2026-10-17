"""
MyJarvis — Entry point CLI
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import typer
from rich.console import Console

from myjarvis.core.config import load_config
from myjarvis.core.jarvis import MyJarvis

app = typer.Typer(
    name="myjarvis",
    help="MyJarvis — Personal AI daemon with ALFRED personality",
    add_completion=False,
)
console = Console()


@app.command()
def ask(
    query: str = typer.Argument(..., help="Pergunta para o Jarvis"),
    model: str | None = typer.Option(None, "--model", "-m", help="Override model"),
    stream: bool = typer.Option(False, "--stream", "-s", help="Stream tokens"),
    no_context: bool = typer.Option(False, "--no-context", help="Disable memory context"),
):
    """Pergunta única ao Jarvis."""
    config = load_config()
    jarvis = MyJarvis(config=config)

    try:
        if stream:
            async def _stream():
                async for token in jarvis.ask_stream(
                    query, model=model, context=not no_context
                ):
                    console.print(token, end="", highlight=False)
                console.print()
            asyncio.run(_stream())
        else:
            response = jarvis.ask(query, model=model, context=not no_context)
            console.print(response, highlight=False)
    finally:
        jarvis.close()


@app.command()
def chat(
    model: str | None = typer.Option(None, "--model", "-m", help="Override model"),
    stream: bool = typer.Option(True, "--stream/--no-stream", help="Stream tokens"),
):
    """Modo conversa interativa."""
    config = load_config()
    jarvis = MyJarvis(config=config)

    console.print("[dim]MyJarvis chat — Ctrl+C para sair[/dim]")
    console.print()

    try:
        while True:
            try:
                query = console.input("[bold cyan]Você:[/bold cyan] ")
            except (EOFError, KeyboardInterrupt):
                console.print("\n[dim]Até mais.[/dim]")
                break

            if not query.strip():
                continue

            console.print("[bold green]Jarvis:[/bold green] ", end="", highlight=False)

            if stream:
                async def _stream():
                    async for token in jarvis.ask_stream(query, model=model):
                        console.print(token, end="", highlight=False)
                    console.print()
                asyncio.run(_stream())
            else:
                response = jarvis.ask(query, model=model)
                console.print(response, highlight=False)

            console.print()
    finally:
        jarvis.close()


@app.command()
def daemon(
    foreground: bool = typer.Option(False, "--foreground", "-f", help="Run in foreground"),
    config_path: Path | None = typer.Option(None, "--config", "-c", help="Config file path"),
):
    """Inicia o daemon MyJarvis (background service + tray)."""
    from myjarvis.daemon import run_daemon

    if config_path:
        import os
        os.environ["MYJARVIS_CONFIG"] = str(config_path)

    run_daemon(foreground=foreground)


@app.command()
def tray():
    """Inicia apenas o system tray icon."""
    from myjarvis.tray import run_tray
    run_tray()


@app.command()
def setup(
    install_service: bool = typer.Option(False, "--service", help="Install as Windows Service (requires admin)"),
    autostart: bool = typer.Option(True, "--autostart/--no-autostart", help="Configure auto-start"),
):
    """Configuração inicial e instalação."""
    from myjarvis.setup import run_setup
    run_setup(install_service=install_service, autostart=autostart)


@app.command()
def status():
    """Status do daemon e saúde."""
    from myjarvis.daemon import get_daemon_status
    status = get_daemon_status()
    console.print_json(data=status)


@app.command()
def memory(
    action: str = typer.Argument(..., help="Ação: stats, search, index, clear"),
    path: str | None = typer.Argument(None, help="Caminho para indexar"),
    query: str | None = typer.Option(None, "--query", "-q", help="Query de busca"),
    top_k: int = typer.Option(5, "--top-k", "-k", help="Resultados"),
):
    """Gerencia memória."""
    config = load_config()
    jarvis = MyJarvis(config=config)

    try:
        if action == "stats":
            console.print_json(data=jarvis.memory.stats())
        elif action == "search":
            if not query:
                console.print("[red]--query obrigatório[/red]")
                raise typer.Exit(1)
            results = jarvis.memory.search(query, top_k=top_k)
            console.print_json(data=results)
        elif action == "index":
            if not path:
                console.print("[red]path obrigatório[/red]")
                raise typer.Exit(1)
            result = jarvis.memory.index(path)
            console.print_json(data=result)
        elif action == "clear":
            # TODO: implementar clear
            console.print("[yellow]Não implementado ainda[/yellow]")
        else:
            console.print(f"[red]Ação desconhecida: {action}[/red]")
    finally:
        jarvis.close()


@app.command()
def models():
    """Lista modelos disponíveis."""
    config = load_config()
    jarvis = MyJarvis(config=config)
    try:
        models = jarvis.list_models()
        console.print_json(data=models)
    finally:
        jarvis.close()


@app.command()
def engines():
    """Lista engines disponíveis."""
    config = load_config()
    jarvis = MyJarvis(config=config)
    try:
        engines = jarvis.list_engines()
        console.print_json(data=engines)
    finally:
        jarvis.close()


if __name__ == "__main__":
    app()
"""WhOSSpr Flow CLI.

Command-line interface for the speech-to-text service.
"""

import logging
import signal
import sys
import time
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from whosspr import __version__
from whosspr.config import (
    Config, ModelSize, DeviceType,
    load_config, save_config, create_default_config,
)
from whosspr.controller import DictationController, DictationState
from whosspr.permissions import check_all, PermissionStatus
from whosspr.enhancer import create_enhancer


def setup_logging(debug: bool = False) -> None:
    """Configure logging."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


logger = logging.getLogger(__name__)

app = typer.Typer(
    name="whosspr",
    help="WhOSSpr Flow - Open source speech-to-text for macOS",
    add_completion=False,
)
console = Console()

# Global for signal handling
_controller: Optional[DictationController] = None


def version_callback(value: bool) -> None:
    """Show version and exit."""
    if value:
        console.print(f"WhOSSpr Flow version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", "-v",
        callback=version_callback, is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    """WhOSSpr Flow - Open source speech-to-text for macOS."""
    pass


@app.command()
def start(
    config_file: Optional[Path] = typer.Option(None, "--config", "-c", help="Config file path."),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Whisper model size."),
    language: Optional[str] = typer.Option(None, "--language", "-l", help="Language code."),
    device: Optional[str] = typer.Option(None, "--device", "-d", help="Device (auto/cpu/mps/cuda)."),
    enhancement: bool = typer.Option(False, "--enhancement/-E", help="Enable text enhancement."),
    api_key: Optional[str] = typer.Option(None, "--api-key", envvar="OPENAI_API_KEY"),
    hold_shortcut: Optional[str] = typer.Option(None, "--hold-shortcut"),
    toggle_shortcut: Optional[str] = typer.Option(None, "--toggle-shortcut"),
    skip_permission_check: bool = typer.Option(False, "--skip-permission-check"),
    debug: bool = typer.Option(False, "--debug"),
) -> None:
    """Start the WhOSSpr dictation service."""
    global _controller
    
    setup_logging(debug)
    logger.info(f"WhOSSpr Flow v{__version__} starting...")
    
    # Load and apply config
    config = load_config(str(config_file) if config_file else None)
    
    if model:
        try:
            config.whisper.model_size = ModelSize(model)
        except ValueError:
            console.print(f"[red]Invalid model: {model}[/red]")
            raise typer.Exit(1)
    
    if language:
        config.whisper.language = language
    if device:
        try:
            config.whisper.device = DeviceType(device)
        except ValueError:
            console.print(f"[red]Invalid device: {device}[/red]")
            raise typer.Exit(1)
    if enhancement:
        config.enhancement.enabled = True
    if api_key:
        config.enhancement.api_key = api_key
        config.enhancement.enabled = True
    if hold_shortcut:
        config.shortcuts.hold_to_dictate = hold_shortcut
    if toggle_shortcut:
        config.shortcuts.toggle_dictation = toggle_shortcut
    
    # Check permissions
    if not skip_permission_check:
        perms = check_all()
        denied = [k for k, v in perms.items() if v != PermissionStatus.GRANTED]
        if denied:
            console.print("\n[yellow]⚠️  Missing permissions:[/yellow]")
            for p in denied:
                console.print(f"  [red]• {p}[/red]")
            console.print("\nRun [cyan]whosspr check[/cyan] for instructions.")
            if not typer.confirm("\nContinue anyway?", default=False):
                raise typer.Exit(1)
    
    # Callbacks
    state_icons = {
        DictationState.IDLE: "⏸️",
        DictationState.RECORDING: "🎤",
        DictationState.PROCESSING: "⏳",
    }
    
    def on_state(state: DictationState) -> None:
        console.print(f"\r{state_icons.get(state, '')} {state.value}", end="  ")
    
    def on_text(text: str) -> None:
        console.print(f"\n[green]Transcribed:[/green] {text}")
    
    def on_error(error: str) -> None:
        console.print(f"\n[red]Error:[/red] {error}")
    
    # Create enhancer if enabled
    enhancer = None
    if config.enhancement.enabled:
        enhancer = create_enhancer(
            api_key=config.enhancement.api_key,
            api_key_helper=config.enhancement.api_key_helper,
            api_key_env_var=config.enhancement.api_key_env_var,
            base_url=config.enhancement.api_base_url,
            model=config.enhancement.model,
            prompt_file=config.enhancement.system_prompt_file,
        )
        if not enhancer:
            console.print("[yellow]Warning: Enhancement enabled but no API key found[/yellow]")
    
    # Create controller
    _controller = DictationController(
        config, on_state=on_state, on_text=on_text, on_error=on_error, enhancer=enhancer
    )
    
    # Signal handler
    def signal_handler(sig, frame):
        console.print("\n\n[yellow]Shutting down...[/yellow]")
        if _controller:
            _controller.stop()
        raise typer.Exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Show startup info
    console.print(Panel.fit(
        f"[bold green]WhOSSpr Flow v{__version__}[/bold green]\n\n"
        f"Model: [cyan]{config.whisper.model_size.value}[/cyan]\n"
        f"Language: [cyan]{config.whisper.language or 'auto'}[/cyan]\n"
        f"Device: [cyan]{config.whisper.device.value}[/cyan]\n"
        f"Enhancement: [cyan]{'on' if config.enhancement.enabled else 'off'}[/cyan]\n\n"
        f"Hold: [yellow]{config.shortcuts.hold_to_dictate}[/yellow]\n"
        f"Toggle: [yellow]{config.shortcuts.toggle_dictation}[/yellow]",
        title="Starting",
    ))
    console.print("\nPress [bold]Ctrl+C[/bold] to stop.\n")
    
    # Start service
    if not _controller.start():
        console.print("[red]Failed to start.[/red]")
        raise typer.Exit(1)
    
    # Run until interrupted
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Shutting down...[/yellow]")
    finally:
        if _controller:
            _controller.stop()


@app.command()
def check() -> None:
    """Check required macOS permissions."""
    console.print(Panel.fit("[bold]Permission Check[/bold]", title="WhOSSpr Flow"))
    
    perms = check_all()
    
    table = Table(title="Required Permissions")
    table.add_column("Permission", style="cyan")
    table.add_column("Status", justify="center")
    
    for perm, status in perms.items():
        if status == PermissionStatus.GRANTED:
            table.add_row(perm.capitalize(), "[green]✅ Granted[/green]")
        else:
            table.add_row(perm.capitalize(), "[red]❌ Denied[/red]")
    
    console.print(table)
    
    denied = [p for p, s in perms.items() if s != PermissionStatus.GRANTED]
    if denied:
        console.print("\n[yellow]To grant permissions:[/yellow]")
        console.print("System Preferences → Security & Privacy → Privacy")
    else:
        console.print("\n[green]✅ All permissions granted![/green]")


@app.command()
def config(
    show: bool = typer.Option(False, "--show", "-s"),
    init: bool = typer.Option(False, "--init", "-i"),
    path: Optional[Path] = typer.Option(None, "--path", "-p"),
) -> None:
    """Show or create configuration."""
    if init:
        out_path = path or Path("whosspr.json")
        cfg = create_default_config()
        save_config(cfg, str(out_path))
        console.print(f"[green]Created:[/green] {out_path}")
        return
    
    cfg = load_config(str(path) if path else None)
    
    table = Table(title="Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value")
    
    table.add_row("Model", cfg.whisper.model_size.value)
    table.add_row("Language", cfg.whisper.language or "auto")
    table.add_row("Device", cfg.whisper.device.value)
    table.add_row("Enhancement", "on" if cfg.enhancement.enabled else "off")
    table.add_row("Hold Shortcut", cfg.shortcuts.hold_to_dictate)
    table.add_row("Toggle Shortcut", cfg.shortcuts.toggle_dictation)
    
    console.print(table)


@app.command()
def models() -> None:
    """List available Whisper models."""
    table = Table(title="Whisper Models")
    table.add_column("Model", style="cyan")
    table.add_column("Size")
    table.add_column("~VRAM")
    
    info = [
        ("tiny", "39M", "~1 GB"),
        ("base", "74M", "~1 GB"),
        ("small", "244M", "~2 GB"),
        ("medium", "769M", "~5 GB"),
        ("large", "1.5B", "~10 GB"),
        ("turbo", "809M", "~6 GB"),
    ]
    
    for name, size, vram in info:
        table.add_row(name, size, vram)
    
    console.print(table)


if __name__ == "__main__":
    app()

"""WhOSSpr Flow CLI application.

Simplified CLI using Typer for the speech-to-text service.
"""

import logging
import signal
import sys
import threading
import time
import traceback
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
from whosspr.core import (
    DictationState,
    DictationController,
    check_permissions,
    PermissionStatus,
)
from whosspr.enhancer import create_enhancer


# Thread exception handler
def thread_exception_handler(args):
    """Handle uncaught exceptions in threads."""
    print(f"THREAD EXCEPTION: {args.exc_type.__name__}: {args.exc_value}", file=sys.stderr, flush=True)
    traceback.print_exception(args.exc_type, args.exc_value, args.exc_tb, file=sys.stderr)

threading.excepthook = thread_exception_handler


# Setup logging
def setup_logging(debug: bool = False) -> None:
    """Configure logging."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

logger = logging.getLogger(__name__)


# Create app
app = typer.Typer(
    name="whosspr",
    help="WhOSSpr Flow - Open source speech-to-text for macOS",
    add_completion=False,
)

console = Console()

# Global controller for signal handling
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
        callback=version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    """WhOSSpr Flow - Open source speech-to-text for macOS."""
    pass


@app.command()
def start(
    config_file: Optional[Path] = typer.Option(
        None, "--config", "-c",
        help="Path to configuration file.",
    ),
    model: Optional[str] = typer.Option(
        None, "--model", "-m",
        help="Whisper model size (tiny, base, small, medium, large, turbo).",
    ),
    language: Optional[str] = typer.Option(
        None, "--language", "-l",
        help="Language code for transcription (e.g., 'en', 'es').",
    ),
    device: Optional[str] = typer.Option(
        None, "--device", "-d",
        help="Device to use (auto, cpu, mps, cuda).",
    ),
    enhancement: bool = typer.Option(
        False, "--enhancement/--no-enhancement", "-e/-E",
        help="Enable/disable text enhancement via API.",
    ),
    api_key: Optional[str] = typer.Option(
        None, "--api-key",
        help="API key for text enhancement.",
        envvar="OPENAI_API_KEY",
    ),
    hold_shortcut: Optional[str] = typer.Option(
        None, "--hold-shortcut",
        help="Hold-to-dictate keyboard shortcut (e.g., 'ctrl+cmd+1').",
    ),
    toggle_shortcut: Optional[str] = typer.Option(
        None, "--toggle-shortcut",
        help="Toggle dictation keyboard shortcut (e.g., 'ctrl+cmd+2').",
    ),
    skip_permission_check: bool = typer.Option(
        False, "--skip-permission-check",
        help="Skip permission checks (not recommended).",
    ),
    debug: bool = typer.Option(
        False, "--debug",
        help="Enable debug logging.",
    ),
) -> None:
    """Start the WhOSSpr dictation service.
    
    The service listens for keyboard shortcuts to start/stop dictation.
    Transcribed text is automatically inserted at the cursor position.
    
    Press Ctrl+C to stop the service.
    """
    global _controller
    
    setup_logging(debug)
    logger.info(f"WhOSSpr Flow v{__version__} starting...")
    
    # Load configuration
    config = load_config(str(config_file) if config_file else None)
    
    # Apply command-line overrides
    if model:
        try:
            config.whisper.model_size = ModelSize(model)
        except ValueError:
            console.print(f"[red]Invalid model: {model}[/red]")
            console.print(f"Valid: {', '.join(m.value for m in ModelSize)}")
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
        perms = check_permissions()
        denied = [k for k, v in perms.items() if v != PermissionStatus.GRANTED]
        
        if denied:
            console.print("\n[yellow]⚠️  Missing permissions:[/yellow]")
            for p in denied:
                console.print(f"  [red]• {p}[/red]")
            
            console.print("\nRun [cyan]whosspr check[/cyan] for instructions.")
            
            if not typer.confirm("\nContinue anyway?", default=False):
                raise typer.Exit(1)
    
    # State change callback
    def on_state(state: DictationState) -> None:
        icons = {
            DictationState.IDLE: "⏸️",
            DictationState.RECORDING: "🎤",
            DictationState.TRANSCRIBING: "⏳",
            DictationState.ENHANCING: "✨",
            DictationState.INSERTING: "📝",
            DictationState.ERROR: "❌",
        }
        console.print(f"\r{icons.get(state, '')} State: [cyan]{state.value}[/cyan]", end="")
    
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
        if enhancer:
            logger.info("Text enhancement enabled")
        else:
            console.print("[yellow]Warning: Enhancement enabled but no API key found[/yellow]")
    
    # Create controller
    _controller = DictationController(
        config,
        on_state=on_state,
        on_text=on_text,
        on_error=on_error,
        enhancer=enhancer,
    )
    
    # Signal handler
    def signal_handler(sig, frame):
        console.print("\n\n[yellow]Shutting down...[/yellow]")
        if _controller:
            _controller.stop()
        raise typer.Exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Display startup info
    console.print(Panel.fit(
        f"[bold green]WhOSSpr Flow v{__version__}[/bold green]\n\n"
        f"Model: [cyan]{config.whisper.model_size.value}[/cyan]\n"
        f"Language: [cyan]{config.whisper.language or 'auto'}[/cyan]\n"
        f"Device: [cyan]{config.whisper.device.value}[/cyan]\n"
        f"Enhancement: [cyan]{'enabled' if config.enhancement.enabled else 'disabled'}[/cyan]\n\n"
        f"Hold shortcut: [yellow]{config.shortcuts.hold_to_dictate}[/yellow]\n"
        f"Toggle shortcut: [yellow]{config.shortcuts.toggle_dictation}[/yellow]",
        title="Starting Dictation Service",
    ))
    
    console.print("\nPress [bold]Ctrl+C[/bold] to stop.\n")
    
    # Start the service
    if not _controller.start():
        console.print("[red]Failed to start dictation service.[/red]")
        raise typer.Exit(1)
    
    # Keep running
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
    """Check required permissions for WhOSSpr.
    
    Shows the status of required macOS permissions:
    - Microphone access (for recording audio)
    - Accessibility access (for injecting text)
    """
    console.print(Panel.fit(
        "[bold]Permission Check[/bold]",
        title="WhOSSpr Flow",
    ))
    
    perms = check_permissions()
    
    table = Table(title="Required Permissions")
    table.add_column("Permission", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("Description")
    
    status_map = {
        PermissionStatus.GRANTED: ("✅ Granted", "green"),
        PermissionStatus.DENIED: ("❌ Denied", "red"),
        PermissionStatus.UNKNOWN: ("❓ Unknown", "yellow"),
    }
    
    descs = {
        "microphone": "Required to record audio for transcription",
        "accessibility": "Required to inject text into applications",
    }
    
    for perm, status in perms.items():
        text, color = status_map.get(status, ("Unknown", "white"))
        table.add_row(perm.capitalize(), f"[{color}]{text}[/{color}]", descs.get(perm, ""))
    
    console.print(table)
    
    denied = [p for p, s in perms.items() if s != PermissionStatus.GRANTED]
    
    if denied:
        console.print("\n[yellow]To grant permissions:[/yellow]")
        if "microphone" in denied:
            console.print("[bold]Microphone:[/bold] System Preferences → Security & Privacy → Privacy → Microphone")
        if "accessibility" in denied:
            console.print("[bold]Accessibility:[/bold] System Preferences → Security & Privacy → Privacy → Accessibility")
    else:
        console.print("\n[green]✅ All permissions granted![/green]")


@app.command()
def config(
    show: bool = typer.Option(False, "--show", "-s", help="Show current configuration."),
    init: bool = typer.Option(False, "--init", "-i", help="Create a new config file."),
    path: Optional[Path] = typer.Option(None, "--path", "-p", help="Path to config file."),
) -> None:
    """Show or create configuration.
    
    Without options, shows the current configuration.
    Use --init to create a new config file with defaults.
    """
    if init:
        out_path = path or Path("whosspr.json")
        cfg = create_default_config()
        save_config(cfg, str(out_path))
        console.print(f"[green]Created config file:[/green] {out_path}")
        return
    
    cfg = load_config(str(path) if path else None)
    
    table = Table(title="Current Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value")
    
    table.add_row("Whisper Model", cfg.whisper.model_size.value)
    table.add_row("Language", cfg.whisper.language or "auto")
    table.add_row("Device", cfg.whisper.device.value)
    table.add_row("Enhancement", "enabled" if cfg.enhancement.enabled else "disabled")
    table.add_row("API Base URL", cfg.enhancement.api_base_url)
    table.add_row("Hold Shortcut", cfg.shortcuts.hold_to_dictate)
    table.add_row("Toggle Shortcut", cfg.shortcuts.toggle_dictation)
    table.add_row("Sample Rate", str(cfg.audio.sample_rate))
    table.add_row("Tmp Directory", cfg.tmp_dir)
    
    console.print(table)


@app.command()
def models() -> None:
    """List available Whisper models."""
    table = Table(title="Available Whisper Models")
    table.add_column("Model", style="cyan")
    table.add_column("Parameters")
    table.add_column("English-only", justify="center")
    table.add_column("Multilingual", justify="center")
    table.add_column("~VRAM")
    
    info = [
        ("tiny", "39M", "✅", "✅", "~1 GB"),
        ("base", "74M", "✅", "✅", "~1 GB"),
        ("small", "244M", "✅", "✅", "~2 GB"),
        ("medium", "769M", "✅", "✅", "~5 GB"),
        ("large", "1550M", "❌", "✅", "~10 GB"),
        ("large-v2", "1550M", "❌", "✅", "~10 GB"),
        ("large-v3", "1550M", "❌", "✅", "~10 GB"),
        ("turbo", "809M", "❌", "✅", "~6 GB"),
    ]
    
    for m, params, en, multi, vram in info:
        table.add_row(m, params, en, multi, vram)
    
    console.print(table)
    console.print("\n[dim]Note: Smaller models are faster but less accurate.[/dim]")


if __name__ == "__main__":
    app()

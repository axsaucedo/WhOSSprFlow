"""WhOSSper Flow CLI application.

Provides commands for:
- start: Start the dictation service
- config: Show/edit configuration
- check: Check permissions
"""

import json
import sys
import signal
import threading
import traceback
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from whossper import __version__
from whossper.config.manager import ConfigManager
from whossper.config.schema import WhossperConfig, WhisperModelSize, DeviceType
from whossper.core.dictation_controller import DictationController, DictationState
from whossper.permissions.mac_permissions import PermissionsManager, PermissionStatus


# Global thread exception handler
def thread_exception_handler(args):
    """Handle uncaught exceptions in threads."""
    print(f"THREAD EXCEPTION: {args.exc_type.__name__}: {args.exc_value}", file=sys.stderr, flush=True)
    traceback.print_exception(args.exc_type, args.exc_value, args.exc_tb, file=sys.stderr)
    sys.stderr.flush()

# Install the global thread exception handler
threading.excepthook = thread_exception_handler


# Create Typer app
app = typer.Typer(
    name="whossper",
    help="WhOSSper Flow - Open source speech-to-text for macOS",
    add_completion=False,
)

console = Console()

# Global controller for signal handling
_controller: Optional[DictationController] = None


def version_callback(value: bool) -> None:
    """Show version and exit."""
    if value:
        console.print(f"WhOSSper Flow version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    """WhOSSper Flow - Open source speech-to-text for macOS."""
    pass


@app.command()
def start(
    config_file: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to configuration file.",
    ),
    model: Optional[str] = typer.Option(
        None,
        "--model",
        "-m",
        help="Whisper model size (tiny, base, small, medium, large, turbo).",
    ),
    language: Optional[str] = typer.Option(
        None,
        "--language",
        "-l",
        help="Language code for transcription (e.g., 'en', 'es', 'fr').",
    ),
    device: Optional[str] = typer.Option(
        None,
        "--device",
        "-d",
        help="Device to use (auto, cpu, mps, cuda).",
    ),
    enhancement: bool = typer.Option(
        False,
        "--enhancement/--no-enhancement",
        "-e/-E",
        help="Enable/disable text enhancement via API.",
    ),
    api_key: Optional[str] = typer.Option(
        None,
        "--api-key",
        help="API key for text enhancement.",
        envvar="OPENAI_API_KEY",
    ),
    hold_shortcut: Optional[str] = typer.Option(
        None,
        "--hold-shortcut",
        help="Hold-to-dictate keyboard shortcut (e.g., 'ctrl+cmd+1').",
    ),
    toggle_shortcut: Optional[str] = typer.Option(
        None,
        "--toggle-shortcut",
        help="Toggle dictation keyboard shortcut (e.g., 'ctrl+cmd+2').",
    ),
    skip_permission_check: bool = typer.Option(
        False,
        "--skip-permission-check",
        help="Skip permission checks (not recommended).",
    ),
    debug: bool = typer.Option(
        False,
        "--debug",
        help="Enable debug logging with verbose output.",
    ),
    log_file: Optional[Path] = typer.Option(
        None,
        "--log-file",
        help="Path to log file. If not specified, logs go to stderr only.",
    ),
) -> None:
    """Start the WhOSSper dictation service.
    
    The service listens for keyboard shortcuts to start/stop dictation.
    Transcribed text is automatically inserted at the cursor position.
    
    Press Ctrl+C to stop the service.
    """
    global _controller
    
    # Setup logging FIRST before any other operations
    from whossper.logging_config import setup_logging, get_default_log_file
    
    log_path = str(log_file) if log_file else None
    if debug and not log_path:
        # In debug mode, auto-create log file if not specified
        log_path = get_default_log_file("./tmp/logs")
    
    setup_logging(debug=debug, log_file=log_path)
    
    import logging
    logger = logging.getLogger("whossper.cli")
    logger.info(f"WhOSSper Flow v{__version__} starting...")
    if log_path:
        console.print(f"[dim]Logging to: {log_path}[/dim]")
    
    # Load configuration
    if config_file:
        manager = ConfigManager(str(config_file))
    else:
        manager = ConfigManager()
    
    config = manager.load()
    logger.debug(f"Loaded config: {config}")
    
    # Apply command-line overrides
    if model:
        try:
            config.whisper.model_size = WhisperModelSize(model)
        except ValueError:
            console.print(f"[red]Invalid model size: {model}[/red]")
            console.print(f"Valid options: {', '.join(m.value for m in WhisperModelSize)}")
            raise typer.Exit(1)
    
    if language:
        config.whisper.language = language
    
    if device:
        try:
            config.whisper.device = DeviceType(device)
        except ValueError:
            console.print(f"[red]Invalid device: {device}[/red]")
            console.print(f"Valid options: {', '.join(d.value for d in DeviceType)}")
            raise typer.Exit(1)
    
    if enhancement:
        config.enhancement.enabled = True
    
    if api_key:
        config.enhancement.api_key = api_key
        if not config.enhancement.enabled:
            config.enhancement.enabled = True
    
    if hold_shortcut:
        config.shortcuts.hold_to_dictate = hold_shortcut
    
    if toggle_shortcut:
        config.shortcuts.toggle_dictation = toggle_shortcut
    
    # Check permissions
    if not skip_permission_check:
        perms = PermissionsManager()
        perms_status = perms.check_all_permissions()
        
        all_granted = all(
            status == PermissionStatus.GRANTED
            for status in perms_status.values()
        )
        
        if not all_granted:
            console.print("\n[yellow]⚠️  Missing permissions detected:[/yellow]\n")
            
            for perm, status in perms_status.items():
                if status != PermissionStatus.GRANTED:
                    color = "yellow" if status == PermissionStatus.UNKNOWN else "red"
                    console.print(f"  [{color}]• {perm}: {status.value}[/{color}]")
            
            console.print("\nRun [cyan]whossper check[/cyan] for instructions.")
            
            if not typer.confirm("\nContinue anyway?", default=False):
                raise typer.Exit(1)
    
    # Set up state change callback
    def on_state_change(state: DictationState) -> None:
        state_icons = {
            DictationState.IDLE: "⏸️",
            DictationState.RECORDING: "🎤",
            DictationState.TRANSCRIBING: "⏳",
            DictationState.ENHANCING: "✨",
            DictationState.INSERTING: "📝",
            DictationState.ERROR: "❌",
        }
        icon = state_icons.get(state, "")
        console.print(f"\r{icon} State: [cyan]{state.value}[/cyan]", end="")
    
    def on_transcription(text: str) -> None:
        console.print(f"\n[green]Transcribed:[/green] {text}")
    
    def on_error(error: str) -> None:
        console.print(f"\n[red]Error:[/red] {error}")
    
    # Create controller
    _controller = DictationController(
        config,
        on_state_change=on_state_change,
        on_transcription=on_transcription,
        on_error=on_error,
    )
    
    # Set up signal handler for graceful shutdown
    def signal_handler(sig, frame):
        console.print("\n\n[yellow]Shutting down...[/yellow]")
        if _controller:
            _controller.stop()
        raise typer.Exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Display startup info
    console.print(Panel.fit(
        f"[bold green]WhOSSper Flow v{__version__}[/bold green]\n\n"
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
        signal.pause()
    except AttributeError:
        # Windows fallback
        import time
        while True:
            time.sleep(1)


@app.command()
def check() -> None:
    """Check required permissions for WhOSSper.
    
    Shows the status of required macOS permissions:
    - Microphone access (for recording audio)
    - Accessibility access (for injecting text into applications)
    """
    console.print(Panel.fit(
        "[bold]Permission Check[/bold]",
        title="WhOSSper Flow",
    ))
    
    perms = PermissionsManager()
    perms_status = perms.check_all_permissions()
    
    table = Table(title="Required Permissions")
    table.add_column("Permission", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("Description")
    
    status_colors = {
        PermissionStatus.GRANTED: ("✅ Granted", "green"),
        PermissionStatus.DENIED: ("❌ Denied", "red"),
        PermissionStatus.NOT_DETERMINED: ("❓ Not asked", "yellow"),
        PermissionStatus.UNKNOWN: ("❓ Unknown", "yellow"),
    }
    
    descriptions = {
        "microphone": "Required to record audio for transcription",
        "accessibility": "Required to inject text into applications",
    }
    
    for perm, status in perms_status.items():
        status_text, color = status_colors.get(status, ("Unknown", "white"))
        desc = descriptions.get(perm, "")
        table.add_row(perm.capitalize(), f"[{color}]{status_text}[/{color}]", desc)
    
    console.print(table)
    
    # Show instructions for denied permissions
    denied = [p for p, s in perms_status.items() if s != PermissionStatus.GRANTED]
    
    if denied:
        console.print("\n[yellow]To grant permissions:[/yellow]\n")
        
        instructions = perms.get_permission_instructions()
        for perm, instruction in instructions.items():
            if perm in denied:
                console.print(f"[bold]{perm.capitalize()}:[/bold]")
                console.print(f"  {instruction}\n")
        
        # Offer to open System Preferences
        if typer.confirm("Open System Preferences to grant permissions?", default=True):
            if "microphone" in denied:
                perms.request_microphone_permission()
            if "accessibility" in denied:
                perms.open_accessibility_preferences()
    else:
        console.print("\n[green]✅ All permissions granted![/green]")


@app.command()
def config(
    show: bool = typer.Option(
        False,
        "--show",
        "-s",
        help="Show current configuration.",
    ),
    init: bool = typer.Option(
        False,
        "--init",
        "-i",
        help="Create a new config file with defaults.",
    ),
    path: Optional[Path] = typer.Option(
        None,
        "--path",
        "-p",
        help="Path to config file (for --init or --show).",
    ),
    set_model: Optional[str] = typer.Option(
        None,
        "--model",
        help="Set Whisper model size.",
    ),
    set_language: Optional[str] = typer.Option(
        None,
        "--language",
        help="Set language for transcription.",
    ),
    set_enhancement: Optional[bool] = typer.Option(
        None,
        "--enhancement/--no-enhancement",
        help="Enable/disable text enhancement.",
    ),
) -> None:
    """Show or modify configuration.
    
    Without options, shows the current configuration.
    Use --init to create a new config file with defaults.
    """
    config_path = str(path) if path else None
    manager = ConfigManager(config_path)
    
    if init:
        # Create new config with defaults
        out_path = path or Path("whossper.json")
        cfg = WhossperConfig()
        manager = ConfigManager(str(out_path))
        manager.save(cfg)
        console.print(f"[green]Created config file:[/green] {out_path}")
        return
    
    # Load existing config
    cfg = manager.load()
    
    # Apply modifications
    modified = False
    
    if set_model:
        try:
            cfg.whisper.model_size = WhisperModelSize(set_model)
            modified = True
        except ValueError:
            console.print(f"[red]Invalid model: {set_model}[/red]")
            raise typer.Exit(1)
    
    if set_language:
        cfg.whisper.language = set_language
        modified = True
    
    if set_enhancement is not None:
        cfg.enhancement.enabled = set_enhancement
        modified = True
    
    if modified:
        manager.save(cfg)
        console.print("[green]Configuration updated.[/green]")
    
    if show or not modified:
        # Display config
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
        
        # Show config file location
        if manager.config_path and Path(manager.config_path).exists():
            console.print(f"\n[dim]Config file: {manager.config_path}[/dim]")


@app.command()
def models() -> None:
    """List available Whisper models.
    
    Shows all available model sizes and their approximate memory requirements.
    """
    table = Table(title="Available Whisper Models")
    table.add_column("Model", style="cyan")
    table.add_column("Parameters")
    table.add_column("English-only", justify="center")
    table.add_column("Multilingual", justify="center")
    table.add_column("~VRAM")
    
    models_info = [
        ("tiny", "39M", "✅", "✅", "~1 GB"),
        ("base", "74M", "✅", "✅", "~1 GB"),
        ("small", "244M", "✅", "✅", "~2 GB"),
        ("medium", "769M", "✅", "✅", "~5 GB"),
        ("large", "1550M", "❌", "✅", "~10 GB"),
        ("large-v2", "1550M", "❌", "✅", "~10 GB"),
        ("large-v3", "1550M", "❌", "✅", "~10 GB"),
        ("turbo", "809M", "❌", "✅", "~6 GB"),
    ]
    
    for model, params, en, multi, vram in models_info:
        table.add_row(model, params, en, multi, vram)
    
    console.print(table)
    console.print("\n[dim]Note: Smaller models are faster but less accurate.[/dim]")


if __name__ == "__main__":
    app()

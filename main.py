"""WhOSSper Flow - Open Source Speech-to-Text for macOS."""

from whossper import __version__, __app_name__


def main():
    """Main entry point for WhOSSper Flow."""
    print(f"{__app_name__} v{__version__}")
    print("Use 'whossper --help' to see available commands.")


if __name__ == "__main__":
    main()


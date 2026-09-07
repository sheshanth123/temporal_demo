"""eBay Browse API client package."""


def main() -> None:
    """Run the command-line application without importing it at package load."""
    from ebay_client.main import main as run

    run()


__all__ = ["main"]

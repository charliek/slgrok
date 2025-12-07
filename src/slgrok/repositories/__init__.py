"""Repository layer for external API communication."""

from slgrok.repositories.ngrok import NgrokConnectionError, NgrokRepository

__all__ = ["NgrokConnectionError", "NgrokRepository"]

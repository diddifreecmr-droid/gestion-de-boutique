"""Configuration propre à l'adaptateur HTTP.

L'interface ne lit pas la configuration globale (`app.bootstrap`) : le composition root
lui transmet uniquement ce dont elle a besoin (specs § 4.1, règle 4).
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class HttpConfig:
    api_prefix: str
    expose_docs: bool

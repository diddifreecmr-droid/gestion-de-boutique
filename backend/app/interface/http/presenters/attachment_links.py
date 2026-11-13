"""Adresse d'un lien signé vers le contenu d'une pièce jointe (TR-17).

Seul endroit qui écrit la forme du lien : `GET /attachments/{id}/url` et les vignettes de la
liste des articles (T30) servent exactement la même adresse, ouverte sans jeton par `<img>`.
"""

from app.application.attachments.links import SignedLink


def content_url(api_prefix: str, link: SignedLink) -> str:
    path = f"{api_prefix}/shops/{link.shop_id}/attachments/{link.attachment_id}/content"
    return f"{path}?expires={link.expires}&signature={link.signature}"

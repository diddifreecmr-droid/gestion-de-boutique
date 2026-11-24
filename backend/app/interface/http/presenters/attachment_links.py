"""Adresse d'un lien signé vers le contenu d'une pièce jointe (TR-17).

Seul endroit qui écrit la forme du lien : `GET /attachments/{id}/url`, les vignettes de la
liste des articles (T30) et le logo de la boutique (profil, reçu) servent la même adresse,
ouverte sans jeton par `<img>`.
"""

from app.application.attachments.links import SignedLink


def content_url(api_prefix: str, link: SignedLink) -> str:
    path = f"{api_prefix}/shops/{link.shop_id}/attachments/{link.attachment_id}/content"
    return f"{path}?expires={link.expires}&signature={link.signature}"


def optional_url(api_prefix: str, link: SignedLink | None) -> str | None:
    return None if link is None else content_url(api_prefix, link)

"""Publicação no X via API v2 (OAuth 1.0a, contexto de usuário).

Antes de publicar, confere se o token pertence à conta esperada. Isso evita
que um secret faltando ou trocado num Environment faça um post sair na conta
errada (ex.: post político na conta de segurança).
"""

import os


class ContaErrada(RuntimeError):
    pass


def _cliente():
    import tweepy  # import tardio: testes não precisam da lib

    return tweepy.Client(
        consumer_key=os.environ["X_API_KEY"],
        consumer_secret=os.environ["X_API_SECRET"],
        access_token=os.environ["X_ACCESS_TOKEN"],
        access_token_secret=os.environ["X_ACCESS_TOKEN_SECRET"],
    )


def publicar(texto: str, usuario_esperado: str, cliente=None) -> str:
    """Publica o post e retorna o ID. Lança exceção em caso de erro."""
    cliente = cliente or _cliente()
    eu = cliente.get_me(user_auth=True)
    usuario = str(eu.data["username"] if isinstance(eu.data, dict) else eu.data.username)
    if usuario.lower() != usuario_esperado.lower().lstrip("@"):
        raise ContaErrada(
            f"o token configurado é da conta @{usuario}, mas esta execução é da @{usuario_esperado}. "
            "Confira os secrets X_ACCESS_TOKEN/X_ACCESS_TOKEN_SECRET do Environment desta conta."
        )
    resp = cliente.create_tweet(text=texto, user_auth=True)
    return str(resp.data["id"])


def url_do_post(post_id: str) -> str:
    return f"https://x.com/i/web/status/{post_id}"

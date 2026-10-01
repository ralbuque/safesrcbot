"""Publicação no X via API v2 (OAuth 1.0a, contexto de usuário)."""

import os


def publicar(texto: str) -> str:
    """Publica o post e retorna o ID. Lança exceção em caso de erro."""
    import tweepy  # import tardio: testes não precisam da lib

    cliente = tweepy.Client(
        consumer_key=os.environ["X_API_KEY"],
        consumer_secret=os.environ["X_API_SECRET"],
        access_token=os.environ["X_ACCESS_TOKEN"],
        access_token_secret=os.environ["X_ACCESS_TOKEN_SECRET"],
    )
    resp = cliente.create_tweet(text=texto, user_auth=True)
    return str(resp.data["id"])


def url_do_post(post_id: str) -> str:
    return f"https://x.com/i/web/status/{post_id}"

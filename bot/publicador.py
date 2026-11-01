"""Publicação no X via API v2 (OAuth 1.0a, contexto de usuário).

Antes de publicar, confere se o token pertence à conta esperada. Isso evita
que um secret faltando ou trocado num Environment faça um post sair na conta
errada (ex.: post político na conta de segurança).

Imagens (charges) são enviadas pelo upload em partes da API v2
(initialize -> append -> finalize) e anexadas ao post pelo media_id.
"""

import os

API_MIDIA = "https://api.x.com/2/media/upload"
TIMEOUT = 60


class ContaErrada(RuntimeError):
    pass


class MidiaErro(RuntimeError):
    pass


def _cliente():
    import tweepy  # import tardio: testes não precisam da lib

    return tweepy.Client(
        consumer_key=os.environ["X_API_KEY"],
        consumer_secret=os.environ["X_API_SECRET"],
        access_token=os.environ["X_ACCESS_TOKEN"],
        access_token_secret=os.environ["X_ACCESS_TOKEN_SECRET"],
    )


def _sessao_oauth1():
    from requests_oauthlib import OAuth1Session  # dependência do tweepy

    return OAuth1Session(
        os.environ["X_API_KEY"],
        client_secret=os.environ["X_API_SECRET"],
        resource_owner_key=os.environ["X_ACCESS_TOKEN"],
        resource_owner_secret=os.environ["X_ACCESS_TOKEN_SECRET"],
    )


def _checar(resp, etapa: str) -> dict:
    if resp.status_code not in (200, 201, 202, 204):
        raise MidiaErro(f"upload de imagem ({etapa}): HTTP {resp.status_code} {resp.text[:300]}")
    return resp.json() if resp.content else {}


def enviar_imagem(dados: bytes, mime: str = "image/jpeg", sessao=None) -> str:
    """Envia a imagem ao X e devolve o media_id."""
    sessao = sessao or _sessao_oauth1()
    ini = _checar(
        sessao.post(
            f"{API_MIDIA}/initialize",
            json={"media_type": mime, "total_bytes": len(dados), "media_category": "tweet_image"},
            timeout=TIMEOUT,
        ),
        "initialize",
    )
    media_id = str(ini["data"]["id"])
    _checar(
        sessao.post(
            f"{API_MIDIA}/{media_id}/append",
            data={"segment_index": "0"},
            files={"media": ("charge.jpg", dados, mime)},
            timeout=TIMEOUT,
        ),
        "append",
    )
    fim = _checar(sessao.post(f"{API_MIDIA}/{media_id}/finalize", timeout=TIMEOUT), "finalize")
    estado = (fim.get("data", {}).get("processing_info") or {}).get("state")
    if estado == "failed":
        raise MidiaErro("o X recusou a imagem no processamento")
    return media_id


def publicar(texto: str, usuario_esperado: str, cliente=None, imagem: bytes | None = None, enviar=enviar_imagem) -> str:
    """Publica o post (com imagem opcional) e retorna o ID. Lança exceção em caso de erro."""
    cliente = cliente or _cliente()
    eu = cliente.get_me(user_auth=True)
    usuario = str(eu.data["username"] if isinstance(eu.data, dict) else eu.data.username)
    if usuario.lower() != usuario_esperado.lower().lstrip("@"):
        raise ContaErrada(
            f"o token configurado é da conta @{usuario}, mas esta execução é da @{usuario_esperado}. "
            "Confira os secrets X_ACCESS_TOKEN/X_ACCESS_TOKEN_SECRET do Environment desta conta."
        )
    if imagem:
        media_id = enviar(imagem)
        resp = cliente.create_tweet(text=texto, media_ids=[media_id], user_auth=True)
    else:
        resp = cliente.create_tweet(text=texto, user_auth=True)
    return str(resp.data["id"])


def url_do_post(post_id: str) -> str:
    return f"https://x.com/i/web/status/{post_id}"

"""Charge (cartum editorial) gerada por IA para acompanhar o post.

Fluxo: o Claude descreve a cena (`charge_descricao`) -> montar_prompt() acrescenta
o estilo fixo de charge e as proibições -> gerar_imagem() chama a API de imagens
da OpenAI -> carimbar() escreve "Charge gerada por IA" num canto e salva em JPEG.

O estilo é SEMPRE de desenho/cartum, nunca fotográfico, para não parecer foto real.
"""

import base64
import io
import os

API_OPENAI = "https://api.openai.com/v1/images/generations"
TIMEOUT = 180

ESTILO = (
    "Charge editorial de jornal brasileiro, desenhada à mão: traço de nanquim, cores chapadas, "
    "caricatura exagerada e cômica, estilo cartum clássico de jornal. "
    "Claramente uma ILUSTRAÇÃO desenhada: NÃO fotográfica, NÃO fotorrealista, sem aparência 3D realista. "
    "Composição simples e legível em tela de celular. "
    "Se houver texto (balão de fala, placa ou legenda), em português do Brasil, curto e com ortografia correta."
)

PROIBICOES = (
    "Proibido: sangue, ferimentos, armas apontadas para pessoas, mortos, vítimas, nudez, "
    "conteúdo sexual, símbolos de ódio, humilhação de grupos por origem, raça, religião, sexo ou orientação sexual."
)


class ChargeErro(RuntimeError):
    pass


def montar_prompt(descricao: str) -> str:
    return f"{ESTILO}\n\nCena: {descricao.strip()}\n\n{PROIBICOES}"


def gerar_imagem(descricao: str, cfg: dict, api_key: str | None = None, sessao=None) -> bytes:
    """Gera a imagem e devolve os bytes (PNG/JPEG/WebP, conforme a API). Lança ChargeErro."""
    api_key = api_key or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ChargeErro("OPENAI_API_KEY não configurada")
    if sessao is None:
        import requests as sessao  # import tardio

    corpo = {
        "model": os.environ.get("OPENAI_IMAGE_MODEL") or cfg.get("modelo") or "gpt-image-2",
        "prompt": montar_prompt(descricao),
        "size": cfg.get("tamanho") or "1024x1024",
        "quality": cfg.get("qualidade") or "medium",
        "n": 1,
    }
    resp = sessao.post(
        API_OPENAI,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=corpo,
        timeout=TIMEOUT,
    )
    if resp.status_code != 200:
        try:
            msg = resp.json().get("error", {}).get("message", "")
        except Exception:  # noqa: BLE001
            msg = resp.text[:300]
        raise ChargeErro(f"API de imagens respondeu HTTP {resp.status_code}: {msg}")
    try:
        return base64.b64decode(resp.json()["data"][0]["b64_json"])
    except (KeyError, IndexError, ValueError) as e:
        raise ChargeErro(f"resposta inesperada da API de imagens: {e}") from e


def carimbar(imagem: bytes, texto: str = "Charge gerada por IA", largura_max: int = 1600) -> bytes:
    """Escreve o aviso num canto inferior e devolve JPEG (pequeno o bastante para o X)."""
    from PIL import Image, ImageDraw, ImageFont

    img = Image.open(io.BytesIO(imagem)).convert("RGB")
    if img.width > largura_max:
        img = img.resize((largura_max, round(img.height * largura_max / img.width)))
    if texto:
        desenho = ImageDraw.Draw(img)
        tamanho = max(14, img.width // 40)
        fonte = ImageFont.load_default(size=tamanho)
        x0, y0, x1, y1 = desenho.textbbox((0, 0), texto, font=fonte)
        margem, folga = tamanho // 2, tamanho // 3
        caixa_w, caixa_h = (x1 - x0) + 2 * folga, (y1 - y0) + 2 * folga
        cx, cy = img.width - caixa_w - margem, img.height - caixa_h - margem
        desenho.rectangle([cx, cy, cx + caixa_w, cy + caixa_h], fill=(255, 255, 255), outline=(0, 0, 0), width=2)
        desenho.text((cx + folga - x0, cy + folga - y0), texto, fill=(0, 0, 0), font=fonte)
    saida = io.BytesIO()
    img.save(saida, format="JPEG", quality=85, optimize=True)
    return saida.getvalue()

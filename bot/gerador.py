"""Pesquisa a notícia e escreve o post usando a API do Claude com busca na web."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from . import historico
from .validador import validar_gerado

PROMPT_SISTEMA = Path(__file__).resolve().parent.parent / "prompts" / "sistema.md"
MAX_RODADAS = 10
MAX_BUSCAS = 6

FERRAMENTA_REGISTRO = {
    "name": "registrar_post",
    "description": "Registra o post escolhido (ou a decisão de não postar agora).",
    "input_schema": {
        "type": "object",
        "properties": {
            "pular": {"type": "boolean", "description": "true se não houver notícia boa e nova"},
            "motivo_pular": {"type": "string"},
            "texto": {"type": "string", "description": "Texto do post, sem URL"},
            "fonte_url": {"type": "string", "description": "URL https da fonte escolhida"},
            "fonte_nome": {"type": "string", "description": "Nome do veículo/projeto da fonte"},
            "titulo": {"type": "string", "description": "Título original da notícia"},
            "data_publicacao": {"type": "string", "description": "Data de publicação (AAAA-MM-DD)"},
            "categoria": {
                "type": "string",
                "enum": [
                    "vulnerabilidade",
                    "supply-chain",
                    "pesquisa",
                    "ia-llm",
                    "ferramentas-padroes",
                    "incidente",
                ],
            },
            "cves": {"type": "array", "items": {"type": "string"}},
            "justificativa": {"type": "string", "description": "Por que este tema foi escolhido (uso interno)"},
        },
        "required": ["pular"],
    },
}


@dataclass
class Resultado:
    pular: bool
    motivo: str = ""
    dados: dict = field(default_factory=dict)


def _mensagem_usuario(agora: datetime, hist: dict) -> str:
    return (
        f"Data e hora atuais: {agora.strftime('%Y-%m-%d %H:%M')} (horário de Brasília).\n\n"
        f"Posts recentes (não repita):\n{historico.resumo_recente(hist)}\n\n"
        "Pesquise e escolha a melhor notícia para o próximo post."
    )


def gerar(cliente, modelo: str, hist: dict, agora: datetime, incluir_link: bool) -> Resultado:
    """Roda o loop de conversa até o modelo registrar um post válido."""
    sistema = PROMPT_SISTEMA.read_text(encoding="utf-8")
    ferramentas = [
        {
            "type": "web_search_20260318",
            "name": "web_search",
            "max_uses": MAX_BUSCAS,
            "user_location": {"type": "approximate", "country": "BR", "timezone": "America/Sao_Paulo"},
        },
        FERRAMENTA_REGISTRO,
    ]
    mensagens: list[dict] = [{"role": "user", "content": _mensagem_usuario(agora, hist)}]

    for _ in range(MAX_RODADAS):
        resp = cliente.messages.create(
            model=modelo,
            max_tokens=4096,
            system=sistema,
            tools=ferramentas,
            messages=mensagens,
        )
        mensagens.append({"role": "assistant", "content": resp.content})

        if resp.stop_reason == "pause_turn":
            continue  # busca longa: reenviar para o servidor continuar

        chamada = next(
            (b for b in resp.content if getattr(b, "type", None) == "tool_use" and b.name == "registrar_post"),
            None,
        )
        if chamada is None:
            mensagens.append({"role": "user", "content": "Finalize chamando a ferramenta registrar_post."})
            continue

        dados = dict(chamada.input)
        if dados.get("pular"):
            return Resultado(pular=True, motivo=dados.get("motivo_pular", "sem motivo informado"))

        erros = _verificar(dados, hist, incluir_link)
        if not erros:
            return Resultado(pular=False, dados=dados)

        mensagens.append(
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": chamada.id,
                        "is_error": True,
                        "content": "Post rejeitado: " + "; ".join(erros) + ". Corrija e chame registrar_post de novo.",
                    }
                ],
            }
        )

    raise RuntimeError(f"o modelo não produziu um post válido em {MAX_RODADAS} rodadas")


def _verificar(dados: dict, hist: dict, incluir_link: bool) -> list[str]:
    faltando = [c for c in ("texto", "fonte_url", "titulo", "categoria") if not dados.get(c)]
    if faltando:
        return [f"campos obrigatórios ausentes: {', '.join(faltando)}"]
    erros = validar_gerado(dados["texto"], dados["fonte_url"], incluir_link)
    dup = historico.verificar_duplicado(hist, dados["fonte_url"], dados.get("cves") or [])
    if dup:
        erros.append(f"tema repetido ({dup}); escolha outra notícia")
    return erros

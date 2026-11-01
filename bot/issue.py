"""Formato da issue de rascunho (modo revisão) e leitura de volta na aprovação."""

import base64
import json
import re

from .contagem import LIMITE_X, contar

_MARCADOR = "safesrcbot:meta"
_RE_META = re.compile(r"<!--\s*" + _MARCADOR + r"\s+([A-Za-z0-9+/=]+)\s*-->")
_RE_TEXTO = re.compile(r"^~~~text\n(.*?)\n~~~$", re.DOTALL | re.MULTILINE)


def montar_corpo(texto_final: str, meta: dict) -> str:
    meta_b64 = base64.b64encode(json.dumps(meta, ensure_ascii=False).encode()).decode()
    linhas_extra = []
    if meta.get("cves"):
        linhas_extra.append(f"**CVEs:** {', '.join(meta['cves'])}")
    if meta.get("ano_evento"):
        linhas_extra.append(f"**Ano do evento:** {meta['ano_evento']}")
    if meta.get("fontes_extras"):
        linhas_extra.append("**Outras fontes:** " + " · ".join(f"<{u}>" for u in meta["fontes_extras"][:5]))
    extra = "\n".join(linhas_extra)
    charge = ""
    if meta.get("charge_arquivo") or meta.get("charge_erro") or meta.get("charge_descricao"):
        if meta.get("charge_url"):
            charge = f"\n### Charge\n\n![charge]({meta['charge_url']})\n"
        elif meta.get("charge_arquivo"):
            charge = f"\n### Charge\n\nArquivo: `{meta['charge_arquivo']}`\n"
        else:
            charge = f"\n### Charge\n\n⚠️ Não foi possível gerar a charge: {meta.get('charge_erro') or 'motivo desconhecido'}. O post sai só com o texto.\n"
        if meta.get("charge_descricao"):
            charge += f"\n*Cena pedida:* {meta['charge_descricao']}\n"
        if meta.get("charge_arquivo"):
            charge += "\nPara publicar **sem** a charge, adicione a label `sem-charge` junto com `aprovado`.\n"
    aviso = (
        "\n> ⚠️ Conta com revisão obrigatória: confira os fatos na fonte antes de aprovar.\n"
        if meta.get("revisao_obrigatoria")
        else ""
    )
    return f"""<!-- {_MARCADOR} {meta_b64} -->
## @{meta.get('usuario_x', '?')}: texto do post
{aviso}
Pode editar o texto dentro do bloco abaixo antes de aprovar (mantenha as linhas `~~~`).

~~~text
{texto_final}
~~~

{charge}
**Tamanho:** {contar(texto_final)}/{LIMITE_X}
**Fonte:** [{meta.get('fonte_nome') or 'fonte'}]({meta.get('fonte_url', '')}) ({meta.get('data_publicacao') or 'data não informada'})
**Título da fonte:** {meta.get('titulo', '')}
**Categoria:** {meta.get('categoria', '')} · **Tema:** `{meta.get('tema_chave') or '-'}`
{extra}

**Por que este tema:** {meta.get('justificativa', '')}

---
✅ Para publicar: adicione a label `aprovado`.
🗑️ Para descartar: feche a issue.
"""


def ler_corpo(corpo: str) -> tuple[str, dict]:
    """Extrai (texto_final, meta) do corpo da issue. Lança ValueError se inválido."""
    corpo = corpo.replace("\r\n", "\n")
    m_texto = _RE_TEXTO.search(corpo)
    if not m_texto:
        raise ValueError("bloco ~~~text ... ~~~ não encontrado no corpo da issue")
    m_meta = _RE_META.search(corpo)
    meta = json.loads(base64.b64decode(m_meta.group(1))) if m_meta else {}
    return m_texto.group(1).strip(), meta

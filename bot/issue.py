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
    cves = ", ".join(meta.get("cves") or []) or "—"
    return f"""<!-- {_MARCADOR} {meta_b64} -->
## Texto do post

Pode editar o texto dentro do bloco abaixo antes de aprovar (mantenha as linhas `~~~`).

~~~text
{texto_final}
~~~

**Tamanho:** {contar(texto_final)}/{LIMITE_X}
**Fonte:** [{meta.get('fonte_nome', 'fonte')}]({meta.get('fonte_url', '')}) — {meta.get('data_publicacao') or 'data não informada'}
**Título original:** {meta.get('titulo', '')}
**Categoria:** {meta.get('categoria', '')} · **CVEs:** {cves}

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

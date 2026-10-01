# CLAUDE.md: contexto do projeto safesrcbot

> Este arquivo é a memória do projeto para qualquer instância do Claude (ou pessoa) que for mexer aqui.
> **Mantenha-o atualizado**: ao mudar comportamento, configuração ou decisões, atualize a seção correspondente
> e acrescente uma linha no "Registro de decisões" no fim.

## Objetivo

Bot que mantém ativa a conta do X do Ricardo sobre **segurança da informação**, com foco em **segurança no desenvolvimento de software** (AppSec, DevSecOps, supply chain). Ele publica **4 posts por dia em português do Brasil**, cada um com uma notícia recente e relevante da área.

O dono tem pouco tempo e viaja muito, então tudo roda no **GitHub Actions**. Nada depende de uma máquina local.

## Limites (não mudar sem discutir com o dono)

- **Sem respostas automáticas, sem seguir contas, sem curtidas automatizadas.** Desde 2026 a API do X bloqueia respostas automatizadas a quem não mencionou a conta (fev/2026) e removeu follow/like dos planos self-serve (abr/2026). O X também suspende contas que usam IA para responder como se fosse humano (mai/2026). Engajamento (comentar/seguir) é feito **manualmente** pelo dono; no futuro o bot pode apenas *sugerir* (ver Roadmap).
- Não usar automação de navegador para burlar o item acima.
- Só posts originais (não replies), em pt-BR, sem @menções e sem URLs no texto além do link da fonte.

## Como funciona

```
cron 4x/dia ─► postar.yml ─► python -m bot gerar
                               │  Claude (API) + web_search: pesquisa e escolhe 1 notícia
                               │  ferramenta registrar_post ─► validador + checagem de duplicidade
                               │      (erro ► devolve ao modelo para corrigir, até 10 rodadas)
                               ├─ MODO=revisao    ► cria issue "[rascunho] ..." (label rascunho)
                               ├─ MODO=automatico ► publica direto no X
                               └─ MODO=simulacao  ► só imprime (não grava nada)
                             commit de data/historico.json

label "aprovado" na issue ─► aprovar.yml ─► python -m bot publicar-rascunho
                               lê o texto (possivelmente editado) do bloco ~~~text da issue,
                               publica, comenta o link, fecha a issue, commita o histórico
```

Horários (Brasília): 08:07, 12:07, 17:07 e 21:07. O cron do GitHub está em UTC e pode atrasar alguns minutos.

## Estrutura

| Caminho | O quê |
|---|---|
| `prompts/sistema.md` | **Prompt editorial** (temas, fontes, tom, regras). É o principal ponto de ajuste de conteúdo. |
| `bot/gerador.py` | Loop com a API do Claude: web search + ferramenta `registrar_post`, trata `pause_turn` e devolve erros de validação ao modelo. |
| `bot/validador.py` | Regras determinísticas: ≤280 caracteres (link vale 23), sem URL no texto, sem @, ≤2 hashtags, fonte https. Também é a barreira contra prompt injection vinda de páginas web. |
| `bot/contagem.py` | Contagem de caracteres no padrão do X (twitter-text v3). |
| `bot/historico.py` | `data/historico.json`: evita repetir a mesma fonte (URL normalizada) e o mesmo CVE em 7 dias. |
| `bot/issue.py` | Formato da issue de rascunho (metadados em base64 num comentário HTML + texto em bloco `~~~text`). |
| `bot/publicador.py` | Publicação via tweepy (API v2, OAuth 1.0a de usuário). |
| `bot/__main__.py` | CLI: `gerar` e `publicar-rascunho`. |
| `.github/workflows/postar.yml` | Agendamento 4x/dia + execução manual (com escolha de modo). |
| `.github/workflows/aprovar.yml` | Publica issue aprovada. Só roda se quem pôs a label for o dono do repo. |
| `.github/workflows/testes.yml` | pytest em push/PR. |
| `tests/test_bot.py` | Testes unitários (sem rede; o cliente do Claude é falso). |

## Configuração (GitHub → Settings → Secrets and variables → Actions)

**Secrets**

| Nome | Uso |
|---|---|
| `ANTHROPIC_API_KEY` | API do Claude |
| `X_API_KEY`, `X_API_SECRET` | Consumer key/secret do app no portal de desenvolvedor do X |
| `X_ACCESS_TOKEN`, `X_ACCESS_TOKEN_SECRET` | Token de acesso **da conta que vai postar**, gerado com permissão *Read and write* |

**Variables** (opcionais)

| Nome | Padrão | Valores |
|---|---|---|
| `MODO` | `revisao` | `revisao`, `automatico`, `simulacao` |
| `INCLUIR_LINK` | `true` | `true`/`false`. Post com link custa ~US$ 0,20 na API do X, sem link ~US$ 0,015. |
| `ANTHROPIC_MODEL` | `claude-sonnet-5-5` | qualquer ID de modelo da API do Claude |

## Comandos úteis

```bash
pip install -r requirements.txt -r requirements-dev.txt
python -m pytest -q

# Rodar localmente sem publicar (precisa de ANTHROPIC_API_KEY):
MODO=simulacao python -m bot gerar          # PowerShell: $env:MODO="simulacao"; python -m bot gerar

# Disparar no GitHub (gh CLI):
gh workflow run postar.yml -f modo=simulacao
```

## Convenções

- Código, comentários, mensagens e documentação em **português**.
- Python 3.12, sem framework; dependências fixadas em `requirements*.txt`.
- Actions de terceiros **fixadas por SHA** de commit (com a tag em comentário). Ao atualizar, buscar o SHA da nova tag (`git ls-remote https://github.com/actions/checkout`).
- Dados vindos de issues/eventos chegam aos scripts via `env:`, **nunca** interpolados com `${{ }}` dentro de `run:` (evita injeção de comando).
- Todo comportamento novo vem com teste em `tests/`.
- Ajuste de conteúdo/tom: editar `prompts/sistema.md`, não o código.

## Custos estimados (set/2026)

- X API pay-per-use: 4 posts/dia ≈ US$ 24/mês com link ou ≈ US$ 2/mês sem link.
- Claude (Sonnet 5.5 + até 6 buscas por execução a US$ 10/1000): estimativa de US$ 10–20/mês. Conferir no console da Anthropic após a primeira semana.
- GitHub Actions: dentro da cota gratuita.

## Roadmap / ideias

- [ ] Depois de ~1 semana de rascunhos bons, mudar `MODO` para `automatico`.
- [ ] Resumo diário de engajamento: sugerir 5–10 posts para o dono comentar (com rascunho de resposta) e contas para seguir, via issue ou e-mail. **Somente sugestão; a ação é manual.** Ler posts pela API custa ~US$ 0,005/post.
- [ ] Threads ocasionais para pesquisas mais densas.
- [ ] Métricas: buscar impressões/curtidas dos posts e usar no prompt para aprender o que funciona.

## Registro de decisões

- 2026-09-30: Projeto criado. Opção "GitHub Actions + API do Claude + API do X" escolhida em vez do Cowork/Grok, por segurança (segredos no GitHub) e independência de máquina. Começa em `MODO=revisao` (aprovação por issue). Posts em pt-BR. Engajamento automatizado descartado por causa das regras do X.

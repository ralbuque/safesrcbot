# CLAUDE.md: contexto do projeto (bot multi-contas do X)

> Este arquivo é a memória do projeto para qualquer instância do Claude (ou pessoa) que for mexer aqui.
> **Mantenha-o atualizado**: ao mudar comportamento, configuração ou decisões, atualize a seção correspondente
> e acrescente uma linha no "Registro de decisões" no fim.

## Objetivo

Bot que mantém ativas 4 contas do X do Ricardo. **Atenção:** o id interno de cada conta (pasta, Environment) nem sempre é igual ao @ no X; o @ real fica em `usuario_x` no `config.json`. Todos os posts são em português do Brasil. Roda 100% no **GitHub Actions** porque o dono viaja muito.

| Conta (pasta) | @ no X | Assunto | Posts/dia | Link no post | Revisão |
|---|---|---|---|---|---|
| `safesrc` | @ralbuque | Segurança no desenvolvimento de software (AppSec, DevSecOps, supply chain) | 4 | sim (fonte) | **automática** desde 27/10/2026 (`modo: automatico`) |
| `ancapsu` | @ancapsu | Política brasileira contemporânea, perspectiva de direita/bolsonarista | 4 | não | **obrigatória** |
| `palacioassombra` | @palacioassombra | História política do Brasil (eventos com 10+ anos), humor, perspectiva de direita | 2 | não | **obrigatória** |
| `mundoemrevo` | @mundoemrevo | Guerras/conflitos (prioridade Ucrânia; Israel, Irã...), pró-Ucrânia e pró-Israel | 4 | não | **obrigatória** |

## Limites (não mudar sem discutir com o dono)

- **Contas políticas (`revisao_obrigatoria: true`) nunca publicam sozinhas.** O código ignora `automatico` para elas (`Conta.modo_efetivo`). Cada post é aprovado por um humano, porque conteúdo político persuasivo automatizado sem revisão traz risco de desinformação e de suspensão das contas pelas regras de manipulação de plataforma do X. Isso foi combinado com o dono em 26/10/2026.
- **Todo fato precisa de fonte confirmada na pesquisa** (`fonte_url`), mesmo quando o post sai sem link. A fonte aparece na issue para o revisor conferir. Opinião e viés são permitidos; fato inventado, citação inventada e acusação sem base não são. As regras completas estão em `contas/<id>/prompt.md`.
- **Sem respostas automáticas, sem seguir contas, sem curtidas automatizadas.** A API do X bloqueia respostas automatizadas a quem não mencionou a conta (fev/2026) e removeu follow/like dos planos self-serve (abr/2026). O X suspende contas com IA respondendo como humano (mai/2026). Também não usar automação de navegador para burlar isso.
- **As contas não se citam nem se repostam automaticamente** (evita parecer rede coordenada).
- Posts originais apenas, sem @menções e sem URLs no texto além do link da fonte (quando `link_no_post`).

## Como funciona

```
cron a cada 20 min (:07, :27, :47 UTC) ─► postar.yml
   job planejar: python3 -m bot planejar ► contas com horário PENDENTE: o último horário de
                 "horarios" (Brasília) já passou há no máximo 4 h e ainda não foi atendido
                 (historico.json → "ultima_execucao")
   job gerar (matriz, 1 job por conta, environment = id da conta):
       sinais_x.coletar  ► tendências do Brasil + busca recente (Bearer token; só se sinais_x.ativo)
       gerador.gerar     ► Claude + web_search; ferramenta registrar_post
                           ► verificar(): validador, categoria, ano_evento (palacio), duplicidade
                           (erro ► devolvido ao modelo para corrigir, até 10 rodadas)
       modo revisao    ► issue "[@conta] ..." com labels rascunho + conta:<id>
       modo automatico ► publica direto (só contas sem revisão obrigatória)
       modo simulacao  ► só imprime
       commit de contas/<id>/historico.json (com retry de rebase/push)

label "aprovado" na issue ─► aprovar.yml
   job ler:      python3 -m bot ler-issue ► conta (dos metadados da issue; issues antigas = safesrc)
   job publicar: environment = conta; lê o bloco ~~~text (pode ter sido editado), publica,
                 comenta o link, fecha a issue, commita o histórico
   job avisar-falha: comenta na issue e remove a label "aprovado" se algo falhar
```

**Trava de segurança:** antes de publicar, `publicador.publicar` chama `GET /2/users/me` e confere se o token é da conta esperada (`usuario_x`). Se um Environment estiver sem secrets e cair no secret do repositório, o post é bloqueado em vez de sair na conta errada.

**Agendamento do GitHub não é pontual:** execuções agendadas atrasam (vimos 30–60 min) e algumas são puladas. Por isso o planejador não compara com a hora exata. Ele gera para cada horário pendente, uma única vez, com até 4 h de atraso (`bot/conta.py: horario_pendente`, `TOLERANCIA_ATRASO`). `ultima_execucao` é gravado em `contas/<id>/historico.json` quando a geração termina (com post ou com `pular`; não em `simulacao`). Execuções agendadas (`AGENDADO=true`) conferem de novo antes de gerar, para não duplicar quando duas ficam na fila.

## Estrutura

| Caminho | O quê |
|---|---|
| `contas/<id>/config.json` | Comportamento da conta: `usuario_x`, `horarios` (horas cheias, Brasília), `modo`, `revisao_obrigatoria`, `link_no_post`, `categorias`, `idade_minima_anos`, `janela_tema_dias`, `modelo` (opcional), `sinais_x` |
| `contas/<id>/prompt.md` | **Linha editorial** da conta. É o principal ponto de ajuste de conteúdo e tom. |
| `contas/<id>/historico.json` | Posts já feitos, gerado pelo bot. Não editar à mão sem necessidade. |
| `bot/conta.py` | Carrega e valida configs; `modo_efetivo`; `contas_do_horario`. |
| `bot/gerador.py` | Loop com a API do Claude; `regras_do_sistema` (regras fixas acrescentadas a todo prompt); `verificar`. |
| `bot/sinais_x.py` | Tendências (WOEID 23424768 = Brasil) e busca recente no X. Falhas aqui não derrubam a geração. |
| `bot/validador.py` | Regras determinísticas do texto (280 caracteres, link vale 23, sem URL, sem @, ≤2 hashtags, fonte https). |
| `bot/historico.py` | Evita repetir fonte (URL normalizada), CVE (7 dias) e `tema_chave` (janela por conta). |
| `bot/issue.py` | Formato da issue (metadados em base64 num comentário HTML + texto em bloco `~~~text`). |
| `bot/publicador.py` | Publicação via tweepy (OAuth 1.0a) + trava de identidade. |
| `bot/__main__.py` | CLI: `planejar`, `gerar --conta`, `ler-issue`, `publicar-rascunho --conta`. |
| `scripts/autorizar_conta.py` | Gera os tokens de uma conta pelo fluxo PIN (rodar localmente). |
| `.github/workflows/` | `postar.yml`, `aprovar.yml`, `testes.yml`. |
| `tests/test_bot.py` | Testes unitários (sem rede; clientes falsos). |

## Configuração no GitHub

**Secrets do repositório** (Settings → Secrets and variables → Actions):

| Nome | Uso |
|---|---|
| `ANTHROPIC_API_KEY` | API do Claude |
| `X_API_KEY`, `X_API_SECRET` | Consumer key/secret do app do X (um app para todas as contas) |
| `X_BEARER_TOKEN` | Bearer token do app (leitura de tendências e busca) |

**Environments** (Settings → Environments), um por conta, com **o mesmo nome da pasta** (`safesrc`, `ancapsu`, `palacioassombra`, `mundoemrevo`). Cada um tem os secrets:

| Nome | Uso |
|---|---|
| `X_ACCESS_TOKEN`, `X_ACCESS_TOKEN_SECRET` | Token **da conta** (gerado com o app em *Read and write*). Para contas que não são donas do app, use `scripts/autorizar_conta.py`. |

Não deixe `X_ACCESS_TOKEN` no nível do repositório: cada conta tem o seu no Environment.

**Variables** (opcional): `ANTHROPIC_MODEL` (padrão `claude-sonnet-5-5`; `modelo` no config da conta tem prioridade menor que esta variável).

## Como adicionar uma conta nova

1. Crie `contas/<id>/config.json` e `contas/<id>/prompt.md`, copiando de uma conta parecida. O `<id>` só pode ter letras minúsculas, números e `_`.
2. Crie o Environment `<id>` no GitHub com `X_ACCESS_TOKEN` e `X_ACCESS_TOKEN_SECRET` (use `scripts/autorizar_conta.py`).
3. Teste: Actions → Gerar post → Run workflow com conta `<id>` e modo `simulacao`.
4. Atualize a tabela do topo deste arquivo e o "Registro de decisões".

## Comandos úteis

```bash
pip install -r requirements.txt -r requirements-dev.txt
python -m pytest -q

# Local, sem publicar (precisa de ANTHROPIC_API_KEY; X_BEARER_TOKEN é opcional):
MODO=simulacao python -m bot gerar --conta ancapsu
# PowerShell: $env:MODO="simulacao"; python -m bot gerar --conta ancapsu
```

## Convenções

- Código, comentários, mensagens e documentação em **português**.
- Python 3.12, sem framework; dependências fixadas em `requirements*.txt`. O job `planejar` roda com o `python3` do runner, **sem** dependências: `bot/__main__.py` e o que ele importa no topo não podem importar bibliotecas externas (use import tardio).
- Actions de terceiros **fixadas por SHA** de commit (com a tag em comentário). Runners fixados em `ubuntu-24.04`.
- Dados vindos de issues/eventos chegam aos scripts via `env:`, **nunca** interpolados com `${{ }}` dentro de `run:` (evita injeção de comando). IDs de conta são validados por regex e pela existência da pasta.
- Todo comportamento novo vem com teste em `tests/`.
- Ajuste de conteúdo/tom: editar `contas/<id>/prompt.md`, não o código.

## Custos estimados (out/2026, preços pay-per-use)

| Item | Estimativa/mês |
|---|---|
| Claude (Sonnet 5.5 + até 6 buscas web por execução, 14 execuções/dia) | US$ 35–70 |
| X leituras (tendências US$ 0,01/req + busca US$ 0,005/post; ~10 execuções/dia com sinais) | até ~US$ 57 (há deduplicação em 24 h) |
| X posts (safesrc com link US$ 0,20; demais sem link US$ 0,015) + `users/me` US$ 0,01 por publicação | ~US$ 33 |
| GitHub Actions | grátis (repositório público) |

Para reduzir: diminuir `sinais_x.max_posts`, desativar sinais numa conta (`"ativo": false`) ou reduzir `horarios`.

## Roadmap / ideias

- [ ] Avaliar custo real após ~1 semana e ajustar `max_posts`/`horarios`.
- [ ] Resumo diário de engajamento: sugerir posts para o dono comentar e contas para seguir. **Somente sugestão; a ação é manual.**
- [ ] Métricas dos posts publicados (impressões/curtidas) realimentando o prompt.
- [ ] Threads ocasionais.

## Registro de decisões

- 2026-09-30: Projeto criado para @safesrc. Opção "GitHub Actions + API do Claude + API do X". Começa em `MODO=revisao` (aprovação por issue). Engajamento automatizado descartado por causa das regras do X.
- 2026-10-26: Multi-contas, com @ancapsu, @palacioassombra e @mundoemrevo. Contas políticas com revisão humana obrigatória, fatos ancorados em fonte (post sem link) e viés assumido como opinião. Leitura de tendências/posts do X (Bearer token). Um Environment por conta + trava de identidade antes de publicar. Histórico movido para `contas/<id>/historico.json`. Horários (Brasília): safesrc 8/12/17/21, ancapsu 7/11/16/20, palacioassombra 10/19, mundoemrevo 6/10/14/18.
- 2026-10-26: A conta `safesrc` publica no X como **@ralbuque** (`usuario_x: ralbuque`); o id interno continua `safesrc` para não mexer em Environment, histórico e labels.
- 2026-10-27: Geração agendada ligada para as 4 contas. `safesrc` (@ralbuque) passou para `modo: automatico`; as contas políticas seguem com revisão obrigatória.
- 2026-10-28: Agendamento passou a tolerar atrasos. Execuções agendadas do GitHub chegavam com 30–60 min de atraso, ou nem rodavam, e o planejador antigo (hora exata) não gerava nada. Agora o cron roda a cada 20 min e gera para cada horário pendente (até 4 h de atraso), uma vez só.

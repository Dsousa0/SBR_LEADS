# SBR Leads — Contexto para o Claude Code

Ferramenta interna de prospecção de leads B2B sobre a base pública de CNPJs da Receita
Federal, com integração ao Pedido Mobile para cruzar prospectos com a carteira de clientes.

> **Antes de começar**, leia [`docs/CLAUDE.md`](docs/CLAUDE.md) — é a fonte de verdade do
> estado atual, decisões tomadas e próximas frentes. Detalhes técnicos em
> [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md); uso e setup em [`README.md`](README.md).

## Estado Atual

Etapa 5 (refinamento) concluída e em evolução contínua. **Já em produção de uso interno:**
importação da base CNPJ, API REST + frontend HTMX, autenticação JWT, integração Pedido
Mobile e os dashboards do Cockpit Comercial (KPIs do gestor, Análise de Vendas/curvas ABC,
Recompra) e Rotas de Visita.

**Próximas frentes:** Recompra → Cross-sell · Cockpit Fase 3 (realizado vs. meta) ·
Etapa 6 (deploy VPS Hostinger). Ver `docs/CLAUDE.md` para o detalhamento vivo.

## Comandos

```bash
# Subir o ambiente (app + postgres + pgadmin)
docker compose up -d --build
docker compose logs -f app          # logs em tempo real
docker compose down                 # parar (preserva dados)

# Testes (102 testes; pytest.ini fica em app/)
docker compose exec app python -m pytest       # dentro do container
cd app && python -m pytest                      # local, se as deps estiverem instaladas

# Lint (mesmo comando do CI)
ruff check app/ etl/

# Importação da base CNPJ (cara: ~3–8h — não rodar à toa)
docker compose --profile etl run --rm etl python download.py
docker compose --profile etl run --rm etl python importer.py
docker compose --profile etl run --rm etl python validators.py

# psql direto
docker compose exec postgres psql -U prospec -d prospec_db
```

App em **http://localhost:8000**. Credenciais do admin local: ver `README.md` / `.env`
(nunca colocar segredos aqui).

## Stack

Python 3.11 · FastAPI 0.115 · PostgreSQL 16 · SQLAlchemy · pydantic-settings ·
HTMX 1.9 + Jinja2 + TailwindCSS (CDN) · Leaflet 1.9 + markercluster · JWT (python-jose +
passlib/bcrypt) · openpyxl · Docker Compose · Caddy (produção) · pytest + ruff.

## Arquitetura

```
app/
├── main.py              # startup, bootstrap do banco, exception handlers
├── config.py            # Settings (pydantic-settings; valida DATABASE_URL na startup)
├── database.py          # engine e sessão SQLAlchemy
├── auth.py              # JWT, require_login, require_admin
├── service.py           # busca de leads (build_where, buscar, buscar_para_mapa)
├── dashboard_service.py / dashboard_filters.py   # Cockpit do gestor + filtros na URL
├── analise_service.py   # Análise de Vendas — curvas ABC (Pareto)
├── recompra_service.py  # classificar_recompra (pura) + montar/opcoes
├── rotas_service.py     # montagem de rotas de visita (vizinho mais próximo, puro)
├── pedido_mobile.py     # sync da API externa (SOMENTE leitura: nunca POST/PUT/DELETE)
├── routers/             # frontend, api, admin, auth_router, dashboard, navegacao, rotas
├── templates/           # base, index, login, admin/, partials/
└── tests/               # pytest — lógica pura dos services é o foco da cobertura
etl/                     # download.py, importer.py, update_monthly.py, validators.py, schema.sql
docs/                    # CLAUDE.md (estado vivo), ARCHITECTURE.md, ETAPAS.md, superpowers/
```

Padrão: cada dashboard tem um `*_service.py` com **funções puras testáveis** (sem I/O) que
os routers consomem. Specs e planos de cada feature em `docs/superpowers/{specs,plans}/`.

## Princípios Inegociáveis

- ❌ **Sem APIs pagas** — toda fonte de dados deve ser gratuita.
- ❌ **Sem SQLite** — o volume (~22M estabelecimentos) exige PostgreSQL.
- ❌ **Nunca commitar `.env`** — apenas `.env.example`.
- ❌ **Nunca apagar `data/`** sem confirmação explícita (contém o banco).
- ❌ **`pedido_mobile.py` é somente leitura** — jamais escrever na API externa.
- ✅ **Português brasileiro** em UI, mensagens, commits e comentários.
- ✅ **Testar localmente** antes de propor mudança.
- ✅ **Manter compatibilidade com a VPS** — nada que rode só localmente.

## Gotchas

- Arquivos da Receita vêm em **ISO-8859-1**, separador `;`, quote `"` → converter para UTF-8.
- Importação usa **`COPY FROM STDIN`** (não INSERT) — 10–100x mais rápido.
- Dashboards têm **cache por recorte de filtros** (TTL + poda); ao mudar a assinatura dos
  filtros, invalide o cache.
- Sync do Pedido Mobile é **incremental** (só deltas via `ultimaVersao`) e protegido por
  **lock** contra execuções simultâneas.
- Geocode do mapa é **client-side** com cache em `localStorage`; sempre **escapar XSS** em
  popups do Leaflet e no `leads_json`.

## Convenções

- **Git:** branch `main`; commits `tipo: descrição` (`feat`/`fix`/`docs`/`chore`/`refactor`).
- **Python:** PEP 8 + type hints; `ruff` como linter (roda no CI em push/PR na `main`).
- **SQL:** palavras-chave em maiúsculas; tabelas/colunas em `snake_case`.
- **Env:** tudo em `.env` (gitignored); template em `.env.example`; acesso via pydantic-settings.

## Fluxo de Trabalho

1. Ler `docs/CLAUDE.md` para o estado atual antes de mudanças estruturais.
2. Feature nova → escrever spec/plano em `docs/superpowers/` e a lógica como funções puras num `*_service.py`.
3. Cobrir com testes em `app/tests/`; rodar `pytest` e `ruff` antes de finalizar.
4. Mudança de stack/arquitetura → alinhar com o usuário antes.

## agnostic-core

Submodule em `.agnostic-core/` com skills, agents e workflows reutilizáveis. **Antes de
implementar**, consultar por skills relevantes (`skills/{security,backend,frontend,testing}/`).
Catálogo de comandos em `.agnostic-core/commands/claude-code/COMMANDS.md`.

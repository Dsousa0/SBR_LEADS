# Rotas de Visita — Design

> Spec de design da feature "Rotas de Visita" do SBR Leads.
> Brainstorm conduzido em 2026-06-09/10. Visão **gestor/admin** (login próprio de vendedor fica para fase futura).
> Faz parte da evolução do Cockpit Comercial (frente paralela à Fase 3).

## Objetivo

Permitir que o gestor monte **rotas de visita** para um vendedor: escolher clientes (Pedido Mobile) e prospectos (farmácias da base Receita ainda não clientes) numa cidade, ordená-los por proximidade, ajustar manualmente, **salvar com nome** e abrir a rota no Google Maps para navegação. Tudo com **custo zero de API** (geocodificação por CEP via AwesomeAPI, handoff gratuito pro Google Maps).

## Decisões do brainstorm

1. **Persistência:** rotas **salvas e nomeadas** (tabelas novas + tela "Minhas rotas"), não descartáveis.
2. **Dono:** toda rota **pertence a um vendedor** (o gestor escolhe ao montar).
3. **Seleção de paradas:** **manual** — o gestor vê os candidatos no mapa/lista e marca quem visitar.
4. **Ponto de partida:** **uma das paradas**, escolhida pelo gestor; a ordem flui a partir dela.
5. **Rota longa (> 10 paradas):** o "Abrir no Google Maps" **quebra em trechos** (cada trecho começa onde o anterior terminou).
6. **Navegação:** novo item **"Rotas"** no menu lateral.
7. **Clientes em risco:** **destacados** entre os candidatos (selo 🔴) com filtro dedicado, reaproveitando a inteligência do cockpit.
8. **Ordenação (vizinho mais próximo):** roda no **backend como função pura testável** (browser geocodifica e envia coords).
9. **Layout da tela de montagem:** **mapa no centro, 3 colunas** (candidatos | mapa | rota).

## Navegação e telas

Novo item **"Rotas"** no menu lateral. Duas telas, ambas atrás do login:

- **`GET /rotas` — Minhas rotas:** lista das rotas salvas (nome, vendedor, cidade, nº de paradas, atualizada em). Ações por linha: **abrir**, **editar**, **excluir**. Botão **"+ Nova rota"**.
- **`GET /rotas/nova`** e **`GET /rotas/{id}` — Montar/editar rota:** layout de 3 colunas. `nova` abre vazia; `{id}` carrega uma rota salva para edição.

## Modelo de dados

Duas tabelas novas no PostgreSQL:

```sql
CREATE TABLE rota (
    id             SERIAL PRIMARY KEY,
    nome           TEXT NOT NULL,
    vendedor       TEXT NOT NULL,
    municipio      TEXT NOT NULL,
    uf             TEXT NOT NULL,
    criado_em      TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_em  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE rota_parada (
    id          SERIAL PRIMARY KEY,
    rota_id     INTEGER NOT NULL REFERENCES rota(id) ON DELETE CASCADE,
    ordem       INTEGER NOT NULL,         -- 1, 2, 3… (1 = ponto de partida)
    documento   TEXT NOT NULL,            -- CNPJ (cnpj_basico||ordem||dv) — liga ao estabelecimento/cliente
    nome_cache  TEXT NOT NULL,            -- razão/fantasia para exibir sem novo join
    eh_cliente  BOOLEAN NOT NULL,
    cep_cache   TEXT,
    lat_cache   DOUBLE PRECISION,
    lng_cache   DOUBLE PRECISION
);

CREATE INDEX idx_rota_parada_rota ON rota_parada(rota_id);
CREATE INDEX idx_rota_vendedor ON rota(vendedor);
```

**Por que cache de nome/cep/lat/lng na parada:** a rota salva pode ser reaberta noutro dia ou noutro computador, onde o cache de geocodificação em `localStorage` (por navegador) não existe. Guardar as coordenadas na parada deixa a reabertura instantânea e a ordem estável, sem regeocodificar. Os campos `lat/lng/cep` são anuláveis — se faltarem (parada sem CEP geocodificável), o front cai no fluxo de geocodificação client-side normal.

## Fluxo de montagem (tela de 3 colunas)

1. **Filtros no topo:** **vendedor** (select, obrigatório) + **cidade** (select). Sem ambos, as colunas ficam vazias com instrução.
2. **Coluna esquerda — Candidatos:** clientes do vendedor + prospectos (farmácias não-clientes) na cidade. Cada item mostra nome, indicador cliente/prospecto e selo 🔴 **"Em risco"** quando aplicável. **Filtro "só em risco"**. Checkbox inclui/remove da rota.
3. **Coluna central — Mapa (Leaflet):** pinos de todos os candidatos; os que estão na rota aparecem **numerados na ordem atual**. Reusa o mapa e a geocodificação já existentes.
4. **Coluna direita — Rota:** paradas selecionadas, **arrastáveis** para reordenar (SortableJS). O gestor marca **uma parada como 1ª (🏁)**. Botões:
   - **Ordenar automaticamente** — recalcula a ordem por vizinho mais próximo a partir da 1ª parada.
   - **Abrir no Google Maps** — abre a rota (um ou mais trechos).
   - **Salvar rota** — pede um nome (ou reusa o existente em edição) e persiste.

## Geocodificação, ordenação e handoff

- **Geocodificação:** client-side via AwesomeAPI (`cep.awesomeapi.com.br/json/{cep}`), com cache em `localStorage` — exatamente o padrão já usado no Mapa. As coords obtidas são enviadas ao backend ao ordenar e ao salvar (preenchendo `lat/lng_cache`).
- **Ordenar (vizinho mais próximo):** **função pura no backend**. O browser envia `[{documento, lat, lng}]` + índice da partida; o backend devolve a ordem (greedy nearest-neighbor por distância haversine). Ajuste manual continua por arrastar (não recalcula sozinho).
- **Google Maps:** monta URL de direções (`https://www.google.com/maps/dir/?api=1&origin=…&destination=…&waypoints=…`) com as paradas na ordem. Se a rota tiver **mais de 10 paradas**, **quebra em trechos** de no máximo 10 pontos, onde cada trecho seguinte **começa na última parada do anterior** (continuidade). Também é **função pura testável** que devolve a lista de URLs ("Trecho 1", "Trecho 2"…).

## Backend

Reuso máximo da fundação existente:

- **Candidatos:** reusa `app/service.py` (busca por vendedor + município, `SEGMENTO_FIXO=farmacia`, flag `eh_cliente` via join `pm.documento = e.cnpj_basico||e.cnpj_ordem||e.cnpj_dv`). Traz CEP do estabelecimento para geocodificação.
- **Em risco:** reusa `dashboard_service.clientes_risco(db, f, hoje=...)` para marcar quais candidatos são clientes em risco.
- **Select de vendedores:** reusa `dashboard_service.opcoes_filtro(db)`.
- **Novo módulo `app/rotas_service.py`:** funções puras testáveis (`ordenar_vizinho_mais_proximo`, `montar_urls_google_maps`) + CRUD das rotas (criar, atualizar, listar, excluir, carregar com paradas).

### Endpoints (todos atrás do login)

| Método | Rota | Função |
|--------|------|--------|
| `GET`  | `/rotas` | Tela "Minhas rotas" (lista) |
| `GET`  | `/rotas/nova` | Tela de montagem vazia |
| `GET`  | `/rotas/{id}` | Tela de montagem carregando rota salva |
| `GET`  | `/rotas/candidatos?vendedor=&municipio=` | Candidatos (HTMX/partial): clientes + prospectos + flag risco + CEP |
| `POST` | `/rotas/ordenar` | Recebe coords + partida, devolve a ordem (JSON) |
| `POST` | `/rotas` | Cria rota (nome, vendedor, município, paradas[]) |
| `POST` | `/rotas/{id}` | Atualiza rota existente |
| `POST` | `/rotas/{id}/excluir` | Exclui rota |

## Frontend

- Jinja2 + HTMX + Leaflet (padrão do projeto) + **SortableJS** (CDN com SRI) para o drag-and-drop da coluna de rota.
- Reusa a lógica de geocodificação por CEP do Mapa (cache `localStorage`, chamadas paralelas).
- Estado da rota em memória no JS durante a montagem; ao salvar, `POST` com a lista ordenada de paradas (incluindo `lat/lng/cep/nome/eh_cliente` em cache).
- Parciais Jinja2 dedicadas (ex.: `rotas_lista.html`, `rota_candidatos.html`, `rota_painel.html`).

## Testes (pytest)

- `ordenar_vizinho_mais_proximo` — ordem correta a partir da partida; casos de 0/1/2 pontos; pontos coincidentes.
- `montar_urls_google_maps` — rota ≤ 10 (um trecho); rota > 10 (múltiplos trechos com continuidade); origem/destino corretos.
- Query de candidatos — retorna clientes + prospectos, flags `eh_cliente`/em risco corretas, filtro por vendedor+município.
- CRUD de rota — criar/carregar/atualizar/excluir; cascade das paradas; ordem preservada.

## Fora de escopo (fases futuras)

- Login próprio de vendedor (escopo individual / painel do vendedor).
- Histórico de visitas realizadas ("visitei dia X").
- Outros segmentos além de farmácia (segue `SEGMENTO_FIXO`).
- Otimização de rota além de vizinho mais próximo (ex.: 2-opt, janelas de horário).

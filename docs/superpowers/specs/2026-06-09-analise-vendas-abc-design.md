# Design — Dashboard de Análise de Vendas (Fase 2 / Sub-projeto B)

**Data:** 2026-06-09
**Fase:** Cockpit Comercial — Fase 2, sub-projeto B
**Pré-requisitos concluídos:** Fase 1 (cockpit do gestor), A1 (casca de navegação + hub), A2 (separar Busca e Mapa)

## Objetivo

Adicionar o segundo painel ao hub de Dashboards: **Análise de Vendas**, focado em
**curvas ABC** (Pareto) de **produtos** e **representadas**. Mostra a concentração do
faturamento — quais itens/fornecedores são campeões (classe A) versus a cauda longa
(classe C) — reusando a fundação de filtros e o `dashboard_service` já existentes.

Mix de vendas e sazonalidade ficam **fora** desta versão (refinamento futuro).

## Decisões de produto

| Tema | Decisão |
|------|---------|
| Escopo | Duas curvas ABC: **Produtos** e **Representadas**. |
| Cortes ABC | Padrão **50/30/20** (% de receita acumulada). Seletor na barra de filtros para alternar entre `50-30-20`, `70-20-10`, `80-15-5`. |
| Visualização (por curva) | Cards-resumo por classe + gráfico de **Pareto** (barras de receita + linha de % acumulado) + tabela rankeada. |
| Layout | **Abas** Produtos / Representadas (uma curva visível por vez). |
| Tabela | Chips para filtrar por classe **A/B/C**, iniciando na classe **A**. |

## Arquitetura

### Página irmã do cockpit

- Nova rota `GET /dashboard/analise` (logada), reusando `FiltrosDashboard.from_query`
  e o mesmo padrão de **cache por recorte** (TTL 180s) já usado em `/dashboard`.
- A chave de cache inclui os cortes ABC (recorte diferente = dados diferentes).
- Card "Análise de Vendas" no hub (`dashboards.html`) passa de *Em breve* → *Disponível*
  e aponta para `/dashboard/analise`.

### Backend — novo módulo `app/analise_service.py`

Módulo focado e separado do `dashboard_service` (que serve o cockpit), importando
`FiltrosDashboard` e `build_where` do existente para não duplicar a lógica de WHERE.

Funções:

- `parse_cortes(s: str | None) -> tuple[int, int]`
  Valida a string de cortes (`"50-30-20"`) contra a whitelist
  `{"50-30-20", "70-20-10", "80-15-5"}`. Retorna `(corte_a, corte_b)` em pontos
  percentuais (ex.: `(50, 30)`); fallback no padrão `(50, 30)` para valor ausente/inválido.

- `curva_abc(db, f, *, dimensao, cortes) -> dict`
  - `dimensao="produto"`: agrega na tabela `pedido_mobile_item` (alias `pit`),
    `JOIN pedido_mobile_pedido ped`, `GROUP BY pit.produto_codigo`,
    `SUM(pit.total_liquido)` como receita e `SUM(pit.quantidade)` como quantidade.
    Reusa `build_where(f)` para o filtro de período/vendedor/representada/situação.
  - `dimensao="representada"`: agrega em `pedido_mobile_pedido`,
    `GROUP BY representada`, `SUM(ped.total_liquido)` como receita e `COUNT(*)` como pedidos.
  - Ordena por receita desc, calcula `pct_total` e `pct_acumulado`, classifica A/B/C.
  - Retorna `{"itens": [...], "resumo": {...}}`.

- `montar_analise(db, f, *, cortes) -> dict`
  Agregador: `{ "filtros": f, "opcoes": opcoes_filtro(db), "cortes": "<str>",
  "produtos": curva_abc(...produto...), "representadas": curva_abc(...representada...) }`.
  Reusa `opcoes_filtro` do `dashboard_service` (mesmos selects de vendedor/representada/situação).

### Algoritmo ABC

1. Ordena os itens por receita **desc**.
2. `total = SUM(receita)`. Caso `total == 0` (sem dados), todos os itens viram classe **C**
   e os percentuais ficam zerados (sem divisão por zero).
3. Caminha acumulando a receita. Para cada item, com `acumulado_antes` = soma dos itens anteriores:
   - **A** se `acumulado_antes / total * 100 < corte_a`
   - **B** se `< corte_a + corte_b`
   - senão **C**
   (O item que cruza a fronteira pertence à classe de cima — convenção padrão de curva ABC.)
4. `pct_total` = receita do item / total; `pct_acumulado` = acumulado até e incluindo o item / total.

Estrutura de cada item:
```python
{
  "codigo": str | None,        # produto_codigo (None para representada)
  "nome": str,                 # produto_descricao ou representada
  "receita": float,
  "metrica_qtd": float,        # quantidade (produto) ou nº de pedidos (representada)
  "pct_total": float,          # % do faturamento total
  "pct_acumulado": float,      # % acumulado (para a linha de Pareto)
  "classe": "A" | "B" | "C",
}
```

`resumo` por curva:
```python
{
  "A": {"itens": int, "receita": float, "pct_receita": float},
  "B": {...},
  "C": {...},
  "total_itens": int,
  "total_receita": float,
}
```

### Templates

- `app/templates/analise.html` (página completa, estende `base.html`):
  carrega Chart.js no `head_extra`, inclui o filtro compartilhado parametrizado
  (`acao="/dashboard/analise"`, `alvo="#paineis"`, `mostrar_cortes=True`) e
  `partials/analise_paineis.html`.

- `app/templates/partials/analise_paineis.html` (região `#paineis`, swap via HTMX):
  - Abas **Produtos** / **Representadas** (toggle client-side).
  - Por aba: 3 cards-resumo (A/B/C: nº de itens, receita, % do faturamento) +
    `<canvas>` do gráfico de Pareto + tabela rankeada (posição, nome, receita,
    %, % acumulado, métrica de quantidade, badge da classe).
  - Chips A/B/C acima da tabela filtram as linhas client-side; inicia em **A**.
  - Bloco `<script>` inicializa os gráficos Chart.js (combo: barras + linha acumulada,
    com faixas A/B/C coloridas), seguindo o padrão do `dashboard_paineis.html`.
    Inicializa o gráfico da aba ativa e o da outra aba na primeira exibição (canvas
    oculto não dimensiona corretamente no Chart.js).

- `app/templates/partials/dashboard_filtros.html` (modificado — parametrizado):
  - `{% set acao = acao|default('/dashboard') %}` e `{% set alvo = alvo|default('#paineis') %}`
    aplicados em `hx-get`/`hx-target`.
  - Bloco opcional `{% if mostrar_cortes %}` com o `<select name="cortes">`
    (50/30/20, 70/20/10, 80/15/5). O cockpit continua funcionando sem mudanças
    (defaults preservam o comportamento atual).

- `app/templates/dashboards.html` (modificado): card "Análise de Vendas" vira link
  *Disponível* para `/dashboard/analise`.

### Roteamento

Rota adicionada em `app/routers/dashboard.py` (mantém os dois dashboards juntos no
mesmo router). Espelha o handler do cockpit: monta `FiltrosDashboard`, lê `cortes`
da query, usa cache, e devolve `partials/analise_paineis.html` quando `HX-Request`
ou `analise.html` no carregamento direto.

### Fluxo de dados

1. Usuário abre `/dashboard/analise` → página completa (barra de filtros + painéis).
2. Mudar **qualquer filtro** (período/comparação/vendedor/representada/situação) **ou o corte ABC**
   → `hx-trigger="change"` dispara `GET /dashboard/analise?...` → devolve
   `analise_paineis.html` → troca `#paineis`; URL atualizada via `hx-push-url`.
3. Troca de aba (Produtos/Representadas) e chips de classe (A/B/C) → **client-side**, sem refetch.

> Observação: a comparação de período (`comparacao`) não é usada pela curva ABC nesta versão
> (ABC é um retrato do período selecionado). O campo permanece na barra por consistência com o
> cockpit, mas não altera o resultado.

## Testes (TDD)

`app/tests/` (pytest, seguindo a suíte existente):

- **`parse_cortes`**: cada valor válido → tupla correta; valor inválido/ausente → `(50, 30)`.
- **`curva_abc` (matemática)**: dataset sintético com receitas conhecidas →
  - classificação A/B/C correta nas fronteiras (incluindo o item que cruza o corte);
  - `pct_total` e `pct_acumulado` corretos;
  - `resumo` por classe (contagem, receita, % do total) bate;
  - caso **vazio** (sem itens) → listas vazias, resumo zerado, sem exceção;
  - caso **item único** → classe A, 100% acumulado.
- **Rota**: `GET /dashboard/analise` responde 200 logado; devolve o parcial sob `HX-Request`;
  redireciona/401 sem login (conforme `require_login`).

## Arquivos

**Novos:**
- `app/analise_service.py`
- `app/templates/analise.html`
- `app/templates/partials/analise_paineis.html`
- testes em `app/tests/` (ex.: `test_analise_service.py`, casos de rota no arquivo de rotas existente)

**Modificados:**
- `app/routers/dashboard.py` — rota `/dashboard/analise`
- `app/templates/partials/dashboard_filtros.html` — parametrizar `acao`/`alvo` + bloco `mostrar_cortes`
- `app/templates/dashboards.html` — card "Análise de Vendas" → *Disponível*

## Fora de escopo (futuro)

- Mix de vendas (composição por dimensão).
- Sazonalidade (padrão mês-a-mês ao longo do ano).
- Exportação CSV/XLSX das curvas.
- Classificação ABC por quantidade (esta versão classifica por receita).

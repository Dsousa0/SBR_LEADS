# Backlog — Acessibilidade & Design dos Dashboards

> Levantado em 2026-07-15 (inspeção visual das telas rodando + revisão dos templates).
> Diagnóstico apenas — nada implementado ainda. Telas: Hub, Cockpit do Gestor,
> Análise de Vendas (ABC), Recompra.
> **Placar:** 🔴 Alta: 7 · 🟡 Média: 7 · 🟢 Baixa: 3.
> Contrastes são estimativa por hex — confirmar com axe DevTools antes de fechar cor.

## 🔴 Alta

- [ ] **1. Faixa de Recompra só por cor/emoji** — `partials/recompra_paineis.html:43`.
  Célula tem só 🟢🟡🔴⚪. Usar o `label` que já existe em `FAIXAS` (`app/recompra_service.py`):
  `{{ faixas[c.faixa].emoji }} <span>{{ faixas[c.faixa].label }}</span>` (ou `aria-label`/`title`).
- [ ] **2. Cockpit e Análise sem `<h1>` nem hierarquia** — `dashboard.html`, `analise.html:9-16`.
  Add `<h1>` por página + títulos de card viram `<h2>/<h3>`.
- [ ] **3. Filtros do dashboard com labels não associados** — `partials/dashboard_filtros.html:6-45`.
  Add `for`/`id` (ou envolver o campo). Referência correta: `recompra.html:15-50`.
- [ ] **4. HTMX sem `aria-live` nem indicador visível** — `dashboard_filtros.html:2`, `recompra.html:12`, abas em `analise_paineis.html`.
  Envolver alvo com `aria-live="polite"`/`role="status"`; usar o `.htmx-indicator` já definido em `base.html:57`.
- [ ] **5. Sidebar sem `aria-current`; abas da Análise sem ARIA** — `partials/sidebar.html:2-8`, `partials/analise_paineis.html:5-14`.
  `aria-current="page"` na sidebar; padrão ARIA Tabs (`role=tablist/tab/tabpanel`, `aria-selected`, setas); `aria-pressed` nos chips A/B/C/Todas.
- [ ] **6. Contraste < AA (4.5:1)** — labels/cabeçalhos `text-[#666]` sobre `#111` (~3.3:1); vazio `text-[#555]` (~2.3:1).
  Arquivos: `dashboard_filtros.html:7,12,17…`, `dashboard_paineis.html`, `analise_paineis.html`. Subir para `#8a8a8a`/`#999`+.
- [ ] **7. Cockpit — tabela "Clientes em risco" densa** — `dashboard.html`.
  ~24 linhas sem paginação/scroll interno/cabeçalho fixo. Paginar ou `sticky` no `<thead>`.

## 🟡 Média

- [ ] **8. Sem skip link** — `base.html:111-127`. `<a href="#conteudo" class="sr-only focus:not-sr-only">` + `id="conteudo"` no `<main>`.
- [ ] **9. `<th>` sem `scope="col"` e tabelas sem `<caption>`** — `dashboard_paineis.html`, `analise_paineis.html:60`, `recompra_paineis.html:20`.
- [ ] **10. Botão menu mobile sem `aria-expanded`/`aria-controls`** — `base.html:117-119`.
- [ ] **11. Sidebar off-canvas focável quando escondida (mobile)** — `sidebar.html:10-12`. Usar `inert`/`aria-hidden`.
- [ ] **12. `<canvas>` (Chart.js) sem alternativa textual** — `dashboard_paineis.html:41`, `analise_paineis.html:44`. `role="img"` + `aria-label` ou tabela oculta.
- [ ] **13. Outline de foco removido nos filtros** — `dashboard_filtros.html`. Repor `focus:ring-2 focus:ring-orange-500`.
- [ ] **14. Landmarks** — top bar mobile → `<header>`; `<nav>` principal com `aria-label="Principal"`. `base.html:116`, `sidebar.html:10`.

## 🟢 Baixa

- [ ] **15. Emojis decorativos sem `aria-hidden`** — `dashboards.html:10,17,24`, `dashboard_paineis.html:44,74`, emojis da navegação. (Exceto a Faixa da Recompra → ver item 1.)
- [ ] **16. Títulos de card do hub como `<div>`** — `dashboards.html:11,18,25`. Promover a `<h2>`.
- [ ] **17. Setas ▲/▼ dos deltas de KPI** — `dashboard_paineis.html:10,19`. `aria-label` ("queda de 88%").

## Sequência sugerida

1. **Quick wins de Alta** (baixo esforço, só template): 1, 3, 5, 6.
2. Depois: 4 (aria-live) e 7 (densidade do Cockpit).
3. Média/Baixa em seguida.

## Referências internas (padrões já corretos)

- Associação de label em `recompra.html` (label envolve o select).
- Estados vazios (`{% else %}`) em todas as tabelas.
- KPIs da Recompra e chips de risco do Cockpit já usam emoji + label + cor (`recompra_paineis.html:7`, `dashboard_paineis.html:76-78`).
- Fonte única `FAIXAS` em `app/recompra_service.py` — já tem o `label` para resolver o item 1.

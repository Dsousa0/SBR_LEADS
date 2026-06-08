# Separar Busca e Mapa (A2) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Separar a tela combinada (busca + mapa em abas) em duas páginas — `/` (Busca) e `/mapa` — que compartilham filtros pela URL e os mesmos cards de resumo.

**Architecture:** Filtros viram querystring (GET). `GET /` e `GET /mapa` leem `request.query_params` via o `_form_to_req` existente, rodam as consultas e renderizam página completa (carga direta) ou parcial (HTMX). Barra de filtros e cards viram parciais compartilhados. O `<script>` monolítico do `resultados.html` é dividido: bloco de **mapa** (Leaflet/geocode/cluster) vai para a página de Mapa; bloco de **tabela+modal** fica na Busca. Sem abas.

**Tech Stack:** FastAPI, Jinja2, HTMX, Leaflet + markercluster. Verificação por smoke autenticado (requests) + suíte pytest como regressão.

---

## Estrutura de arquivos

| Arquivo | Ação | Responsabilidade |
|---|---|---|
| `app/templates/partials/busca_filtros.html` | criar | Barra de filtros (movida do `index.html`), com `hx-get` para a página alvo (variável `pagina`). |
| `app/templates/partials/busca_cards.html` | criar | Cards de resumo do recorte (movidos do `resultados.html`). |
| `app/templates/partials/busca_resultados.html` | criar | Cabeçalho (contagem/ordenação/export) + tabela + paginação + modal + `<script>` de tabela/modal. Parcial trocado pelo HTMX na Busca. |
| `app/templates/partials/mapa_painel.html` | criar | Aviso de limite + `#mapa` + controles (satélite/expandir) + `<script>` de mapa. Parcial trocado pelo HTMX no Mapa. |
| `app/templates/index.html` | reescrever | Página de Busca: inclui filtros + `#conteudo` com os resultados. Form aponta `hx-get="/"`. |
| `app/templates/mapa.html` | criar | Página de Mapa: inclui filtros + `#conteudo` com o painel de mapa. Form aponta `hx-get="/mapa"`. |
| `app/routers/frontend.py` | modificar | `GET /` aceita filtros e renderiza resultados (substitui `POST /buscar`); novo `GET /mapa`. |
| `app/templates/partials/sidebar.html` | modificar | Adicionar item **Mapa**. |
| `app/tests/test_form_to_req.py` | criar | Teste de `_form_to_req` com `QueryParams`. |

Verificação: `docker exec -w /code prospec_app ...` (pytest + smoke autenticado `admin@sbr.local` / `Acesso06597`).

---

## Task 1: `_form_to_req` a partir de querystring (teste de conversão)

O `_form_to_req(form, ...)` usa `form.get(...)`. `starlette.datastructures.QueryParams` tem a mesma interface. Este teste trava esse contrato.

**Files:**
- Create: `app/tests/test_form_to_req.py`

- [ ] **Step 1: Escrever o teste**

```python
from starlette.datastructures import QueryParams

from routers.frontend import _form_to_req


def test_form_to_req_aceita_querystring():
    q = QueryParams("uf=PI&segmento=farmacia&apenas_ativas=true&ordenar=capital_desc&produtos_codigos=A,B")
    req = _form_to_req(q, page=2)
    assert req.uf == "PI"
    assert req.segmento == "farmacia"
    assert req.apenas_ativas is True
    assert req.ordenar == "capital_desc"
    assert req.produtos_codigos == ["A", "B"]
    assert req.page == 2


def test_form_to_req_vazio_usa_padroes():
    req = _form_to_req(QueryParams(""))
    assert req.uf is None
    assert req.apenas_ativas is False  # sem o campo, checkbox desmarcado
    assert req.ordenar == "razao_social_asc"
    assert req.page == 1
```

- [ ] **Step 2: Rodar (deve passar já — contrato existente)**

Run: `docker exec -w /code prospec_app python -m pytest tests/test_form_to_req.py -v`
Expected: 2 passed. (Se falhar, é sinal de que `_form_to_req` depende de algo exclusivo de `FormData` — corrigir para usar só `.get`.)

- [ ] **Step 3: Commit**

```bash
git add app/tests/test_form_to_req.py
git commit -m "test: _form_to_req aceita QueryParams (filtros via URL)"
```

---

## Task 2: Rotas GET / e GET /mapa

**Files:**
- Modify: `app/routers/frontend.py`

Contexto: hoje `GET /` (`pagina_inicial`) só renderiza a tela vazia; `POST /buscar` (`buscar_html`) faz a busca e devolve `resultados.html`. Vamos: (a) `GET /` passa a ler filtros e renderizar resultados; (b) criar `GET /mapa`; (c) remover `POST /buscar`.

Assinaturas reais (conferidas em `service.py`): `buscar(req, db) -> BuscarResponse`; `contar(req, db) -> int`; `buscar_stats(req, db, total: int) -> dict`; `buscar_para_mapa(req, db, limite=5000) -> list[Lead]`. `buscar_stats` retorna um **dict** com chaves `estabelecimentos`, `empresas`, `clientes`, `prospectos`.

- [ ] **Step 1: Ajustar o import de `service` e adicionar os helpers de JSON**

Em `app/routers/frontend.py`, no import do `service`, acrescentar `contar`:

```python
from service import ATALHOS, buscar, buscar_para_mapa, buscar_stats, contar
```

Logo antes da função de rota `/` (onde hoje está `pagina_inicial`), adicionar dois helpers que reproduzem a serialização exata já usada hoje (whitelist de campos + escape de `</` para uso com `| safe`):

```python
def _pagina_json(items) -> str:
    """JSON dos leads da página atual — consumido pelo modal de detalhes."""
    return json.dumps([{
        "cnpj": l.cnpj, "razao_social": l.razao_social, "nome_fantasia": l.nome_fantasia,
        "cnae_principal": l.cnae_principal, "cnae_descricao": l.cnae_descricao,
        "tipo_logradouro": l.tipo_logradouro, "logradouro": l.logradouro, "numero": l.numero,
        "complemento": l.complemento, "bairro": l.bairro, "cep": l.cep, "uf": l.uf,
        "municipio": l.municipio, "ddd_1": l.ddd_1, "telefone_1": l.telefone_1,
        "ddd_2": l.ddd_2, "telefone_2": l.telefone_2, "email": l.email,
        "situacao": l.situacao, "porte": l.porte, "capital_social": l.capital_social,
        "eh_cliente": l.eh_cliente, "vendedor": l.vendedor,
        "ultima_compra_em": l.ultima_compra_em.strftime("%d/%m/%Y") if l.ultima_compra_em else None,
        "dias_sem_compra": l.dias_sem_compra,
    } for l in items], ensure_ascii=False).replace("</", "<\\/")


def _leads_mapa_json(leads) -> str:
    """JSON enxuto dos leads — consumido pelos marcadores do mapa."""
    return json.dumps([{
        "cnpj": l.cnpj, "razao_social": l.razao_social, "nome_fantasia": l.nome_fantasia,
        "logradouro": l.logradouro, "tipo_logradouro": l.tipo_logradouro, "numero": l.numero,
        "municipio": l.municipio, "uf": l.uf, "cep": l.cep, "ddd_1": l.ddd_1,
        "telefone_1": l.telefone_1, "eh_cliente": l.eh_cliente, "vendedor": l.vendedor,
    } for l in leads], ensure_ascii=False).replace("</", "<\\/")
```

- [ ] **Step 2: Substituir `pagina_inicial` e `buscar_html` por `GET /` e `GET /mapa`**

Remover a função `pagina_inicial` (`@router.get("/")`) e a função `buscar_html` (`@router.post("/buscar")`). No lugar, adicionar:

```python
@router.get("/", response_class=HTMLResponse)
def busca(
    request: Request,
    current_user: dict = Depends(require_login),
    db: Session = Depends(get_db),
):
    ufs = [UF(sigla=s, nome=n) for s, n in _UFS]
    atalhos_view = [{"segmento": a["segmento"], "descricao": a["descricao"]} for a in ATALHOS]
    ctx = {"request": request, "user": current_user, "ufs": ufs, "atalhos": atalhos_view}

    if not request.query_params:
        ctx["resultado"] = None
        return templates.TemplateResponse("index.html", ctx)

    page = max(1, int(request.query_params.get("page") or 1))
    req = _form_to_req(request.query_params, page=page)
    resultado = buscar(req, db)
    stats_filtro = buscar_stats(req, db, resultado.total)

    ctx.update({
        "resultado": resultado,
        "stats_filtro": stats_filtro,
        "ordenar_atual": req.ordenar,
        "querystring": str(request.url.query),
        "pagina_json": _pagina_json(resultado.items),
    })

    if request.headers.get("HX-Request"):
        return templates.TemplateResponse("partials/busca_resultados.html", ctx)
    return templates.TemplateResponse("index.html", ctx)


@router.get("/mapa", response_class=HTMLResponse)
def mapa(
    request: Request,
    current_user: dict = Depends(require_login),
    db: Session = Depends(get_db),
):
    ufs = [UF(sigla=s, nome=n) for s, n in _UFS]
    atalhos_view = [{"segmento": a["segmento"], "descricao": a["descricao"]} for a in ATALHOS]
    ctx = {"request": request, "user": current_user, "ufs": ufs, "atalhos": atalhos_view}

    if not request.query_params:
        return templates.TemplateResponse("mapa.html", ctx)

    req = _form_to_req(request.query_params)
    leads_mapa = buscar_para_mapa(req, db, limite=LIMITE_MAPA)
    total = contar(req, db)
    stats_filtro = buscar_stats(req, db, total)

    ctx.update({
        "stats_filtro": stats_filtro,
        "resultado_total": total,
        "querystring": str(request.url.query),
        "total_no_mapa": len(leads_mapa),
        "leads_json": _leads_mapa_json(leads_mapa),
    })

    if request.headers.get("HX-Request"):
        return templates.TemplateResponse("partials/mapa_painel.html", ctx)
    return templates.TemplateResponse("mapa.html", ctx)
```

- [ ] **Step 3: Verificar import/rota**

Run:
```bash
docker exec -w /code prospec_app python -c "import routers.frontend; print('import OK')"
```
Expected: "import OK". (Ainda não há os templates novos — o smoke completo vem nas próximas tasks. Esta etapa só garante que o Python carrega.)

- [ ] **Step 4: Commit**

```bash
git add app/routers/frontend.py
git commit -m "feat: GET / e GET /mapa leem filtros da URL (substitui POST /buscar)"
```

---

## Task 3: Parciais compartilhados — filtros e cards

Mover, sem alterar o visual, a barra de filtros (de `index.html`) e os cards (de `resultados.html`) para parciais reutilizáveis. O form ganha um alvo dinâmico via variável `pagina` (`'/'` ou `'/mapa'`).

**Files:**
- Create: `app/templates/partials/busca_filtros.html`
- Create: `app/templates/partials/busca_cards.html`

- [ ] **Step 1: Criar `busca_cards.html`**

Copiar para o novo arquivo o bloco de cards do `resultados.html` (de `{% set pct_cli = ... %}` até o `</div>` que fecha o `grid grid-cols-2 md:grid-cols-4`, linhas ~68-111 do `resultados.html` atual):

```html
{% set pct_cli = ((stats_filtro.clientes / stats_filtro.estabelecimentos * 100) | round(1)) if stats_filtro.estabelecimentos > 0 else 0 %}
{% set pct_pro = ((stats_filtro.prospectos / stats_filtro.estabelecimentos * 100) | round(1)) if stats_filtro.estabelecimentos > 0 else 0 %}
<div class="grid grid-cols-2 md:grid-cols-4 gap-3">
  <div class="bg-[#171717] rounded-xl border border-[#2e2e2e] p-4 text-center">
    <div class="text-2xl font-bold text-orange-500">{{ "{:,}".format(stats_filtro.estabelecimentos).replace(",", ".") }}</div>
    <div class="text-xs text-[#666] mt-0.5 uppercase tracking-wide">estabelecimentos</div>
  </div>
  <div class="bg-[#171717] rounded-xl border border-[#2e2e2e] p-4 text-center">
    <div class="text-2xl font-bold text-orange-500">{{ "{:,}".format(stats_filtro.empresas).replace(",", ".") }}</div>
    <div class="text-xs text-[#666] mt-0.5 uppercase tracking-wide">empresas</div>
  </div>
  <div class="bg-[#171717] rounded-xl border border-[#2e2e2e] p-4 text-center">
    <div class="text-2xl font-bold text-green-400">{{ "{:,}".format(stats_filtro.clientes).replace(",", ".") }}</div>
    <div class="text-xs text-[#666] mt-0.5 uppercase tracking-wide">clientes {% if pct_cli > 0 %}<span class="text-[#888]/70 ml-1">{{ pct_cli }}%</span>{% endif %}</div>
  </div>
  <div class="bg-[#171717] rounded-xl border border-[#2e2e2e] p-4 text-center">
    <div class="text-2xl font-bold text-[#aaa]">{{ "{:,}".format(stats_filtro.prospectos).replace(",", ".") }}</div>
    <div class="text-xs text-[#666] mt-0.5 uppercase tracking-wide">prospectos {% if pct_pro > 0 %}<span class="text-[#888]/70 ml-1">{{ pct_pro }}%</span>{% endif %}</div>
  </div>
</div>
```

- [ ] **Step 2: Criar `busca_filtros.html`**

Mover o conteúdo do form de filtros do `index.html` (a `<div class="sticky ...">` com o `<form id="filtros">` e todos os campos, incluindo a linha 2 de produto e o JS de produto que vem no `{% block scripts %}`... NÃO — só o markup do form aqui). Copiar do `index.html` o bloco da `<div class="sticky top-0 ...">` até o `</div>` que a fecha (envolve o `<form id="filtros">...</form>`). Alterar APENAS o cabeçalho do form:

De:
```html
    <form id="filtros"
          hx-post="/buscar"
          hx-target="#resultado"
          hx-swap="innerHTML show:#resultado:top"
          hx-indicator="#spinner">
```
Para:
```html
    <form id="filtros"
          hx-get="{{ pagina }}"
          hx-target="#conteudo"
          hx-swap="innerHTML show:window:top"
          hx-push-url="true"
          hx-indicator="#spinner">
```

(O restante do form — segmento, uf, município, porte, status, apenas_ativas, botão Buscar, linha de produto, hidden `produtos_codigos` — permanece idêntico.)

- [ ] **Step 3: Commit**

```bash
git add app/templates/partials/busca_filtros.html app/templates/partials/busca_cards.html
git commit -m "refactor: extrair barra de filtros e cards para parciais compartilhados"
```

---

## Task 4: Parcial de resultados da Busca (tabela + modal)

Criar `busca_resultados.html` a partir do `resultados.html` atual, REMOVENDO o que é do mapa e das abas.

**Files:**
- Create: `app/templates/partials/busca_resultados.html`

- [ ] **Step 1: Montar `busca_resultados.html`**

Estrutura do arquivo (reaproveitando blocos do `resultados.html` atual):

1. Bloco `{% if resultado.total == 0 %}` de estado vazio (linhas ~1-9) — manter.
2. `{% else %}`.
3. Cabeçalho de resultados (contagem + ordenação + export, linhas ~13-66) — manter, **mas** trocar o `hx-post="/buscar"` do `<select name="ordenar">` por `hx-get="/"`, `hx-target="#conteudo"`, `hx-include="#filtros"`, `hx-push-url="true"`, e remover `hx-swap="innerHTML show:#resultado:top"` em favor de `hx-swap="innerHTML show:window:top"`. Adicionar, ao lado dos botões de export, o link **Ver no mapa**:
   ```html
   <a href="/mapa?{{ querystring }}"
      class="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg border border-[#3a3a3a] text-[#aaa] hover:border-orange-500 hover:text-orange-500 transition-colors">
     🗺️ Ver no mapa
   </a>
   ```
4. `{% include "partials/busca_cards.html" %}`.
5. A `<table>` (painel-tabela), linhas ~149-230 — manter SEM o wrapper de abas (`tabs-container`/`abas`/`btns-mapa`) e SEM o `#painel-mapa`. Ou seja: copiar só a `<table>...</table>` dentro de um `<div class="bg-[#171717] rounded-xl border border-[#2e2e2e] overflow-x-auto">`.
6. Paginação (linhas ~251-273) — manter, trocando `hx-post="/buscar"` por `hx-get="/"`, `hx-target="#conteudo"`, `hx-include="#filtros"`, `hx-push-url="true"`.
7. Modal de cliente (linhas ~276-301) — manter.
8. `<script>` — manter APENAS as partes de tabela/modal: `_e`, `_fmtCnpj`, `_secao`, `_linha`, `_porteNomes`, `_situacaoNomes`, `abrirModalCliente`, `fecharModalCliente`, o handler de clique em `tr[data-cnpj]`, e o handler de ESC do modal (`_pmEscModalBound`). A var `paginaLeads` vem de `{{ pagina_json | safe }}`. **Remover** todo o bloco de mapa (geocode, `mostrarAba`, `alternarMapaExpandido`, `alternarCamadaMapa`, `iniciarMapa`, `_icone`, `_resolverCoords`, etc.) — isso vai para o mapa.
9. `{% endif %}`.

> Como o modal usa só `paginaLeads`, o `<script>` da Busca deve iniciar com `const paginaLeads = {{ pagina_json | safe }};` (sem `leads`).

- [ ] **Step 2: Commit**

```bash
git add app/templates/partials/busca_resultados.html
git commit -m "feat: parcial de resultados da Busca (tabela + modal, sem abas/mapa)"
```

---

## Task 5: Página de Busca (index.html) reescrita

**Files:**
- Modify: `app/templates/index.html`

- [ ] **Step 1: Reescrever `index.html`**

```html
{% extends "base.html" %}

{% block title %}SBR Leads — Busca de Leads{% endblock %}

{% block content %}
<div class="space-y-4">
  {% set pagina = "/" %}
  {% include "partials/busca_filtros.html" %}

  <div id="conteudo">
    {% if resultado %}
      {% include "partials/busca_resultados.html" %}
    {% else %}
      <div class="bg-[#171717] rounded-xl border border-[#2e2e2e] p-12 text-center text-[#555]">
        <svg class="w-12 h-12 mx-auto mb-3 opacity-30" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
            d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
        </svg>
        <p class="font-medium text-[#666]">Use os filtros e clique em Buscar</p>
      </div>
    {% endif %}
  </div>
</div>
{% endblock %}

{% block scripts %}
<script>
function exportar(formato) {
  const form = document.getElementById('filtros');
  const dados = new FormData(form);
  fetch('/exportar.' + formato, { method: 'POST', body: dados })
    .then(r => r.blob())
    .then(blob => {
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'leads.' + formato;
      a.click();
      URL.revokeObjectURL(url);
    });
}
</script>
{% include "partials/produto_filtro_js.html" %}
{% endblock %}
```

> A função `exportar` e o JS do filtro de produto estavam no `{% block scripts %}` do `index.html` atual. O JS de produto (variáveis `_produtosSelecionados`, `toggleMenuProdutos`, `selecionarProduto`, `removerProduto`, `_renderProdutos`, etc.) deve ser extraído para `partials/produto_filtro_js.html` (Step 2) para ser reusado também no Mapa.

- [ ] **Step 2: Extrair o JS do filtro de produto para um parcial**

Create `app/templates/partials/produto_filtro_js.html` movendo o `<script>` do filtro de produto que hoje está no fim do `index.html` (todo o bloco `// ---- Filtro de produto ----` com `_produtosSelecionados`, `toggleMenuProdutos`, `selecionarProduto`, `removerProduto`, `_atualizarChecks`, `_renderProdutos`, os listeners de `htmx:afterSettle`, `DOMContentLoaded`, e o clique fora). Envolver em `<script> ... </script>`.

- [ ] **Step 3: Verificar a Busca (smoke autenticado)**

Run:
```bash
docker exec -w /code prospec_app python - <<'PY'
import requests
s = requests.Session()
s.post("http://localhost:8000/login", data={"email":"admin@sbr.local","senha":"Acesso06597"}, allow_redirects=False)
# tela inicial
r0 = s.get("http://localhost:8000/")
assert r0.status_code == 200 and 'id="filtros"' in r0.text and 'id="conteudo"' in r0.text
# busca com filtro (pagina completa)
r1 = s.get("http://localhost:8000/?uf=PI&apenas_ativas=true")
assert r1.status_code == 200 and "Ver no mapa" in r1.text, r1.status_code
# parcial HTMX
r2 = s.get("http://localhost:8000/?uf=PI&apenas_ativas=true", headers={"HX-Request":"true"})
assert r2.status_code == 200 and "<html" not in r2.text
print("BUSCA OK", len(r1.text), len(r2.text))
PY
```
Expected: "BUSCA OK ...".

- [ ] **Step 4: Commit**

```bash
git add app/templates/index.html app/templates/partials/produto_filtro_js.html
git commit -m "feat: pagina de Busca com filtros na URL e conteudo via HTMX"
```

---

## Task 6: Painel e página de Mapa

**Files:**
- Create: `app/templates/partials/mapa_painel.html`
- Create: `app/templates/mapa.html`

- [ ] **Step 1: Criar `mapa_painel.html`**

Estrutura:

1. `{% include "partials/busca_cards.html" %}` (mesmos cards).
2. Link **Ver lista**:
   ```html
   <div class="flex justify-end">
     <a href="/?{{ querystring }}"
        class="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg border border-[#3a3a3a] text-[#aaa] hover:border-orange-500 hover:text-orange-500 transition-colors">
       📋 Ver lista
     </a>
   </div>
   ```
3. Container do mapa + controles (satélite/expandir), adaptado do `resultados.html` (linhas ~113-147 e 233-247), num só painel sempre visível (sem abas):
   ```html
   <div id="tabs-container" class="bg-[#171717] rounded-xl border border-[#2e2e2e] overflow-hidden">
     <div class="border-b border-[#2e2e2e] flex items-center justify-end gap-2 px-3 py-2" id="btns-mapa">
       <button onclick="alternarCamadaMapa()" id="btn-satelite" type="button"
               class="text-xs px-3 py-1.5 rounded-lg border border-[#3a3a3a] text-[#aaa] hover:border-orange-500 hover:text-orange-500 transition-colors flex items-center gap-1.5">
         <span id="lbl-satelite">Satélite</span>
       </button>
       <button onclick="alternarMapaExpandido()" id="btn-expandir-mapa" type="button"
               class="text-xs px-3 py-1.5 rounded-lg border border-[#3a3a3a] text-[#aaa] hover:border-orange-500 hover:text-orange-500 transition-colors flex items-center gap-1.5">
         <span id="lbl-expandir">Expandir</span>
       </button>
     </div>
     <div id="painel-mapa">
       {% if total_no_mapa is defined and resultado_total > total_no_mapa %}
       <div class="bg-[#1a1a1a] text-[#888] text-xs px-4 py-2 border-b border-[#2e2e2e]">
         Mostrando os primeiros {{ "{:,}".format(total_no_mapa).replace(",", ".") }} de
         {{ "{:,}".format(resultado_total).replace(",", ".") }} resultados no mapa (refine os filtros para ver todos).
       </div>
       {% endif %}
       <div id="mapa"></div>
     </div>
   </div>
   ```
4. `<script>` do mapa: mover do `resultados.html` o bloco de mapa — `const leads = {{ leads_json | safe }};`, as constantes de geocode, `_esc`, `_icone`, `_cacheGet/_cacheSet`, `_dentroBrasil`, `_norm`, `_cidadeOk`, `_coordsPorEndereco`, `_coordsPorCep`, `_resolverCoords`, `_comConcorrencia`, `alternarMapaExpandido`, `_atualizarBtnSatelite`, `alternarCamadaMapa`, o handler de ESC do expandido (`_pmEscBound`), e `iniciarMapa`. **Remover** `mostrarAba` (não há abas). No fim do script, em vez do "re-abre se o painel-mapa estava visível", chamar o mapa direto:
   ```javascript
   if (document.getElementById('mapa')) window.iniciarMapa();
   ```
   Envolver tudo numa IIFE `(function () { ... })();`.

- [ ] **Step 2: Criar `mapa.html`**

```html
{% extends "base.html" %}

{% block title %}SBR Leads — Mapa{% endblock %}

{% block content %}
<div class="space-y-4">
  {% set pagina = "/mapa" %}
  {% include "partials/busca_filtros.html" %}

  <div id="conteudo">
    {% if resultado is not none and stats_filtro is defined %}
      {% include "partials/mapa_painel.html" %}
    {% else %}
      <div class="bg-[#171717] rounded-xl border border-[#2e2e2e] p-12 text-center text-[#555]">
        <svg class="w-12 h-12 mx-auto mb-3 opacity-30" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
            d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"/>
        </svg>
        <p class="font-medium text-[#666]">Use os filtros e clique em Buscar para ver os leads no mapa</p>
      </div>
    {% endif %}
  </div>
</div>
{% endblock %}

{% block scripts %}
{% include "partials/produto_filtro_js.html" %}
{% endblock %}
```

> Nota: na rota `/mapa`, quando há querystring, o contexto define `stats_filtro` (e não define `resultado`). O guard `{% if stats_filtro is defined %}` decide renderizar o painel. Ajustar o guard do `mapa.html` para `{% if stats_filtro is defined %}` (remover a referência a `resultado`, que não existe no contexto do mapa).

- [ ] **Step 3: Corrigir o guard do mapa.html**

Trocar no `mapa.html`:
```html
    {% if resultado is not none and stats_filtro is defined %}
```
por:
```html
    {% if stats_filtro is defined %}
```

- [ ] **Step 4: Verificar o Mapa (smoke autenticado)**

Run:
```bash
docker exec -w /code prospec_app python - <<'PY'
import requests
s = requests.Session()
s.post("http://localhost:8000/login", data={"email":"admin@sbr.local","senha":"Acesso06597"}, allow_redirects=False)
r0 = s.get("http://localhost:8000/mapa")
assert r0.status_code == 200 and 'id="filtros"' in r0.text
r1 = s.get("http://localhost:8000/mapa?uf=PI&apenas_ativas=true")
assert r1.status_code == 200 and 'id="mapa"' in r1.text and "Ver lista" in r1.text, r1.status_code
assert "/?uf=PI" in r1.text or "/?" in r1.text  # link de volta para a busca
print("MAPA OK", len(r1.text))
PY
```
Expected: "MAPA OK ...".

- [ ] **Step 5: Commit**

```bash
git add app/templates/partials/mapa_painel.html app/templates/mapa.html
git commit -m "feat: pagina de Mapa com filtros na URL e atalho Ver lista"
```

---

## Task 7: Item Mapa no menu lateral

**Files:**
- Modify: `app/templates/partials/sidebar.html`

- [ ] **Step 1: Adicionar o item Mapa**

No `sidebar.html`, logo após o item "Busca de Leads", inserir:

```html
    {{ item('/mapa', '🗺️', 'Mapa', path == '/mapa') }}
```

- [ ] **Step 2: Verificar**

Run:
```bash
docker exec -w /code prospec_app python - <<'PY'
import requests
s = requests.Session()
s.post("http://localhost:8000/login", data={"email":"admin@sbr.local","senha":"Acesso06597"}, allow_redirects=False)
r = s.get("http://localhost:8000/mapa?uf=PI")
assert 'href="/mapa"' in r.text and ">Mapa<" in r.text, "item Mapa ausente"
print("MENU OK")
PY
```
Expected: "MENU OK".

- [ ] **Step 3: Commit**

```bash
git add app/templates/partials/sidebar.html
git commit -m "feat: item Mapa no menu lateral"
```

---

## Task 8: Limpeza e validação final

**Files:**
- Delete: `app/templates/partials/resultados.html` (se não houver mais referências)

- [ ] **Step 1: Conferir que `resultados.html` não é mais referenciado**

Run: `docker exec -w /code prospec_app grep -rn "resultados.html" templates routers || echo "sem referencias"`
Expected: "sem referencias". Se aparecer alguma, ajustar antes de apagar.

- [ ] **Step 2: Remover o `resultados.html` órfão**

Run: `docker exec -w /code prospec_app rm templates/partials/resultados.html`

- [ ] **Step 3: Suíte pytest (regressão)**

Run: `docker exec -w /code prospec_app python -m pytest -q`
Expected: 26 passed (24 anteriores + 2 de `_form_to_req`).

- [ ] **Step 4: Smoke autenticado ponta a ponta**

Run:
```bash
docker exec -w /code prospec_app python - <<'PY'
import requests
s = requests.Session()
s.post("http://localhost:8000/login", data={"email":"admin@sbr.local","senha":"Acesso06597"}, allow_redirects=False)
qs = "uf=PI&apenas_ativas=true&segmento=farmacia"
# Busca -> tem link pro mapa com os MESMOS filtros
b = s.get("http://localhost:8000/?"+qs)
assert b.status_code == 200 and f"/mapa?{qs}".split("&")[0] in b.text
# Mapa -> mesmos filtros, link de volta
m = s.get("http://localhost:8000/mapa?"+qs)
assert m.status_code == 200 and 'id="mapa"' in m.text
# Export ainda funciona (POST com form)
e = s.post("http://localhost:8000/exportar.csv", data={"uf":"PI","apenas_ativas":"true","ordenar":"razao_social_asc"})
assert e.status_code == 200
for u in ["/inicio","/","/mapa?uf=PI","/dashboard","/dashboards","/configuracoes"]:
    assert s.get("http://localhost:8000"+u).status_code == 200, u
print("E2E OK")
PY
```
Expected: "E2E OK".

- [ ] **Step 5: Commit e push**

```bash
git add -A
git commit -m "chore: remover resultados.html orfao (substituido por busca_resultados/mapa_painel)"
git push origin main
```

---

## Notas de implementação

- **Desvio consciente do spec — modal só na Busca:** o spec citava um `cliente_modal.html` compartilhado, mas hoje o modal só abre pelo clique na linha da **tabela** (marcadores do mapa têm apenas tooltip). Mantenho o modal na Busca (`busca_resultados.html`), sem `cliente_modal.html` separado — preserva o comportamento atual e reduz risco. "Marcador do mapa abre o modal" fica como possível melhoria futura.
- **Risco principal:** a divisão do `<script>` monolítico do `resultados.html`. Estratégia: o bloco de **mapa** (geocode/Leaflet/cluster + controles) vai inteiro para `mapa_painel.html`; o bloco de **tabela/modal** vai para `busca_resultados.html`. `mostrarAba` e a lógica de abas são removidas. Verificar no navegador (não só no smoke HTTP) que o mapa renderiza marcadores e o modal abre ao clicar numa linha.
- `_form_to_req` é reutilizado para form (export POST) e querystring (GET) — mesma interface `.get`.
- Export segue em `POST /exportar.csv|xlsx` lendo o form; sem mudança.
- Serialização dos leads preservada exatamente (whitelist + `.replace("</", "<\\/")` + `| safe`), igual ao código atual — não trocar por `model_dump`/`tojson` para não mudar o shape que o JS do mapa/modal espera (ex.: `ultima_compra_em` pré-formatado em `%d/%m/%Y`).
- Próximo: B — Dashboard de Análise de Vendas (card "Disponível" no hub).
```

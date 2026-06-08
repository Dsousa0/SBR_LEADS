# Casca de Navegação + Hub de Dashboards (A1) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Substituir o cabeçalho superior por um menu lateral fixo e adicionar as páginas Início, Hub de Dashboards e Configurações, movendo o sync do Pedido Mobile para Configurações.

**Architecture:** Mudança de chrome (layout) + rotas de páginas, sem mudança de dados. `base.html` vira casca com `<aside>` (sidebar) + `<main>`, renderizando o sidebar só quando há `user`. Item ativo via `request.url.path`. Páginas novas num router `routers/navegacao.py`. Busca (`/`) permanece; separação Busca/Mapa é o A2.

**Tech Stack:** FastAPI, Jinja2, HTMX, TailwindCSS (CDN). Verificação por smoke autenticado (requests) no container, além da suíte pytest existente como regressão.

---

## Estrutura de arquivos

| Arquivo | Ação | Responsabilidade |
|---|---|---|
| `app/templates/partials/sidebar.html` | criar | Menu lateral: marca, navegação com item ativo, seção admin, usuário + Sair. |
| `app/templates/base.html` | modificar | Casca flex: sidebar + main; topbar mobile com hambúrguer; sidebar só com `user`. |
| `app/routers/navegacao.py` | criar | Rotas `GET /inicio`, `/dashboards`, `/configuracoes` + helpers `_get_stats`, `_info_pedido_mobile` (movidos do frontend). |
| `app/templates/inicio.html` | criar | Home enxuta: saudação + atalhos + status de sync. |
| `app/templates/dashboards.html` | criar | Hub: cards de dashboards. |
| `app/templates/configuracoes.html` | criar | Sync do Pedido Mobile + infos da base. |
| `app/main.py` | modificar | Registrar `navegacao_router`. |
| `app/routers/frontend.py` | modificar | Remover `_get_stats`/`_info_pedido_mobile` (movidos) e simplificar `pagina_inicial` (sem stats/pm). |
| `app/templates/index.html` | modificar | Remover bloco de stats e card de sync; ajustar sticky dos filtros. |
| `app/templates/partials/dashboard_filtros.html` | modificar | Ajustar sticky `top-[53px]` → `top-0`. |

Comando de verificação: `docker exec -w /code prospec_app ...` (pytest e smoke autenticado com `admin@sbr.local` / `Acesso06597`).

---

## Task 1: Sidebar + casca no base.html

**Files:**
- Create: `app/templates/partials/sidebar.html`
- Modify: `app/templates/base.html`

- [ ] **Step 1: Criar o partial do sidebar**

Create `app/templates/partials/sidebar.html`:

```html
{% set path = request.url.path %}
{% macro item(href, icon, label, ativo) %}
<a href="{{ href }}"
   class="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors
          {% if ativo %}bg-orange-500/12 text-orange-500 font-semibold{% else %}text-[#888] hover:bg-[#1a1a1a] hover:text-[#ccc]{% endif %}">
  <span class="w-4 text-center">{{ icon }}</span> {{ label }}
</a>
{% endmacro %}

<aside id="sidebar"
       class="fixed lg:static inset-y-0 left-0 z-40 w-56 flex-shrink-0 bg-[#0f0f0f] border-r border-[#2e2e2e]
              flex flex-col -translate-x-full lg:translate-x-0 transition-transform duration-200">
  <a href="/inicio" class="flex items-center gap-2 px-4 py-4">
    <span class="text-orange-500 font-black text-lg tracking-tight">SBR</span>
    <span class="text-white font-light text-lg tracking-widest">Leads</span>
  </a>

  <nav class="flex-1 px-2 space-y-1 overflow-y-auto">
    {{ item('/inicio', '🏠', 'Início', path == '/inicio') }}
    {{ item('/', '🔎', 'Busca de Leads', path == '/') }}
    {{ item('/dashboards', '📊', 'Dashboards', path.startswith('/dashboard')) }}
    <div class="h-px bg-[#1e1e1e] my-2 mx-2"></div>
    <div class="text-[9px] uppercase tracking-wider text-[#444] px-3 py-1">Administração</div>
    {% if user.role == 'admin' %}
    {{ item('/admin/usuarios', '👥', 'Usuários', path.startswith('/admin')) }}
    {% endif %}
    {{ item('/configuracoes', '⚙️', 'Configurações', path == '/configuracoes') }}
  </nav>

  <div class="border-t border-[#1e1e1e] p-3 flex items-center justify-between">
    <span class="text-xs text-[#777] truncate">{{ user.nome }}</span>
    <a href="/logout" class="text-xs text-[#555] hover:text-[#999]">Sair</a>
  </div>
</aside>
```

- [ ] **Step 2: Reestruturar o body do base.html**

Em `app/templates/base.html`, substituir todo o bloco do `<body>` (das linhas do `<body ...>` até `</body>`) por:

```html
<body class="min-h-screen">
{% if user is defined and user %}
  <div class="flex min-h-screen">
    {% include "partials/sidebar.html" %}
    <div class="flex-1 min-w-0 flex flex-col">
      <div class="lg:hidden sticky top-0 z-30 bg-[#0f0f0f] border-b border-[#2e2e2e] flex items-center gap-3 px-4 py-3">
        <button type="button" aria-label="Menu"
                onclick="document.getElementById('sidebar').classList.toggle('-translate-x-full')"
                class="text-[#999] text-xl leading-none">&#9776;</button>
        <span class="text-orange-500 font-black tracking-tight">SBR</span>
        <span class="text-white font-light tracking-widest">Leads</span>
      </div>
      <main class="flex-1 p-5">
        {% block content %}{% endblock %}
      </main>
    </div>
  </div>
{% else %}
  <main class="max-w-7xl mx-auto px-5 py-5">
    {% block content %}{% endblock %}
  </main>
{% endif %}

  {% block scripts %}{% endblock %}
</body>
```

- [ ] **Step 3: Verificar (smoke autenticado)**

Run:

```bash
docker exec -w /code prospec_app python - <<'PY'
import requests
s = requests.Session()
s.post("http://localhost:8000/login", data={"email":"admin@sbr.local","senha":"Acesso06597"}, allow_redirects=False)
r = s.get("http://localhost:8000/dashboard")
assert r.status_code == 200, r.status_code
assert 'id="sidebar"' in r.text, "sidebar ausente"
assert "Busca de Leads" in r.text and "Configurações" in r.text, "itens do menu ausentes"
print("SIDEBAR OK", len(r.text))
PY
```
Expected: "SIDEBAR OK ...".

- [ ] **Step 4: Commit**

```bash
git add app/templates/partials/sidebar.html app/templates/base.html
git commit -m "feat: menu lateral substituindo o header (casca de navegacao)"
```

---

## Task 2: Router de navegação + páginas Início, Dashboards, Configurações

**Files:**
- Create: `app/routers/navegacao.py`
- Create: `app/templates/inicio.html`
- Create: `app/templates/dashboards.html`
- Create: `app/templates/configuracoes.html`
- Modify: `app/main.py`

- [ ] **Step 1: Criar o router (movendo os helpers do frontend)**

Create `app/routers/navegacao.py`:

```python
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from auth import require_login
from database import get_db
from pedido_mobile import sync_em_andamento, total_clientes, ultima_sync
from schemas import Stats

router = APIRouter()
templates = Jinja2Templates(directory="templates")


def _get_stats(db: Session) -> Stats:
    try:
        total_estab = db.execute(text("SELECT COUNT(*) FROM estabelecimento")).scalar() or 0
        total_emp = db.execute(text("SELECT COUNT(*) FROM empresa")).scalar() or 0
        ultima = db.execute(
            text("SELECT mes_referencia FROM importacao WHERE status='concluido' ORDER BY concluida_em DESC LIMIT 1")
        ).scalar()
    except ProgrammingError:
        db.rollback()
        return Stats(total_estabelecimentos=0, total_empresas=0, ultima_importacao=None, distribuicao_uf=[])
    return Stats(
        total_estabelecimentos=total_estab,
        total_empresas=total_emp,
        ultima_importacao=ultima,
        distribuicao_uf=[],
    )


def _info_pedido_mobile(db: Session) -> dict:
    try:
        return {"total": total_clientes(db), "ultima": ultima_sync(db)}
    except Exception:
        db.rollback()
        return {"total": 0, "ultima": None}


@router.get("/inicio", response_class=HTMLResponse)
def inicio(request: Request, current_user: dict = Depends(require_login), db: Session = Depends(get_db)):
    return templates.TemplateResponse("inicio.html", {
        "request": request, "user": current_user, "pm": _info_pedido_mobile(db),
    })


@router.get("/dashboards", response_class=HTMLResponse)
def dashboards(request: Request, current_user: dict = Depends(require_login)):
    return templates.TemplateResponse("dashboards.html", {
        "request": request, "user": current_user,
    })


@router.get("/configuracoes", response_class=HTMLResponse)
def configuracoes(request: Request, current_user: dict = Depends(require_login), db: Session = Depends(get_db)):
    return templates.TemplateResponse("configuracoes.html", {
        "request": request, "user": current_user,
        "stats": _get_stats(db),
        "pm": _info_pedido_mobile(db),
        "sincronizando": sync_em_andamento(db),
        "resultado": None,
        "erro": None,
    })
```

- [ ] **Step 2: Criar inicio.html**

Create `app/templates/inicio.html`:

```html
{% extends "base.html" %}
{% block title %}Início{% endblock %}
{% block content %}
<div class="space-y-6 max-w-5xl">
  <div>
    <h1 class="text-2xl font-bold text-white">Olá, {{ user.nome }}</h1>
    <p class="text-[#888] text-sm mt-1">Bem-vindo ao SBR Leads. Por onde quer começar?</p>
  </div>

  <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
    <a href="/" class="bg-[#171717] border border-[#2e2e2e] rounded-xl p-5 hover:border-orange-500 transition-colors group">
      <div class="text-2xl">🔎</div>
      <div class="text-white font-semibold mt-2 group-hover:text-orange-500">Busca de Leads</div>
      <div class="text-[#888] text-xs mt-1">Empresas por segmento, cidade e produto.</div>
    </a>
    <a href="/dashboards" class="bg-[#171717] border border-[#2e2e2e] rounded-xl p-5 hover:border-orange-500 transition-colors group">
      <div class="text-2xl">📊</div>
      <div class="text-white font-semibold mt-2 group-hover:text-orange-500">Dashboards</div>
      <div class="text-[#888] text-xs mt-1">Painéis comerciais e de análise.</div>
    </a>
    <a href="/configuracoes" class="bg-[#171717] border border-[#2e2e2e] rounded-xl p-5 hover:border-orange-500 transition-colors group">
      <div class="text-2xl">⚙️</div>
      <div class="text-white font-semibold mt-2 group-hover:text-orange-500">Configurações</div>
      <div class="text-[#888] text-xs mt-1">Sincronização e dados da base.</div>
    </a>
  </div>

  <div class="bg-[#171717] border border-[#2e2e2e] rounded-xl p-5">
    <div class="text-sm font-semibold text-white mb-1">Pedido Mobile</div>
    {% if pm.ultima %}
    <div class="text-[#888] text-sm">
      Última sincronização: {{ pm.ultima.concluida_em.strftime('%d/%m/%Y %H:%M') if pm.ultima.concluida_em else '—' }}
      · {{ pm.total }} clientes
    </div>
    {% else %}
    <div class="text-[#888] text-sm">Nunca sincronizado.</div>
    {% endif %}
    <a href="/configuracoes" class="text-orange-500 text-xs mt-2 inline-block hover:text-orange-400">Ir para Configurações →</a>
  </div>
</div>
{% endblock %}
```

- [ ] **Step 3: Criar dashboards.html**

Create `app/templates/dashboards.html`:

```html
{% extends "base.html" %}
{% block title %}Dashboards{% endblock %}
{% block content %}
<div class="max-w-5xl">
  <h1 class="text-xl font-bold text-white">Dashboards</h1>
  <p class="text-[#888] text-sm mt-1 mb-5">Escolha um painel para abrir.</p>

  <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
    <a href="/dashboard" class="bg-[#171717] border border-[#2e2e2e] rounded-xl p-5 hover:border-orange-500 hover:-translate-y-0.5 transition-all group">
      <div class="text-2xl">🏆</div>
      <div class="text-white font-semibold mt-2 group-hover:text-orange-500">Cockpit do Gestor</div>
      <div class="text-[#888] text-xs mt-1 leading-relaxed">Ranking de vendedores, KPIs comparados, clientes em risco e concentração da carteira.</div>
      <span class="inline-block mt-3 text-[9px] px-2 py-0.5 rounded-full bg-green-500/12 text-green-400">Disponível</span>
    </a>

    <div class="bg-[#171717] border border-[#2e2e2e] rounded-xl p-5 opacity-60 cursor-not-allowed">
      <div class="text-2xl">📈</div>
      <div class="text-white font-semibold mt-2">Análise de Vendas</div>
      <div class="text-[#888] text-xs mt-1 leading-relaxed">Curva ABC de produtos, representadas, mix e sazonalidade.</div>
      <span class="inline-block mt-3 text-[9px] px-2 py-0.5 rounded-full bg-yellow-500/10 text-yellow-400">Em breve</span>
    </div>
  </div>
</div>
{% endblock %}
```

- [ ] **Step 4: Criar configuracoes.html**

Create `app/templates/configuracoes.html`:

```html
{% extends "base.html" %}
{% block title %}Configurações{% endblock %}
{% block content %}
<div class="space-y-5 max-w-5xl">
  <h1 class="text-xl font-bold text-white">Configurações</h1>

  {% include "partials/pedido_mobile_card.html" %}

  <div>
    <div class="text-sm font-semibold text-white mb-2">Base da Receita Federal</div>
    <div class="grid grid-cols-3 gap-3">
      <div class="bg-[#171717] rounded-xl border border-[#2e2e2e] p-4 text-center">
        <div class="text-2xl font-bold text-orange-500">{{ "{:,}".format(stats.total_estabelecimentos).replace(",", ".") }}</div>
        <div class="text-xs text-[#666] mt-0.5 uppercase tracking-wide">estabelecimentos</div>
      </div>
      <div class="bg-[#171717] rounded-xl border border-[#2e2e2e] p-4 text-center">
        <div class="text-2xl font-bold text-orange-500">{{ "{:,}".format(stats.total_empresas).replace(",", ".") }}</div>
        <div class="text-xs text-[#666] mt-0.5 uppercase tracking-wide">empresas</div>
      </div>
      <div class="bg-[#171717] rounded-xl border border-[#2e2e2e] p-4 text-center">
        <div class="text-2xl font-bold text-orange-500">{{ stats.ultima_importacao or "—" }}</div>
        <div class="text-xs text-[#666] mt-0.5 uppercase tracking-wide">última atualização</div>
      </div>
    </div>
  </div>
</div>
{% endblock %}
```

- [ ] **Step 5: Registrar o router no main.py**

Em `app/main.py`, adicionar o import junto aos outros routers:

```python
from routers.navegacao import router as navegacao_router
```

E registrar (junto aos outros `app.include_router(...)`):

```python
app.include_router(navegacao_router)
```

- [ ] **Step 6: Verificar (smoke autenticado)**

Run:

```bash
docker exec -w /code prospec_app python - <<'PY'
import requests
s = requests.Session()
s.post("http://localhost:8000/login", data={"email":"admin@sbr.local","senha":"Acesso06597"}, allow_redirects=False)
for u, marca in [("/inicio","Olá,"), ("/dashboards","Cockpit do Gestor"), ("/configuracoes","Base da Receita")]:
    r = s.get("http://localhost:8000"+u)
    assert r.status_code == 200, (u, r.status_code)
    assert marca in r.text, (u, "marcador ausente")
    assert 'id="sidebar"' in r.text, (u, "sem sidebar")
    print("OK", u, len(r.text))
PY
```
Expected: 3 linhas "OK".

- [ ] **Step 7: Commit**

```bash
git add app/routers/navegacao.py app/templates/inicio.html app/templates/dashboards.html app/templates/configuracoes.html app/main.py
git commit -m "feat: paginas Inicio, Hub de Dashboards e Configuracoes"
```

---

## Task 3: Limpar a Busca (remover stats e sync, que foram para Configurações)

**Files:**
- Modify: `app/routers/frontend.py`
- Modify: `app/templates/index.html`

- [ ] **Step 1: Remover os helpers movidos e simplificar `pagina_inicial`**

Em `app/routers/frontend.py`:

a) Remover as funções `_get_stats` e `_info_pedido_mobile` (foram para `routers/navegacao.py`).

b) Ajustar imports: após remover `_get_stats`, ficam sem uso em `frontend.py` o import de `Stats` (de `schemas`) e `ProgrammingError` (de `sqlalchemy.exc`) — removê-los. Também remover de `from pedido_mobile import ...` os nomes `total_clientes` e `ultima_sync` (usados só por `_info_pedido_mobile`, que saiu); manter `SyncError`, `sincronizar`, `sync_em_andamento` (ainda usados pelos endpoints de sync). A verificação de import no Step 3 confirma que não sobrou referência quebrada.

c) Substituir a função `pagina_inicial` por:

```python
@router.get("/", response_class=HTMLResponse)
def pagina_inicial(
    request: Request,
    current_user: dict = Depends(require_login),
    db: Session = Depends(get_db),
):
    ufs = [UF(sigla=s, nome=n) for s, n in _UFS]
    atalhos_view = [{"segmento": a["segmento"], "descricao": a["descricao"]} for a in ATALHOS]
    return templates.TemplateResponse("index.html", {
        "request": request,
        "user": current_user,
        "ufs": ufs,
        "atalhos": atalhos_view,
    })
```

- [ ] **Step 2: Remover o bloco de stats e o card de sync do index.html**

Em `app/templates/index.html`, remover **todo** o bloco de stats rápidas e o include do card de sync (atualmente entre o fim do `</form>`/`</div>` dos filtros e o `<div id="resultado">`):

Remover este trecho:

```html
  <!-- ========= STATS RÁPIDAS ========= -->
  <div class="grid grid-cols-3 gap-3">
    <div class="bg-[#171717] rounded-xl border border-[#2e2e2e] p-4 text-center">
      <div class="text-2xl font-bold text-orange-500">{{ "{:,}".format(stats.total_estabelecimentos).replace(",", ".") }}</div>
      <div class="text-xs text-[#666] mt-0.5 uppercase tracking-wide">estabelecimentos</div>
    </div>
    <div class="bg-[#171717] rounded-xl border border-[#2e2e2e] p-4 text-center">
      <div class="text-2xl font-bold text-orange-500">{{ "{:,}".format(stats.total_empresas).replace(",", ".") }}</div>
      <div class="text-xs text-[#666] mt-0.5 uppercase tracking-wide">empresas</div>
    </div>
    <div class="bg-[#171717] rounded-xl border border-[#2e2e2e] p-4 text-center">
      <div class="text-2xl font-bold text-orange-500">{{ stats.ultima_importacao or "—" }}</div>
      <div class="text-xs text-[#666] mt-0.5 uppercase tracking-wide">última atualização</div>
    </div>
  </div>

  <!-- ========= PEDIDO MOBILE ========= -->
  {% include "partials/pedido_mobile_card.html" %}
```

(O `<div id="resultado">` e tudo abaixo permanecem.)

- [ ] **Step 3: Verificar (import + smoke da busca)**

Run:

```bash
docker exec -w /code prospec_app python -c "import importlib, routers.frontend, routers.navegacao; print('imports OK')"
docker exec -w /code prospec_app python - <<'PY'
import requests
s = requests.Session()
s.post("http://localhost:8000/login", data={"email":"admin@sbr.local","senha":"Acesso06597"}, allow_redirects=False)
r = s.get("http://localhost:8000/")
assert r.status_code == 200, r.status_code
assert "pm-card" not in r.text, "card de sync ainda esta na busca"
assert 'id="sidebar"' in r.text, "sem sidebar"
# a busca em si ainda funciona
b = s.post("http://localhost:8000/buscar", data={"uf":"", "segmento":"", "ordenar":"razao_social_asc"})
assert b.status_code == 200, b.status_code
print("BUSCA OK", len(r.text))
PY
```
Expected: "imports OK" e "BUSCA OK ...".

- [ ] **Step 4: Commit**

```bash
git add app/routers/frontend.py app/templates/index.html
git commit -m "refactor: mover stats e sync da busca para Configuracoes"
```

---

## Task 4: Ajustar sticky dos filtros (header antigo não existe mais)

**Files:**
- Modify: `app/templates/index.html`
- Modify: `app/templates/partials/dashboard_filtros.html`

- [ ] **Step 1: Ajustar o sticky da busca**

Em `app/templates/index.html`, na div dos filtros, trocar `sticky top-[53px]` por `sticky top-0`:

De:
```html
  <div class="sticky top-[53px] z-20 -mx-5 px-5 py-3 bg-[#111] border-b border-[#2a2a2a] shadow-[0_4px_24px_rgba(0,0,0,0.6)]">
```
Para:
```html
  <div class="sticky top-0 z-20 -mx-5 px-5 py-3 bg-[#111] border-b border-[#2a2a2a] shadow-[0_4px_24px_rgba(0,0,0,0.6)]">
```

- [ ] **Step 2: Ajustar o sticky do cockpit**

Em `app/templates/partials/dashboard_filtros.html`, na tag `<form>`, trocar `sticky top-[53px]` por `sticky top-0`:

De:
```html
      class="sticky top-[53px] z-20 -mx-5 px-5 py-3 bg-[#111] border-b border-[#2a2a2a] flex flex-wrap items-end gap-2.5">
```
Para:
```html
      class="sticky top-0 z-20 -mx-5 px-5 py-3 bg-[#111] border-b border-[#2a2a2a] flex flex-wrap items-end gap-2.5">
```

- [ ] **Step 3: Verificar**

Run:

```bash
docker exec -w /code prospec_app python - <<'PY'
import requests
s = requests.Session()
s.post("http://localhost:8000/login", data={"email":"admin@sbr.local","senha":"Acesso06597"}, allow_redirects=False)
for u in ("/", "/dashboard"):
    r = s.get("http://localhost:8000"+u)
    assert r.status_code == 200, (u, r.status_code)
    assert "top-[53px]" not in r.text, (u, "sticky antigo ainda presente")
    print("OK", u)
PY
```
Expected: 2 linhas "OK".

- [ ] **Step 4: Commit**

```bash
git add app/templates/index.html app/templates/partials/dashboard_filtros.html
git commit -m "fix: ajustar sticky dos filtros para o novo chrome (sem header)"
```

---

## Task 5: Validação final

**Files:** nenhum (validação).

- [ ] **Step 1: Suíte pytest (regressão — não pode quebrar)**

Run: `docker exec -w /code prospec_app python -m pytest -q`
Expected: 24 passed (mesma suíte da Fase 1, intacta).

- [ ] **Step 2: Smoke autenticado em todas as páginas**

Run:

```bash
docker exec -w /code prospec_app python - <<'PY'
import requests
s = requests.Session()
s.post("http://localhost:8000/login", data={"email":"admin@sbr.local","senha":"Acesso06597"}, allow_redirects=False)
casos = ["/inicio", "/", "/dashboards", "/dashboard", "/configuracoes", "/admin/usuarios"]
for u in casos:
    r = s.get("http://localhost:8000"+u)
    assert r.status_code == 200, (u, r.status_code)
    assert 'id="sidebar"' in r.text, (u, "sem sidebar")
    print("OK", u, len(r.text))
PY
```
Expected: 6 linhas "OK".

- [ ] **Step 3: Push**

```bash
git push origin main
```

---

## Notas de implementação

- A casca só renderiza o sidebar quando há `user`; `login.html`/`trocar_senha.html` são documentos standalone (não estendem `base.html`), então não são afetados.
- `request.url.path` está disponível no Jinja porque todas as rotas passam `request` ao `TemplateResponse`.
- O card de sync (`partials/pedido_mobile_card.html`) continua disparando `/sync-clientes` e `/sync-status` (em `frontend.py`); só muda o lugar onde é exibido (Configurações).
- Verificação é por smoke autenticado (real, ponta a ponta) — A1 é navegação/template, sem lógica nova que justifique pytest dedicado; a suíte pytest existente roda como rede de regressão.
- Próximo: A2 (separar Busca/Mapa com filtros na URL) — aí o item **Mapa** entra no menu.

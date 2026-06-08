# Design — Casca de Navegação + Hub de Dashboards (Sub-projeto A1)

> Data: 2026-06-08
> Status: aprovado para implementação (pendente revisão final do usuário)
> Escopo: **somente A1**. A2 (separar Busca/Mapa) e B (dashboard de Análise) estão no roadmap ao fim, fora deste documento.

## Objetivo

Substituir o cabeçalho superior por um **menu lateral fixo** e introduzir um **hub de Dashboards** (galeria de cards). Reorganiza como tudo é acessado, criando espaço para múltiplos dashboards e novas funcionalidades sem mexer no menu a cada adição.

## Decisões validadas (brainstorming)

1. **Menu lateral** com: Início, Busca de Leads, Dashboards, Usuários, Configurações. (**Mapa** entra no menu no A2, quando a página dedicada existir — incluí-lo agora seria um link duplicado da Busca.)
2. **Início enxuto:** saudação + cards de atalho (Busca, Dashboards) + status da última sincronização do Pedido Mobile. (Evoluímos depois.)
3. **Hub de Dashboards:** cards com título + descrição; clicar abre o dashboard. Cockpit = "Disponível"; Análise de Vendas = "Em breve" (entra no B).
4. **Configurações** = controles de sincronização do Pedido Mobile (movidos da home atual) + infos da base (total de empresas, última importação da Receita).
5. **Usuários** = página de admin já existente (`/admin/usuarios`), agora acessível pelo menu.
6. **Busca permanece como está no A1** (tela atual combinada busca+mapa). A separação Busca/Mapa com filtros na URL é o A2.
7. Sequência: **A1 → A2 → B**, um de cada vez.

## Arquitetura

Mantém o stack (FastAPI + Jinja2 + HTMX + Tailwind). A mudança é de **layout (chrome)** e **rotas de páginas**, não de dados.

- **`base.html` vira casca com sidebar.** O `<header>` superior é substituído por um layout flex: `<aside>` (menu lateral) + `<main>` (conteúdo). O sidebar só é renderizado quando há usuário logado (`{% if user is defined and user %}`); telas pré-login (login, trocar-senha) ficam sem sidebar, em largura cheia.
- **Item ativo pelo caminho atual.** O sidebar usa `request.url.path` (já disponível no contexto Jinja via `TemplateResponse`) para destacar o item correspondente. Um helper de prefixo decide o "ativo" (ex.: `/admin` → Usuários).
- **Responsivo, simples (app é desktop-first).** Sidebar fixo em `lg:` (≥1024px). Abaixo disso, o sidebar recolhe e um botão "hambúrguer" no topo o alterna (toggle por JS vanilla mínimo — sem nova dependência).
- **Rotas das páginas novas** ficam em um router próprio `routers/navegacao.py` (Início, Dashboards, Configurações), mantendo `frontend.py` focado em busca/exportação. Os endpoints de sync (`/sync-clientes`, `/sync-status`) permanecem em `frontend.py`; a página de Configurações apenas renderiza o card de sync existente.

## Componentes

| Arquivo | Responsabilidade |
|---|---|
| `app/templates/base.html` (modificar) | Casca: sidebar + main. Mantém os blocos `title`, `head_extra`, `content`, `scripts`. |
| `app/templates/partials/sidebar.html` (novo) | Menu lateral: marca, itens de navegação (com ativo), seção Admin (só `role == admin` para Usuários), usuário + Sair no rodapé. |
| `app/templates/inicio.html` (novo) | Home enxuta: saudação, cards de atalho, card de status da última sync. |
| `app/templates/dashboards.html` (novo) | Hub: grid de cards (título, descrição, tag de status). Cockpit linka `/dashboard`; Análise de Vendas é card "Em breve" desabilitado. |
| `app/templates/configuracoes.html` (novo) | Página de configurações: inclui o card de sync (`partials/pedido_mobile_card.html`) + bloco de infos da base. |
| `app/routers/navegacao.py` (novo) | Rotas `GET /inicio`, `GET /dashboards`, `GET /configuracoes` (todas com `require_login`). |
| `app/main.py` (modificar) | Registrar o `navegacao_router`. |
| `app/routers/frontend.py` (modificar) | Remover o card de sync da home (`/`); o sync passa a ser exibido em Configurações. A `/` segue servindo a busca. |
| `app/templates/index.html` (modificar) | Remover o card de sync; ajustar o sticky dos filtros (ver abaixo). |
| `app/templates/dashboard.html` + `partials/dashboard_filtros.html` (modificar) | Ajustar o `sticky top-[53px]` (dependia do header antigo) para o novo chrome. |

### Rota inicial

`GET /` permanece como a **Busca de Leads** (comportamento atual) no A1. O sidebar terá "Início" → `/inicio` e "Busca de Leads" → `/`. (Quem quiser, no A2/futuro, pode-se decidir tornar `/` um redirect para `/inicio`; fora do escopo agora.)

## Fluxo de dados

Sem mudança de dados. Cada rota nova renderiza um template que estende `base.html`; a casca injeta o sidebar com base em `user` e `request.url.path`. Configurações reaproveita os helpers existentes (`_info_pedido_mobile`, stats da base) e o parcial `pedido_mobile_card.html`; o disparo/poll de sync continua nos endpoints atuais.

## Tratamento de erros e bordas

- **Pré-login sem sidebar:** com `user` indefinido, a casca renderiza só o `<main>` em largura cheia (login/trocar-senha intactos).
- **Itens restritos:** "Usuários" só aparece para `role == 'admin'` (como o link Admin atual).
- **Sticky offsets:** os filtros do cockpit e da busca usavam `top-[53px]` (altura do header antigo). Com o novo chrome, ajustar para o offset correto (ex.: `top-0` dentro do `<main>`), senão a barra "flutua" errado. É um ajuste pontual no escopo.
- **Sem dados de sync/importação:** Configurações mostra "Nunca sincronizado" / "—" em vez de quebrar (helpers já tratam exceção).

## Testes

- **Rotas novas (pytest):** `/inicio`, `/dashboards`, `/configuracoes` retornam 200 autenticado e redirecionam para `/login` sem sessão.
- **Casca:** o template renderiza o sidebar quando há `user` e o omite quando não há; o item ativo corresponde ao caminho.
- **Hub:** `/dashboards` lista o card do Cockpit linkando `/dashboard`.
- **Configurações:** renderiza o card de sync (contém o botão/última sync).
- **Smoke autenticado:** login → navegar por `/inicio`, `/dashboards`, `/configuracoes`, `/`, `/dashboard`, `/admin/usuarios` → todos 200, sidebar presente.
- **Não regredir:** `/` (busca) e `/dashboard` (cockpit) seguem funcionando.

## Fora de escopo (roadmap)

- **A2 — Separar Busca e Mapa:** filtros como estado de URL compartilhado entre as duas telas, página `/mapa` dedicada (mesmos filtros + mesmos cards), atalhos "Ver no mapa / Ver lista", e inclusão do item **Mapa** no menu.
- **B — Dashboard de Análise de Vendas:** curva ABC de produtos, representadas, mix, sazonalidade — entra como card "Disponível" no hub.
- Evolução do Início para incluir números headline (resumo).

import time
from datetime import datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

import dashboard_service as svc
from auth import require_login
from config import BRT
from dashboard_filters import FiltrosDashboard
from database import get_db

router = APIRouter()
templates = Jinja2Templates(directory="templates")

_CACHE_TTL_SEGUNDOS = 180
_cache: dict = {}  # chave_cache -> (ts, dados)


def _dados_cacheados(db: Session, f: FiltrosDashboard, *, hoje) -> dict:
    chave = f.chave_cache()
    agora = time.monotonic()
    item = _cache.get(chave)
    if item and (agora - item[0]) < _CACHE_TTL_SEGUNDOS:
        return item[1]
    dados = svc.montar_dados(db, f, hoje=hoje)
    _cache[chave] = (agora, dados)
    return dados


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(
    request: Request,
    current_user: dict = Depends(require_login),
    db: Session = Depends(get_db),
):
    hoje = datetime.now(BRT).date()
    f = FiltrosDashboard.from_query(dict(request.query_params), hoje=hoje)
    dados = _dados_cacheados(db, f, hoje=hoje)

    template = "partials/dashboard_paineis.html" if request.headers.get("HX-Request") else "dashboard.html"
    return templates.TemplateResponse(template, {
        "request": request,
        "user": current_user,
        "dados": dados,
    })

"""Serviço do dashboard de Recompra.

A matemática (datas de compra + hoje -> ritmo e faixa) é função pura, testável
sem banco — no espírito de analise_service. Os helpers de banco ficam abaixo.

Cada cliente é julgado pela régua DELE mesmo: a mediana dos intervalos entre as
compras define o ritmo; o percentil 90 dos intervalos define até onde um atraso
ainda é "normal" para ele.
"""
from datetime import date

from sqlalchemy import text  # usado pelos helpers de banco (montar_recompra/opcoes_recompra)
from sqlalchemy.orm import Session  # idem

FAIXA_EM_DIA = "em_dia"
FAIXA_ATRASANDO = "atrasando"
FAIXA_ATRASADO = "atrasado"
FAIXA_SEM_PADRAO = "sem_padrao"
MIN_COMPRAS = 3


def _mediana(xs: list[float]) -> float:
    s = sorted(xs)
    n = len(s)
    if n == 0:
        return 0.0
    meio = n // 2
    if n % 2:
        return float(s[meio])
    return (s[meio - 1] + s[meio]) / 2


def _percentil(xs: list[float], p: float) -> float:
    """Percentil por interpolação linear (p em [0,1]); rank = p*(n-1)."""
    s = sorted(xs)
    n = len(s)
    if n == 0:
        return 0.0
    if n == 1:
        return float(s[0])
    rank = p * (n - 1)
    lo = int(rank)
    frac = rank - lo
    if lo + 1 >= n:
        return float(s[-1])
    return s[lo] + frac * (s[lo + 1] - s[lo])


def classificar_recompra(datas: list[date], hoje: date, *, receita_total: float = 0.0) -> dict:
    """Classifica um cliente pelo próprio ritmo de compra.

    Devolve sempre: n_compras, ultima_compra, dias_sem_comprar, ticket_medio, faixa.
    Para >= MIN_COMPRAS adiciona mediana, maior_intervalo_normal e indice.
    """
    datas = sorted(datas)
    n = len(datas)
    ultima = datas[-1] if n else None
    dias_sem_comprar = (hoje - ultima).days if ultima else None
    ticket_medio = (receita_total / n) if n else 0.0

    resultado = {
        "n_compras": n,
        "ultima_compra": ultima,
        "dias_sem_comprar": dias_sem_comprar,
        "ticket_medio": round(ticket_medio, 2),
        "mediana": None,
        "maior_intervalo_normal": None,
        "indice": None,
        "faixa": FAIXA_SEM_PADRAO,
    }
    if n < MIN_COMPRAS:
        return resultado

    intervalos = [(datas[i] - datas[i - 1]).days for i in range(1, n)]
    mediana = _mediana(intervalos)
    p90 = _percentil(intervalos, 0.9)
    mediana_safe = mediana if mediana >= 1 else 1.0
    indice = dias_sem_comprar / mediana_safe

    if dias_sem_comprar <= mediana:
        faixa = FAIXA_EM_DIA
    elif dias_sem_comprar <= p90:
        faixa = FAIXA_ATRASANDO
    else:
        faixa = FAIXA_ATRASADO

    resultado.update({
        "mediana": round(mediana, 1),
        "maior_intervalo_normal": round(p90, 1),
        "indice": round(indice, 2),
        "faixa": faixa,
    })
    return resultado

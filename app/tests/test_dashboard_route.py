from datetime import date

import routers.dashboard as rota
from dashboard_filters import FiltrosDashboard


def test_chave_de_cache_isola_recortes(monkeypatch):
    rota._cache.clear()
    chamadas = []

    def fake_montar(db, f, *, hoje):
        chamadas.append(f.vendedor)
        return {"marcador": f.vendedor}

    monkeypatch.setattr(rota.svc, "montar_dados", fake_montar)

    a = FiltrosDashboard.from_query({"vendedor": "Joao"}, hoje=date(2026, 6, 8))
    b = FiltrosDashboard.from_query({"vendedor": "Maria"}, hoje=date(2026, 6, 8))

    rota._dados_cacheados(None, a, hoje=date(2026, 6, 8))
    rota._dados_cacheados(None, a, hoje=date(2026, 6, 8))  # reusa cache
    rota._dados_cacheados(None, b, hoje=date(2026, 6, 8))

    assert chamadas == ["Joao", "Maria"]  # 'Joao' só calculou uma vez


def test_cache_analise_isola_por_criterio_e_cortes(monkeypatch):
    rota._cache_analise.clear()
    chamadas = []

    def fake_montar(db, f, *, criterio, cortes_str):
        chamadas.append((criterio, cortes_str))
        return {"marcador": criterio}

    monkeypatch.setattr(rota.svc_analise, "montar_analise", fake_montar)

    f = FiltrosDashboard.from_query({}, hoje=date(2026, 6, 8))
    rota._dados_analise_cacheados(None, f, criterio="receita", cortes_str="50-30-20")
    rota._dados_analise_cacheados(None, f, criterio="receita", cortes_str="50-30-20")  # reusa cache
    rota._dados_analise_cacheados(None, f, criterio="quantidade", cortes_str="50-30-20")
    rota._dados_analise_cacheados(None, f, criterio="receita", cortes_str="70-20-10")

    assert chamadas == [
        ("receita", "50-30-20"),
        ("quantidade", "50-30-20"),
        ("receita", "70-20-10"),
    ]

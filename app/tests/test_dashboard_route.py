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

from datetime import date

from dashboard_filters import FiltrosDashboard, derivar_comparacao


def _f(inicio, fim, comparacao, cmp_inicio=None, cmp_fim=None):
    return FiltrosDashboard(inicio=inicio, fim=fim, comparacao=comparacao,
                            cmp_inicio=cmp_inicio, cmp_fim=cmp_fim,
                            vendedor=None, representada=None, situacao="confirmados")


# ---- parsing / padrões ----

def test_padrao_e_mes_corrente():
    f = FiltrosDashboard.from_query({}, hoje=date(2026, 6, 8))
    assert f.inicio == date(2026, 6, 1)
    assert f.fim == date(2026, 6, 8)
    assert f.comparacao == "mes_anterior"
    assert f.vendedor is None
    assert f.situacao == "confirmados"


def test_intervalo_explicito():
    f = FiltrosDashboard.from_query(
        {"inicio": "2026-03-01", "fim": "2026-03-15", "vendedor": "Joao"},
        hoje=date(2026, 6, 8),
    )
    assert f.inicio == date(2026, 3, 1)
    assert f.fim == date(2026, 3, 15)
    assert f.vendedor == "Joao"


def test_intervalo_invertido_normaliza():
    f = FiltrosDashboard.from_query(
        {"inicio": "2026-03-15", "fim": "2026-03-01"}, hoje=date(2026, 6, 8)
    )
    assert f.inicio <= f.fim


def test_vazio_string_vira_none():
    f = FiltrosDashboard.from_query({"vendedor": "", "representada": "  "}, hoje=date(2026, 6, 8))
    assert f.vendedor is None
    assert f.representada is None


# ---- derivação da comparação ----

def test_comp_mes_anterior():
    assert derivar_comparacao(_f(date(2026, 6, 1), date(2026, 6, 8), "mes_anterior")) == (date(2026, 5, 1), date(2026, 5, 8))


def test_comp_ano_anterior():
    assert derivar_comparacao(_f(date(2026, 6, 1), date(2026, 6, 8), "ano_anterior")) == (date(2025, 6, 1), date(2025, 6, 8))


def test_comp_trimestre_anterior():
    assert derivar_comparacao(_f(date(2026, 6, 1), date(2026, 6, 30), "trimestre_anterior")) == (date(2026, 3, 1), date(2026, 3, 30))


def test_comp_personalizado():
    assert derivar_comparacao(
        _f(date(2026, 6, 1), date(2026, 6, 8), "personalizado", date(2026, 1, 1), date(2026, 1, 31))
    ) == (date(2026, 1, 1), date(2026, 1, 31))


def test_comp_nenhuma():
    assert derivar_comparacao(_f(date(2026, 6, 1), date(2026, 6, 8), "nenhuma")) is None


def test_comp_clampa_dia():
    assert derivar_comparacao(_f(date(2026, 3, 1), date(2026, 3, 31), "mes_anterior")) == (date(2026, 2, 1), date(2026, 2, 28))


# ---- chave de cache ----

def test_chave_cache_distingue_recortes():
    a = FiltrosDashboard.from_query({"vendedor": "Joao"}, hoje=date(2026, 6, 8))
    b = FiltrosDashboard.from_query({"vendedor": "Maria"}, hoje=date(2026, 6, 8))
    c = FiltrosDashboard.from_query({"vendedor": "Joao"}, hoje=date(2026, 6, 8))
    assert a.chave_cache() != b.chave_cache()
    assert a.chave_cache() == c.chave_cache()

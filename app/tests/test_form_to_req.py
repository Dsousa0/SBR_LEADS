from starlette.datastructures import QueryParams

from routers.frontend import _form_to_req


def test_form_to_req_aceita_querystring():
    q = QueryParams("uf=PI&apenas_ativas=true&ordenar=capital_desc&produtos_codigos=A,B")
    req = _form_to_req(q, page=2)
    assert req.uf == "PI"
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


def test_form_to_req_segmento_fixo_em_farmacia():
    # O segmento saiu da UI: sempre farmácia, mesmo que o form mande outro valor.
    assert _form_to_req(QueryParams("")).segmento == "farmacia"
    assert _form_to_req(QueryParams("segmento=restaurante")).segmento == "farmacia"

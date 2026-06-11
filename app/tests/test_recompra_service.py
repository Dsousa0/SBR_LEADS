from datetime import date, timedelta

import recompra_service as svc


def _datas(inicio: date, *intervalos: int) -> list[date]:
    """Constrói datas de compra a partir de um início e dos intervalos entre elas."""
    datas = [inicio]
    for d in intervalos:
        datas.append(datas[-1] + timedelta(days=d))
    return datas


# ---- mediana ----

def test_mediana_impar():
    assert svc._mediana([10, 30, 20]) == 20

def test_mediana_par_media_dos_centrais():
    assert svc._mediana([10, 20, 30, 40]) == 25

def test_mediana_vazia_zero():
    assert svc._mediana([]) == 0.0


# ---- percentil (interpolação linear) ----

def test_percentil_p90_interpola():
    # [20,30,40], p=0.9 -> rank=1.8 -> 30 + 0.8*(40-30) = 38
    assert svc._percentil([20, 30, 40], 0.9) == 38.0

def test_percentil_um_elemento():
    assert svc._percentil([25], 0.9) == 25.0

def test_percentil_vazio_zero():
    assert svc._percentil([], 0.9) == 0.0


# ---- classificar_recompra ----

def test_sem_padrao_com_menos_de_3_compras():
    for ints in ([], [30]):  # 1 e 2 compras
        datas = _datas(date(2026, 1, 1), *ints)
        r = svc.classificar_recompra(datas, date(2026, 3, 1), receita_total=200)
        assert r["faixa"] == "sem_padrao"
        assert r["indice"] is None
        assert r["mediana"] is None
        assert r["n_compras"] == len(datas)
        assert r["ultima_compra"] == datas[-1]
        assert r["ticket_medio"] == round(200 / len(datas), 2)


def test_faixa_em_dia_no_limite_da_mediana():
    datas = _datas(date(2026, 1, 1), 20, 30, 40)
    ultima = datas[-1]
    r = svc.classificar_recompra(datas, ultima + timedelta(days=30), receita_total=400)
    assert r["mediana"] == 30.0
    assert r["maior_intervalo_normal"] == 38.0
    assert r["dias_sem_comprar"] == 30
    assert r["faixa"] == "em_dia"        # 30 <= mediana(30)
    assert r["indice"] == 1.0


def test_faixa_atrasando_entre_mediana_e_p90():
    datas = _datas(date(2026, 1, 1), 20, 30, 40)
    ultima = datas[-1]
    r = svc.classificar_recompra(datas, ultima + timedelta(days=35), receita_total=400)
    assert r["faixa"] == "atrasando"     # 30 < 35 <= 38


def test_faixa_atrasando_no_limite_p90():
    datas = _datas(date(2026, 1, 1), 20, 30, 40)
    ultima = datas[-1]
    r = svc.classificar_recompra(datas, ultima + timedelta(days=38), receita_total=400)
    assert r["faixa"] == "atrasando"     # 38 <= p90(38)


def test_faixa_atrasado_acima_do_p90():
    datas = _datas(date(2026, 1, 1), 20, 30, 40)
    ultima = datas[-1]
    r = svc.classificar_recompra(datas, ultima + timedelta(days=39), receita_total=400)
    assert r["faixa"] == "atrasado"      # 39 > p90(38)
    assert r["indice"] == round(39 / 30, 2)


def test_p90_robusto_a_outlier():
    datas = _datas(date(2026, 1, 1), 30, 30, 30, 200)
    ultima = datas[-1]
    r = svc.classificar_recompra(datas, ultima + timedelta(days=60), receita_total=500)
    assert r["mediana"] == 30.0
    assert r["maior_intervalo_normal"] < 200
    assert r["faixa"] in ("atrasando", "atrasado")


def test_ticket_medio():
    datas = _datas(date(2026, 1, 1), 30, 30)  # 3 compras
    r = svc.classificar_recompra(datas, datas[-1] + timedelta(days=10), receita_total=900)
    assert r["ticket_medio"] == 300.0


def test_mediana_zero_nao_quebra():
    d = date(2026, 1, 1)
    r = svc.classificar_recompra([d, d, d], d + timedelta(days=5), receita_total=300)
    assert r["mediana"] == 0.0
    assert r["indice"] == 5.0            # usa mediana mínima de 1 para o índice
    assert r["faixa"] == "atrasado"


def test_sem_compras_retorna_sem_padrao():
    r = svc.classificar_recompra([], date(2026, 3, 1))
    assert r["faixa"] == "sem_padrao"
    assert r["n_compras"] == 0
    assert r["ultima_compra"] is None
    assert r["dias_sem_comprar"] is None
    assert r["ticket_medio"] == 0.0

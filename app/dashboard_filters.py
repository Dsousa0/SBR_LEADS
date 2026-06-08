import calendar
from dataclasses import dataclass
from datetime import date


def _parse_date(s, padrao):
    if not s:
        return padrao
    try:
        return date.fromisoformat(s)
    except (ValueError, TypeError):
        return padrao


def _limpar(v):
    v = (v or "").strip()
    return v or None


_COMPARACOES = {"mes_anterior", "ano_anterior", "trimestre_anterior", "personalizado", "nenhuma"}


def _shift_meses(d: date, meses: int) -> date:
    total = (d.year * 12 + (d.month - 1)) + meses
    ano, mes = divmod(total, 12)
    mes += 1
    ultimo_dia = calendar.monthrange(ano, mes)[1]
    return date(ano, mes, min(d.day, ultimo_dia))


@dataclass
class FiltrosDashboard:
    inicio: date
    fim: date
    comparacao: str
    cmp_inicio: date | None
    cmp_fim: date | None
    vendedor: str | None
    representada: str | None
    situacao: str

    @classmethod
    def from_query(cls, q: dict, hoje: date) -> "FiltrosDashboard":
        inicio = _parse_date(q.get("inicio"), hoje.replace(day=1))
        fim = _parse_date(q.get("fim"), hoje)
        if fim < inicio:
            inicio, fim = fim, inicio

        comparacao = q.get("comparacao") or "mes_anterior"
        if comparacao not in _COMPARACOES:
            comparacao = "mes_anterior"

        cmp_inicio = _parse_date(q.get("cmp_inicio"), None)
        cmp_fim = _parse_date(q.get("cmp_fim"), None)

        situacao = q.get("situacao") or "confirmados"

        return cls(
            inicio=inicio,
            fim=fim,
            comparacao=comparacao,
            cmp_inicio=cmp_inicio,
            cmp_fim=cmp_fim,
            vendedor=_limpar(q.get("vendedor")),
            representada=_limpar(q.get("representada")),
            situacao=situacao,
        )

    def chave_cache(self) -> str:
        return "|".join(str(x) for x in (
            self.inicio, self.fim, self.comparacao, self.cmp_inicio, self.cmp_fim,
            self.vendedor, self.representada, self.situacao,
        ))


def derivar_comparacao(f: "FiltrosDashboard") -> tuple[date, date] | None:
    """Retorna (inicio, fim) do período de comparação, ou None se 'nenhuma'."""
    if f.comparacao == "nenhuma":
        return None
    if f.comparacao == "personalizado":
        if f.cmp_inicio and f.cmp_fim:
            return (f.cmp_inicio, f.cmp_fim)
        return None
    deslocamento = {"mes_anterior": -1, "trimestre_anterior": -3, "ano_anterior": -12}[f.comparacao]
    return (_shift_meses(f.inicio, deslocamento), _shift_meses(f.fim, deslocamento))

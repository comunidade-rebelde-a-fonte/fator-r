"""Dinheiro e percentuais em Decimal. Quantização só na saída."""

from decimal import ROUND_HALF_EVEN, Decimal

CENTAVO = Decimal("0.01")
SEIS_CASAS = Decimal("0.000001")


def quantizar_dinheiro(valor: Decimal) -> Decimal:
    return valor.quantize(CENTAVO, rounding=ROUND_HALF_EVEN)


def quantizar_percentual(valor: Decimal) -> Decimal:
    return valor.quantize(SEIS_CASAS, rounding=ROUND_HALF_EVEN)


def para_decimal(valor: str | int | Decimal) -> Decimal:
    if isinstance(valor, float):  # pragma: no cover - proteção contra uso indevido
        raise TypeError("Use Decimal ou str para dinheiro, nunca float")
    return Decimal(valor)


def formatar_brl(valor: Decimal | str | int | None) -> str:
    """600000.00 -> 600.000,00 (texto de template; o valor já vem calculado)."""
    if valor is None:
        return "-"
    quantizado = quantizar_dinheiro(Decimal(str(valor)))
    inteiro, _, centavos = f"{abs(quantizado):.2f}".partition(".")
    grupos = f"{int(inteiro):,}".replace(",", ".")
    return f"{'-' if quantizado < 0 else ''}{grupos},{centavos}"


def formatar_percentual_br(valor: Decimal | str | None) -> str:
    """0.240000 -> 24,00%."""
    if valor is None:
        return "-"
    percentual = (Decimal(str(valor)) * 100).quantize(CENTAVO, rounding=ROUND_HALF_EVEN)
    return f"{percentual:.2f}".replace(".", ",") + "%"

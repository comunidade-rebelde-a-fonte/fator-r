"""CNPJ: normalização, validação dos dígitos verificadores e formatação."""

import re

_PESOS_DV1 = (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
_PESOS_DV2 = (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)


class CnpjInvalido(ValueError):
    pass


def _digito(numeros: str, pesos: tuple[int, ...]) -> str:
    resto = sum(int(n) * p for n, p in zip(numeros, pesos, strict=True)) % 11
    return "0" if resto < 2 else str(11 - resto)


def normalizar_cnpj(valor: str) -> str:
    """Devolve só os 14 dígitos de um CNPJ válido; levanta CnpjInvalido caso contrário."""
    digitos = re.sub(r"\D", "", valor)
    if len(digitos) != 14 or len(set(digitos)) == 1:
        raise CnpjInvalido("CNPJ inválido")
    dv1 = _digito(digitos[:12], _PESOS_DV1)
    dv2 = _digito(digitos[:12] + dv1, _PESOS_DV2)
    if digitos[12:] != dv1 + dv2:
        raise CnpjInvalido("CNPJ inválido")
    return digitos


def cnpj_valido(valor: str) -> bool:
    try:
        normalizar_cnpj(valor)
    except CnpjInvalido:
        return False
    return True


def formatar_cnpj(digitos: str) -> str:
    d = normalizar_cnpj(digitos)
    return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:]}"

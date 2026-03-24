"""Funções de formatação para valores brasileiros (BRL, %, números)."""

import math


def formatar_moeda(valor, prefixo="R$ "):
    """Formata valor como moeda brasileira: R$ 1.234.567,89"""
    if valor is None or (isinstance(valor, float) and math.isnan(valor)):
        return f"{prefixo}—"
    negativo = valor < 0
    valor = abs(valor)
    inteiro = int(valor)
    decimal = round((valor - inteiro) * 100)
    parte_inteira = f"{inteiro:,}".replace(",", ".")
    resultado = f"{prefixo}{parte_inteira},{decimal:02d}"
    if negativo:
        resultado = f"-{resultado}"
    return resultado


def formatar_bilhoes(valor, prefixo="R$ "):
    """Formata valor em bilhões: R$ 2,6 bi"""
    if valor is None or (isinstance(valor, float) and math.isnan(valor)):
        return f"{prefixo}—"
    if abs(valor) >= 1e9:
        return f"{prefixo}{valor / 1e9:,.1f} bi".replace(",", "X").replace(".", ",").replace("X", ".")
    if abs(valor) >= 1e6:
        return f"{prefixo}{valor / 1e6:,.1f} mi".replace(",", "X").replace(".", ",").replace("X", ".")
    if abs(valor) >= 1e3:
        return f"{prefixo}{valor / 1e3:,.1f} mil".replace(",", "X").replace(".", ",").replace("X", ".")
    return formatar_moeda(valor, prefixo)


def formatar_percentual(valor, casas=2):
    """Formata valor como percentual: 12,34%"""
    if valor is None or (isinstance(valor, float) and math.isnan(valor)):
        return "—"
    return f"{valor:,.{casas}f}%".replace(",", "X").replace(".", ",").replace("X", ".")


def formatar_numero(valor, casas=0):
    """Formata número com separador de milhar brasileiro: 1.234.567"""
    if valor is None or (isinstance(valor, float) and math.isnan(valor)):
        return "—"
    if casas == 0:
        return f"{int(valor):,}".replace(",", ".")
    return f"{valor:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")

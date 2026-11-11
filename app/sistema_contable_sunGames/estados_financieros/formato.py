from decimal import Decimal


def cifra(valor):
    """Dos decimales, separador de miles y negativos entre paréntesis."""
    valor = Decimal(valor)
    texto = f"{abs(valor):,.2f}"
    return f"({texto})" if valor < 0 else texto

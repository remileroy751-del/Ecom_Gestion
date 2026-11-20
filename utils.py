"""
Utilitaires partagés par les différents modules de l'application.
"""


def fmt(valeur):
    """
    Formate un nombre avec un espace comme séparateur de milliers
    (ex: 1234567 -> "1 234 567"), sans virgule ni point.
    """
    try:
        return f"{valeur:,.0f}".replace(",", " ")
    except (TypeError, ValueError):
        return str(valeur)

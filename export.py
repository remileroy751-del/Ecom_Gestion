"""
Export des rapports détaillés (journalier ou par période) en PDF et Excel.

Chaque rapport comporte deux tableaux : les factures (ventes) puis les
dépenses de la période sélectionnée, avec leur total respectif en bas.
"""

import os
from datetime import datetime

from utils import fmt


def _dossier_bureau():
    """
    Retourne le chemin du Bureau de l'utilisateur (Windows/macOS/Linux).
    Si aucun dossier "Desktop"/"Bureau" n'est trouvé, retourne le dossier
    personnel de l'utilisateur en repli.
    """
    accueil = os.path.expanduser("~")
    for nom_dossier in ("Desktop", "Bureau"):
        candidat = os.path.join(accueil, nom_dossier)
        if os.path.isdir(candidat):
            return candidat
    return accueil


def _nom_fichier(prefixe, extension):
    horodatage = datetime.now().strftime("%Y%m%d_%H%M%S")
    dossier = _dossier_bureau()
    return os.path.join(dossier, f"{prefixe}_{horodatage}.{extension}")


def _libelle_role(role):
    if role == "responsable":
        return "Chef"
    if role == "saisie":
        return "Secrétaire"
    return "Automatique"


def exporter_rapport_detail_pdf(nom_entreprise, titre, factures, depenses, avec_date=False):
    from fpdf import FPDF

    pdf = FPDF(orientation="L")  # paysage : plus de place pour les colonnes
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, nom_entreprise, ln=True)
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 8, titre, ln=True)
    pdf.ln(4)

    # --- Tableau des ventes (factures) ---
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Ventes", ln=True)

    colonnes = (["Date"] if avec_date else []) + ["N° Facture", "Montant (FCFA)", "Traçabilité", "Client", "Numéro"]
    largeurs = ([28] if avec_date else []) + [35, 40, 45, 65, 40]

    pdf.set_font("Helvetica", "B", 9)
    for c, l in zip(colonnes, largeurs):
        pdf.cell(l, 8, c, border=1)
    pdf.ln()

    pdf.set_font("Helvetica", "", 9)
    total_factures = 0
    for f in factures:
        total_factures += f["montant_total"]
        valeurs = ([f["date_jour"]] if avec_date else []) + [
            f["numero"], fmt(f["montant_total"]), _libelle_role(f["role"]),
            f.get("client_nom") or "-", f.get("client_telephone") or "-",
        ]
        for v, l in zip(valeurs, largeurs):
            pdf.cell(l, 7, str(v), border=1)
        pdf.ln()
    if not factures:
        pdf.cell(sum(largeurs), 7, "Aucune facture sur cette période.", border=1, ln=True)

    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(sum(largeurs), 8, f"TOTAL DES FACTURES : {fmt(total_factures)} FCFA", border=1, ln=True)
    pdf.ln(8)

    # --- Tableau des dépenses ---
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Dépenses", ln=True)

    colonnes_d = (["Date"] if avec_date else []) + ["Nature des dépenses", "Montant (FCFA)", "Traçabilité"]
    largeurs_d = ([28] if avec_date else []) + [110, 40, 60]

    pdf.set_font("Helvetica", "B", 9)
    for c, l in zip(colonnes_d, largeurs_d):
        pdf.cell(l, 8, c, border=1)
    pdf.ln()

    pdf.set_font("Helvetica", "", 9)
    total_depenses = 0
    for d in depenses:
        total_depenses += d["montant"]
        valeurs = ([d["date_jour"]] if avec_date else []) + [d["libelle"], fmt(d["montant"]), _libelle_role(d["role"])]
        for v, l in zip(valeurs, largeurs_d):
            pdf.cell(l, 7, str(v), border=1)
        pdf.ln()
    if not depenses:
        pdf.cell(sum(largeurs_d), 7, "Aucune dépense sur cette période.", border=1, ln=True)

    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(sum(largeurs_d), 8, f"TOTAL DES DÉPENSES : {fmt(total_depenses)} FCFA", border=1, ln=True)

    chemin = _nom_fichier("rapport_detaille", "pdf")
    pdf.output(chemin)
    return chemin


def exporter_rapport_detail_excel(nom_entreprise, titre, factures, depenses, avec_date=False):
    from openpyxl import Workbook
    from openpyxl.styles import Font

    classeur = Workbook()
    feuille = classeur.active
    feuille.title = "Rapport"

    feuille["A1"] = nom_entreprise
    feuille["A1"].font = Font(bold=True, size=14)
    feuille["A2"] = titre
    feuille["A2"].font = Font(italic=True)

    ligne = 4

    # --- Ventes ---
    feuille.cell(row=ligne, column=1, value="Ventes").font = Font(bold=True, size=12)
    ligne += 1
    colonnes = (["Date"] if avec_date else []) + ["N° Facture", "Montant (FCFA)", "Traçabilité", "Client", "Numéro"]
    for col_idx, nom_colonne in enumerate(colonnes, start=1):
        c = feuille.cell(row=ligne, column=col_idx, value=nom_colonne)
        c.font = Font(bold=True)
    ligne += 1

    total_factures = 0
    for f in factures:
        total_factures += f["montant_total"]
        valeurs = ([f["date_jour"]] if avec_date else []) + [
            f["numero"], f["montant_total"], _libelle_role(f["role"]),
            f.get("client_nom") or "-", f.get("client_telephone") or "-",
        ]
        for col_idx, v in enumerate(valeurs, start=1):
            feuille.cell(row=ligne, column=col_idx, value=v)
        ligne += 1
    if not factures:
        feuille.cell(row=ligne, column=1, value="Aucune facture sur cette période.")
        ligne += 1

    c = feuille.cell(row=ligne, column=1, value=f"TOTAL DES FACTURES : {fmt(total_factures)} FCFA")
    c.font = Font(bold=True)
    ligne += 3

    # --- Dépenses ---
    feuille.cell(row=ligne, column=1, value="Dépenses").font = Font(bold=True, size=12)
    ligne += 1
    colonnes_d = (["Date"] if avec_date else []) + ["Nature des dépenses", "Montant (FCFA)", "Traçabilité"]
    for col_idx, nom_colonne in enumerate(colonnes_d, start=1):
        c = feuille.cell(row=ligne, column=col_idx, value=nom_colonne)
        c.font = Font(bold=True)
    ligne += 1

    total_depenses = 0
    for d in depenses:
        total_depenses += d["montant"]
        valeurs = ([d["date_jour"]] if avec_date else []) + [d["libelle"], d["montant"], _libelle_role(d["role"])]
        for col_idx, v in enumerate(valeurs, start=1):
            feuille.cell(row=ligne, column=col_idx, value=v)
        ligne += 1
    if not depenses:
        feuille.cell(row=ligne, column=1, value="Aucune dépense sur cette période.")
        ligne += 1

    c = feuille.cell(row=ligne, column=1, value=f"TOTAL DES DÉPENSES : {fmt(total_depenses)} FCFA")
    c.font = Font(bold=True)

    for lettre, largeur in [("A", 14), ("B", 26), ("C", 18), ("D", 22), ("E", 26), ("F", 18)]:
        feuille.column_dimensions[lettre].width = largeur

    chemin = _nom_fichier("rapport_detaille", "xlsx")
    classeur.save(chemin)
    return chemin


def exporter_mouvements_pdf(nom_entreprise, nom_produit, titre, mouvements):
    from fpdf import FPDF

    pdf = FPDF(orientation="L")
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, nom_entreprise, ln=True)
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 8, f"Mouvements de stock — {nom_produit}", ln=True)
    pdf.cell(0, 8, titre, ln=True)
    pdf.ln(4)

    colonnes = ["Date", "Type", "Quantité", "Prix unitaire (FCFA)", "N° Facture", "Traçabilité"]
    largeurs = [30, 25, 28, 45, 40, 45]

    pdf.set_font("Helvetica", "B", 9)
    for c, l in zip(colonnes, largeurs):
        pdf.cell(l, 8, c, border=1)
    pdf.ln()

    pdf.set_font("Helvetica", "", 9)
    total_entrees, total_sorties = 0, 0
    for m in mouvements:
        if m["type"] == "entree":
            total_entrees += m["quantite"]
        else:
            total_sorties += m["quantite"]
        valeurs = [
            m["date_jour"], "Entrée" if m["type"] == "entree" else "Sortie (vente)",
            str(m["quantite"]), fmt(m["prix_unitaire"]), m.get("numero_facture") or "-", _libelle_role(m["role"]),
        ]
        for v, l in zip(valeurs, largeurs):
            pdf.cell(l, 7, str(v), border=1)
        pdf.ln()
    if not mouvements:
        pdf.cell(sum(largeurs), 7, "Aucun mouvement sur cette période.", border=1, ln=True)

    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 8, f"Total entrées : {total_entrees} unité(s)      Total sorties : {total_sorties} unité(s)", ln=True)

    chemin = _nom_fichier("mouvements_stock", "pdf")
    pdf.output(chemin)
    return chemin


def exporter_mouvements_excel(nom_entreprise, nom_produit, titre, mouvements):
    from openpyxl import Workbook
    from openpyxl.styles import Font

    classeur = Workbook()
    feuille = classeur.active
    feuille.title = "Mouvements"

    feuille["A1"] = nom_entreprise
    feuille["A1"].font = Font(bold=True, size=14)
    feuille["A2"] = f"Mouvements de stock — {nom_produit}"
    feuille["A2"].font = Font(bold=True, size=12)
    feuille["A3"] = titre
    feuille["A3"].font = Font(italic=True)

    ligne = 5
    colonnes = ["Date", "Type", "Quantité", "Prix unitaire (FCFA)", "N° Facture", "Traçabilité"]
    for col_idx, nom_colonne in enumerate(colonnes, start=1):
        c = feuille.cell(row=ligne, column=col_idx, value=nom_colonne)
        c.font = Font(bold=True)
    ligne += 1

    total_entrees, total_sorties = 0, 0
    for m in mouvements:
        if m["type"] == "entree":
            total_entrees += m["quantite"]
        else:
            total_sorties += m["quantite"]
        valeurs = [
            m["date_jour"], "Entrée" if m["type"] == "entree" else "Sortie (vente)",
            m["quantite"], m["prix_unitaire"], m.get("numero_facture") or "-", _libelle_role(m["role"]),
        ]
        for col_idx, v in enumerate(valeurs, start=1):
            feuille.cell(row=ligne, column=col_idx, value=v)
        ligne += 1
    if not mouvements:
        feuille.cell(row=ligne, column=1, value="Aucun mouvement sur cette période.")
        ligne += 1

    ligne += 1
    c = feuille.cell(row=ligne, column=1, value=f"Total entrées : {total_entrees} unité(s)")
    c.font = Font(bold=True)
    c2 = feuille.cell(row=ligne, column=3, value=f"Total sorties : {total_sorties} unité(s)")
    c2.font = Font(bold=True)

    for lettre, largeur in [("A", 14), ("B", 18), ("C", 12), ("D", 20), ("E", 16), ("F", 18)]:
        feuille.column_dimensions[lettre].width = largeur

    chemin = _nom_fichier("mouvements_stock", "xlsx")
    classeur.save(chemin)
    return chemin

"""
Outil de nettoyage des fichiers résiduels du logiciel de gestion de stock.

À utiliser APRÈS avoir désinstallé / supprimé le logiciel : il retrouve puis
supprime les données que celui-ci a laissées sur l'ordinateur (base de
données, factures, logo, journaux, cache).

Sécurité :
  - seuls des éléments portant un nom CONNU du logiciel sont supprimés
    (jamais un dossier entier choisi par l'utilisateur) ;
  - une confirmation explicite est demandée avant toute suppression ;
  - une sauvegarde (.zip) peut être créée au préalable ;
  - la suppression est refusée tant que le logiciel est ouvert.

Les rapports PDF/Excel exportés sur le Bureau ne sont PAS touchés : ce sont
des documents de l'utilisateur.
"""

import os
import subprocess
import zipfile
from datetime import datetime

from utils import chemin_donnees_exe

NOM_EXE_LOGICIEL = "GestionStock.exe"

# Noms exacts de ce que le logiciel (toutes versions confondues) peut créer.
ELEMENTS_CONNUS = (
    "gestion_pme.db",
    "gestion_pme.db-journal",
    "gestion_pme.db-wal",
    "gestion_pme.db-shm",
    "rapports_email.log",
    "pub_cache.json",
    "assets",
    "factures",
    "exports",
)


# --------------------------------------------------------------------------
# Logique (sans interface, testable)
# --------------------------------------------------------------------------

def taille_element(chemin):
    """Taille en octets d'un fichier ou d'un dossier (récursif)."""
    if os.path.islink(chemin) or os.path.isfile(chemin):
        try:
            return os.path.getsize(chemin)
        except OSError:
            return 0
    total = 0
    for racine, _dossiers, fichiers in os.walk(chemin):
        for nom in fichiers:
            try:
                total += os.path.getsize(os.path.join(racine, nom))
            except OSError:
                pass
    return total


def formater_taille(octets):
    for unite in ("o", "Ko", "Mo", "Go"):
        if octets < 1024 or unite == "Go":
            return f"{octets:.0f} {unite}" if unite == "o" else f"{octets:.1f} {unite}"
        octets /= 1024


def scanner(dossiers):
    """
    Retourne la liste des éléments résiduels trouvés dans les dossiers
    donnés : [{"chemin", "dossier", "taille"}, ...].
    """
    trouves = []
    deja_vus = set()
    for dossier in dossiers:
        if not dossier or not os.path.isdir(dossier):
            continue
        for nom in ELEMENTS_CONNUS:
            chemin = os.path.join(dossier, nom)
            cle = os.path.normcase(os.path.abspath(chemin))
            if cle in deja_vus or not os.path.lexists(chemin):
                continue
            deja_vus.add(cle)
            trouves.append({"chemin": chemin, "dossier": dossier,
                            "taille": taille_element(chemin)})
    return trouves


def _supprimer_chemin(chemin):
    """Supprime un fichier, un lien ou un dossier (sans suivre les liens)."""
    if os.path.islink(chemin) or os.path.isfile(chemin):
        os.remove(chemin)
        return
    for racine, dossiers, fichiers in os.walk(chemin, topdown=False):
        for nom in fichiers:
            os.remove(os.path.join(racine, nom))
        for nom in dossiers:
            sous = os.path.join(racine, nom)
            if os.path.islink(sous):
                os.remove(sous)
            else:
                os.rmdir(sous)
    os.rmdir(chemin)


def supprimer(elements):
    """
    Supprime les éléments donnés. Retourne (supprimes, erreurs) où erreurs
    est une liste de (chemin, message).
    Le dossier de données %LOCALAPPDATA%\\GestionStock lui-même est retiré
    s'il est vide ; les autres dossiers (ex: dossier du code source) ne sont
    jamais supprimés, seulement leur contenu connu.
    """
    supprimes, erreurs = [], []
    dossiers_concernes = set()
    for el in elements:
        chemin = el["chemin"]
        if os.path.basename(chemin) not in ELEMENTS_CONNUS:
            erreurs.append((chemin, "Nom non reconnu : suppression refusée."))
            continue
        try:
            _supprimer_chemin(chemin)
            supprimes.append(chemin)
        except OSError as e:
            erreurs.append((chemin, str(e)))
        dossiers_concernes.add(el["dossier"])

    dossier_exe = os.path.normcase(os.path.abspath(chemin_donnees_exe()))
    for dossier in dossiers_concernes:
        if os.path.normcase(os.path.abspath(dossier)) == dossier_exe:
            try:
                os.rmdir(dossier)  # ne fonctionne que s'il est vide
            except OSError:
                pass
    return supprimes, erreurs


def sauvegarder(elements, fichier_zip):
    """Crée une copie de sécurité (.zip) des éléments donnés."""
    with zipfile.ZipFile(fichier_zip, "w", zipfile.ZIP_DEFLATED) as z:
        for el in elements:
            chemin = el["chemin"]
            base = os.path.dirname(chemin)
            if os.path.isfile(chemin):
                z.write(chemin, os.path.relpath(chemin, base))
                continue
            for racine, _d, fichiers in os.walk(chemin):
                for nom in fichiers:
                    complet = os.path.join(racine, nom)
                    z.write(complet, os.path.relpath(complet, base))


def logiciel_en_cours():
    """True si le logiciel est actuellement ouvert (Windows uniquement)."""
    if os.name != "nt":
        return False
    try:
        sortie = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {NOM_EXE_LOGICIEL}", "/NH"],
            capture_output=True, text=True, timeout=10,
            creationflags=0x08000000,  # CREATE_NO_WINDOW
        ).stdout
        return NOM_EXE_LOGICIEL.lower() in sortie.lower()
    except Exception:
        return False


# --------------------------------------------------------------------------
# Interface
# --------------------------------------------------------------------------

def lancer_interface():
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    fenetre = tk.Tk()
    fenetre.title("Nettoyage des fichiers résiduels — Gestion de Stock")
    fenetre.geometry("720x520")
    fenetre.minsize(620, 460)

    dossiers = [chemin_donnees_exe()]
    elements = []

    tk.Label(fenetre, text="Nettoyage des fichiers résiduels",
             font=("Segoe UI", 16, "bold")).pack(pady=(14, 2))
    tk.Label(
        fenetre, justify="left", wraplength=660, font=("Segoe UI", 10),
        text=("Cet outil supprime les données laissées sur cet ordinateur par le "
              "logiciel de gestion de stock : base de données (ventes, stock, "
              "clients, dépenses), factures, logo, journaux et cache.\n"
              "La suppression est DÉFINITIVE. Pensez à créer une sauvegarde."),
    ).pack(padx=20, pady=(0, 8))

    cadre = tk.Frame(fenetre)
    cadre.pack(fill="both", expand=True, padx=20)
    colonnes = ("element", "emplacement", "taille")
    arbre = ttk.Treeview(cadre, columns=colonnes, show="headings", height=9)
    arbre.heading("element", text="Élément")
    arbre.heading("emplacement", text="Emplacement")
    arbre.heading("taille", text="Taille")
    arbre.column("element", width=170)
    arbre.column("emplacement", width=380)
    arbre.column("taille", width=80, anchor="e")
    defil = ttk.Scrollbar(cadre, orient="vertical", command=arbre.yview)
    arbre.configure(yscrollcommand=defil.set)
    arbre.pack(side="left", fill="both", expand=True)
    defil.pack(side="right", fill="y")

    statut = tk.Label(fenetre, anchor="w", font=("Segoe UI", 10))
    statut.pack(fill="x", padx=20, pady=(8, 0))

    def actualiser():
        nonlocal elements
        elements = scanner(dossiers)
        arbre.delete(*arbre.get_children())
        for el in elements:
            arbre.insert("", "end", values=(
                os.path.basename(el["chemin"]), el["dossier"],
                formater_taille(el["taille"])))
        if elements:
            total = sum(e["taille"] for e in elements)
            statut.config(text=f"{len(elements)} élément(s) trouvé(s) — "
                               f"{formater_taille(total)} au total.", fg="black")
            bouton_sauv.config(state="normal")
            bouton_suppr.config(state="normal")
        else:
            statut.config(text="Aucun fichier résiduel trouvé : "
                               "votre ordinateur est propre.", fg="#1a7f37")
            bouton_sauv.config(state="disabled")
            bouton_suppr.config(state="disabled")

    def ajouter_dossier():
        d = filedialog.askdirectory(
            title="Dossier où le logiciel était lancé (version non compilée)")
        if d and d not in dossiers:
            dossiers.append(d)
        actualiser()
        if d and not any(e["dossier"] == d for e in elements):
            messagebox.showinfo("Information",
                                "Aucun fichier du logiciel n'a été trouvé dans ce dossier.")

    def faire_sauvegarde():
        if not elements:
            return
        nom = f"sauvegarde_gestion_stock_{datetime.now():%Y%m%d_%H%M%S}.zip"
        fichier = filedialog.asksaveasfilename(
            title="Enregistrer la sauvegarde", initialfile=nom,
            defaultextension=".zip", filetypes=[("Archive ZIP", "*.zip")])
        if not fichier:
            return
        try:
            sauvegarder(elements, fichier)
            messagebox.showinfo("Sauvegarde terminée", f"Copie enregistrée :\n{fichier}")
        except Exception as e:
            messagebox.showerror("Erreur", f"La sauvegarde a échoué :\n{e}")

    def lancer_suppression():
        if not elements:
            return
        if logiciel_en_cours():
            messagebox.showwarning(
                "Logiciel ouvert",
                "Le logiciel de gestion de stock est encore ouvert.\n"
                "Fermez-le, puis recommencez.")
            return
        if not messagebox.askyesno(
                "Confirmer la suppression définitive",
                f"{len(elements)} élément(s) vont être supprimés DÉFINITIVEMENT "
                "(base de données, factures, logo...).\n\n"
                "Cette action est irréversible. Avez-vous fait une sauvegarde si "
                "vous en avez besoin ?\n\nContinuer ?",
                icon="warning", default="no"):
            return
        supprimes, erreurs = supprimer(elements)
        actualiser()
        if erreurs:
            detail = "\n".join(f"- {os.path.basename(c)} : {m}" for c, m in erreurs)
            messagebox.showwarning(
                "Terminé avec des erreurs",
                f"{len(supprimes)} élément(s) supprimé(s).\n\n"
                f"Impossible de supprimer :\n{detail}")
        else:
            messagebox.showinfo("Terminé",
                                f"{len(supprimes)} élément(s) supprimé(s). "
                                "Il ne reste plus de fichier résiduel.")

    barre = tk.Frame(fenetre)
    barre.pack(fill="x", padx=20, pady=12)
    tk.Button(barre, text="Ajouter un dossier…", command=ajouter_dossier).pack(side="left")
    tk.Button(barre, text="Actualiser", command=actualiser).pack(side="left", padx=6)
    bouton_suppr = tk.Button(barre, text="Supprimer définitivement",
                             bg="#c62828", fg="white", command=lancer_suppression)
    bouton_suppr.pack(side="right")
    bouton_sauv = tk.Button(barre, text="Sauvegarder d'abord…", command=faire_sauvegarde)
    bouton_sauv.pack(side="right", padx=6)

    actualiser()
    fenetre.mainloop()


if __name__ == "__main__":
    lancer_interface()

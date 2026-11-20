"""
Application de gestion PME — Interface principale.
Configuration obligatoire à la première ouverture, stock avec coût moyen
pondéré, ventes, dépenses, clôture journalière verrouillée, rapports
(par date précise et par période), rapport automatique par email.

Lancer avec : python main.py
"""

import os
import shutil
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog
from tkcalendar import DateEntry
from datetime import datetime, date, timedelta
from PIL import Image

import database as db
import facture
import export
from utils import fmt

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

COULEUR_FOND = "#F4F6F9"
COULEUR_CARTE = "#FFFFFF"
COULEUR_TITRE = "#1F2A44"
COULEUR_ACCENT = "#2E6BE6"
COULEUR_DANGER = "#D64545"
COULEUR_SUCCES = "#1E9E5A"


def libelle_role(role):
    if role == "responsable":
        return "Saisi par le Chef"
    if role == "saisie":
        return "Saisi par le Secrétaire"
    return "Charge automatique"


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        db.init_db()

        self.title("Système de Gestion Avancée du Stock v1.0")
        self.geometry("1080x700")
        self.minsize(960, 620)
        self.configure(fg_color=COULEUR_FOND)

        self.role = None  # 'saisie' ou 'responsable'
        self.produits_temp_setup = []  # produits ajoutés pendant l'assistant de configuration
        self._facture_etat = None  # None | "saisie" | "lecture"
        self._facture_en_cours = None  # facture multi-produits en cours de composition

        # Pied de page permanent, affiché sur tous les écrans (empaqueté en
        # premier avec side="bottom" pour réserver sa place tout en bas).
        pied_de_page = ctk.CTkFrame(self, fg_color="#E5E7EB", height=28, corner_radius=0)
        pied_de_page.pack(side="bottom", fill="x")
        pied_de_page.pack_propagate(False)
        ctk.CTkLabel(
            pied_de_page,
            text="Cette application avancée de Stock est produit par Ecom-Academy. Contactez-nous au +22899373635.",
            font=("Segoe UI", 10), text_color="#6B7280",
        ).pack(expand=True)

        self.container = ctk.CTkFrame(self, fg_color=COULEUR_FOND)
        self.container.pack(fill="both", expand=True)

        if not db.configuration_terminee():
            self.afficher_setup_etape1()
        else:
            self.afficher_login()

    def _clear(self):
        for widget in self.container.winfo_children():
            widget.destroy()

    def _nom_entreprise(self):
        config = db.get_configuration()
        return config["nom_entreprise"] if config else "Mon entreprise"

    def _logo_image(self, taille=(48, 48)):
        """Charge le logo enregistré à la configuration, sous forme de CTkImage, ou None."""
        config = db.get_configuration()
        chemin = config.get("logo_path") if config else None
        if not chemin or not os.path.exists(chemin):
            return None
        try:
            img = Image.open(chemin)
            img.thumbnail(taille)
            return ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
        except Exception:
            return None

    # ================= ASSISTANT DE PREMIÈRE CONFIGURATION =================

    def afficher_setup_etape1(self):
        self._clear()
        if not hasattr(self, "_setup_logo_path"):
            self._setup_logo_path = None

        carte = ctk.CTkFrame(self.container, fg_color=COULEUR_CARTE, corner_radius=16, width=520, height=640)
        carte.place(relx=0.5, rely=0.5, anchor="center")
        carte.pack_propagate(False)

        ctk.CTkLabel(carte, text="Configuration initiale", font=("Segoe UI", 20, "bold"),
                     text_color=COULEUR_TITRE).pack(pady=(24, 2))
        ctk.CTkLabel(carte, text="Étape 1 sur 2 — Compte",
                     font=("Segoe UI", 12), text_color="#6B7280").pack(pady=(0, 14))

        # Zone déroulante : garantit que tous les champs restent accessibles
        # même sur un petit écran, sans jamais cacher le bouton "Suivant".
        champs = ctk.CTkScrollableFrame(carte, fg_color="transparent", width=460, height=440)
        champs.pack(fill="both", expand=True, padx=20)

        # --- Logo (facultatif) ---
        logo_frame = ctk.CTkFrame(champs, fg_color="transparent")
        logo_frame.pack(fill="x", pady=(4, 14))
        self._logo_preview_label = ctk.CTkLabel(
            logo_frame, text="Logo", width=64, height=64, fg_color="#F3F4F6",
            corner_radius=8, text_color="#9CA3AF", font=("Segoe UI", 11))
        self._logo_preview_label.pack(side="left")

        def choisir_logo():
            chemin = filedialog.askopenfilename(
                title="Choisir un logo",
                filetypes=[("Images", "*.png *.jpg *.jpeg *.gif *.bmp")],
            )
            if not chemin:
                return
            try:
                img = Image.open(chemin)
                img.thumbnail((64, 64))
                apercu = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
                self._logo_preview_label.configure(image=apercu, text="")
                self._logo_preview_label.image = apercu
                self._setup_logo_path = chemin
            except Exception:
                messagebox.showerror("Erreur", "Impossible de lire ce fichier image.")

        ctk.CTkButton(logo_frame, text="Choisir un logo (facultatif)", height=36, corner_radius=8,
                       fg_color="transparent", border_width=1, border_color="#D1D5DB",
                       text_color=COULEUR_TITRE, command=choisir_logo).pack(side="left", padx=12)

        def ligne(label, show=None):
            ctk.CTkLabel(champs, text=label, font=("Segoe UI", 12), text_color=COULEUR_TITRE).pack(anchor="w", pady=(10, 2))
            e = ctk.CTkEntry(champs, height=38, corner_radius=8, show=show)
            e.pack(fill="x")
            return e

        e_nom_entreprise = ligne("Nom de l'entreprise")
        e_identifiant = ligne("Identifiant (unique pour tout le personnel)")
        e_mdp_saisie = ligne("Mot de passe saisie (comptable / secrétaire)", show="•")
        e_mdp_saisie_confirm = ligne("Confirmer le mot de passe saisie", show="•")
        e_mdp_resp = ligne("Mot de passe responsable", show="•")
        e_mdp_resp_confirm = ligne("Confirmer le mot de passe responsable", show="•")

        # --- Jours de travail par semaine (pour la répartition des charges fixes) ---
        ctk.CTkLabel(champs, text="Nombre de jours de travail par semaine",
                     font=("Segoe UI", 12, "bold"), text_color=COULEUR_TITRE).pack(anchor="w", pady=(14, 4))
        ctk.CTkLabel(champs, text="Utilisé pour répartir automatiquement les charges fixes (loyer, etc.) par jour.",
                     font=("Segoe UI", 10), text_color="#9CA3AF").pack(anchor="w", pady=(0, 6))
        combo_jours_travail = ctk.CTkOptionMenu(champs, values=["7 jours/7", "6 jours/7", "5 jours/7"], width=160)
        combo_jours_travail.set("6 jours/7")
        combo_jours_travail.pack(anchor="w", pady=(0, 8))

        def suivant():
            nom_entreprise = e_nom_entreprise.get().strip()
            identifiant = e_identifiant.get().strip()
            mdp_saisie = e_mdp_saisie.get()
            mdp_resp = e_mdp_resp.get()
            jours_travail_semaine = int(combo_jours_travail.get().split(" ")[0])

            if not all([nom_entreprise, identifiant, mdp_saisie, mdp_resp]):
                messagebox.showerror("Champs manquants", "Tous les champs sont obligatoires (le logo est facultatif).")
                return
            if mdp_saisie != e_mdp_saisie_confirm.get():
                messagebox.showerror("Erreur", "Les deux mots de passe 'saisie' ne correspondent pas.")
                return
            if mdp_resp != e_mdp_resp_confirm.get():
                messagebox.showerror("Erreur", "Les deux mots de passe 'responsable' ne correspondent pas.")
                return
            if mdp_saisie == mdp_resp:
                messagebox.showerror("Erreur", "Le mot de passe saisie et le mot de passe responsable doivent être différents.")
                return

            self._setup_data = dict(
                nom_entreprise=nom_entreprise, identifiant=identifiant,
                mdp_saisie=mdp_saisie, mdp_responsable=mdp_resp,
                logo_path=self._setup_logo_path,
                jours_travail_semaine=jours_travail_semaine,
            )
            self.afficher_setup_etape2()

        ctk.CTkButton(carte, text="Suivant →", height=42, corner_radius=8, fg_color=COULEUR_ACCENT,
                       command=suivant).pack(fill="x", padx=20, pady=(10, 20))

    def afficher_setup_etape2(self):
        self._clear()
        carte = ctk.CTkFrame(self.container, fg_color=COULEUR_CARTE, corner_radius=16, width=580, height=660)
        carte.place(relx=0.5, rely=0.5, anchor="center")
        carte.pack_propagate(False)

        ctk.CTkLabel(carte, text="Configuration initiale", font=("Segoe UI", 20, "bold"),
                     text_color=COULEUR_TITRE).pack(pady=(28, 2))
        ctk.CTkLabel(carte, text="Étape 2 sur 2 — Produits vendus et en stock (obligatoire)",
                     font=("Segoe UI", 12), text_color="#6B7280").pack(pady=(0, 16))

        formulaire = ctk.CTkFrame(carte, fg_color="transparent")
        formulaire.pack(fill="x", padx=32)

        e_nom = ctk.CTkEntry(formulaire, placeholder_text="Nom du produit", height=38, corner_radius=8)
        e_nom.grid(row=0, column=0, sticky="ew", padx=(0, 8), pady=4)
        e_qte = ctk.CTkEntry(formulaire, placeholder_text="Quantité", height=38, corner_radius=8, width=100)
        e_qte.grid(row=0, column=1, pady=4)
        e_achat = ctk.CTkEntry(formulaire, placeholder_text="Coût d'achat unit.", height=38, corner_radius=8, width=130)
        e_achat.grid(row=1, column=0, sticky="ew", padx=(0, 8), pady=4)
        e_vente = ctk.CTkEntry(formulaire, placeholder_text="Prix de vente unit.", height=38, corner_radius=8, width=130)
        e_vente.grid(row=1, column=1, pady=4)
        formulaire.grid_columnconfigure(0, weight=1)

        liste_frame = ctk.CTkScrollableFrame(carte, fg_color="#F9FAFB", corner_radius=10, height=260)
        liste_frame.pack(fill="both", expand=True, padx=32, pady=16)

        def rafraichir_liste():
            for w in liste_frame.winfo_children():
                w.destroy()
            if not self.produits_temp_setup:
                ctk.CTkLabel(liste_frame, text="Aucun produit ajouté pour le moment.",
                             font=("Segoe UI", 12), text_color="#9CA3AF").pack(pady=20)
            for p in self.produits_temp_setup:
                ligne = ctk.CTkFrame(liste_frame, fg_color="transparent")
                ligne.pack(fill="x", pady=4, padx=6)
                ctk.CTkLabel(ligne, text=p["nom"], font=("Segoe UI", 13)).pack(side="left")
                ctk.CTkLabel(ligne, text=f"Achat : {fmt(p['prix_achat'])} / Vente : {fmt(p['prix_vente'])}",
                             font=("Segoe UI", 11), text_color="#6B7280").pack(side="left", padx=12)
                ctk.CTkLabel(ligne, text=f"Qté : {p['quantite']}", font=("Segoe UI", 12),
                             text_color="#6B7280").pack(side="right")

        def ajouter_produit_temp():
            nom = e_nom.get().strip()
            qte_texte = e_qte.get().strip()
            achat_texte = e_achat.get().strip()
            vente_texte = e_vente.get().strip()
            if not nom or not qte_texte or not achat_texte or not vente_texte:
                messagebox.showerror("Erreur", "Le nom, la quantité, le coût d'achat et le prix de vente sont tous obligatoires.")
                return
            try:
                qte = int(qte_texte)
                prix_achat = float(achat_texte)
                prix_vente = float(vente_texte)
                if qte < 0 or prix_achat < 0 or prix_vente < 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Erreur", "Quantité, coût d'achat et prix de vente doivent être des nombres positifs.")
                return
            if any(p["nom"].lower() == nom.lower() for p in self.produits_temp_setup):
                messagebox.showerror("Erreur", "Ce produit a déjà été ajouté.")
                return
            self.produits_temp_setup.append({
                "nom": nom, "quantite": qte, "prix_achat": prix_achat, "prix_vente": prix_vente,
            })
            e_nom.delete(0, "end")
            e_qte.delete(0, "end")
            e_achat.delete(0, "end")
            e_vente.delete(0, "end")
            rafraichir_liste()

        ctk.CTkButton(formulaire, text="+ Ajouter le produit", height=38, corner_radius=8,
                       fg_color=COULEUR_ACCENT, command=ajouter_produit_temp
                       ).grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))

        rafraichir_liste()

        def terminer():
            if not self.produits_temp_setup:
                messagebox.showerror("Configuration incomplète",
                                      "Vous devez ajouter au moins un produit avant de continuer.")
                return

            # Copie le logo choisi dans le dossier de l'application pour
            # qu'il reste accessible même si le fichier d'origine est déplacé.
            logo_source = self._setup_data.get("logo_path")
            if logo_source:
                try:
                    dossier_assets = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
                    os.makedirs(dossier_assets, exist_ok=True)
                    extension = os.path.splitext(logo_source)[1] or ".png"
                    destination = os.path.join(dossier_assets, f"logo{extension}")
                    shutil.copy(logo_source, destination)
                    self._setup_data["logo_path"] = destination
                except Exception:
                    self._setup_data["logo_path"] = None

            db.enregistrer_configuration(**self._setup_data)
            for p in self.produits_temp_setup:
                db.ajouter_produit(p["nom"], quantite_stock=p["quantite"],
                                    prix_achat=p["prix_achat"], prix_vente=p["prix_vente"])
            self.afficher_avertissement_confidentialite()

        bas = ctk.CTkFrame(carte, fg_color="transparent")
        bas.pack(fill="x", padx=32, pady=(0, 24))
        ctk.CTkButton(bas, text="← Retour", height=40, corner_radius=8, fg_color="transparent",
                      text_color=COULEUR_TITRE, border_width=1, border_color="#D1D5DB",
                      command=self.afficher_setup_etape1).pack(side="left")
        ctk.CTkButton(bas, text="Terminer la configuration", height=40, corner_radius=8,
                      fg_color=COULEUR_SUCCES, command=terminer).pack(side="right")

    # ================= AVERTISSEMENT CONFIDENTIALITÉ =================

    def afficher_avertissement_confidentialite(self):
        self._clear()
        carte = ctk.CTkFrame(self.container, fg_color=COULEUR_CARTE, corner_radius=16, width=480, height=340)
        carte.place(relx=0.5, rely=0.5, anchor="center")
        carte.pack_propagate(False)

        ctk.CTkLabel(carte, text="⚠️ Important", font=("Segoe UI", 18, "bold"),
                     text_color=COULEUR_TITRE).pack(pady=(28, 12), padx=32)
        ctk.CTkLabel(
            carte,
            text=("Ce logiciel n'est aucunement pas connecté à internet, par conséquent "
                  "toutes vos données sont conservées sur votre ordinateur. Ecom-Academy "
                  "n'est pas responsable des fuites de données sensibles de votre Entreprise."),
            font=("Segoe UI", 13), text_color="#374151", wraplength=400, justify="left",
        ).pack(padx=32, pady=(0, 24))

        def continuer():
            self.afficher_login()

        ctk.CTkButton(carte, text="J'ai compris", height=42, corner_radius=8, fg_color=COULEUR_ACCENT,
                       command=continuer).pack(padx=32, pady=(0, 28), fill="x")

    # ================= LOGIN =================

    def afficher_login(self):
        self._clear()
        carte = ctk.CTkFrame(self.container, fg_color=COULEUR_CARTE, corner_radius=16, width=380, height=360)
        carte.place(relx=0.5, rely=0.5, anchor="center")
        carte.pack_propagate(False)

        logo = self._logo_image((56, 56))
        if logo:
            ctk.CTkLabel(carte, image=logo, text="").pack(pady=(26, 4))
        ctk.CTkLabel(carte, text=self._nom_entreprise(), font=("Segoe UI", 22, "bold"),
                     text_color=COULEUR_TITRE).pack(pady=(6 if logo else 32, 2))
        ctk.CTkLabel(carte, text="Système de Gestion Avancée du Stock v1.0",
                     font=("Segoe UI", 10), text_color="#9CA3AF").pack(pady=(0, 4))
        ctk.CTkLabel(carte, text="Connexion", font=("Segoe UI", 14), text_color="#6B7280").pack(pady=(0, 20))

        self.entry_id = ctk.CTkEntry(carte, placeholder_text="Identifiant", width=280, height=40, corner_radius=8)
        self.entry_id.pack(pady=8)
        self.entry_mdp = ctk.CTkEntry(carte, placeholder_text="Mot de passe", show="•", width=280, height=40, corner_radius=8)
        self.entry_mdp.pack(pady=8)

        ctk.CTkButton(carte, text="Se connecter", width=280, height=40, corner_radius=8,
                       fg_color=COULEUR_ACCENT, command=self.login).pack(pady=(20, 6))
        self.entry_mdp.bind("<Return>", lambda e: self.login())

    def login(self):
        identifiant = self.entry_id.get().strip()
        mdp = self.entry_mdp.get().strip()
        role = db.verify_login(identifiant, mdp)
        if role is None:
            messagebox.showerror("Connexion refusée", "Identifiant ou mot de passe incorrect.")
            return
        self.role = role
        self._facture_etat = None
        self._facture_en_cours = None
        self.afficher_dashboard()

    # ================= SHELL (barre latérale + contenu) =================

    def afficher_shell(self, page_active, contenu_builder):
        self._clear()

        racine = ctk.CTkFrame(self.container, fg_color=COULEUR_FOND)
        racine.pack(fill="both", expand=True)

        shell = ctk.CTkFrame(racine, fg_color=COULEUR_FOND)
        shell.pack(side="top", fill="both", expand=True)

        sidebar = ctk.CTkFrame(shell, fg_color=COULEUR_CARTE, width=220, corner_radius=0)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        entete = ctk.CTkFrame(sidebar, fg_color="transparent")
        entete.pack(fill="x", padx=20, pady=(28, 4))
        logo = self._logo_image((32, 32))
        if logo:
            ctk.CTkLabel(entete, image=logo, text="").pack(side="left", padx=(0, 8))
        ctk.CTkLabel(entete, text=self._nom_entreprise(), font=("Segoe UI", 16, "bold"),
                     text_color=COULEUR_TITRE, wraplength=150, justify="left").pack(side="left")

        role_label = "Responsable" if self.role == "responsable" else "Saisie"
        ctk.CTkLabel(sidebar, text=role_label, font=("Segoe UI", 11), text_color="#6B7280").pack(pady=(0, 24), padx=20, anchor="w")

        pages = [
            ("Tableau de bord", self.afficher_dashboard),
            ("Ventes", self.afficher_ventes),
            ("Produits / Stock", self.afficher_produits),
            ("Stock final", self.afficher_stock_final),
            ("Dépenses", self.afficher_depenses),
            ("Clôture du jour", self.afficher_cloture),
            ("Rapports", self.afficher_rapports),
        ]
        for label, action in pages:
            actif = (label == page_active)
            ctk.CTkButton(
                sidebar, text=label, anchor="w", height=42, corner_radius=8,
                fg_color=COULEUR_ACCENT if actif else "transparent",
                text_color="white" if actif else COULEUR_TITRE,
                hover_color="#E8EEFC", command=action,
            ).pack(fill="x", padx=14, pady=4)

        ctk.CTkButton(sidebar, text="Déconnexion", anchor="w", height=42, corner_radius=8,
                       fg_color="transparent", text_color=COULEUR_DANGER, hover_color="#FBE7E7",
                       command=self.afficher_login).pack(fill="x", padx=14, pady=(30, 10), side="bottom")

        if self.role == "responsable":
            ctk.CTkButton(
                sidebar, text="⚙ Options avancées", anchor="w", height=42, corner_radius=8,
                fg_color=COULEUR_ACCENT if page_active == "Options avancées" else "transparent",
                text_color="white" if page_active == "Options avancées" else COULEUR_TITRE,
                hover_color="#E8EEFC", command=self.afficher_options_avancees,
            ).pack(fill="x", padx=14, pady=(4, 0), side="bottom")

        contenu = ctk.CTkFrame(shell, fg_color=COULEUR_FOND)
        contenu.pack(side="left", fill="both", expand=True, padx=32, pady=28)
        contenu_builder(contenu)

    # ================= DASHBOARD =================

    def afficher_dashboard(self):
        self.afficher_shell("Tableau de bord", self._construire_dashboard)

    def _construire_dashboard(self, parent):
        journee = db.get_or_create_journee_du_jour()
        ventes = db.ventes_du_jour(journee["id"])
        depenses = db.depenses_du_jour(journee["id"])
        ca = sum(v["montant_total"] for v in ventes)
        total_dep = sum(d["montant"] for d in depenses)
        marge = ca - total_dep
        stock_bas = db.produits_stock_bas()

        ctk.CTkLabel(parent, text="Tableau de bord", font=("Segoe UI", 22, "bold"), text_color=COULEUR_TITRE).pack(anchor="w")
        statut_txt = "🔒 Journée clôturée" if journee["statut"] == "cloturee" else "🟢 Journée en cours"
        ctk.CTkLabel(parent, text=f"{datetime.now().strftime('%d/%m/%Y')} — {statut_txt}",
                     font=("Segoe UI", 13), text_color="#6B7280").pack(anchor="w", pady=(0, 20))

        cartes = ctk.CTkFrame(parent, fg_color=COULEUR_FOND)
        cartes.pack(fill="x", pady=(0, 8))
        self._carte_stat(cartes, "Chiffre d'affaires du jour", f"{fmt(ca)} FCFA", COULEUR_SUCCES).pack(side="left", padx=(0, 16))
        self._carte_stat(cartes, "Dépenses du jour", f"{fmt(total_dep)} FCFA", COULEUR_DANGER).pack(side="left", padx=(0, 16))
        self._carte_stat(cartes, "Marge du jour", f"{fmt(marge)} FCFA", COULEUR_ACCENT).pack(side="left")

        # --- Résumé de la journée précédente, en plus petit ---
        hier = (date.today() - timedelta(days=1)).isoformat()
        journee_hier = db.rapport_journee_par_date(hier)
        if journee_hier:
            marge_hier = journee_hier["chiffre_affaires"] - journee_hier["total_depenses"]
            ctk.CTkLabel(
                parent,
                text=(f"Hier ({journee_hier['date_jour']}) — "
                      f"CA : {fmt(journee_hier['chiffre_affaires'])} FCFA · "
                      f"Dépenses : {fmt(journee_hier['total_depenses'])} FCFA · "
                      f"Marge : {fmt(marge_hier)} FCFA"),
                font=("Segoe UI", 11), text_color="#9CA3AF",
            ).pack(anchor="w", pady=(2, 20))
        else:
            ctk.CTkLabel(parent, text="Hier — aucune donnée enregistrée.",
                         font=("Segoe UI", 11), text_color="#9CA3AF").pack(anchor="w", pady=(2, 20))

        if stock_bas:
            alerte = ctk.CTkFrame(parent, fg_color="#FFF4E5", corner_radius=10)
            alerte.pack(fill="x", pady=(0, 20))
            noms = ", ".join(p["nom"] for p in stock_bas[:5])
            ctk.CTkLabel(alerte, text=f"⚠️ Stock bas : {noms}", font=("Segoe UI", 12, "bold"),
                         text_color="#92400E").pack(anchor="w", padx=16, pady=10)

    def _carte_stat(self, parent, titre, valeur, couleur):
        carte = ctk.CTkFrame(parent, fg_color=COULEUR_CARTE, corner_radius=14, width=250, height=110)
        carte.pack_propagate(False)
        ctk.CTkLabel(carte, text=titre, font=("Segoe UI", 12), text_color="#6B7280").pack(anchor="w", padx=18, pady=(18, 4))
        ctk.CTkLabel(carte, text=valeur, font=("Segoe UI", 22, "bold"), text_color=couleur).pack(anchor="w", padx=18)
        return carte

    # ================= VENTES =================

    def afficher_ventes(self):
        self.afficher_shell("Ventes", self._construire_ventes)

    def _construire_ventes(self, parent):
        journee = db.get_or_create_journee_du_jour()
        verrouille = journee["statut"] == "cloturee"

        ctk.CTkLabel(parent, text="Ventes", font=("Segoe UI", 22, "bold"), text_color=COULEUR_TITRE).pack(anchor="w", pady=(0, 4))
        if verrouille:
            ctk.CTkLabel(parent, text="🔒 La journée est clôturée. Demandez une autorisation au responsable pour saisir.",
                         font=("Segoe UI", 12), text_color=COULEUR_DANGER).pack(anchor="w", pady=(0, 16))

        zone_haute = ctk.CTkFrame(parent, fg_color="transparent")
        zone_haute.pack(fill="both", expand=True)

        etat = getattr(self, "_facture_etat", None)  # None | "saisie" | "lecture"

        if etat == "saisie":
            self._construire_saisie_facture(zone_haute, verrouille)
        elif etat == "lecture":
            self._construire_lecture_facture(zone_haute, verrouille)
        else:
            self._construire_accueil_ventes(zone_haute, verrouille, journee)

    def _construire_accueil_ventes(self, parent, verrouille, journee):
        ctk.CTkButton(
            parent, text="🧾 Vendre", height=48, width=200, corner_radius=10,
            font=("Segoe UI", 15, "bold"), fg_color=COULEUR_ACCENT,
            state="disabled" if verrouille else "normal",
            command=self._demarrer_nouvelle_facture,
        ).pack(anchor="w", pady=(6, 20))

        ctk.CTkLabel(parent, text="Factures du jour", font=("Segoe UI", 15, "bold"),
                     text_color=COULEUR_TITRE).pack(anchor="w", pady=(0, 8))
        liste = ctk.CTkScrollableFrame(parent, fg_color=COULEUR_CARTE, corner_radius=14, height=280)
        liste.pack(fill="both", expand=True)
        factures_jour = db.factures_du_jour(journee["id"])
        if not factures_jour:
            ctk.CTkLabel(liste, text="Aucune facture enregistrée pour le moment.",
                         font=("Segoe UI", 12), text_color="#9CA3AF").pack(pady=16)
        for fct in factures_jour:
            ligne = ctk.CTkFrame(liste, fg_color="transparent")
            ligne.pack(fill="x", pady=6, padx=10)
            heure = fct["date_facture"][11:16] if len(fct["date_facture"]) >= 16 else ""
            ctk.CTkLabel(ligne, text=f"N° {fct['numero']}", font=("Segoe UI", 13, "bold"),
                         text_color=COULEUR_TITRE).pack(side="left")
            ctk.CTkLabel(ligne, text=heure, font=("Segoe UI", 12), text_color="#6B7280").pack(side="left", padx=12)
            ctk.CTkLabel(ligne, text=libelle_role(fct["role"]), font=("Segoe UI", 10, "italic"),
                         text_color="#9CA3AF").pack(side="left", padx=12)
            ctk.CTkLabel(ligne, text=f"{fmt(fct['montant_total'])} FCFA", font=("Segoe UI", 13, "bold"),
                         text_color=COULEUR_SUCCES).pack(side="right")
            ctk.CTkButton(ligne, text="Voir le détail", width=110, height=28, fg_color="transparent",
                           border_width=1, border_color="#D1D5DB", text_color=COULEUR_TITRE,
                           command=lambda fid=fct["id"]: self._afficher_detail_facture(fid)
                           ).pack(side="right", padx=(0, 16))

    def _afficher_detail_facture(self, facture_id):
        fct = db.get_facture(facture_id)
        if fct is None:
            return

        fenetre = ctk.CTkToplevel(self)
        fenetre.title(f"Facture {fct['numero']}")
        fenetre.geometry("520x560")
        fenetre.grab_set()

        ctk.CTkLabel(fenetre, text=f"Facture {fct['numero']}", font=("Segoe UI", 16, "bold")).pack(pady=(20, 4))
        if fct["client"]:
            c = fct["client"]
            infos_client = " — ".join(x for x in [c.get("nom"), c.get("telephone"), c.get("adresse")] if x)
            ctk.CTkLabel(fenetre, text=f"Client : {infos_client}", font=("Segoe UI", 15, "bold"),
                         text_color=COULEUR_TITRE).pack(pady=(0, 8))

        zone = ctk.CTkScrollableFrame(fenetre, fg_color=COULEUR_CARTE, corner_radius=12, width=460, height=280)
        zone.pack(padx=20, pady=(4, 10), fill="both", expand=True)

        ctk.CTkLabel(zone, text=f"{libelle_role(fct['role'])} — {fct['date_facture']}",
                     font=("Segoe UI", 10, "italic"), text_color="#9CA3AF").pack(anchor="w", padx=8, pady=(6, 4))

        entete = ctk.CTkFrame(zone, fg_color="#F3F4F6")
        entete.pack(fill="x")
        ctk.CTkLabel(entete, text="Désignation", font=("Segoe UI", 12, "bold"), width=180, anchor="w").pack(side="left", padx=8, pady=8)
        ctk.CTkLabel(entete, text="Qté", font=("Segoe UI", 12, "bold"), width=50, anchor="e").pack(side="left", padx=8, pady=8)
        ctk.CTkLabel(entete, text="P.U.", font=("Segoe UI", 12, "bold"), width=90, anchor="e").pack(side="left", padx=8, pady=8)
        ctk.CTkLabel(entete, text="Montant", font=("Segoe UI", 12, "bold"), width=100, anchor="e").pack(side="left", padx=8, pady=8)

        for l in fct["lignes"]:
            ligne = ctk.CTkFrame(zone, fg_color="transparent")
            ligne.pack(fill="x")
            ctk.CTkLabel(ligne, text=l["produit_nom"], width=180, anchor="w").pack(side="left", padx=8, pady=4)
            ctk.CTkLabel(ligne, text=str(l["quantite"]), width=50, anchor="e").pack(side="left", padx=8, pady=4)
            ctk.CTkLabel(ligne, text=fmt(l["prix_unitaire"]), width=90, anchor="e").pack(side="left", padx=8, pady=4)
            ctk.CTkLabel(ligne, text=fmt(l["montant_total"]), width=100, anchor="e").pack(side="left", padx=8, pady=4)

        ctk.CTkFrame(fenetre, fg_color="black", height=2).pack(fill="x", padx=20, pady=(6, 6))

        def ligne_total(libelle, valeur, couleur=COULEUR_TITRE, gras=False):
            l = ctk.CTkFrame(fenetre, fg_color="transparent")
            l.pack(fill="x", padx=20)
            ctk.CTkLabel(l, text=f"{libelle} {fmt(valeur)} FCFA", font=("Segoe UI", 13, "bold" if gras else "normal"),
                         text_color=couleur).pack(side="left", pady=2)

        ligne_total("Sous-total :", fct["sous_total"])
        if fct["montant_remise"] > 0:
            ligne_total("Remise :", -fct["montant_remise"], couleur=COULEUR_DANGER)
        if fct["tva_active"]:
            ligne_total(f"TVA {fct['tva_taux']:.0f}% :", fct["montant_tva"])
        ligne_total("MONTANT À PAYER :", fct["montant_total"], couleur=COULEUR_SUCCES, gras=True)

        ctk.CTkButton(fenetre, text="Fermer", fg_color=COULEUR_ACCENT, command=fenetre.destroy).pack(pady=16)

    def _demarrer_nouvelle_facture(self):
        self._facture_etat = "saisie"
        self._facture_en_cours = {
            "lignes": [],  # {produit_id, produit, quantite, prix_unitaire, montant}
            "client_nom": "", "client_telephone": "", "client_adresse": "",
            "remise_montant": 0, "remise_pourcentage": 0, "tva_active": False,
            "facture_db": None,  # rempli une fois réellement enregistrée en base
        }
        self.afficher_ventes()

    def _construire_saisie_facture(self, parent, verrouille):
        f = self._facture_en_cours
        produits = db.liste_produits()
        noms_produits = [p["nom"] for p in produits] or ["Aucun produit"]
        clients = db.liste_clients()

        def libelle_client(c):
            return c["nom"] if c["nom"] else f"Client #{c['id']} ({c['telephone']})"

        noms_clients = ["(Nouveau client)"] + [libelle_client(c) for c in clients]

        ctk.CTkLabel(parent, text="Ajouter des produits à la facture", font=("Segoe UI", 16, "bold"),
                     text_color=COULEUR_TITRE).pack(anchor="w", pady=(0, 10))

        formulaire = ctk.CTkFrame(parent, fg_color=COULEUR_CARTE, corner_radius=14)
        formulaire.pack(fill="x", pady=(0, 16))

        ctk.CTkLabel(formulaire, text="Produit", font=("Segoe UI", 12)).grid(row=0, column=0, padx=16, pady=(16, 4), sticky="w")
        ctk.CTkLabel(formulaire, text="Quantité", font=("Segoe UI", 12)).grid(row=0, column=1, padx=8, pady=(16, 4), sticky="w")
        ctk.CTkLabel(formulaire, text="Prix unitaire", font=("Segoe UI", 12)).grid(row=0, column=2, padx=8, pady=(16, 4), sticky="w")
        ctk.CTkLabel(formulaire, text="Montant", font=("Segoe UI", 12)).grid(row=0, column=3, padx=8, pady=(16, 4), sticky="w")
        ctk.CTkLabel(formulaire, text="Stock disponible", font=("Segoe UI", 12)).grid(row=0, column=4, padx=8, pady=(16, 4), sticky="w")

        label_prix_unitaire = ctk.CTkLabel(formulaire, text="—", font=("Segoe UI", 14, "bold"), text_color=COULEUR_TITRE)
        label_total = ctk.CTkLabel(formulaire, text="0 FCFA", font=("Segoe UI", 15, "bold"), text_color=COULEUR_SUCCES)
        label_stock_disponible = ctk.CTkLabel(formulaire, text="—", font=("Segoe UI", 14, "bold"), text_color="#6B7280")

        def deja_dans_facture(produit_id):
            return sum(l["quantite"] for l in f["lignes"] if l["produit_id"] == produit_id)

        def produit_selectionne():
            return next((p for p in produits if p["nom"] == combo_produit.get()), None)

        def maj_affichage(*_):
            p = produit_selectionne()
            try:
                qte = int(entry_qte.get())
            except ValueError:
                qte = 0
            if p:
                stock_restant = p["quantite_stock"] - deja_dans_facture(p["id"])
                label_prix_unitaire.configure(text=f"{fmt(p['prix_vente'])} FCFA")
                label_total.configure(text=f"{fmt(p['prix_vente'] * max(qte, 0))} FCFA")
                label_stock_disponible.configure(
                    text=f"{stock_restant} unité(s)",
                    text_color=COULEUR_DANGER if stock_restant <= p["seuil_alerte"] else "#6B7280",
                )
            else:
                label_prix_unitaire.configure(text="—")
                label_total.configure(text="0 FCFA")
                label_stock_disponible.configure(text="—", text_color="#6B7280")

        combo_produit = ctk.CTkOptionMenu(formulaire, values=noms_produits, width=200, command=lambda _: maj_affichage())
        combo_produit.grid(row=1, column=0, padx=16, pady=(0, 16))

        entry_qte = ctk.CTkEntry(formulaire, width=90)
        entry_qte.insert(0, "1")
        entry_qte.grid(row=1, column=1, padx=8, pady=(0, 16))
        entry_qte.bind("<KeyRelease>", maj_affichage)

        label_prix_unitaire.grid(row=1, column=2, padx=8, pady=(0, 16))
        label_total.grid(row=1, column=3, padx=8, pady=(0, 16))
        label_stock_disponible.grid(row=1, column=4, padx=8, pady=(0, 16))

        if produits:
            maj_affichage()

        def ajouter_ligne():
            p = produit_selectionne()
            if p is None:
                messagebox.showerror("Erreur", "Sélectionnez un produit valide.")
                return
            try:
                qte = int(entry_qte.get())
                if qte <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Erreur", "La quantité doit être un entier supérieur à zéro.")
                return
            if p["quantite_stock"] - deja_dans_facture(p["id"]) < qte:
                messagebox.showerror("Erreur", "Stock insuffisant pour cette quantité.")
                return
            f["lignes"].append({
                "produit_id": p["id"], "produit": p["nom"], "quantite": qte,
                "prix_unitaire": p["prix_vente"], "montant": p["prix_vente"] * qte,
            })
            self.afficher_ventes()

        ctk.CTkButton(formulaire, text="Enregistrer ce produit dans la facture", fg_color=COULEUR_SUCCES,
                       command=ajouter_ligne).grid(row=2, column=0, columnspan=5, padx=16, pady=(4, 16), sticky="ew")

        # --- Lignes déjà ajoutées ---
        if f["lignes"]:
            ctk.CTkLabel(parent, text="Produits ajoutés à cette facture", font=("Segoe UI", 13, "bold"),
                         text_color=COULEUR_TITRE).pack(anchor="w", pady=(0, 6))
            liste_lignes = ctk.CTkFrame(parent, fg_color=COULEUR_CARTE, corner_radius=14)
            liste_lignes.pack(fill="x", pady=(0, 16))
            for l in f["lignes"]:
                ligne = ctk.CTkFrame(liste_lignes, fg_color="transparent")
                ligne.pack(fill="x", padx=16, pady=6)
                ctk.CTkLabel(ligne, text=l["produit"], font=("Segoe UI", 13)).pack(side="left")
                ctk.CTkLabel(ligne, text=f"{l['quantite']} x {fmt(l['prix_unitaire'])} FCFA",
                             font=("Segoe UI", 12), text_color="#6B7280").pack(side="left", padx=16)
                ctk.CTkLabel(ligne, text=f"{fmt(l['montant'])} FCFA", font=("Segoe UI", 13, "bold"),
                             text_color=COULEUR_SUCCES).pack(side="right")

        # --- Client (facultatif) ---
        ctk.CTkLabel(parent, text="Client (facultatif)", font=("Segoe UI", 13, "bold"),
                     text_color=COULEUR_TITRE).pack(anchor="w", pady=(0, 6))
        carte_client = ctk.CTkFrame(parent, fg_color=COULEUR_CARTE, corner_radius=14)
        carte_client.pack(fill="x", pady=(0, 16))

        entry_nom_client = ctk.CTkEntry(carte_client, placeholder_text="Nom du client", width=200)
        entry_tel_client = ctk.CTkEntry(carte_client, placeholder_text="Téléphone", width=150)
        entry_adresse_client = ctk.CTkEntry(carte_client, placeholder_text="Adresse", width=200)
        entry_nom_client.insert(0, f["client_nom"])
        entry_tel_client.insert(0, f["client_telephone"])
        entry_adresse_client.insert(0, f["client_adresse"])

        def client_selectionne(valeur):
            if valeur == "(Nouveau client)":
                return
            c = next((c for c in clients if libelle_client(c) == valeur), None)
            if c:
                entry_nom_client.delete(0, "end"); entry_nom_client.insert(0, c["nom"] or "")
                entry_tel_client.delete(0, "end"); entry_tel_client.insert(0, c["telephone"] or "")
                entry_adresse_client.delete(0, "end"); entry_adresse_client.insert(0, c["adresse"] or "")

        combo_client = ctk.CTkOptionMenu(carte_client, values=noms_clients, width=200, command=client_selectionne)
        combo_client.grid(row=0, column=0, padx=16, pady=16)
        entry_nom_client.grid(row=0, column=1, padx=8, pady=16)
        entry_tel_client.grid(row=0, column=2, padx=8, pady=16)
        entry_adresse_client.grid(row=0, column=3, padx=8, pady=16)

        def terminer():
            if not f["lignes"]:
                messagebox.showerror("Erreur", "Ajoutez au moins un produit avant de terminer la facture.")
                return
            f["client_nom"] = entry_nom_client.get().strip()
            f["client_telephone"] = entry_tel_client.get().strip()
            f["client_adresse"] = entry_adresse_client.get().strip()
            self._facture_etat = "lecture"
            self.afficher_ventes()

        def annuler():
            self._facture_etat = None
            self._facture_en_cours = None
            self.afficher_ventes()

        boutons = ctk.CTkFrame(parent, fg_color="transparent")
        boutons.pack(fill="x", pady=(0, 20))
        ctk.CTkButton(boutons, text="Terminé", fg_color=COULEUR_ACCENT, height=42,
                       command=terminer).pack(side="left", padx=(0, 10))
        ctk.CTkButton(boutons, text="Annuler la facture", fg_color="transparent", border_width=1,
                       border_color="#D1D5DB", text_color=COULEUR_DANGER, command=annuler).pack(side="left")

    def _construire_lecture_facture(self, parent, verrouille):
        f = self._facture_en_cours
        deja_enregistree = f.get("facture_db") is not None

        sous_total = sum(l["montant"] for l in f["lignes"])
        montant_remise = f["remise_montant"] if f["remise_montant"] > 0 else round(sous_total * f["remise_pourcentage"] / 100, 2)
        montant_remise = min(montant_remise, sous_total)
        apres_remise = sous_total - montant_remise
        montant_tva = round(apres_remise * 0.18, 2) if f["tva_active"] else 0
        montant_total = apres_remise + montant_tva

        titre = "Facture enregistrée" if deja_enregistree else "Aperçu de la facture (pas encore enregistrée)"
        couleur_titre = COULEUR_SUCCES if deja_enregistree else "#92400E"
        numero = f["facture_db"]["numero"] if deja_enregistree else "(à générer à l'enregistrement)"

        ctk.CTkLabel(parent, text=titre, font=("Segoe UI", 16, "bold"), text_color=couleur_titre).pack(anchor="w", pady=(0, 2))
        ctk.CTkLabel(parent, text=f"N° {numero}", font=("Segoe UI", 12), text_color="#6B7280").pack(anchor="w", pady=(0, 4))
        if f["client_nom"] or f["client_telephone"]:
            infos_client = " — ".join(x for x in [f["client_nom"], f["client_telephone"], f["client_adresse"]] if x)
            ctk.CTkLabel(parent, text=f"Client : {infos_client}", font=("Segoe UI", 15, "bold"),
                         text_color=COULEUR_TITRE).pack(anchor="w", pady=(0, 10))

        # --- Tableau Désignation / Quantité / Prix unitaire / Montant ---
        tableau = ctk.CTkFrame(parent, fg_color=COULEUR_CARTE, corner_radius=14)
        tableau.pack(fill="x", pady=(6, 16))

        role_aff = f["facture_db"]["role"] if deja_enregistree else self.role
        date_aff = f["facture_db"]["date_facture"] if deja_enregistree else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ctk.CTkLabel(tableau, text=f"{libelle_role(role_aff)} — {date_aff}", font=("Segoe UI", 10, "italic"),
                     text_color="#9CA3AF").pack(anchor="w", padx=12, pady=(10, 0))

        entete = ctk.CTkFrame(tableau, fg_color="#F3F4F6")
        entete.pack(fill="x", pady=(8, 0))
        ctk.CTkLabel(entete, text="Désignation", font=("Segoe UI", 12, "bold"), width=220, anchor="w").pack(side="left", padx=12, pady=10)
        ctk.CTkLabel(entete, text="Quantité", font=("Segoe UI", 12, "bold"), width=90, anchor="e").pack(side="left", padx=12, pady=10)
        ctk.CTkLabel(entete, text="Prix unitaire", font=("Segoe UI", 12, "bold"), width=120, anchor="e").pack(side="left", padx=12, pady=10)
        ctk.CTkLabel(entete, text="Montant", font=("Segoe UI", 12, "bold"), width=120, anchor="e").pack(side="left", padx=12, pady=10)

        for l in f["lignes"]:
            ligne = ctk.CTkFrame(tableau, fg_color="transparent")
            ligne.pack(fill="x")
            ctk.CTkLabel(ligne, text=l["produit"], width=220, anchor="w").pack(side="left", padx=12, pady=4)
            ctk.CTkLabel(ligne, text=str(l["quantite"]), width=90, anchor="e").pack(side="left", padx=12, pady=4)
            ctk.CTkLabel(ligne, text=f"{fmt(l['prix_unitaire'])}", width=120, anchor="e").pack(side="left", padx=12, pady=4)
            ctk.CTkLabel(ligne, text=f"{fmt(l['montant'])}", width=120, anchor="e").pack(side="left", padx=12, pady=4)

        # Trait noir séparant la liste des produits des montants (sous-total, remise, TVA, total)
        ctk.CTkFrame(tableau, fg_color="black", height=2, corner_radius=0).pack(fill="x", padx=12, pady=(8, 4))

        pied_tableau = ctk.CTkFrame(tableau, fg_color="transparent")
        pied_tableau.pack(fill="x", pady=(0, 4))

        def ligne_totaux(libelle, valeur, couleur=COULEUR_TITRE, gras=False):
            l = ctk.CTkFrame(pied_tableau, fg_color="transparent")
            l.pack(fill="x")
            ctk.CTkLabel(l, text=f"{libelle} {fmt(valeur)} FCFA", font=("Segoe UI", 13, "bold" if gras else "normal"),
                         text_color=couleur).pack(side="left", padx=12, pady=2)

        ligne_totaux("Sous-total :", sous_total)
        if montant_remise > 0:
            ligne_totaux("Remise :", -montant_remise, couleur=COULEUR_DANGER)
        if f["tva_active"]:
            ligne_totaux("TVA 18% :", montant_tva)
        ligne_totaux("MONTANT À PAYER :", montant_total, couleur=COULEUR_SUCCES, gras=True)
        ctk.CTkFrame(tableau, fg_color="transparent", height=6).pack()

        # --- Remise / TVA (avant enregistrement uniquement) ---
        if not deja_enregistree:
            options = ctk.CTkFrame(parent, fg_color="transparent")
            options.pack(fill="x", pady=(0, 10))

            def ouvrir_remise():
                self._afficher_dialogue_remise(f)

            def basculer_tva():
                f["tva_active"] = not f["tva_active"]
                self.afficher_ventes()

            ctk.CTkButton(options, text="Remise", fg_color="transparent", border_width=1,
                           border_color="#D1D5DB", text_color=COULEUR_TITRE, command=ouvrir_remise).pack(side="left", padx=(0, 10))
            texte_tva = "✓ TVA 18% activée" if f["tva_active"] else "TVA 18%"
            ctk.CTkButton(options, text=texte_tva,
                           fg_color=COULEUR_ACCENT if f["tva_active"] else "transparent",
                           text_color="white" if f["tva_active"] else COULEUR_TITRE,
                           border_width=1, border_color="#D1D5DB", command=basculer_tva).pack(side="left")

        # --- Actions ---
        def enregistrer():
            if deja_enregistree or verrouille:
                return
            try:
                client_id = db.trouver_ou_creer_client(f["client_nom"], f["client_telephone"], f["client_adresse"])
                lignes_db = [{"produit_id": l["produit_id"], "quantite": l["quantite"], "prix_unitaire": l["prix_unitaire"]}
                             for l in f["lignes"]]
                facture_db = db.enregistrer_facture(
                    lignes_db, self.role, client_id=client_id,
                    remise_montant=f["remise_montant"], remise_pourcentage=f["remise_pourcentage"],
                    tva_active=f["tva_active"], tva_taux=18,
                )
                f["facture_db"] = facture_db
                self.afficher_ventes()
            except (PermissionError, ValueError) as e:
                messagebox.showerror("Erreur", str(e))

        def modifier():
            self._facture_etat = "saisie"
            self.afficher_ventes()

        def retour():
            self._facture_etat = None
            self._facture_en_cours = None
            self.afficher_ventes()

        def imprimer():
            lignes_texte = "\n".join(
                f"  {l['produit']:<28} {l['quantite']:>4}  x {l['prix_unitaire']:>10,.0f}  = {l['montant']:>12,.0f} FCFA"
                for l in f["lignes"]
            )
            info = {
                "numero": f["facture_db"]["numero"] if deja_enregistree else "provisoire",
                "nom_entreprise": self._nom_entreprise(),
                "date": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "produit": lignes_texte, "quantite": "", "prix_unitaire": 0,
                "montant_total": montant_total,
                "client_nom": f["client_nom"], "client_telephone": f["client_telephone"], "client_adresse": f["client_adresse"],
            }
            chemin = facture.enregistrer_facture_fichier(info)
            ok, message = facture.imprimer_facture(chemin)
            messagebox.showinfo("Impression", message)

        boutons = ctk.CTkFrame(parent, fg_color="transparent")
        boutons.pack(fill="x", pady=(6, 20))

        if deja_enregistree:
            ctk.CTkButton(boutons, text="Retour", fg_color=COULEUR_ACCENT, command=retour).pack(side="left", padx=(0, 10))
            ctk.CTkButton(boutons, text="Imprimer", fg_color=COULEUR_ACCENT, command=imprimer).pack(side="left")
        else:
            ctk.CTkButton(boutons, text="Enregistrer", fg_color=COULEUR_SUCCES,
                           state="disabled" if verrouille else "normal", command=enregistrer).pack(side="left", padx=(0, 10))
            ctk.CTkButton(boutons, text="Modifier", fg_color="transparent", border_width=1, border_color="#D1D5DB",
                           text_color=COULEUR_TITRE, command=modifier).pack(side="left", padx=(0, 10))
            ctk.CTkButton(boutons, text="Imprimer", fg_color=COULEUR_ACCENT, command=imprimer).pack(side="left")

    def _afficher_dialogue_remise(self, f):
        fenetre = ctk.CTkToplevel(self)
        fenetre.title("Remise")
        fenetre.geometry("340x260")
        fenetre.grab_set()

        ctk.CTkLabel(fenetre, text="Appliquer une remise", font=("Segoe UI", 15, "bold")).pack(pady=(20, 10))

        ctk.CTkLabel(fenetre, text="Montant fixe (FCFA)", font=("Segoe UI", 12)).pack(anchor="w", padx=24)
        entry_montant = ctk.CTkEntry(fenetre, width=200)
        entry_montant.insert(0, str(f["remise_montant"] or ""))
        entry_montant.pack(padx=24, pady=(2, 12))

        ctk.CTkLabel(fenetre, text="OU pourcentage (%)", font=("Segoe UI", 12)).pack(anchor="w", padx=24)
        entry_pourcentage = ctk.CTkEntry(fenetre, width=200)
        entry_pourcentage.insert(0, str(f["remise_pourcentage"] or ""))
        entry_pourcentage.pack(padx=24, pady=(2, 16))

        def appliquer():
            montant = entry_montant.get().strip()
            pourcentage = entry_pourcentage.get().strip()
            try:
                f["remise_montant"] = float(montant) if montant else 0
                f["remise_pourcentage"] = float(pourcentage) if pourcentage else 0
            except ValueError:
                messagebox.showerror("Erreur", "Montant et pourcentage doivent être des nombres.")
                return
            fenetre.destroy()
            self.afficher_ventes()

        ctk.CTkButton(fenetre, text="Appliquer", fg_color=COULEUR_ACCENT, command=appliquer).pack(pady=6)
        ctk.CTkButton(fenetre, text="Annuler", fg_color="transparent", command=fenetre.destroy).pack()

    # ================= PRODUITS / STOCK =================

    def afficher_produits(self):
        self.afficher_shell("Produits / Stock", self._construire_produits)

    def _construire_produits(self, parent):
        ctk.CTkLabel(parent, text="Produits & stock", font=("Segoe UI", 22, "bold"), text_color=COULEUR_TITRE).pack(anchor="w", pady=(0, 16))

        produits = db.liste_produits()
        noms_produits = [p["nom"] for p in produits] or ["Aucun produit"]

        # --- Augmenter le stock d'un produit déjà enregistré ---
        ctk.CTkLabel(parent, text="Augmenter le stock d'un produit existant", font=("Segoe UI", 15, "bold"), text_color=COULEUR_TITRE).pack(anchor="w", pady=(0, 8))
        entree_frame = ctk.CTkFrame(parent, fg_color=COULEUR_CARTE, corner_radius=14)
        entree_frame.pack(fill="x", pady=(0, 20))

        ctk.CTkLabel(entree_frame, text="Produit", font=("Segoe UI", 12)).grid(row=0, column=0, padx=16, pady=16, sticky="w")
        combo_produit = ctk.CTkOptionMenu(entree_frame, values=noms_produits, width=200)
        combo_produit.grid(row=0, column=1, padx=8, pady=16)

        ctk.CTkLabel(entree_frame, text="Quantité entrée", font=("Segoe UI", 12)).grid(row=0, column=2, padx=16, pady=16, sticky="w")
        entry_qte = ctk.CTkEntry(entree_frame, width=110)
        entry_qte.grid(row=0, column=3, padx=8, pady=16)

        ctk.CTkLabel(entree_frame, text="Prix d'achat unitaire", font=("Segoe UI", 12)).grid(row=0, column=4, padx=16, pady=16, sticky="w")
        entry_prix = ctk.CTkEntry(entree_frame, width=120)
        entry_prix.grid(row=0, column=5, padx=8, pady=16)

        ctk.CTkLabel(entree_frame, text="Marge visée % (facultatif)", font=("Segoe UI", 12)
                     ).grid(row=1, column=0, columnspan=2, padx=16, pady=(0, 16), sticky="w")
        entry_marge = ctk.CTkEntry(entree_frame, width=110, placeholder_text="ex: 20")
        entry_marge.grid(row=1, column=2, padx=8, pady=(0, 16), sticky="w")
        ctk.CTkLabel(entree_frame, text="Si rempli, le prix de vente est recalculé automatiquement\nsur la base du nouveau coût moyen pondéré.",
                     font=("Segoe UI", 10), text_color="#9CA3AF", justify="left"
                     ).grid(row=1, column=3, columnspan=4, padx=8, pady=(0, 16), sticky="w")

        def valider_entree():
            nom = combo_produit.get()
            produit = next((p for p in produits if p["nom"] == nom), None)
            if produit is None:
                messagebox.showerror("Erreur", "Sélectionnez un produit valide.")
                return
            try:
                qte = int(entry_qte.get())
                prix = float(entry_prix.get())
                marge_texte = entry_marge.get().strip()
                marge = float(marge_texte) if marge_texte else None
                resultat = db.entree_stock(produit["id"], qte, prix, self.role, marge_pourcentage=marge)
                message = (
                    f"{qte} unité(s) de « {nom} » ajoutée(s).\n"
                    f"Nouveau stock : {resultat['nouveau_stock']}\n"
                    f"Nouveau coût d'achat moyen pondéré : {resultat['nouveau_cmup']:,.2f} FCFA"
                )
                if resultat.get("nouveau_prix_vente") is not None:
                    message += f"\nNouveau prix de vente (marge {marge:.0f}%) : {resultat['nouveau_prix_vente']:,.2f} FCFA"
                messagebox.showinfo("Entrée enregistrée", message)
                self.afficher_produits()
            except ValueError as e:
                messagebox.showerror("Erreur", str(e) if str(e) else "Quantité, prix et marge doivent être des nombres valides.")

        ctk.CTkButton(entree_frame, text="Enregistrer l'entrée", fg_color=COULEUR_ACCENT,
                       command=valider_entree).grid(row=0, column=6, padx=16, pady=16)

        # --- Ajouter un nouveau produit (nécessite le mot de passe responsable) ---
        ctk.CTkLabel(parent, text="Ajouter un nouveau produit au catalogue", font=("Segoe UI", 15, "bold"),
                     text_color=COULEUR_TITRE).pack(anchor="w", pady=(0, 8))
        ajout_frame = ctk.CTkFrame(parent, fg_color=COULEUR_CARTE, corner_radius=14)
        ajout_frame.pack(fill="x", pady=(0, 20))

        entry_nom_nouveau = ctk.CTkEntry(ajout_frame, placeholder_text="Nom du produit", width=180)
        entry_nom_nouveau.grid(row=0, column=0, padx=16, pady=16)
        entry_qte_nouveau = ctk.CTkEntry(ajout_frame, placeholder_text="Quantité initiale", width=120)
        entry_qte_nouveau.grid(row=0, column=1, padx=8, pady=16)
        entry_achat_nouveau = ctk.CTkEntry(ajout_frame, placeholder_text="Coût d'achat", width=120)
        entry_achat_nouveau.grid(row=0, column=2, padx=8, pady=16)
        entry_prix_vente = ctk.CTkEntry(ajout_frame, placeholder_text="Prix de vente", width=120)
        entry_prix_vente.grid(row=0, column=3, padx=8, pady=16)

        ctk.CTkLabel(ajout_frame, text="Mot de passe responsable (obligatoire pour confirmer)",
                     font=("Segoe UI", 11)).grid(row=1, column=0, columnspan=2, padx=16, pady=(0, 16), sticky="w")
        entry_mdp_confirmation = ctk.CTkEntry(ajout_frame, show="•", width=180)
        entry_mdp_confirmation.grid(row=1, column=2, padx=8, pady=(0, 16))

        def ajouter_nouveau():
            nom = entry_nom_nouveau.get().strip()
            if not nom:
                messagebox.showerror("Erreur", "Le nom du produit est obligatoire.")
                return
            if not db.verifier_mot_de_passe_type("responsable", entry_mdp_confirmation.get()):
                messagebox.showerror("Erreur", "Mot de passe responsable incorrect.")
                return
            try:
                qte = int(entry_qte_nouveau.get() or 0)
                prix_achat = float(entry_achat_nouveau.get() or 0)
                prix_vente = float(entry_prix_vente.get() or 0)
                db.ajouter_produit(nom, quantite_stock=qte, prix_achat=prix_achat, prix_vente=prix_vente)
                messagebox.showinfo("Produit ajouté", f"« {nom} » a été ajouté au catalogue.")
                self.afficher_produits()
            except ValueError:
                messagebox.showerror("Erreur", "Quantité, coût d'achat et prix de vente doivent être des nombres valides.")
            except Exception as e:
                messagebox.showerror("Erreur", str(e))

        ctk.CTkButton(ajout_frame, text="Ajouter au catalogue", fg_color=COULEUR_ACCENT,
                       command=ajouter_nouveau).grid(row=1, column=3, padx=16, pady=(0, 16))

        # --- Liste des produits ---
        ctk.CTkLabel(parent, text="Catalogue", font=("Segoe UI", 15, "bold"), text_color=COULEUR_TITRE).pack(anchor="w", pady=(0, 8))
        liste = ctk.CTkScrollableFrame(parent, fg_color=COULEUR_CARTE, corner_radius=14, height=240)
        liste.pack(fill="both", expand=True)
        for p in produits:
            ligne = ctk.CTkFrame(liste, fg_color="transparent")
            ligne.pack(fill="x", pady=6, padx=10)
            ctk.CTkLabel(ligne, text=p["nom"], font=("Segoe UI", 13)).pack(side="left")
            couleur = COULEUR_DANGER if p["quantite_stock"] <= p["seuil_alerte"] else "#6B7280"
            ctk.CTkLabel(ligne, text=f"Stock : {p['quantite_stock']}", font=("Segoe UI", 12), text_color=couleur).pack(side="left", padx=16)
            ctk.CTkLabel(ligne, text=f"Coût moyen : {fmt(p['prix_achat'])} FCFA", font=("Segoe UI", 12),
                         text_color="#6B7280").pack(side="left", padx=16)
            ctk.CTkLabel(ligne, text=f"Vente : {fmt(p['prix_vente'])} FCFA", font=("Segoe UI", 13, "bold"),
                         text_color=COULEUR_TITRE).pack(side="right")

    # ================= STOCK FINAL =================

    def afficher_stock_final(self):
        self.afficher_shell("Stock final", self._construire_stock_final)

    def _construire_stock_final(self, parent):
        ctk.CTkLabel(parent, text="Stock final en temps réel", font=("Segoe UI", 22, "bold"),
                     text_color=COULEUR_TITRE).pack(anchor="w", pady=(0, 4))
        ctk.CTkLabel(parent, text="Quantités restantes actuellement en stock, valorisées au coût moyen pondéré.",
                     font=("Segoe UI", 12), text_color="#6B7280").pack(anchor="w", pady=(0, 16))

        donnees = db.stock_final()

        cartes = ctk.CTkFrame(parent, fg_color=COULEUR_FOND)
        cartes.pack(fill="x", pady=(0, 20))
        self._carte_stat(cartes, "Valeur totale du stock", f"{fmt(donnees['valeur_totale'])} FCFA",
                          COULEUR_ACCENT).pack(side="left", padx=(0, 16))
        self._carte_stat(cartes, "Références en stock", str(len(donnees["produits"])),
                          COULEUR_SUCCES).pack(side="left")

        liste = ctk.CTkScrollableFrame(parent, fg_color=COULEUR_CARTE, corner_radius=14, height=340)
        liste.pack(fill="both", expand=True)
        for p in donnees["produits"]:
            ligne = ctk.CTkFrame(liste, fg_color="transparent")
            ligne.pack(fill="x", pady=6, padx=10)
            couleur = COULEUR_DANGER if p["quantite_stock"] <= p["seuil_alerte"] else COULEUR_TITRE
            ctk.CTkLabel(ligne, text=p["nom"], font=("Segoe UI", 13)).pack(side="left")
            ctk.CTkLabel(ligne, text=f"Qté : {p['quantite_stock']}", font=("Segoe UI", 12),
                         text_color=couleur).pack(side="left", padx=16)
            ctk.CTkLabel(ligne, text=f"Valeur : {fmt(p['valeur_stock'])} FCFA", font=("Segoe UI", 13, "bold"),
                         text_color=COULEUR_ACCENT).pack(side="right")

    # ================= DEPENSES =================

    def afficher_depenses(self):
        self.afficher_shell("Dépenses", self._construire_depenses)

    def _construire_depenses(self, parent):
        journee = db.get_or_create_journee_du_jour()
        verrouille = journee["statut"] == "cloturee"

        ctk.CTkLabel(parent, text="Dépenses du jour", font=("Segoe UI", 22, "bold"), text_color=COULEUR_TITRE).pack(anchor="w", pady=(0, 16))

        formulaire = ctk.CTkFrame(parent, fg_color=COULEUR_CARTE, corner_radius=14)
        formulaire.pack(fill="x", pady=(0, 20))

        ctk.CTkLabel(formulaire, text="Libellé", font=("Segoe UI", 12)).grid(row=0, column=0, padx=16, pady=16, sticky="w")
        entry_libelle = ctk.CTkEntry(formulaire, width=220)
        entry_libelle.grid(row=0, column=1, padx=8, pady=16)

        ctk.CTkLabel(formulaire, text="Montant", font=("Segoe UI", 12)).grid(row=0, column=2, padx=16, pady=16, sticky="w")
        entry_montant = ctk.CTkEntry(formulaire, width=140)
        entry_montant.grid(row=0, column=3, padx=8, pady=16)

        def valider():
            if verrouille:
                messagebox.showwarning("Journée clôturée", "Impossible de saisir : la journée est verrouillée.")
                return
            try:
                db.enregistrer_depense(entry_libelle.get().strip(), float(entry_montant.get() or 0), None, self.role)
                self.afficher_depenses()
            except (PermissionError, ValueError) as e:
                messagebox.showerror("Erreur", str(e))

        ctk.CTkButton(formulaire, text="Enregistrer", fg_color=COULEUR_ACCENT, width=140,
                       command=valider, state="disabled" if verrouille else "normal"
                       ).grid(row=0, column=4, padx=16, pady=16)

        liste = ctk.CTkScrollableFrame(parent, fg_color=COULEUR_CARTE, corner_radius=14, height=260)
        liste.pack(fill="both", expand=True)
        for d in db.depenses_du_jour(journee["id"]):
            ligne = ctk.CTkFrame(liste, fg_color="transparent")
            ligne.pack(fill="x", pady=6, padx=10)
            ctk.CTkLabel(ligne, text=d["libelle"], font=("Segoe UI", 13)).pack(side="left")
            ctk.CTkLabel(ligne, text=libelle_role(d["role"]), font=("Segoe UI", 10, "italic"),
                         text_color="#9CA3AF").pack(side="left", padx=16)
            ctk.CTkLabel(ligne, text=f"{fmt(d['montant'])} FCFA", font=("Segoe UI", 13, "bold"),
                         text_color=COULEUR_DANGER).pack(side="right")

    # ================= CLOTURE =================

    def afficher_cloture(self):
        self.afficher_shell("Clôture du jour", self._construire_cloture)

    def _construire_cloture(self, parent):
        journee = db.get_or_create_journee_du_jour()
        ctk.CTkLabel(parent, text="Clôture de la journée", font=("Segoe UI", 22, "bold"), text_color=COULEUR_TITRE).pack(anchor="w", pady=(0, 16))

        carte = ctk.CTkFrame(parent, fg_color=COULEUR_CARTE, corner_radius=14)
        carte.pack(fill="x", pady=(0, 20))

        if journee["statut"] == "cloturee":
            ctk.CTkLabel(carte, text="🔒 Journée déjà clôturée", font=("Segoe UI", 16, "bold"),
                         text_color=COULEUR_DANGER).pack(padx=20, pady=20, anchor="w")
            ctk.CTkLabel(carte, text=f"Chiffre d'affaires : {fmt(journee['chiffre_affaires'])} FCFA", font=("Segoe UI", 13)).pack(padx=20, anchor="w")
            ctk.CTkLabel(carte, text=f"Dépenses : {fmt(journee['total_depenses'])} FCFA", font=("Segoe UI", 13)).pack(padx=20, pady=(0, 20), anchor="w")

            if self.role == "responsable":
                ctk.CTkButton(carte, text="Déverrouiller la journée (responsable)", fg_color=COULEUR_DANGER,
                              command=lambda: self._deverrouiller(journee["id"])).pack(padx=20, pady=(0, 20), anchor="w")
        else:
            ventes = db.ventes_du_jour(journee["id"])
            depenses = db.depenses_du_jour(journee["id"])
            ca = sum(v["montant_total"] for v in ventes)
            total_dep = sum(d["montant"] for d in depenses)

            ctk.CTkLabel(carte, text="Résumé avant clôture", font=("Segoe UI", 15, "bold"), text_color=COULEUR_TITRE).pack(padx=20, pady=(20, 10), anchor="w")
            ctk.CTkLabel(carte, text=f"Chiffre d'affaires : {fmt(ca)} FCFA", font=("Segoe UI", 13)).pack(padx=20, anchor="w")
            ctk.CTkLabel(carte, text=f"Dépenses : {fmt(total_dep)} FCFA", font=("Segoe UI", 13)).pack(padx=20, anchor="w")
            ctk.CTkLabel(carte, text=f"Nombre de ventes : {len(ventes)}", font=("Segoe UI", 13)).pack(padx=20, pady=(0, 16), anchor="w")
            ctk.CTkLabel(carte, text="⚠️ Une fois clôturée, plus aucune saisie ne sera possible sans autorisation du responsable.",
                         font=("Segoe UI", 11), text_color="#92400E").pack(padx=20, anchor="w")

            ctk.CTkButton(carte, text="Clôturer la journée", fg_color=COULEUR_SUCCES, height=44,
                          command=lambda: self._cloturer(journee["id"])).pack(padx=20, pady=20, anchor="w")

    def _cloturer(self, journee_id):
        if not messagebox.askyesno("Confirmer la clôture", "Clôturer la journée ? Cette action verrouille toutes les saisies."):
            return
        resultat = db.cloturer_journee(journee_id, self.role)
        messagebox.showinfo(
            "Journée clôturée",
            f"Journée clôturée avec succès.\n\n"
            f"Chiffre d'affaires : {fmt(resultat['chiffre_affaires'])} FCFA\n"
            f"Dépenses : {fmt(resultat['total_depenses'])} FCFA\n\n"
            f"Vous pouvez exporter le rapport détaillé (PDF/Excel) depuis l'écran Rapports.",
        )
        self.afficher_cloture()

    def _deverrouiller(self, journee_id):
        if not messagebox.askyesno("Confirmer le déverrouillage", "Déverrouiller la journée ? Cette action sera enregistrée dans l'audit."):
            return
        db.deverrouiller_journee(journee_id, self.role)
        self.afficher_cloture()

    # ================= OPTIONS AVANCÉES (responsable uniquement) =================

    def afficher_options_avancees(self):
        if self.role != "responsable":
            messagebox.showerror("Accès refusé", "Cette section est réservée au responsable.")
            return
        self.afficher_shell("Options avancées", self._construire_options_avancees)

    def _construire_options_avancees(self, parent):
        ctk.CTkLabel(parent, text="Options avancées", font=("Segoe UI", 22, "bold"),
                     text_color=COULEUR_TITRE).pack(anchor="w", pady=(0, 4))
        ctk.CTkLabel(parent, text="Réservé au responsable.", font=("Segoe UI", 12),
                     text_color="#6B7280").pack(anchor="w", pady=(0, 20))

        carte = ctk.CTkFrame(parent, fg_color=COULEUR_CARTE, corner_radius=14)
        carte.pack(fill="x")

        ctk.CTkLabel(carte, text="Changer un mot de passe", font=("Segoe UI", 15, "bold"),
                     text_color=COULEUR_TITRE).pack(anchor="w", padx=20, pady=(20, 10))

        zone = ctk.CTkFrame(carte, fg_color="transparent")
        zone.pack(fill="x", padx=20, pady=(0, 20))

        def vider_zone():
            for w in zone.winfo_children():
                w.destroy()

        def etape_choix_type():
            vider_zone()
            ctk.CTkLabel(zone, text="Quel mot de passe voulez-vous changer ?",
                         font=("Segoe UI", 12)).pack(anchor="w", pady=(0, 10))
            boutons = ctk.CTkFrame(zone, fg_color="transparent")
            boutons.pack(fill="x")
            ctk.CTkButton(boutons, text="Mot de passe saisie", fg_color=COULEUR_ACCENT,
                           command=lambda: etape_ancien_mdp("saisie")).pack(side="left", padx=(0, 12))
            ctk.CTkButton(boutons, text="Mot de passe responsable", fg_color=COULEUR_ACCENT,
                           command=lambda: etape_ancien_mdp("responsable")).pack(side="left")

        def etape_ancien_mdp(type_mdp):
            vider_zone()
            libelle = "saisie" if type_mdp == "saisie" else "responsable"
            ctk.CTkLabel(zone, text=f"Changement du mot de passe « {libelle} »",
                         font=("Segoe UI", 13, "bold"), text_color=COULEUR_TITRE).pack(anchor="w", pady=(0, 10))
            ctk.CTkLabel(zone, text="Entrez l'ancien mot de passe pour continuer",
                         font=("Segoe UI", 12)).pack(anchor="w", pady=(0, 4))
            entry_ancien = ctk.CTkEntry(zone, show="•", width=280, height=38)
            entry_ancien.pack(anchor="w", pady=(0, 10))

            def verifier():
                if not db.verifier_mot_de_passe_type(type_mdp, entry_ancien.get()):
                    messagebox.showerror("Erreur", "Ancien mot de passe incorrect.")
                    return
                etape_nouveau_mdp(type_mdp, entry_ancien.get())

            entry_ancien.bind("<Return>", lambda e: verifier())
            boutons = ctk.CTkFrame(zone, fg_color="transparent")
            boutons.pack(fill="x", pady=(4, 0))
            ctk.CTkButton(boutons, text="Vérifier", fg_color=COULEUR_ACCENT, command=verifier).pack(side="left", padx=(0, 12))
            ctk.CTkButton(boutons, text="← Annuler", fg_color="transparent", border_width=1,
                           border_color="#D1D5DB", text_color=COULEUR_TITRE,
                           command=etape_choix_type).pack(side="left")

        def etape_nouveau_mdp(type_mdp, ancien_mdp):
            vider_zone()
            ctk.CTkLabel(zone, text="Nouveau mot de passe", font=("Segoe UI", 12)).pack(anchor="w", pady=(0, 2))
            entry_nouveau = ctk.CTkEntry(zone, show="•", width=280, height=38)
            entry_nouveau.pack(anchor="w", pady=(0, 10))
            ctk.CTkLabel(zone, text="Confirmer le nouveau mot de passe", font=("Segoe UI", 12)).pack(anchor="w", pady=(0, 2))
            entry_confirm = ctk.CTkEntry(zone, show="•", width=280, height=38)
            entry_confirm.pack(anchor="w", pady=(0, 10))

            def enregistrer():
                nouveau = entry_nouveau.get()
                if nouveau != entry_confirm.get():
                    messagebox.showerror("Erreur", "Les deux saisies du nouveau mot de passe ne correspondent pas.")
                    return
                try:
                    db.changer_mot_de_passe(type_mdp, ancien_mdp, nouveau)
                    messagebox.showinfo("Succès", "Mot de passe mis à jour avec succès.")
                    etape_choix_type()
                except ValueError as e:
                    messagebox.showerror("Erreur", str(e))

            boutons = ctk.CTkFrame(zone, fg_color="transparent")
            boutons.pack(fill="x", pady=(4, 0))
            ctk.CTkButton(boutons, text="Enregistrer le nouveau mot de passe", fg_color=COULEUR_SUCCES,
                           command=enregistrer).pack(side="left", padx=(0, 12))
            ctk.CTkButton(boutons, text="← Annuler", fg_color="transparent", border_width=1,
                           border_color="#D1D5DB", text_color=COULEUR_TITRE,
                           command=etape_choix_type).pack(side="left")

        etape_choix_type()

        # --- Modifier le prix de vente d'un produit ---
        ctk.CTkLabel(parent, text="Modifier le prix de vente d'un produit", font=("Segoe UI", 15, "bold"),
                     text_color=COULEUR_TITRE).pack(anchor="w", pady=(24, 8))
        carte_prix = ctk.CTkFrame(parent, fg_color=COULEUR_CARTE, corner_radius=14)
        carte_prix.pack(fill="x", pady=(0, 24))
        zone_prix = ctk.CTkFrame(carte_prix, fg_color="transparent")
        zone_prix.pack(fill="x", padx=20, pady=20)

        def vider_zone_prix():
            for w in zone_prix.winfo_children():
                w.destroy()

        def etape_choix_produit_prix():
            vider_zone_prix()
            produits = db.liste_produits()
            if not produits:
                ctk.CTkLabel(zone_prix, text="Aucun produit enregistré.", font=("Segoe UI", 12),
                             text_color="#9CA3AF").pack(anchor="w")
                return
            ctk.CTkLabel(zone_prix, text="Sélectionnez un produit", font=("Segoe UI", 12)).pack(anchor="w", pady=(0, 6))
            noms = [p["nom"] for p in produits]
            combo = ctk.CTkOptionMenu(zone_prix, values=noms, width=220)
            combo.pack(anchor="w", pady=(0, 10))
            ctk.CTkButton(zone_prix, text="Modifier le prix unitaire", fg_color=COULEUR_ACCENT,
                           command=lambda: etape_nouveau_prix(next(p for p in produits if p["nom"] == combo.get()))
                           ).pack(anchor="w")

        def etape_nouveau_prix(produit):
            vider_zone_prix()
            ctk.CTkLabel(zone_prix, text=f"« {produit['nom']} »", font=("Segoe UI", 13, "bold"),
                         text_color=COULEUR_TITRE).pack(anchor="w", pady=(0, 4))
            ctk.CTkLabel(zone_prix, text=f"Prix de vente actuel : {fmt(produit['prix_vente'])} FCFA",
                         font=("Segoe UI", 12), text_color="#6B7280").pack(anchor="w", pady=(0, 10))
            ctk.CTkLabel(zone_prix, text="Nouveau prix de vente unitaire", font=("Segoe UI", 12)).pack(anchor="w", pady=(0, 2))
            entry_nouveau_prix = ctk.CTkEntry(zone_prix, width=160)
            entry_nouveau_prix.pack(anchor="w", pady=(0, 10))

            def enregistrer_prix():
                try:
                    nouveau = float(entry_nouveau_prix.get())
                    db.modifier_prix_vente(produit["id"], nouveau)
                    messagebox.showinfo("Succès", f"Prix de vente de « {produit['nom']} » mis à jour : {fmt(nouveau)} FCFA")
                    etape_choix_produit_prix()
                except ValueError as e:
                    messagebox.showerror("Erreur", str(e) if str(e) else "Le prix doit être un nombre valide.")

            boutons_prix = ctk.CTkFrame(zone_prix, fg_color="transparent")
            boutons_prix.pack(fill="x")
            ctk.CTkButton(boutons_prix, text="Enregistrer le nouveau prix", fg_color=COULEUR_SUCCES,
                           command=enregistrer_prix).pack(side="left", padx=(0, 10))
            ctk.CTkButton(boutons_prix, text="← Annuler", fg_color="transparent", border_width=1,
                           border_color="#D1D5DB", text_color=COULEUR_TITRE,
                           command=etape_choix_produit_prix).pack(side="left")

        etape_choix_produit_prix()

        # --- Supprimer un produit ---
        ctk.CTkLabel(parent, text="Supprimer un produit du stock", font=("Segoe UI", 15, "bold"),
                     text_color=COULEUR_TITRE).pack(anchor="w", pady=(0, 8))
        carte_suppr = ctk.CTkFrame(parent, fg_color=COULEUR_CARTE, corner_radius=14)
        carte_suppr.pack(fill="x", pady=(0, 24))
        zone_suppr = ctk.CTkFrame(carte_suppr, fg_color="transparent")
        zone_suppr.pack(fill="x", padx=20, pady=20)

        produits_suppr = db.liste_produits()
        if not produits_suppr:
            ctk.CTkLabel(zone_suppr, text="Aucun produit enregistré.", font=("Segoe UI", 12),
                         text_color="#9CA3AF").pack(anchor="w")
        else:
            noms_suppr = [p["nom"] for p in produits_suppr]
            combo_suppr = ctk.CTkOptionMenu(zone_suppr, values=noms_suppr, width=220)
            combo_suppr.pack(side="left", padx=(0, 12))

            def supprimer():
                produit = next(p for p in produits_suppr if p["nom"] == combo_suppr.get())
                if not messagebox.askyesno("Confirmer la suppression",
                                            f"Supprimer définitivement « {produit['nom']} » ? Cette action est irréversible."):
                    return
                supprime = db.supprimer_produit(produit["id"])
                if supprime:
                    messagebox.showinfo("Produit supprimé", f"« {produit['nom']} » a été supprimé définitivement.")
                else:
                    messagebox.showinfo(
                        "Produit désactivé",
                        f"« {produit['nom']} » a un historique de ventes/mouvements de stock : il a été retiré "
                        "du catalogue actif plutôt que supprimé, afin de préserver l'historique.",
                    )
                self.afficher_options_avancees()

            ctk.CTkButton(zone_suppr, text="Supprimer définitivement", fg_color=COULEUR_DANGER,
                           command=supprimer).pack(side="left")

        # --- Clients enregistrés et cumul de leurs achats ---
        ctk.CTkLabel(parent, text="Clients enregistrés", font=("Segoe UI", 15, "bold"),
                     text_color=COULEUR_TITRE).pack(anchor="w", pady=(0, 8))
        clients = db.clients_avec_cumul()
        liste_clients = ctk.CTkScrollableFrame(parent, fg_color=COULEUR_CARTE, corner_radius=14, height=240)
        liste_clients.pack(fill="both", expand=True)
        if not clients:
            ctk.CTkLabel(liste_clients, text="Aucun client enregistré pour le moment.",
                         font=("Segoe UI", 12), text_color="#9CA3AF").pack(pady=20)
        for c in clients:
            ligne = ctk.CTkFrame(liste_clients, fg_color="transparent")
            ligne.pack(fill="x", pady=6, padx=10)
            ctk.CTkLabel(ligne, text=c["nom"] or "(sans nom)", font=("Segoe UI", 13)).pack(side="left")
            ctk.CTkLabel(ligne, text=c["telephone"] or "", font=("Segoe UI", 12),
                         text_color="#6B7280").pack(side="left", padx=12)
            ctk.CTkLabel(ligne, text=f"{c['nb_achats']} achat(s)", font=("Segoe UI", 12),
                         text_color="#6B7280").pack(side="left", padx=12)
            ctk.CTkLabel(ligne, text=f"{fmt(c['total_achats'])} FCFA", font=("Segoe UI", 13, "bold"),
                         text_color=COULEUR_SUCCES).pack(side="right")

        # --- Charges fixes ---
        ctk.CTkLabel(parent, text="Charges fixes", font=("Segoe UI", 15, "bold"),
                     text_color=COULEUR_TITRE).pack(anchor="w", pady=(24, 4))
        config = db.get_configuration()
        total_jour = db.total_charges_fixes_du_jour()
        ctk.CTkLabel(
            parent,
            text=(f"Réparties automatiquement chaque jour selon {config['jours_travail_semaine']} jours de "
                  f"travail/semaine — équivalent actuel : {fmt(total_jour)} FCFA/jour, ajouté aux dépenses à chaque clôture."),
            font=("Segoe UI", 11), text_color="#6B7280", wraplength=700, justify="left",
        ).pack(anchor="w", pady=(0, 8))

        carte_charges = ctk.CTkFrame(parent, fg_color=COULEUR_CARTE, corner_radius=14)
        carte_charges.pack(fill="x", pady=(0, 24))
        formulaire_charge = ctk.CTkFrame(carte_charges, fg_color="transparent")
        formulaire_charge.pack(fill="x", padx=20, pady=20)

        entry_libelle_charge = ctk.CTkEntry(formulaire_charge, placeholder_text="Libellé (ex : Loyer)", width=200)
        entry_libelle_charge.grid(row=0, column=0, padx=(0, 10), pady=6)
        entry_montant_charge = ctk.CTkEntry(formulaire_charge, placeholder_text="Montant", width=120)
        entry_montant_charge.grid(row=0, column=1, padx=10, pady=6)
        combo_periodicite = ctk.CTkOptionMenu(
            formulaire_charge,
            values=["Tous les jours", "Chaque semaine", "Chaque 2 semaines", "Chaque mois"],
            width=170,
        )
        combo_periodicite.set("Chaque mois")
        combo_periodicite.grid(row=0, column=2, padx=10, pady=6)

        def ajouter_charge():
            libelle = entry_libelle_charge.get().strip()
            if not libelle:
                messagebox.showerror("Erreur", "Le libellé est obligatoire.")
                return
            try:
                montant = float(entry_montant_charge.get())
            except ValueError:
                messagebox.showerror("Erreur", "Le montant doit être un nombre valide.")
                return
            periodicite = {
                "Tous les jours": "jour", "Chaque semaine": "semaine",
                "Chaque 2 semaines": "quinzaine", "Chaque mois": "mois",
            }[combo_periodicite.get()]
            db.ajouter_charge_fixe(libelle, montant, periodicite)
            self.afficher_options_avancees()

        ctk.CTkButton(formulaire_charge, text="Enregistrer la charge fixe", fg_color=COULEUR_ACCENT,
                       command=ajouter_charge).grid(row=0, column=3, padx=(10, 0), pady=6)

        charges = db.liste_charges_fixes()
        if charges:
            liste_charges = ctk.CTkFrame(carte_charges, fg_color="transparent")
            liste_charges.pack(fill="x", padx=20, pady=(0, 16))
            libelle_periodicite = {"jour": "/jour", "semaine": "/semaine", "quinzaine": "/2 semaines", "mois": "/mois"}
            for c in charges:
                ligne = ctk.CTkFrame(liste_charges, fg_color="transparent")
                ligne.pack(fill="x", pady=4)
                ctk.CTkLabel(ligne, text=c["libelle"], font=("Segoe UI", 13)).pack(side="left")
                ctk.CTkLabel(ligne, text=f"{fmt(c['montant'])} FCFA{libelle_periodicite[c['periodicite']]}",
                             font=("Segoe UI", 12), text_color="#6B7280").pack(side="left", padx=12)
                equiv = db.equivalent_journalier(c, config["jours_travail_semaine"])
                ctk.CTkLabel(ligne, text=f"≈ {fmt(equiv)} FCFA/jour", font=("Segoe UI", 12),
                             text_color=COULEUR_ACCENT).pack(side="left", padx=12)

                def supprimer(charge_id=c["id"]):
                    db.supprimer_charge_fixe(charge_id)
                    self.afficher_options_avancees()

                ctk.CTkButton(ligne, text="Supprimer", fg_color="transparent", text_color=COULEUR_DANGER,
                               hover_color="#FBE7E7", width=80, command=supprimer).pack(side="right")

    # ================= RAPPORTS =================

    def afficher_rapports(self):
        self.afficher_shell("Rapports", self._construire_rapports)

    def _construire_rapports(self, parent):
        ctk.CTkLabel(parent, text="Rapports", font=("Segoe UI", 22, "bold"), text_color=COULEUR_TITRE).pack(anchor="w", pady=(0, 16))

        # --- Rapport par date précise (accessible à tous) ---
        ctk.CTkLabel(parent, text="Rapport journalier par date précise", font=("Segoe UI", 15, "bold"),
                     text_color=COULEUR_TITRE).pack(anchor="w", pady=(0, 8))
        carte_date = ctk.CTkFrame(parent, fg_color=COULEUR_CARTE, corner_radius=14)
        carte_date.pack(fill="x", pady=(0, 16))

        ctk.CTkLabel(carte_date, text="Date", font=("Segoe UI", 12)).grid(row=0, column=0, padx=16, pady=16, sticky="w")
        selecteur_date = DateEntry(carte_date, width=18, date_pattern="yyyy-mm-dd",
                                    font=("Segoe UI", 13), background=COULEUR_ACCENT, foreground="white",
                                    borderwidth=2, justify="center")
        selecteur_date.grid(row=0, column=1, padx=8, pady=16)

        zone_resultat_jour = ctk.CTkFrame(parent, fg_color="transparent")
        zone_resultat_jour.pack(fill="x", pady=(0, 24))
        self._dernier_rapport_jour = None

        def rechercher_date():
            d = selecteur_date.get_date().isoformat()
            factures = db.factures_par_periode(d, d)
            depenses = db.depenses_par_periode(d, d)
            self._dernier_rapport_jour = {
                "titre": f"Rapport du {d}", "factures": factures, "depenses": depenses, "avec_date": False,
            }
            for w in zone_resultat_jour.winfo_children():
                w.destroy()
            self._construire_tableau_rapport(zone_resultat_jour, self._dernier_rapport_jour)

        def exporter_jour(format_export):
            if not self._dernier_rapport_jour:
                messagebox.showwarning("Aucun résultat", "Recherchez d'abord une date.")
                return
            self._exporter_rapport(self._dernier_rapport_jour, format_export)

        ctk.CTkButton(carte_date, text="Rechercher", fg_color=COULEUR_ACCENT,
                       command=rechercher_date).grid(row=0, column=2, padx=8, pady=16)
        ctk.CTkButton(carte_date, text="Exporter en PDF", fg_color="transparent", border_width=1,
                       border_color="#D1D5DB", text_color=COULEUR_TITRE,
                       command=lambda: exporter_jour("pdf")).grid(row=0, column=3, padx=8, pady=16)
        ctk.CTkButton(carte_date, text="Exporter en Excel", fg_color="transparent", border_width=1,
                       border_color="#D1D5DB", text_color=COULEUR_TITRE,
                       command=lambda: exporter_jour("excel")).grid(row=0, column=4, padx=8, pady=16)

        # --- Rapport par période (responsable uniquement) ---
        ctk.CTkLabel(parent, text="Rapport sur une période", font=("Segoe UI", 15, "bold"),
                     text_color=COULEUR_TITRE).pack(anchor="w", pady=(0, 8))
        carte_periode = ctk.CTkFrame(parent, fg_color=COULEUR_CARTE, corner_radius=14)
        carte_periode.pack(fill="x", pady=(0, 16))

        if self.role != "responsable":
            ctk.CTkLabel(carte_periode, text="🔒 Accès réservé au responsable.", font=("Segoe UI", 13),
                         text_color=COULEUR_DANGER).pack(padx=20, pady=20, anchor="w")
            return

        ctk.CTkLabel(carte_periode, text="Du", font=("Segoe UI", 12)).grid(row=0, column=0, padx=16, pady=16, sticky="w")
        selecteur_debut = DateEntry(carte_periode, width=18, date_pattern="yyyy-mm-dd",
                                     font=("Segoe UI", 13), background=COULEUR_ACCENT, foreground="white",
                                     borderwidth=2, justify="center")
        selecteur_debut.grid(row=0, column=1, padx=8, pady=16)

        ctk.CTkLabel(carte_periode, text="Au", font=("Segoe UI", 12)).grid(row=0, column=2, padx=16, pady=16, sticky="w")
        selecteur_fin = DateEntry(carte_periode, width=18, date_pattern="yyyy-mm-dd",
                                   font=("Segoe UI", 13), background=COULEUR_ACCENT, foreground="white",
                                   borderwidth=2, justify="center")
        selecteur_fin.grid(row=0, column=3, padx=8, pady=16)

        zone_resultat_periode = ctk.CTkFrame(parent, fg_color="transparent")
        zone_resultat_periode.pack(fill="x")
        self._dernier_rapport_periode = None

        def rechercher_periode():
            debut, fin = selecteur_debut.get_date().isoformat(), selecteur_fin.get_date().isoformat()
            factures = db.factures_par_periode(debut, fin)
            depenses = db.depenses_par_periode(debut, fin)
            self._dernier_rapport_periode = {
                "titre": f"Rapport du {debut} au {fin}", "factures": factures, "depenses": depenses, "avec_date": True,
            }
            for w in zone_resultat_periode.winfo_children():
                w.destroy()
            self._construire_tableau_rapport(zone_resultat_periode, self._dernier_rapport_periode)

        def exporter_periode(format_export):
            if not self._dernier_rapport_periode:
                messagebox.showwarning("Aucun résultat", "Recherchez d'abord une période.")
                return
            self._exporter_rapport(self._dernier_rapport_periode, format_export)

        ctk.CTkButton(carte_periode, text="Rechercher", fg_color=COULEUR_ACCENT,
                       command=rechercher_periode).grid(row=0, column=4, padx=8, pady=16)
        ctk.CTkButton(carte_periode, text="Exporter en PDF", fg_color="transparent", border_width=1,
                       border_color="#D1D5DB", text_color=COULEUR_TITRE,
                       command=lambda: exporter_periode("pdf")).grid(row=0, column=5, padx=8, pady=16)
        ctk.CTkButton(carte_periode, text="Exporter en Excel", fg_color="transparent", border_width=1,
                       border_color="#D1D5DB", text_color=COULEUR_TITRE,
                       command=lambda: exporter_periode("excel")).grid(row=0, column=6, padx=8, pady=16)

        # --- Mouvements de stock par produit (responsable uniquement) ---
        ctk.CTkLabel(parent, text="Mouvements de stock par produit", font=("Segoe UI", 15, "bold"),
                     text_color=COULEUR_TITRE).pack(anchor="w", pady=(24, 8))
        ctk.CTkLabel(parent, text="Sélectionnez un produit puis une date (identique dans « Du » et « Au ») "
                                   "ou une période, pour voir toutes ses entrées et sorties, triées de la "
                                   "plus ancienne à la plus récente.",
                     font=("Segoe UI", 11), text_color="#6B7280", wraplength=700, justify="left").pack(anchor="w", pady=(0, 8))
        carte_mvt = ctk.CTkFrame(parent, fg_color=COULEUR_CARTE, corner_radius=14)
        carte_mvt.pack(fill="x", pady=(0, 16))

        produits = db.liste_produits(actifs_seulement=False)
        noms_produits = [p["nom"] for p in produits] or ["Aucun produit"]

        ctk.CTkLabel(carte_mvt, text="Produit", font=("Segoe UI", 12)).grid(row=0, column=0, padx=16, pady=16, sticky="w")
        combo_produit_mvt = ctk.CTkOptionMenu(carte_mvt, values=noms_produits, width=200)
        combo_produit_mvt.grid(row=0, column=1, padx=8, pady=16)

        ctk.CTkLabel(carte_mvt, text="Du", font=("Segoe UI", 12)).grid(row=0, column=2, padx=16, pady=16, sticky="w")
        selecteur_mvt_debut = DateEntry(carte_mvt, width=18, date_pattern="yyyy-mm-dd",
                                         font=("Segoe UI", 13), background=COULEUR_ACCENT, foreground="white",
                                         borderwidth=2, justify="center")
        selecteur_mvt_debut.grid(row=0, column=3, padx=8, pady=16)

        ctk.CTkLabel(carte_mvt, text="Au", font=("Segoe UI", 12)).grid(row=0, column=4, padx=16, pady=16, sticky="w")
        selecteur_mvt_fin = DateEntry(carte_mvt, width=18, date_pattern="yyyy-mm-dd",
                                       font=("Segoe UI", 13), background=COULEUR_ACCENT, foreground="white",
                                       borderwidth=2, justify="center")
        selecteur_mvt_fin.grid(row=0, column=5, padx=8, pady=16)

        zone_resultat_mvt = ctk.CTkFrame(parent, fg_color="transparent")
        zone_resultat_mvt.pack(fill="both", expand=True, pady=(0, 20))
        self._dernier_rapport_mouvements = None

        def rechercher_mouvements():
            produit = next((p for p in produits if p["nom"] == combo_produit_mvt.get()), None)
            if produit is None:
                messagebox.showerror("Erreur", "Sélectionnez un produit valide.")
                return
            debut, fin = selecteur_mvt_debut.get_date().isoformat(), selecteur_mvt_fin.get_date().isoformat()
            mouvements = db.mouvements_produit_periode(produit["id"], debut, fin)
            titre = f"Rapport du {debut}" if debut == fin else f"Rapport du {debut} au {fin}"
            self._dernier_rapport_mouvements = {
                "produit_nom": produit["nom"], "titre": titre, "mouvements": mouvements,
            }
            for w in zone_resultat_mvt.winfo_children():
                w.destroy()
            self._construire_tableau_mouvements(zone_resultat_mvt, self._dernier_rapport_mouvements)

        def exporter_mouvements(format_export):
            if not self._dernier_rapport_mouvements:
                messagebox.showwarning("Aucun résultat", "Recherchez d'abord un produit et une période.")
                return
            data = self._dernier_rapport_mouvements
            try:
                if format_export == "pdf":
                    chemin = export.exporter_mouvements_pdf(
                        self._nom_entreprise(), data["produit_nom"], data["titre"], data["mouvements"])
                else:
                    chemin = export.exporter_mouvements_excel(
                        self._nom_entreprise(), data["produit_nom"], data["titre"], data["mouvements"])
                messagebox.showinfo("Export réussi", f"Fichier créé sur le Bureau :\n{chemin}")
            except ImportError as e:
                messagebox.showerror("Bibliothèque manquante", f"Installez la dépendance nécessaire : {e}")

        ctk.CTkButton(carte_mvt, text="Rechercher", fg_color=COULEUR_ACCENT,
                       command=rechercher_mouvements).grid(row=1, column=0, columnspan=2, padx=16, pady=(0, 16), sticky="ew")
        ctk.CTkButton(carte_mvt, text="Exporter en PDF", fg_color="transparent", border_width=1,
                       border_color="#D1D5DB", text_color=COULEUR_TITRE,
                       command=lambda: exporter_mouvements("pdf")).grid(row=1, column=2, columnspan=2, padx=8, pady=(0, 16), sticky="ew")
        ctk.CTkButton(carte_mvt, text="Exporter en Excel", fg_color="transparent", border_width=1,
                       border_color="#D1D5DB", text_color=COULEUR_TITRE,
                       command=lambda: exporter_mouvements("excel")).grid(row=1, column=4, columnspan=2, padx=8, pady=(0, 16), sticky="ew")

    def _construire_tableau_mouvements(self, parent, data):
        ctk.CTkLabel(parent, text=f"{data['titre']} — {data['produit_nom']}", font=("Segoe UI", 15, "bold"),
                     text_color=COULEUR_TITRE).pack(anchor="w", pady=(4, 10))

        mouvements = data["mouvements"]
        colonnes = ["Date", "Type", "Quantité", "Prix unitaire", "N° Facture", "Traçabilité"]
        largeurs = [100, 130, 90, 110, 110, 140]

        tableau = ctk.CTkFrame(parent, fg_color=COULEUR_CARTE, corner_radius=14)
        tableau.pack(fill="x")
        entete = ctk.CTkFrame(tableau, fg_color="#F3F4F6")
        entete.pack(fill="x")
        for texte, largeur in zip(colonnes, largeurs):
            ctk.CTkLabel(entete, text=texte, font=("Segoe UI", 12, "bold"), width=largeur, anchor="w").pack(side="left", padx=8, pady=8)

        total_entrees, total_sorties = 0, 0
        if not mouvements:
            ctk.CTkLabel(tableau, text="Aucun mouvement sur cette période.", font=("Segoe UI", 12),
                         text_color="#9CA3AF").pack(anchor="w", padx=12, pady=12)
        for m in mouvements:
            est_entree = m["type"] == "entree"
            if est_entree:
                total_entrees += m["quantite"]
            else:
                total_sorties += m["quantite"]
            valeurs = [
                m["date_jour"], "🟢 Entrée" if est_entree else "🔴 Sortie (vente)", str(m["quantite"]),
                f"{fmt(m['prix_unitaire'])} FCFA", m.get("numero_facture") or "-", libelle_role(m["role"]),
            ]
            ligne = ctk.CTkFrame(tableau, fg_color="transparent")
            ligne.pack(fill="x")
            for idx, (texte, largeur) in enumerate(zip(valeurs, largeurs)):
                couleur = (COULEUR_SUCCES if est_entree else COULEUR_DANGER) if idx == 1 else COULEUR_TITRE
                ctk.CTkLabel(ligne, text=texte, width=largeur, anchor="w",
                             text_color=couleur).pack(side="left", padx=8, pady=5)

        ctk.CTkLabel(
            parent, text=f"Total entrées : {total_entrees} unité(s)      Total sorties : {total_sorties} unité(s)",
            font=("Segoe UI", 13, "bold"), text_color=COULEUR_TITRE,
        ).pack(anchor="w", pady=(8, 10))

    def _exporter_rapport(self, data, format_export):
        try:
            if format_export == "pdf":
                chemin = export.exporter_rapport_detail_pdf(
                    self._nom_entreprise(), data["titre"], data["factures"], data["depenses"], data["avec_date"])
            else:
                chemin = export.exporter_rapport_detail_excel(
                    self._nom_entreprise(), data["titre"], data["factures"], data["depenses"], data["avec_date"])
            messagebox.showinfo("Export réussi", f"Fichier créé sur le Bureau :\n{chemin}")
        except ImportError as e:
            messagebox.showerror("Bibliothèque manquante", f"Installez la dépendance nécessaire : {e}")

    def _construire_tableau_rapport(self, parent, data):
        titre, factures, depenses, avec_date = data["titre"], data["factures"], data["depenses"], data["avec_date"]

        ctk.CTkLabel(parent, text=titre, font=("Segoe UI", 17, "bold"), text_color=COULEUR_TITRE).pack(anchor="w", pady=(4, 14))

        # --- Tableau des ventes ---
        ctk.CTkLabel(parent, text="Ventes", font=("Segoe UI", 14, "bold"), text_color=COULEUR_TITRE).pack(anchor="w", pady=(0, 6))

        colonnes_v = (["Date"] if avec_date else []) + ["N° Facture", "Montant", "Traçabilité", "Client", "Numéro"]
        largeurs_v = ([90] if avec_date else []) + [110, 110, 140, 160, 120]

        tableau_v = ctk.CTkFrame(parent, fg_color=COULEUR_CARTE, corner_radius=14)
        tableau_v.pack(fill="x", pady=(0, 6))
        entete_v = ctk.CTkFrame(tableau_v, fg_color="#F3F4F6")
        entete_v.pack(fill="x")
        for texte, largeur in zip(colonnes_v, largeurs_v):
            ctk.CTkLabel(entete_v, text=texte, font=("Segoe UI", 12, "bold"), width=largeur, anchor="w").pack(side="left", padx=8, pady=8)

        total_factures = 0
        if not factures:
            ctk.CTkLabel(tableau_v, text="Aucune facture sur cette période.", font=("Segoe UI", 12),
                         text_color="#9CA3AF").pack(anchor="w", padx=12, pady=12)
        for f in factures:
            total_factures += f["montant_total"]
            valeurs = ([f["date_jour"]] if avec_date else []) + [
                f["numero"], f"{fmt(f['montant_total'])} FCFA", libelle_role(f["role"]),
                f.get("client_nom") or "-", f.get("client_telephone") or "-",
            ]
            ligne = ctk.CTkFrame(tableau_v, fg_color="transparent")
            ligne.pack(fill="x")
            for texte, largeur in zip(valeurs, largeurs_v):
                ctk.CTkLabel(ligne, text=texte, width=largeur, anchor="w").pack(side="left", padx=8, pady=5)

        ctk.CTkLabel(parent, text=f"TOTAL DES FACTURES : {fmt(total_factures)} FCFA", font=("Segoe UI", 13, "bold"),
                     text_color=COULEUR_SUCCES).pack(anchor="w", pady=(0, 20))

        # --- Tableau des dépenses ---
        ctk.CTkLabel(parent, text="Dépenses", font=("Segoe UI", 14, "bold"), text_color=COULEUR_TITRE).pack(anchor="w", pady=(0, 6))

        colonnes_d = (["Date"] if avec_date else []) + ["Nature des dépenses", "Montant", "Traçabilité"]
        largeurs_d = ([90] if avec_date else []) + [260, 110, 140]

        tableau_d = ctk.CTkFrame(parent, fg_color=COULEUR_CARTE, corner_radius=14)
        tableau_d.pack(fill="x", pady=(0, 6))
        entete_d = ctk.CTkFrame(tableau_d, fg_color="#F3F4F6")
        entete_d.pack(fill="x")
        for texte, largeur in zip(colonnes_d, largeurs_d):
            ctk.CTkLabel(entete_d, text=texte, font=("Segoe UI", 12, "bold"), width=largeur, anchor="w").pack(side="left", padx=8, pady=8)

        total_depenses = 0
        if not depenses:
            ctk.CTkLabel(tableau_d, text="Aucune dépense sur cette période.", font=("Segoe UI", 12),
                         text_color="#9CA3AF").pack(anchor="w", padx=12, pady=12)
        for d in depenses:
            total_depenses += d["montant"]
            valeurs = ([d["date_jour"]] if avec_date else []) + [d["libelle"], f"{fmt(d['montant'])} FCFA", libelle_role(d["role"])]
            ligne = ctk.CTkFrame(tableau_d, fg_color="transparent")
            ligne.pack(fill="x")
            for texte, largeur in zip(valeurs, largeurs_d):
                ctk.CTkLabel(ligne, text=texte, width=largeur, anchor="w").pack(side="left", padx=8, pady=5)

        ctk.CTkLabel(parent, text=f"TOTAL DES DÉPENSES : {fmt(total_depenses)} FCFA", font=("Segoe UI", 13, "bold"),
                     text_color=COULEUR_DANGER).pack(anchor="w", pady=(0, 10))


if __name__ == "__main__":
    app = App()
    app.mainloop()

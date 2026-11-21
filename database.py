"""
Module de gestion de la base de données SQLite locale.
Chaque entreprise a son propre fichier .db stocké sur son ordinateur.
"""

import sqlite3
import hashlib
import json
import os
from datetime import date, datetime

from utils import dossier_donnees

DB_PATH = os.path.join(dossier_donnees(), "gestion_pme.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Crée toutes les tables si elles n'existent pas encore."""
    conn = get_connection()
    cur = conn.cursor()

    cur.executescript("""
    CREATE TABLE IF NOT EXISTS configuration (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        nom_entreprise TEXT NOT NULL DEFAULT '',
        identifiant TEXT NOT NULL DEFAULT '',
        mdp_saisie_hash TEXT NOT NULL DEFAULT '',
        mdp_responsable_hash TEXT NOT NULL DEFAULT '',
        email_principal TEXT NOT NULL DEFAULT '',
        email_secondaire TEXT DEFAULT '',
        smtp_hote TEXT DEFAULT '',
        smtp_port INTEGER DEFAULT 587,
        smtp_utilisateur TEXT DEFAULT '',
        smtp_mot_de_passe TEXT DEFAULT '',
        logo_path TEXT DEFAULT '',
        pref_entree_stock INTEGER NOT NULL DEFAULT 1,
        pref_depenses INTEGER NOT NULL DEFAULT 1,
        pref_stock_final INTEGER NOT NULL DEFAULT 0,
        jours_travail_semaine INTEGER NOT NULL DEFAULT 6,
        configuration_terminee INTEGER NOT NULL DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS produits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nom TEXT NOT NULL UNIQUE,
        prix_achat REAL NOT NULL DEFAULT 0,
        prix_vente REAL NOT NULL DEFAULT 0,
        quantite_stock INTEGER NOT NULL DEFAULT 0,
        seuil_alerte INTEGER NOT NULL DEFAULT 5,
        categorie TEXT,
        actif INTEGER NOT NULL DEFAULT 1,
        date_creation TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS journees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date_jour TEXT NOT NULL UNIQUE,
        statut TEXT NOT NULL DEFAULT 'ouverte' CHECK(statut IN ('ouverte', 'cloturee')),
        chiffre_affaires REAL DEFAULT 0,
        total_depenses REAL DEFAULT 0,
        date_cloture TEXT,
        rapport_envoye INTEGER NOT NULL DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nom TEXT,
        telephone TEXT,
        adresse TEXT,
        date_creation TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS factures (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero TEXT,
        journee_id INTEGER NOT NULL REFERENCES journees(id),
        client_id INTEGER REFERENCES clients(id),
        sous_total REAL NOT NULL DEFAULT 0,
        remise_montant REAL NOT NULL DEFAULT 0,
        remise_pourcentage REAL NOT NULL DEFAULT 0,
        montant_remise REAL NOT NULL DEFAULT 0,
        tva_active INTEGER NOT NULL DEFAULT 0,
        tva_taux REAL NOT NULL DEFAULT 18,
        montant_tva REAL NOT NULL DEFAULT 0,
        montant_total REAL NOT NULL DEFAULT 0,
        role TEXT NOT NULL,
        date_facture TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS ventes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        journee_id INTEGER NOT NULL REFERENCES journees(id),
        facture_id INTEGER REFERENCES factures(id),
        produit_id INTEGER NOT NULL REFERENCES produits(id),
        client_id INTEGER REFERENCES clients(id),
        quantite INTEGER NOT NULL,
        prix_unitaire REAL NOT NULL,
        montant_total REAL NOT NULL,
        role TEXT NOT NULL,
        date_vente TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS charges_fixes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        libelle TEXT NOT NULL,
        montant REAL NOT NULL,
        periodicite TEXT NOT NULL CHECK(periodicite IN ('jour', 'semaine', 'quinzaine', 'mois')),
        actif INTEGER NOT NULL DEFAULT 1,
        date_creation TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS depenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        journee_id INTEGER NOT NULL REFERENCES journees(id),
        libelle TEXT NOT NULL,
        montant REAL NOT NULL,
        categorie TEXT,
        role TEXT NOT NULL,
        date_depense TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS mouvements_stock (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        produit_id INTEGER NOT NULL REFERENCES produits(id),
        type_mouvement TEXT NOT NULL CHECK(type_mouvement IN ('entree', 'sortie', 'ajustement')),
        quantite INTEGER NOT NULL,
        prix_unitaire_achat REAL,
        motif TEXT,
        role TEXT NOT NULL,
        date_mouvement TEXT NOT NULL DEFAULT (datetime('now')),
        journee_id INTEGER REFERENCES journees(id)
    );

    CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        table_cible TEXT NOT NULL,
        enregistrement_id INTEGER NOT NULL,
        action TEXT NOT NULL CHECK(action IN ('modification', 'suppression', 'deverrouillage_journee')),
        ancienne_valeur TEXT,
        nouvelle_valeur TEXT,
        role TEXT NOT NULL,
        date_action TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE INDEX IF NOT EXISTS idx_ventes_journee ON ventes(journee_id);
    CREATE INDEX IF NOT EXISTS idx_depenses_journee ON depenses(journee_id);
    CREATE INDEX IF NOT EXISTS idx_mouvements_produit ON mouvements_stock(produit_id);
    """)

    conn.commit()

    # Migration douce : ajoute les colonnes manquantes si la base a été créée
    # avec une version antérieure du schéma, sans perdre les données existantes.
    colonnes_a_ajouter = [
        ("logo_path", "TEXT DEFAULT ''"),
        ("pref_entree_stock", "INTEGER NOT NULL DEFAULT 1"),
        ("pref_depenses", "INTEGER NOT NULL DEFAULT 1"),
        ("pref_stock_final", "INTEGER NOT NULL DEFAULT 0"),
        ("email_principal", "TEXT NOT NULL DEFAULT ''"),
        ("email_secondaire", "TEXT DEFAULT ''"),
        ("jours_travail_semaine", "INTEGER NOT NULL DEFAULT 6"),
        ("smtp_hote", "TEXT DEFAULT ''"),
        ("smtp_port", "INTEGER DEFAULT 587"),
        ("smtp_utilisateur", "TEXT DEFAULT ''"),
        ("smtp_mot_de_passe", "TEXT DEFAULT ''"),
    ]
    for nom_colonne, definition in colonnes_a_ajouter:
        try:
            cur.execute(f"ALTER TABLE configuration ADD COLUMN {nom_colonne} {definition}")
        except sqlite3.OperationalError:
            pass  # la colonne existe déjà
    try:
        cur.execute("ALTER TABLE ventes ADD COLUMN client_id INTEGER REFERENCES clients(id)")
    except sqlite3.OperationalError:
        pass
    try:
        cur.execute("ALTER TABLE ventes ADD COLUMN facture_id INTEGER REFERENCES factures(id)")
    except sqlite3.OperationalError:
        pass
    try:
        cur.execute("ALTER TABLE journees RENAME COLUMN rapport_whatsapp_envoye TO rapport_envoye")
    except sqlite3.OperationalError:
        pass

    # Migration : élargit la contrainte CHECK de charges_fixes pour accepter
    # 'quinzaine' si la table a été créée avec une version antérieure du schéma
    # (SQLite ne permet pas de modifier un CHECK existant sans recréer la table).
    row = cur.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'charges_fixes'"
    ).fetchone()
    if row and row[0] and "quinzaine" not in row[0]:
        cur.executescript("""
            ALTER TABLE charges_fixes RENAME TO charges_fixes_ancien;
            CREATE TABLE charges_fixes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                libelle TEXT NOT NULL,
                montant REAL NOT NULL,
                periodicite TEXT NOT NULL CHECK(periodicite IN ('jour', 'semaine', 'quinzaine', 'mois')),
                actif INTEGER NOT NULL DEFAULT 1,
                date_creation TEXT NOT NULL DEFAULT (datetime('now'))
            );
            INSERT INTO charges_fixes (id, libelle, montant, periodicite, actif, date_creation)
                SELECT id, libelle, montant, periodicite, actif, date_creation FROM charges_fixes_ancien;
            DROP TABLE charges_fixes_ancien;
        """)
    conn.commit()

    cur.execute("SELECT COUNT(*) FROM configuration")
    if cur.fetchone()[0] == 0:
        cur.execute("INSERT INTO configuration (id) VALUES (1)")
        conn.commit()

    conn.close()


# ---------- Configuration / prise en main ----------

def hash_password(mot_de_passe: str) -> str:
    return hashlib.sha256(mot_de_passe.encode("utf-8")).hexdigest()


def get_configuration():
    conn = get_connection()
    row = conn.execute("SELECT * FROM configuration WHERE id = 1").fetchone()
    conn.close()
    return dict(row) if row else None


def configuration_terminee():
    config = get_configuration()
    return bool(config and config["configuration_terminee"])


def enregistrer_configuration(nom_entreprise, identifiant, mdp_saisie, mdp_responsable,
                               logo_path=None, jours_travail_semaine=6):
    conn = get_connection()
    conn.execute(
        """UPDATE configuration
           SET nom_entreprise = ?, identifiant = ?, mdp_saisie_hash = ?,
               mdp_responsable_hash = ?, logo_path = ?, jours_travail_semaine = ?,
               configuration_terminee = 1
           WHERE id = 1""",
        (nom_entreprise, identifiant, hash_password(mdp_saisie),
         hash_password(mdp_responsable), logo_path or "", int(jours_travail_semaine)),
    )
    conn.commit()
    conn.close()


def mettre_a_jour_smtp(hote, port, utilisateur, mot_de_passe):
    conn = get_connection()
    conn.execute(
        "UPDATE configuration SET smtp_hote = ?, smtp_port = ?, smtp_utilisateur = ?, smtp_mot_de_passe = ? WHERE id = 1",
        (hote, int(port), utilisateur, mot_de_passe),
    )
    conn.commit()
    conn.close()


def verify_login(identifiant, mot_de_passe):
    """Retourne 'responsable', 'saisie' ou None selon le mot de passe fourni."""
    config = get_configuration()
    if not config or config["identifiant"] != identifiant:
        return None
    h = hash_password(mot_de_passe)
    if h == config["mdp_responsable_hash"]:
        return "responsable"
    if h == config["mdp_saisie_hash"]:
        return "saisie"
    return None


def verifier_mot_de_passe_type(type_mdp, mot_de_passe):
    """Vérifie un mot de passe contre un type précis ('saisie' ou 'responsable')."""
    if type_mdp not in ("saisie", "responsable"):
        raise ValueError("Type de mot de passe invalide.")
    config = get_configuration()
    colonne = "mdp_saisie_hash" if type_mdp == "saisie" else "mdp_responsable_hash"
    return config[colonne] == hash_password(mot_de_passe)


def changer_mot_de_passe(type_mdp, ancien_mdp, nouveau_mdp):
    """Change le mot de passe 'saisie' ou 'responsable', après vérification de l'ancien."""
    if type_mdp not in ("saisie", "responsable"):
        raise ValueError("Type de mot de passe invalide.")
    if not nouveau_mdp:
        raise ValueError("Le nouveau mot de passe est obligatoire.")
    if not verifier_mot_de_passe_type(type_mdp, ancien_mdp):
        raise ValueError("Ancien mot de passe incorrect.")

    config = get_configuration()
    colonne = "mdp_saisie_hash" if type_mdp == "saisie" else "mdp_responsable_hash"
    autre_colonne = "mdp_responsable_hash" if type_mdp == "saisie" else "mdp_saisie_hash"
    if hash_password(nouveau_mdp) == config[autre_colonne]:
        raise ValueError("Le nouveau mot de passe doit être différent de l'autre mot de passe.")

    conn = get_connection()
    conn.execute(f"UPDATE configuration SET {colonne} = ? WHERE id = 1", (hash_password(nouveau_mdp),))
    conn.commit()
    conn.close()


# ---------- Journées ----------

def get_or_create_journee_du_jour():
    today = date.today().isoformat()
    conn = get_connection()
    row = conn.execute("SELECT * FROM journees WHERE date_jour = ?", (today,)).fetchone()
    nouvelle_journee = row is None
    if nouvelle_journee:
        conn.execute("INSERT INTO journees (date_jour) VALUES (?)", (today,))
        conn.commit()
        row = conn.execute("SELECT * FROM journees WHERE date_jour = ?", (today,)).fetchone()
    conn.close()
    if nouvelle_journee:
        # Applique dès l'ouverture de la journée la part journalière des
        # charges fixes actives, pour qu'elle soit visible dès la première
        # vente plutôt que de surgir d'un coup à la clôture.
        appliquer_charges_fixes_du_jour(row["id"])
    return dict(row)


def cloturer_journee(journee_id, role):
    # Applique la part journalière des charges fixes actives avant de
    # calculer le total des dépenses, pour qu'elle soit bien comptée dans
    # la marge de la journée.
    appliquer_charges_fixes_du_jour(journee_id, role)

    conn = get_connection()
    ca = conn.execute(
        "SELECT COALESCE(SUM(montant_total), 0) AS total FROM ventes WHERE journee_id = ?",
        (journee_id,),
    ).fetchone()["total"]
    depenses = conn.execute(
        "SELECT COALESCE(SUM(montant), 0) AS total FROM depenses WHERE journee_id = ?",
        (journee_id,),
    ).fetchone()["total"]

    conn.execute(
        """UPDATE journees
           SET statut = 'cloturee', chiffre_affaires = ?, total_depenses = ?, date_cloture = ?
           WHERE id = ?""",
        (ca, depenses, datetime.now().isoformat(), journee_id),
    )
    conn.commit()
    conn.close()
    return {"chiffre_affaires": ca, "total_depenses": depenses}


def marquer_rapport_envoye(journee_id):
    conn = get_connection()
    conn.execute("UPDATE journees SET rapport_envoye = 1 WHERE id = ?", (journee_id,))
    conn.commit()
    conn.close()


def deverrouiller_journee(journee_id, role):
    conn = get_connection()
    ancienne = conn.execute("SELECT * FROM journees WHERE id = ?", (journee_id,)).fetchone()
    conn.execute("UPDATE journees SET statut = 'ouverte' WHERE id = ?", (journee_id,))
    conn.execute(
        """INSERT INTO audit_log (table_cible, enregistrement_id, action, ancienne_valeur, role)
           VALUES ('journees', ?, 'deverrouillage_journee', ?, ?)""",
        (journee_id, json.dumps(dict(ancienne)), role),
    )
    conn.commit()
    conn.close()


def rapport_journee_par_date(date_str):
    """
    date_str au format AAAA-MM-JJ. Retourne la journée correspondante ou None.
    Pour une journée encore ouverte (non clôturée), le chiffre d'affaires et
    les dépenses sont calculés en direct à partir des ventes/dépenses
    déjà saisies, plutôt que de renvoyer les valeurs figées à zéro
    (qui ne sont écrites en base qu'au moment de la clôture) — ainsi une
    recherche sur la journée en cours affiche bien les chiffres à jour.
    """
    conn = get_connection()
    row = conn.execute("SELECT * FROM journees WHERE date_jour = ?", (date_str,)).fetchone()
    if row is None:
        conn.close()
        return None
    journee = dict(row)
    if journee["statut"] == "ouverte":
        ca = conn.execute(
            "SELECT COALESCE(SUM(montant_total), 0) AS t FROM ventes WHERE journee_id = ?", (journee["id"],)
        ).fetchone()["t"]
        dep = conn.execute(
            "SELECT COALESCE(SUM(montant), 0) AS t FROM depenses WHERE journee_id = ?", (journee["id"],)
        ).fetchone()["t"]
        journee["chiffre_affaires"] = ca
        journee["total_depenses"] = dep
    conn.close()
    return journee


def rapport_periode(date_debut, date_fin):
    """Agrège les journées clôturées entre deux dates (incluses), format AAAA-MM-JJ."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT * FROM journees
           WHERE date_jour BETWEEN ? AND ? AND statut = 'cloturee'
           ORDER BY date_jour""",
        (date_debut, date_fin),
    ).fetchall()
    conn.close()
    journees = [dict(r) for r in rows]
    return {
        "journees": journees,
        "total_ca": sum(j["chiffre_affaires"] for j in journees),
        "total_depenses": sum(j["total_depenses"] for j in journees),
        "nb_jours": len(journees),
    }


# ---------- Produits / stock ----------

def liste_produits(actifs_seulement=True):
    conn = get_connection()
    if actifs_seulement:
        rows = conn.execute("SELECT * FROM produits WHERE actif = 1 ORDER BY nom").fetchall()
    else:
        rows = conn.execute("SELECT * FROM produits ORDER BY nom").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def ajouter_produit(nom, quantite_stock=0, prix_achat=0, prix_vente=0, seuil_alerte=5, categorie=None):
    conn = get_connection()
    conn.execute(
        """INSERT INTO produits (nom, prix_achat, prix_vente, quantite_stock, seuil_alerte, categorie)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (nom, prix_achat, prix_vente, quantite_stock, seuil_alerte, categorie),
    )
    conn.commit()
    conn.close()


def modifier_prix_vente(produit_id, nouveau_prix_vente):
    if nouveau_prix_vente < 0:
        raise ValueError("Le prix de vente ne peut pas être négatif.")
    conn = get_connection()
    produit = conn.execute("SELECT * FROM produits WHERE id = ?", (produit_id,)).fetchone()
    if produit is None:
        conn.close()
        raise ValueError("Produit introuvable.")
    conn.execute("UPDATE produits SET prix_vente = ? WHERE id = ?", (nouveau_prix_vente, produit_id))
    conn.commit()
    conn.close()


def supprimer_produit(produit_id):
    """
    Supprime définitivement un produit. Si le produit a déjà des ventes ou
    mouvements de stock enregistrés (historique), la suppression physique
    casserait cet historique : dans ce cas, le produit est seulement
    désactivé (retiré des listes actives) plutôt que supprimé de la base.
    Retourne True si suppression définitive, False si simple désactivation.
    """
    conn = get_connection()
    a_des_ventes = conn.execute("SELECT COUNT(*) AS n FROM ventes WHERE produit_id = ?", (produit_id,)).fetchone()["n"]
    a_des_mouvements = conn.execute("SELECT COUNT(*) AS n FROM mouvements_stock WHERE produit_id = ?", (produit_id,)).fetchone()["n"]

    if a_des_ventes or a_des_mouvements:
        conn.execute("UPDATE produits SET actif = 0 WHERE id = ?", (produit_id,))
        conn.commit()
        conn.close()
        return False

    conn.execute("DELETE FROM produits WHERE id = ?", (produit_id,))
    conn.commit()
    conn.close()
    return True


def produits_stock_bas():
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM produits WHERE actif = 1 AND quantite_stock <= seuil_alerte ORDER BY quantite_stock"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def entree_stock(produit_id, quantite, prix_unitaire_achat, role, motif="Entrée en stock", marge_pourcentage=None):
    """
    Ajoute une quantité en stock pour un produit existant et ajuste le prix
    d'achat unitaire par coût moyen pondéré (CMUP), pour un calcul de marge
    fiable même avec plusieurs entrées du même produit dans la journée.

    CMUP = (stock_actuel * prix_achat_actuel + quantite_ajoutee * prix_entree) / nouveau_stock

    Si marge_pourcentage est fourni, le prix de vente du produit est
    recalculé automatiquement à partir du nouveau CMUP :
        prix_vente = CMUP * (1 + marge_pourcentage / 100)
    """
    if quantite <= 0:
        raise ValueError("La quantité doit être supérieure à zéro.")
    if prix_unitaire_achat < 0:
        raise ValueError("Le prix d'achat ne peut pas être négatif.")

    conn = get_connection()
    produit = conn.execute("SELECT * FROM produits WHERE id = ?", (produit_id,)).fetchone()
    if produit is None:
        conn.close()
        raise ValueError("Produit introuvable.")

    stock_actuel = produit["quantite_stock"]
    prix_actuel = produit["prix_achat"]
    nouveau_stock = stock_actuel + quantite

    if nouveau_stock > 0:
        nouveau_cmup = ((stock_actuel * prix_actuel) + (quantite * prix_unitaire_achat)) / nouveau_stock
    else:
        nouveau_cmup = prix_unitaire_achat
    nouveau_cmup = round(nouveau_cmup, 2)

    nouveau_prix_vente = None
    if marge_pourcentage is not None:
        nouveau_prix_vente = round(nouveau_cmup * (1 + marge_pourcentage / 100), 2)

    journee = get_or_create_journee_du_jour()

    if nouveau_prix_vente is not None:
        conn.execute(
            "UPDATE produits SET quantite_stock = ?, prix_achat = ?, prix_vente = ? WHERE id = ?",
            (nouveau_stock, nouveau_cmup, nouveau_prix_vente, produit_id),
        )
    else:
        conn.execute(
            "UPDATE produits SET quantite_stock = ?, prix_achat = ? WHERE id = ?",
            (nouveau_stock, nouveau_cmup, produit_id),
        )
    conn.execute(
        """INSERT INTO mouvements_stock
           (produit_id, type_mouvement, quantite, prix_unitaire_achat, motif, role, journee_id)
           VALUES (?, 'entree', ?, ?, ?, ?, ?)""",
        (produit_id, quantite, prix_unitaire_achat, motif, role, journee["id"]),
    )
    conn.commit()
    conn.close()
    return {"nouveau_stock": nouveau_stock, "nouveau_cmup": nouveau_cmup, "nouveau_prix_vente": nouveau_prix_vente}


def stock_final():
    """Retourne l'état du stock en temps réel, valorisé au coût moyen pondéré."""
    produits = liste_produits()
    for p in produits:
        p["valeur_stock"] = round(p["quantite_stock"] * p["prix_achat"], 2)
    return {"produits": produits, "valeur_totale": round(sum(p["valeur_stock"] for p in produits), 2)}


def mouvements_entree_du_jour(journee_id):
    conn = get_connection()
    rows = conn.execute(
        """SELECT m.quantite, m.prix_unitaire_achat, p.nom AS produit
           FROM mouvements_stock m JOIN produits p ON p.id = m.produit_id
           WHERE m.journee_id = ? AND m.type_mouvement = 'entree'
           ORDER BY m.date_mouvement""",
        (journee_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def historique_mouvements(produit_id, limite=20):
    conn = get_connection()
    rows = conn.execute(
        """SELECT * FROM mouvements_stock WHERE produit_id = ?
           ORDER BY date_mouvement DESC LIMIT ?""",
        (produit_id, limite),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---------- Ventes ----------

def enregistrer_facture(lignes, role, client_id=None, remise_montant=0, remise_pourcentage=0,
                         tva_active=False, tva_taux=18):
    """
    Enregistre une facture avec plusieurs lignes de produits en une seule
    opération atomique : vérifie le stock de chaque ligne, décrémente le
    stock, calcule remise et TVA, et retourne la facture complète.
    lignes : liste de dicts {"produit_id", "quantite", "prix_unitaire"}.
    """
    journee = get_or_create_journee_du_jour()
    if journee["statut"] == "cloturee":
        raise PermissionError("La journée est clôturée. Autorisation du responsable requise.")
    if not lignes:
        raise ValueError("La facture ne contient aucun produit.")

    conn = get_connection()
    for ligne in lignes:
        produit = conn.execute("SELECT * FROM produits WHERE id = ?", (ligne["produit_id"],)).fetchone()
        if produit is None:
            conn.close()
            raise ValueError("Produit introuvable.")
        if produit["quantite_stock"] < ligne["quantite"]:
            conn.close()
            raise ValueError(f"Stock insuffisant pour « {produit['nom']} ».")

    sous_total = sum(l["quantite"] * l["prix_unitaire"] for l in lignes)
    montant_remise = remise_montant if remise_montant > 0 else round(sous_total * remise_pourcentage / 100, 2)
    montant_remise = min(montant_remise, sous_total)
    apres_remise = sous_total - montant_remise
    montant_tva = round(apres_remise * tva_taux / 100, 2) if tva_active else 0
    montant_total = apres_remise + montant_tva

    cur = conn.execute(
        """INSERT INTO factures (numero, journee_id, client_id, sous_total, remise_montant,
               remise_pourcentage, montant_remise, tva_active, tva_taux, montant_tva, montant_total, role)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (None, journee["id"], client_id, sous_total, remise_montant, remise_pourcentage,
         montant_remise, int(bool(tva_active)), tva_taux, montant_tva, montant_total, role),
    )
    facture_id = cur.lastrowid
    numero = f"F{facture_id:06d}"
    conn.execute("UPDATE factures SET numero = ? WHERE id = ?", (numero, facture_id))

    for ligne in lignes:
        montant_ligne = ligne["quantite"] * ligne["prix_unitaire"]
        conn.execute(
            """INSERT INTO ventes (journee_id, facture_id, produit_id, client_id, quantite,
                   prix_unitaire, montant_total, role)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (journee["id"], facture_id, ligne["produit_id"], client_id, ligne["quantite"],
             ligne["prix_unitaire"], montant_ligne, role),
        )
        conn.execute("UPDATE produits SET quantite_stock = quantite_stock - ? WHERE id = ?",
                     (ligne["quantite"], ligne["produit_id"]))
        conn.execute(
            """INSERT INTO mouvements_stock (produit_id, type_mouvement, quantite, motif, role, journee_id)
               VALUES (?, 'sortie', ?, 'Vente', ?, ?)""",
            (ligne["produit_id"], ligne["quantite"], role, journee["id"]),
        )

    conn.commit()
    conn.close()
    return get_facture(facture_id)


def get_facture(facture_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM factures WHERE id = ?", (facture_id,)).fetchone()
    if row is None:
        conn.close()
        return None
    facture = dict(row)
    lignes = conn.execute(
        """SELECT v.*, p.nom AS produit_nom FROM ventes v
           JOIN produits p ON p.id = v.produit_id
           WHERE v.facture_id = ? ORDER BY v.id""",
        (facture_id,),
    ).fetchall()
    facture["lignes"] = [dict(r) for r in lignes]
    facture["client"] = None
    if facture["client_id"]:
        client = conn.execute("SELECT * FROM clients WHERE id = ?", (facture["client_id"],)).fetchone()
        facture["client"] = dict(client) if client else None
    conn.close()
    return facture


def factures_du_jour(journee_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM factures WHERE journee_id = ? ORDER BY date_facture DESC", (journee_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def ventes_du_jour(journee_id):
    conn = get_connection()
    rows = conn.execute(
        """SELECT v.id, p.nom AS produit, v.quantite, v.prix_unitaire, v.montant_total, v.role, v.date_vente
           FROM ventes v JOIN produits p ON p.id = v.produit_id
           WHERE v.journee_id = ? ORDER BY v.date_vente DESC""",
        (journee_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def factures_par_periode(date_debut, date_fin):
    """
    Factures émises entre deux dates (incluses), avec le nom/téléphone du
    client et la date du jour concerné — utilisé pour les rapports
    détaillés (jour précis : date_debut == date_fin, ou période).
    """
    conn = get_connection()
    rows = conn.execute(
        """SELECT f.*, j.date_jour, c.nom AS client_nom, c.telephone AS client_telephone
           FROM factures f
           JOIN journees j ON j.id = f.journee_id
           LEFT JOIN clients c ON c.id = f.client_id
           WHERE j.date_jour BETWEEN ? AND ?
           ORDER BY j.date_jour, f.date_facture""",
        (date_debut, date_fin),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def depenses_par_periode(date_debut, date_fin):
    """Dépenses entre deux dates (incluses), avec la date du jour concerné."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT d.*, j.date_jour
           FROM depenses d
           JOIN journees j ON j.id = d.journee_id
           WHERE j.date_jour BETWEEN ? AND ?
           ORDER BY j.date_jour, d.date_depense""",
        (date_debut, date_fin),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def mouvements_produit_periode(produit_id, date_debut, date_fin):
    """
    Toutes les entrées et sorties de stock d'un produit entre deux dates
    (incluses), triées de la date la plus ancienne à la plus récente.
    Les sorties correspondent aux ventes : elles sont récupérées depuis la
    table des ventes (jointe à la facture) pour indiquer le numéro de
    facture concerné, plutôt que depuis mouvements_stock qui n'a pas ce lien.
    """
    conn = get_connection()

    entrees = conn.execute(
        """SELECT m.quantite, m.prix_unitaire_achat AS prix_unitaire, m.role,
                  m.date_mouvement AS date_heure, j.date_jour
           FROM mouvements_stock m
           JOIN journees j ON j.id = m.journee_id
           WHERE m.produit_id = ? AND m.type_mouvement = 'entree'
             AND j.date_jour BETWEEN ? AND ?""",
        (produit_id, date_debut, date_fin),
    ).fetchall()

    sorties = conn.execute(
        """SELECT v.quantite, v.prix_unitaire, v.role, v.date_vente AS date_heure,
                  j.date_jour, f.numero AS numero_facture
           FROM ventes v
           JOIN journees j ON j.id = v.journee_id
           LEFT JOIN factures f ON f.id = v.facture_id
           WHERE v.produit_id = ? AND j.date_jour BETWEEN ? AND ?""",
        (produit_id, date_debut, date_fin),
    ).fetchall()
    conn.close()

    mouvements = []
    for e in entrees:
        d = dict(e)
        d["type"] = "entree"
        d["numero_facture"] = None
        mouvements.append(d)
    for s in sorties:
        d = dict(s)
        d["type"] = "sortie"
        mouvements.append(d)

    mouvements.sort(key=lambda m: (m["date_jour"], m["date_heure"]))
    return mouvements


# ---------- Dépenses ----------

def enregistrer_depense(libelle, montant, categorie, role):
    journee = get_or_create_journee_du_jour()
    if journee["statut"] == "cloturee":
        raise PermissionError("La journée est clôturée. Autorisation du responsable requise.")

    conn = get_connection()
    conn.execute(
        "INSERT INTO depenses (journee_id, libelle, montant, categorie, role) VALUES (?, ?, ?, ?, ?)",
        (journee["id"], libelle, montant, categorie, role),
    )
    conn.commit()
    conn.close()


def depenses_du_jour(journee_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM depenses WHERE journee_id = ? ORDER BY date_depense DESC", (journee_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---------- Clients ----------

def liste_clients():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM clients ORDER BY nom").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def trouver_ou_creer_client(nom, telephone, adresse):
    """
    Retrouve un client existant par téléphone (ou nom), sinon le crée.
    Retourne None si ni nom ni téléphone ne sont fournis (client anonyme).
    """
    nom = (nom or "").strip()
    telephone = (telephone or "").strip()
    adresse = (adresse or "").strip()
    if not nom and not telephone:
        return None

    conn = get_connection()
    client = None
    if telephone:
        client = conn.execute("SELECT * FROM clients WHERE telephone = ?", (telephone,)).fetchone()
    if client is None and nom:
        client = conn.execute("SELECT * FROM clients WHERE nom = ?", (nom,)).fetchone()

    if client:
        client_id = client["id"]
        conn.execute(
            """UPDATE clients SET
               nom = COALESCE(NULLIF(?, ''), nom),
               telephone = COALESCE(NULLIF(?, ''), telephone),
               adresse = COALESCE(NULLIF(?, ''), adresse)
               WHERE id = ?""",
            (nom, telephone, adresse, client_id),
        )
    else:
        cur = conn.execute(
            "INSERT INTO clients (nom, telephone, adresse) VALUES (?, ?, ?)",
            (nom, telephone, adresse),
        )
        client_id = cur.lastrowid

    conn.commit()
    conn.close()
    return client_id


def clients_avec_cumul():
    """Liste des clients avec le cumul (montant total et nombre) de leurs achats."""
    conn = get_connection()
    rows = conn.execute(
        """SELECT c.*, COALESCE(SUM(v.montant_total), 0) AS total_achats, COUNT(v.id) AS nb_achats
           FROM clients c LEFT JOIN ventes v ON v.client_id = c.id
           GROUP BY c.id ORDER BY total_achats DESC"""
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---------- Charges fixes ----------

JOURS_PAR_MOIS_MOYEN = 30.4375  # 365,25 / 12


def liste_charges_fixes(actives_seulement=False):
    conn = get_connection()
    if actives_seulement:
        rows = conn.execute("SELECT * FROM charges_fixes WHERE actif = 1 ORDER BY libelle").fetchall()
    else:
        rows = conn.execute("SELECT * FROM charges_fixes ORDER BY libelle").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def ajouter_charge_fixe(libelle, montant, periodicite):
    if periodicite not in ("jour", "semaine", "quinzaine", "mois"):
        raise ValueError("Périodicité invalide.")
    if montant < 0:
        raise ValueError("Le montant ne peut pas être négatif.")
    conn = get_connection()
    conn.execute(
        "INSERT INTO charges_fixes (libelle, montant, periodicite) VALUES (?, ?, ?)",
        (libelle, montant, periodicite),
    )
    conn.commit()
    conn.close()


def supprimer_charge_fixe(charge_id):
    conn = get_connection()
    conn.execute("DELETE FROM charges_fixes WHERE id = ?", (charge_id,))
    conn.commit()
    conn.close()


def equivalent_journalier(charge, jours_travail_semaine):
    """
    Convertit le montant d'une charge fixe en équivalent journalier, selon
    sa périodicité et le nombre de jours de travail par semaine défini à
    la configuration.
    """
    if charge["periodicite"] == "jour":
        return charge["montant"]
    if charge["periodicite"] == "semaine":
        return charge["montant"] / jours_travail_semaine if jours_travail_semaine else 0
    if charge["periodicite"] == "quinzaine":
        return charge["montant"] / (2 * jours_travail_semaine) if jours_travail_semaine else 0
    # "mois" : nombre de jours ouvrés dans un mois moyen = jours/semaine * (jours_par_mois / 7)
    jours_ouvres_mois = jours_travail_semaine * (JOURS_PAR_MOIS_MOYEN / 7)
    return charge["montant"] / jours_ouvres_mois if jours_ouvres_mois else 0


def total_charges_fixes_du_jour():
    """Somme des charges fixes actives, ramenées à leur équivalent journalier."""
    config = get_configuration()
    jours_travail_semaine = config["jours_travail_semaine"] if config else 6
    charges = liste_charges_fixes(actives_seulement=True)
    return round(sum(equivalent_journalier(c, jours_travail_semaine) for c in charges), 2)


def appliquer_charges_fixes_du_jour(journee_id, role="system"):
    """
    Ajoute une dépense par charge fixe active représentant sa part
    journalière — une seule fois par journée (ne duplique pas si déjà
    appliqué). Appelé dès l'ouverture de la journée (première vente/accès)
    afin que la part journalière des charges fixes soit visible tout au
    long de la journée, et pas seulement révélée d'un coup à la clôture.
    """
    conn = get_connection()
    deja_applique = conn.execute(
        "SELECT COUNT(*) AS n FROM depenses WHERE journee_id = ? AND categorie = 'charge_fixe'",
        (journee_id,),
    ).fetchone()["n"]
    if deja_applique:
        conn.close()
        return

    config = get_configuration()
    jours_travail_semaine = config["jours_travail_semaine"] if config else 6
    charges = liste_charges_fixes(actives_seulement=True)
    for charge in charges:
        montant_jour = round(equivalent_journalier(charge, jours_travail_semaine), 2)
        if montant_jour <= 0:
            continue
        conn.execute(
            """INSERT INTO depenses (journee_id, libelle, montant, categorie, role)
               VALUES (?, ?, ?, 'charge_fixe', ?)""",
            (journee_id, f"Charge fixe : {charge['libelle']}", montant_jour, role),
        )
    conn.commit()
    conn.close()

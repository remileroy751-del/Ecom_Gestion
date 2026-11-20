# Système de Gestion Avancée du Stock — v1.0

Application desktop locale (base de données SQLite stockée sur l'ordinateur de
l'entreprise) pour la gestion de stock, des ventes multi-produits et des
dépenses, avec verrouillage journalier et rapports détaillés exportables.

## Installation

1. Installer Python 3.10 ou plus récent : https://www.python.org/downloads/
2. Ouvrir un terminal dans ce dossier et installer les dépendances :

   ```
   pip install -r requirements.txt
   ```

3. Lancer l'application :

   ```
   python main.py
   ```

## Lancement en un clic (sans ligne de commande)

- **Windows** : double-cliquer sur `Lancer_application.bat`.
- **macOS / Linux** : double-cliquer sur `lancer_application.sh` (ou
  `./lancer_application.sh` dans un terminal).
- **Pour vos clients (recommandé)** : `creer_executable.bat` génère un
  `GestionStock.exe` autonome (dossier `dist`), qui n'a pas besoin de
  Python installé sur le poste final. Voir aussi la section **Compiler via
  GitHub** ci-dessous pour une compilation automatisée, sans même avoir
  besoin d'un PC Windows sous la main.

## Configuration initiale (premier lancement uniquement)

1. **Étape 1 — Compte**
   - Logo (facultatif), nom de l'entreprise, identifiant unique, mot de
     passe « saisie » et mot de passe « responsable » (différents — le mot
     de passe saisi à la connexion détermine automatiquement le rôle).
   - **Nombre de jours de travail par semaine** (7/7, 6/7 ou 5/7) — sert à
     répartir automatiquement les charges fixes (loyer, etc.) en équivalent
     journalier.
2. **Étape 2 — Produits** : au moins un produit avec nom, quantité, coût
   d'achat et prix de vente (tous obligatoires).

## Format des montants

Tous les montants affichés utilisent un **espace comme séparateur de
milliers** (ex : `1 234 567 FCFA`) — ni virgule, ni point.

## Écrans inclus

- **Tableau de bord** — chiffre d'affaires, dépenses et marge du jour en
  grand ; en dessous, en plus petite police, le même résumé de **la
  journée précédente**.
- **Ventes** — facture multi-produits :
  1. Bouton **Vendre** → ouvre l'onglet de saisie : on choisit un produit,
     sa quantité, son prix unitaire et son stock disponible s'affichent
     automatiquement. Le bouton **Enregistrer** ajoute le produit à la
     facture (on peut en ajouter plusieurs), le bouton **Terminé** ferme
     l'onglet.
  2. La facture s'affiche alors en lecture, sous forme de tableau
     **Désignation / Quantité / Prix unitaire / Montant**, avec le
     sous-total, la remise, la TVA et le montant à payer resserrés juste
     en dessous (trait noir de séparation, libellé avant le montant — ex.
     « Remise : -102 FCFA »). On peut y appliquer une **Remise** (montant
     fixe ou %) et activer la **TVA 18 %**. Trois boutons : **Enregistrer**
     (sauvegarde définitivement, décrémente le stock), **Modifier** (retour
     à la saisie), **Imprimer**.
  3. Une fois enregistrée, la facture n'est plus modifiable : seuls
     **Retour** (revient à l'écran de vente pour une nouvelle facture) et
     **Imprimer** restent visibles.
  - L'en-tête de la facture affiche le numéro, puis les informations du
    client en gros caractères, puis la traçabilité (« Saisi par le Chef »
    / « Saisi par le Secrétaire ») en plus petit, en haut du tableau.
  - Client facultatif (nom, téléphone, adresse) — retrouvé automatiquement
    par téléphone pour les achats suivants, cumul consultable dans les
    Options avancées.
  - La liste « Factures du jour » affiche chaque facture par son numéro
    avec sa traçabilité ; un clic sur « Voir le détail » ouvre le détail
    complet (produits, remise, TVA).
- **Produits / Stock** — augmenter le stock d'un produit existant (coût
  moyen pondéré recalculé automatiquement) ; ajouter un nouveau produit
  (nécessite le mot de passe responsable).
- **Stock final** — quantités et valeur du stock en temps réel.
- **Dépenses** — saisie + historique, avec la mention **« Saisi par le
  Secrétaire »** ou **« Saisi par le Chef »** sur chaque ligne.
- **Clôture du jour** — verrouille les saisies et applique automatiquement
  la part journalière des charges fixes actives. Déverrouillage réservé
  au responsable.
- **Rapports** — recherche par date précise (calendrier cliquable,
  fonctionne aussi pour la journée en cours) et par période (réservé au
  responsable). Chaque résultat s'affiche en **tableaux détaillés** :
  - En-tête « Rapport du (date) » ou « Rapport du (date1) au (date2) »
  - Tableau **Ventes** : N° Facture / Montant / Traçabilité / Client /
    Numéro (+ colonne Date en plus pour une période), avec le total des
    factures en bas
  - Tableau **Dépenses** : Nature des dépenses / Montant / Traçabilité
    (+ colonne Date en plus pour une période), avec le total en bas
  - Boutons **Exporter en PDF** et **Exporter en Excel**, déposés
    directement sur le **Bureau** de l'ordinateur, avec la même mise en
    forme en tableaux.
  - **Mouvements de stock par produit** (réservé au responsable) : on
    choisit un produit et une date (ou une période), et le tableau liste
    toutes ses entrées et sorties (les sorties étant les ventes, avec leur
    numéro de facture), triées de la plus ancienne à la plus récente, avec
    le total d'unités entrées et sorties. Exportable en PDF/Excel comme les
    autres rapports.
- **Options avancées** (responsable uniquement) :
  - Changement de mot de passe (avec vérification de l'ancien).
  - Modification du prix de vente d'un produit.
  - Suppression d'un produit (définitive si aucun historique, sinon
    simple désactivation pour préserver les rapports passés).
  - Liste des clients avec cumul de leurs achats.
  - **Charges fixes** : libellé, montant, périodicité (tous les jours /
    chaque semaine / chaque 2 semaines / chaque mois) — converties
    automatiquement en équivalent journalier selon le nombre de jours de
    travail par semaine, et appliquées dès l'ouverture de chaque journée
    (pas seulement à la clôture), pour que la marge affichée en cours de
    journée soit toujours réaliste.

Un pied de page permanent affiche : *« Cette application avancée de Stock
est produit par Ecom-Academy. Contactez-nous au +22899373635. »*

Après la configuration initiale, un écran d'avertissement rappelle que
l'application n'est pas connectée à internet et que les données restent
uniquement sur l'ordinateur — l'utilisateur doit cliquer sur **« J'ai
compris »** pour accéder à l'écran de connexion.

## Pas d'envoi automatisé par email

L'application n'envoie plus de rapport par email après chaque clôture.
L'export PDF (voir ci-dessus, déposé sur le Bureau) suffit pour couvrir ce
besoin : le responsable peut l'envoyer lui-même manuellement par email ou
WhatsApp à qui il veut, sans dépendance à un serveur SMTP ni configuration
technique côté client.

## Factures

Les factures sont enregistrées en texte simple dans `factures/` (impression
via l'imprimante par défaut du système).

## Compiler via GitHub (sans PC Windows)

Le dossier `.github/workflows/build-exe.yml` fourni compile automatiquement
`GestionStock.exe` à chaque mise à jour du code, même si vous travaillez
sur Mac ou Linux :

1. Créez un dépôt sur [GitHub](https://github.com) et envoyez-y tous ces
   fichiers (`git init`, `git add .`, `git commit`, puis liez le dépôt
   distant et poussez).
2. Allez dans l'onglet **Actions** du dépôt : la compilation se lance
   automatiquement. Une fois terminée, l'exécutable est disponible en
   téléchargement (section *Artifacts* de l'exécution).
3. Pour une version « officielle » plus facile à partager avec vos clients,
   créez un tag de version (`git tag v1.0` puis `git push origin v1.0`) :
   une **Release GitHub** est alors créée automatiquement avec le `.exe`
   déjà joint, avec un lien de téléchargement direct et stable.

Le fichier `.gitignore` fourni exclut déjà la base de données locale, les
factures, les exports et les fichiers de compilation — seul le code source
est envoyé sur GitHub.

## Prochaines étapes suggérées

- Facture en PDF mis en forme (au lieu du texte simple actuel)
- Sauvegarde automatique chiffrée de la base
- Système de licence/activation par poste
- Bandeau publicitaire avec image (pas seulement du texte)

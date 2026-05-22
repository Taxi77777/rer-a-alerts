# 🚇 RER A - Système d'Alertes Telegram Automatique (Branche A4 Marne-la-Vallée)

Bienvenue dans le guide complet pour installer et configurer votre système d'alertes de perturbations RER A. Ce projet est conçu pour être **100% gratuit à vie**, sans serveur à gérer chez vous, et hébergé directement sur **GitHub Actions**.

Ce système surveille la ligne du **RER A** et filtre les incidents en temps réel pour ne vous envoyer que ce qui affecte vos gares de la branche Marne-la-Vallée (A4) :
*   **Torcy**
*   **Bussy-Saint-Georges**
*   **Val d'Europe**
*   **Chessy - Marne-la-Vallée**

---

## 📋 Prérequis

Pour faire fonctionner ce robot, vous devez effectuer quatre configurations initiales simples (durée totale estimée : 20 minutes). Aucune compétence en programmation n'est requise.

### A) Créer un bot Telegram (5 min)

Le bot est l'outil virtuel qui ira chercher les perturbations pour vous les envoyer.

1.  Ouvrez votre application **Telegram** sur votre téléphone ou sur votre ordinateur ([web.telegram.org](https://web.telegram.org/)).
2.  Dans la barre de recherche en haut, cherchez `@BotFather` (assurez-vous qu'il ait un badge de certification bleu à côté de son nom).
3.  Démarrez la conversation en cliquant sur le bouton **Démarrer** (ou envoyez le message `/start`).
4.  Envoyez le message `/newbot` pour créer un nouveau robot.
5.  **BotFather** va vous demander de lui donner un nom public (par exemple : `Alertes RER A`). Tapez-le et validez.
6.  Ensuite, il va vous demander un identifiant unique (username) qui doit obligatoirement se terminer par le mot `bot` (par exemple : `alertes_rer_a_rachid_bot`).
7.  Une fois l'identifiant accepté, **BotFather** va vous féliciter et vous afficher un texte contenant un **Token HTTP API** (une longue clé secrète contenant des chiffres, des lettres et des symboles).
    *   *Exemple de Token :* `1234567890:ABCdefGhIJKlmNoPQRsTUVwxyZ`
    *   ⚠️ **Important :** Copiez ce Token et conservez-le précieusement dans un bloc-notes. Ne le partagez avec personne, car il permet de contrôler votre bot.

---

### B) Créer le groupe Telegram (3 min)

Le groupe Telegram est l'endroit où vous et vos proches allez recevoir les messages d'alerte.

1.  Dans l'application Telegram, créez un **Nouveau groupe**.
2.  Donnez-lui un nom clair (par exemple : `🚇 Alertes RER A`).
3.  Dans la liste des membres à ajouter, recherchez l'identifiant unique de votre bot créé à l'étape précédente (par exemple : `@alertes_rer_a_rachid_bot`) et ajoutez-le au groupe.
4.  **Étape cruciale :** Vous devez promouvoir votre bot en tant qu'**Administrateur** du groupe.
    *   *Sur téléphone :* Allez sur les infos du groupe, appuyez longuement sur le profil du bot, puis sélectionnez "Promouvoir comme administrateur" ou "Modifier les droits" et assurez-vous qu'il ait le droit d'envoyer des messages.
    *   *Pourquoi ?* Si le bot n'est pas administrateur, il ne sera pas autorisé à publier des messages dans le groupe de discussion.
5.  Invitez les membres de votre famille ou vos amis dans ce groupe via le lien d'invitation classique si vous le souhaitez.

---

### C) Récupérer le CHAT_ID de votre groupe (2 min)

Pour que le bot sache dans quel groupe envoyer les alertes, il a besoin de connaître l'identifiant numérique unique du groupe (appelé `TELEGRAM_CHAT_ID`).

1.  Envoyez un message d'essai quelconque dans votre nouveau groupe (par exemple : `Salut le bot`).
2.  Ouvrez votre navigateur internet habituel (Chrome, Firefox, Safari, Edge...).
3.  Entrez l'URL suivante dans votre barre d'adresse en remplaçant `<TOKEN>` par le long token secret fourni par BotFather à l'étape A :
    ```text
    https://api.telegram.org/bot<TOKEN>/getUpdates
    ```
    *Exemple concret d'URL :* `https://api.telegram.org/bot1234567890:ABCdefGhIJKlmNoPQRsTUVwxyZ/getUpdates`
4.  Appuyez sur Entrée. Vous devriez voir une page avec du texte au format brut (JSON).
5.  Recherchez dans ce texte la mention `"chat":{"id":` suivi d'un nombre négatif.
    *   *Exemple de ce que vous devez chercher :* `"chat":{"id":-1001987654321,"title":"🚇 Alertes RER A",...}`
6.  Copiez ce nombre avec son signe moins (par exemple : `-1001987654321`). C'est votre `TELEGRAM_CHAT_ID`. Notez-le dans votre bloc-notes.
    *   *Note :* Si le texte affiché est vide (`{"ok":true,"result":[]}`), renvoyez un message dans le groupe Telegram, rafraîchissez la page internet ou vérifiez bien que le bot est bien membre du groupe.

---

### D) Inscription à PRIM d'Île-de-France Mobilités (10 min)

PRIM est la plateforme officielle qui fournit gratuitement les données de transports en temps réel pour toute l'Île-de-France.

1.  Rendez-vous sur le site officiel de PRIM : [prim.iledefrance-mobilites.fr](https://prim.iledefrance-mobilites.fr/)
2.  En haut à droite, cliquez sur **S'inscrire** et créez un compte gratuit avec votre adresse e-mail.
3.  Consultez votre boîte mail et cliquez sur le lien de confirmation envoyé par la plateforme.
4.  Connectez-vous à votre espace personnel sur PRIM.
5.  Dans le menu principal, allez dans le **Catalogue des données (APIs)**.
6.  Cherchez le jeu de données nommé : **Messages Info Trafic - Requête globale**.
7.  Cliquez sur le bouton **S'abonner à l'API** associé à ce jeu de données (l'abonnement est immédiat et 100% gratuit).
8.  Dans votre menu utilisateur en haut à droite, allez dans l'onglet **Gérer mes quotas** ou **Mes jetons (API keys)**.
9.  Générez un nouveau jeton (apikey).
10. Copiez la clé API générée (une suite de chiffres et de lettres). C'est votre `PRIM_API_KEY`. Notez-la dans votre bloc-notes.

---

## 🚀 Installation pas à pas sur GitHub

Maintenant que vous avez vos clés d'accès (`PRIM_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`), vous allez déployer le programme sur GitHub pour qu'il s'exécute automatiquement.

### 1. Créer le dépôt sur GitHub
1.  Si ce n'est pas déjà fait, créez un compte gratuit sur [github.com](https://github.com/).
2.  En haut à droite de l'écran d'accueil de GitHub, cliquez sur le bouton `+` puis sur **New repository** (Nouveau dépôt).
3.  Remplissez les champs comme suit :
    *   **Repository name :** `rer-a-alerts`
    *   **Description :** `Bot d'alertes de trafic RER A branche A4 pour Telegram`
    *   **Visibilité :** Cochez impérativement **Private** (Privé). C'est très important pour éviter que d'autres personnes ne puissent voir votre fichier d'historique.
4.  Laissez le reste par défaut et cliquez sur le bouton vert **Create repository**.

---

### 2. Ajouter les fichiers au dépôt
Puisque vous êtes sur votre ordinateur, vous allez importer les fichiers de ce projet.
Dans le dossier `C:\Users\rachi\Downloads\rer-a-alerts\`, vous trouverez les fichiers nécessaires. 

Pour les ajouter sur votre projet GitHub en ligne :
1.  Sur la page de votre nouveau dépôt vide sur GitHub, cliquez sur le lien bleu **uploading an existing file** (importer un fichier existant).
2.  Glissez-déposez l'ensemble des fichiers suivants depuis votre dossier local `C:\Users\rachi\Downloads\rer-a-alerts\` vers la zone de dépôt de GitHub :
    *   `main.py`
    *   `requirements.txt`
    *   `.gitignore`
    *   `alerts_history.json`
3.  Pour le fichier de workflow GitHub Actions, vous devez le placer dans un dossier spécial :
    *   Sur l'interface de GitHub en haut, cliquez sur **Create new file** (Créer un nouveau fichier).
    *   Dans le nom du fichier, écrivez précisément : `.github/workflows/rer-a-alerts.yml` (les dossiers `.github` et `workflows` se créeront automatiquement).
    *   Copiez et collez à l'intérieur le contenu du fichier de configuration du workflow disponible dans votre dossier local.
4.  Cliquez sur le bouton vert **Commit changes** en bas de page pour enregistrer.

---

### 3. Configurer vos Secrets (Clés de sécurité) sur GitHub
Pour que GitHub Actions puisse s'exécuter en toute sécurité sans écrire vos mots de passe dans le code public, nous utilisons les "Secrets GitHub".

1.  Sur la page de votre dépôt de code sur GitHub, cliquez sur l'onglet **Settings** (Paramètres, avec l'icône de rouage en haut à droite).
2.  Dans le menu de gauche, faites défiler vers le bas et cliquez sur **Secrets and variables**, puis sur **Actions**.
3.  Cliquez sur le bouton vert **New repository secret** (Nouveau secret de dépôt) en haut à droite.
4.  Ajoutez votre premier secret :
    *   **Name :** `PRIM_API_KEY`
    *   **Secret :** Collez votre jeton d'API de la plateforme PRIM récupéré à l'étape D.
    *   Cliquez sur **Add secret**.
5.  Cliquez à nouveau sur **New repository secret** pour ajouter le deuxième secret :
    *   **Name :** `TELEGRAM_BOT_TOKEN`
    *   **Secret :** Collez le Token HTTP fourni par BotFather à l'étape A.
    *   Cliquez sur **Add secret**.
6.  Cliquez une dernière fois sur **New repository secret** pour ajouter le troisième secret :
    *   **Name :** `TELEGRAM_CHAT_ID`
    *   **Secret :** Collez le numéro négatif identifiant votre groupe récupéré à l'étape C.
    *   Cliquez sur **Add secret**.

Vos secrets sont maintenant configurés de manière ultra-sécurisée. Ils ne sont visibles par personne.

---

### 4. Activer GitHub Actions et lancer le premier test
Par défaut, GitHub Actions peut nécessiter une activation manuelle sur les dépôts privés copiés.

1.  Allez dans l'onglet **Actions** en haut de la page de votre dépôt.
2.  Si un bouton vert apparaît vous demandant d'activer les Actions, cliquez dessus (`I understand my workflows, go ahead and enable them`).
3.  Dans la colonne de gauche sous **Workflows**, cliquez sur **Suivi Trafic RER A - Alertes Telegram**.
4.  À droite de l'écran, cliquez sur le menu déroulant **Run workflow**, puis cliquez sur le bouton vert **Run workflow**.
5.  Attendez une minute. Une ligne verte va apparaître avec une coche, indiquant que l'exécution s'est déroulée avec succès.
6.  Vérifiez votre groupe Telegram : vous devriez recevoir un message automatique s'il y a des perturbations en cours sur la ligne !

---

## 📱 Utilisation et Dépannage

### Comment fonctionne le bot au quotidien ?
*   **Fréquence :** Le programme tourne automatiquement toutes les 5 minutes.
*   **Doublons :** Le fichier `alerts_history.json` mémorise les alertes déjà envoyées. Si un incident dure 4 heures, vous ne recevrez le message qu'une seule fois.
*   **Mise à jour :** Si la RATP modifie l'heure de fin estimée ou ajoute des détails à un incident existant, le bot détecte la modification et envoie le message précédé de `🔄 Mise à jour :`.
*   **Mode Nuit :** Entre 1h01 et 4h59 du matin, les alertes sont enregistrées silencieusement dans l'historique mais ne sont pas envoyées sur votre téléphone afin de préserver votre sommeil. Elles apparaîtront comme déjà lues à votre réveil.

### Guide de dépannage rapide

| Problème constaté | Cause probable | Solution recommandée |
| :--- | :--- | :--- |
| **Le workflow GitHub Actions échoue (croix rouge)** | Clé manquante ou incorrecte dans les secrets. | Retournez dans *Settings* -> *Secrets* -> *Actions* et vérifiez que les noms des 3 secrets correspondent exactement, sans espaces. |
| **Aucun message reçu sur Telegram alors que le run GitHub est vert** | Le Bot n'est pas administrateur du groupe Telegram. | Allez dans les réglages de votre groupe Telegram, vérifiez que le bot est bien présent et qu'il dispose des permissions d'administration pour écrire. |
| **Erreur dans les logs : "getUpdates vide"** | Aucun message n'a été envoyé dans le groupe avant d'interroger getUpdates. | Renvoyez un message de test dans le groupe Telegram, puis rechargez la page getUpdates. |
| **Le bot envoie trop d'alertes sur d'autres branches** | Les gares d'autres branches sont mal exclues. | Le script exclut par défaut les branches Boissy, Cergy, Poissy et Saint-Germain si notre branche Marne-la-Vallée n'est pas citée. |

---

## 🔧 Personnalisation

Si vous êtes à l'aise, vous pouvez modifier les fichiers directement depuis l'interface web de GitHub (en cliquant sur l'icône de crayon sur un fichier).

### Modifier les gares à surveiller
Dans le fichier `main.py`, vous pouvez modifier la liste des mots-clés de détection à la ligne 15 :
```python
KEYWORDS_A4 = ['torcy', 'bussy', 'val d\'europe', 'chessy', 'marne-la-vallée']
```
Si vous souhaitez ajouter des gares de la branche, ajoutez-les simplement à cette liste en minuscules.

### Modifier la plage de silence de nuit
Dans le fichier `main.py`, vous pouvez modifier la plage d'envoi active dans la fonction `is_in_sending_window` :
```python
start_send = datetime.strptime("05:00", "%H:%M").time()
end_send = datetime.strptime("01:00", "%H:%M").time()
```
Remplacez `"05:00"` et `"01:00"` par les heures de votre choix.

### Modifier la fréquence de vérification
Par défaut, le robot vérifie les perturbations toutes les 5 minutes. Si vous souhaitez modifier cela (par exemple toutes les 10 minutes pour économiser vos quotas PRIM) :
1.  Modifiez le fichier `.github/workflows/rer-a-alerts.yml`.
2.  À la ligne `cron`, changez la valeur :
    *   Toutes les 10 minutes : `cron: '*/10 * * * *'`
    *   Toutes les 15 minutes : `cron: '*/15 * * * *'`
    *   Toutes les minutes : `cron: '*/1 * * * *'` (Attention aux quotas PRIM gratuits !)

# 🚇 RER A — Alertes Telegram (Branche A4 Marne-la-Vallée)

Bot d'alertes de trafic pour le RER A, hébergé gratuitement sur GitHub Actions.
Aucun serveur à gérer, aucun ordinateur à laisser allumé.

**Le bot ne prévient que pour les interruptions complètes de trafic.** Les retards,
ralentissements, trains supprimés et travaux programmés sont volontairement ignorés.

---

## 📍 Gares surveillées

Les 8 gares de la branche A4, dans l'ordre de la ligne :

| # | Gare |
|---|------|
| 1 | Noisy-le-Grand — Mont d'Est |
| 2 | Noisy-Champs |
| 3 | Noisiel |
| 4 | Lognes |
| 5 | Torcy |
| 6 | Bussy-Saint-Georges |
| 7 | Val d'Europe |
| 8 | Chessy — Marne-la-Vallée |

Les perturbations concernant uniquement les branches Cergy, Poissy, Boissy ou
Saint-Germain sont écartées. Les messages portant sur l'ensemble de la ligne A
sont conservés.

---

## 🔔 Ce qui déclenche une alerte

### ✅ Alerte envoyée

Le message doit contenir une expression d'arrêt total :

`trafic interrompu` · `trafic suspendu` · `trafic arrêté` · `interruption totale`
`interruption du trafic` · `circulation interrompue` · `aucun train`
`ne circulent plus` · `gare fermée`

### ✅ Message de reprise

Un message de rétablissement (`trafic rétabli`, `reprise du trafic`,
`retour à la normale`…) est envoyé **uniquement** si une interruption t'a été
notifiée dans les 6 heures précédentes. Pas d'interruption signalée = pas de
message de reprise.

### ❌ Ignoré

Retards, ralentissements, temps d'attente rallongés, trains supprimés,
bagages oubliés, et **travaux programmés** (annoncés des jours à l'avance).

---

## ⏱️ Fréquence : 1 scan toutes les 60 secondes

### Pourquoi pas un simple cron ?

Le cron de GitHub Actions **n'est pas fiable**. GitHub place les tâches planifiées
dans une file d'attente « best effort » et les étrangle fortement. Mesure réelle
sur ce dépôt avec un cron `*/5` (censé tourner toutes les 5 minutes) :

```
06:07 → 08:41 → 11:27 → 13:39 → 15:20 → 17:23 → 18:43
```

Soit **une exécution toutes les ~2 heures**. Passer le cron à `*/1` n'y change
strictement rien : GitHub ignore la demande.

### La solution retenue

Au lieu de demander 1 run par minute, le workflow lance **un seul run qui vit
5h40** et qui interroge l'API PRIM **toutes les 60 secondes** depuis l'intérieur
du job. Le cron `*/5` ne sert plus qu'à relancer la boucle quand elle se termine,
et le bloc `concurrency` garantit qu'un run en attente prend le relais
immédiatement.

**Conséquence : l'onglet Actions affiche en permanence un run « In progress ».
C'est normal, ce n'est pas un bug.**

### ⚠️ Le dépôt DOIT rester public

La boucle tourne en continu, soit ~43 200 minutes par mois.

| Visibilité | Minutes Actions | Verdict |
|---|---|---|
| **Public** | Illimitées et gratuites (runners standard) | ✅ |
| Privé | 2 000/mois offertes | ❌ épuisées en ~33 h |

Repasser le dépôt en privé casserait le bot au bout d'un jour et demi.

Les 3 clés d'accès restent dans **GitHub Secrets**, une zone chiffrée qui reste
invisible même sur un dépôt public. Seuls `main.py`, ce README et
`alerts_history.json` (des infos RATP déjà publiques) sont lisibles.

---

## 🛠️ Installation

### A) Créer le bot Telegram

1. Dans Telegram, cherche **@BotFather** (badge bleu de certification).
2. Envoie `/start` puis `/newbot`.
3. Donne un nom public (ex. `Alertes RER A`), puis un identifiant se terminant
   obligatoirement par `bot` (ex. `alertes_rer_a_rachid_bot`).
4. BotFather affiche un **Token HTTP API** du type
   `1234567890:ABCdefGhIJKlmNoPQRsTUVwxyZ`.

> ⚠️ Ce token permet de contrôler le bot. Ne le partage avec personne.

### B) Créer le groupe Telegram

1. Crée un **Nouveau groupe** (ex. `🚇 Alertes RER A`).
2. Ajoute ton bot au groupe via son identifiant.
3. **Promeus-le Administrateur** avec le droit d'envoyer des messages.
   Sans ça, il ne pourra rien publier.

### C) Récupérer le CHAT_ID

1. Envoie un message quelconque dans le groupe.
2. Ouvre dans ton navigateur :
   `https://api.telegram.org/bot<TOKEN>/getUpdates`
3. Cherche `"chat":{"id":` suivi d'un **nombre négatif**
   (ex. `-1001987654321`). C'est ton `TELEGRAM_CHAT_ID`.

> Page vide (`{"ok":true,"result":[]}`) ? Renvoie un message dans le groupe et
> recharge la page.

### D) Obtenir la clé PRIM

1. Crée un compte gratuit sur [prim.iledefrance-mobilites.fr](https://prim.iledefrance-mobilites.fr).
2. Confirme ton adresse e-mail, puis connecte-toi.
3. Catalogue des données → **Messages Info Trafic - Requête globale** → **S'abonner à l'API**.
4. Menu utilisateur → **Mes jetons** → génère une `apikey`.

### E) Configurer les Secrets GitHub

`Settings` → `Secrets and variables` → `Actions` → `New repository secret`.

Trois secrets à créer, aux noms **exacts** :

| Nom | Valeur |
|---|---|
| `PRIM_API_KEY` | La clé de l'étape D |
| `TELEGRAM_BOT_TOKEN` | Le token de l'étape A |
| `TELEGRAM_CHAT_ID` | Le nombre négatif de l'étape C |

### F) Lancer

`Actions` → `Suivi Trafic RER A - Alertes Telegram` → `Run workflow`.

---

## 📱 Fonctionnement au quotidien

- **Anti-doublon** — `alerts_history.json` mémorise les alertes déjà envoyées.
  Un incident de 4 heures ne génère qu'un seul message.
- **Mises à jour** — si la RATP modifie l'heure de fin ou ajoute des détails,
  le message est renvoyé avec l'en-tête `⚠️ MISE À JOUR`.
- **Mode nuit** — entre 1h01 et 4h59 (heure de Paris), les alertes sont
  enregistrées silencieusement mais pas envoyées.
- **Purge** — les alertes résolues depuis plus de 48 h sont supprimées de
  l'historique.

### Délai réel

| Événement | Heure |
|---|---|
| Le trafic s'arrête | 12:30 |
| La RATP publie sur PRIM | ~12:33 |
| Le bot détecte | 12:33–12:34 |
| **Telegram sonne** | **~12:34** |

Le délai de publication RATP (2 à 5 minutes) n'est pas contournable : l'appli
RATP officielle affiche la même information au même moment.

Toutes les 5h40, au changement de boucle, il existe une fenêtre de 30 à 60 s
sans surveillance, le temps que GitHub provisionne une nouvelle machine
(environ 0,3 % du temps).

---

## 🔧 Dépannage

| Problème | Cause probable | Solution |
|---|---|---|
| Workflow en échec (croix rouge) | Secret manquant ou mal nommé | Vérifie les 3 noms dans `Settings → Secrets → Actions`, sans espace |
| Run vert mais aucun message Telegram | Le bot n'est pas administrateur du groupe | Réglages du groupe → promeus le bot administrateur |
| `getUpdates` renvoie une page vide | Aucun message récent dans le groupe | Envoie un message de test, recharge la page |
| Le bot ne détecte plus rien | Dépôt repassé en privé, quota épuisé | Repasse-le en public |
| Aucune alerte depuis longtemps | Comportement normal | Les arrêts complets sont rares. Les retards ne déclenchent rien. |

---

## ⚙️ Personnalisation

Tout se modifie dans `main.py` via l'interface web de GitHub (icône crayon).

**Ajouter une gare** — liste `KEYWORDS_A4`, en minuscules :

```python
KEYWORDS_A4 = [
    'noisy-le-grand', 'noisy le grand', "mont d'est",
    'noisiel', 'lognes', 'torcy', 'bussy', "val d'europe", 'chessy',
]
```

Puis ajoute la ligne correspondante dans `detect_impacted_stations()` pour
qu'elle apparaisse dans le message.

**Recevoir aussi les travaux programmés** :

```python
IGNORE_PLANNED_WORKS = False
```

**Élargir les alertes** (ex. inclure les trains supprimés) — ajoute l'expression
dans `STOP_KEYWORDS` :

```python
STOP_KEYWORDS = [
    'trafic interrompu',
    'trains supprimes',   # ← nouveau
]
```

**Changer la plage de silence nocturne** — fonction `is_in_sending_window()` :

```python
start_send = datetime.strptime("05:00", "%H:%M").time()
end_send   = datetime.strptime("01:00", "%H:%M").time()
```

**Changer l'intervalle de scan** — dans `.github/workflows/rer-a-alerts.yml` :

```yaml
INTERVALLE=60    # secondes entre deux scans
DUREE=20400      # durée de la boucle (5h40, max 6h par job)
```

> Ne descends pas sous 30 secondes : l'API PRIM impose des quotas et te
> renverrait des erreurs 429.

---

## 📂 Structure

```
rer-a-alerts/
├── main.py                            # Récupération PRIM, filtrage, envoi Telegram
├── requirements.txt                   # requests, pytz
├── alerts_history.json                # Mémoire anti-doublon (auto-commit)
├── .gitignore
└── .github/workflows/rer-a-alerts.yml # Boucle de scan 60 s
```

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Système d'alertes de trafic RER A (Branche Marne-la-Vallée - A4)
Développé pour Rachid - Hébergé gratuitement sur GitHub Actions.
"""

import os
import sys
import json
import time
import argparse
import hashlib
from datetime import datetime
import pytz
import requests

# Configuration de l'encodage pour la console Windows afin d'éviter les crashs d'affichage des émojis
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass # Anciennes versions de Python sans reconfigure

# Fuseau horaire Paris obligatoire pour tous les calculs de dates et d'envoi
PARIS_TZ = pytz.timezone('Europe/Paris')

# Mots-clés définissant uniquement les 4 gares de Rachid
KEYWORDS_A4 = [
    'torcy', 'bussy', 'val d\'europe', 'chessy', 
    'marne-la-vallée', 'marne la vallee', 'marne-la-vallee', 'marne la vallée'
]

# Mots-clés des autres branches du RER A (utilisés pour exclure les perturbations locales)
KEYWORDS_EXCLUDE = ['boissy', 'cergy', 'poissy', 'saint-germain']


def escape_markdown(text):
    """
    Échappe les caractères de contrôle Markdown pour Telegram (mode Markdown V1).
    Caractères concernés : *, _, [, `
    """
    if not text:
        return ""
    for char in ['_', '*', '[', '`']:
        text = text.replace(char, f"\\{char}")
    return text


def extract_text(field):
    """
    Extrait la chaîne de caractères brute des structures de texte de PRIM.
    Gère les listes de dictionnaires multilingues, les dictionnaires uniques ou les chaînes simples.
    """
    if not field:
        return ""
    if isinstance(field, list):
        for item in field:
            if isinstance(item, dict) and "value" in item:
                return item["value"]
            elif isinstance(item, str):
                return item
    elif isinstance(field, dict):
        return field.get("value", "")
    elif isinstance(field, str):
        return field
    return str(field)


def parse_iso_datetime(dt_str):
    """
    Parse une chaîne de date ISO de PRIM en objet datetime conscient du fuseau UTC.
    """
    if not dt_str:
        return None
    try:
        # Nettoyage des formats Z de fin pour la compatibilité Python
        if dt_str.endswith('Z'):
            dt_str = dt_str[:-1] + '+00:00'
        return datetime.fromisoformat(dt_str)
    except Exception:
        return None


def format_datetime_paris(dt_str):
    """
    Prend une date brute de l'API PRIM et la formate en 'JJ/MM HH:MM' à l'heure de Paris.
    """
    if not dt_str:
        return "non communiquée"
    dt = parse_iso_datetime(dt_str)
    if not dt:
        return "non communiquée"
    # Convertir en Europe/Paris
    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt)
    dt_paris = dt.astimezone(PARIS_TZ)
    return dt_paris.strftime("%d/%m %H:%M")


def make_request_with_retry(url, method="GET", headers=None, params=None, json_data=None, retries=3, backoff_factor=2):
    """
    Effectue une requête HTTP avec mécanisme de retry automatique et backoff exponentiel.
    """
    last_exception = None
    for attempt in range(retries):
        try:
            if method == "GET":
                response = requests.get(url, headers=headers, params=params, timeout=15)
            else:
                response = requests.post(url, headers=headers, json=json_data, timeout=15)
            
            # Gestion des erreurs temporaires côté serveur
            if response.status_code in [429, 500, 502, 503, 504]:
                response.raise_for_status()
                
            return response
        except requests.exceptions.RequestException as e:
            last_exception = e
            if attempt < retries - 1:
                sleep_time = backoff_factor ** attempt
                print(f"⚠️ Erreur réseau ({e}). Tentative {attempt+1}/{retries} dans {sleep_time}s...")
                time.sleep(sleep_time)
                
    raise last_exception


def is_alert_relevant(summary, description):
    """
    Logique de filtrage des alertes du RER A.
    - Conserve si l'une des 4 gares de Rachid (Torcy, Bussy, Val d'Europe, Chessy) est mentionnée.
    - Conserve si c'est une perturbation globale sur toute la ligne A.
    - Exclut si c'est uniquement d'autres gares/branches (comme Noisy, Cergy, Boissy).
    """
    text = (summary + " " + description).lower()
    
    # 1. Si le texte contient l'une de nos 4 gares, c'est pertinent
    if any(kw in text for kw in KEYWORDS_A4):
        return True
        
    # 2. Si le texte mentionne d'autres branches ou d'autres gares de la ligne sans nos gares,
    # on filtre. Mais on garde les messages globaux sur l'ensemble de la ligne.
    text_clean = text.replace("malignea.fr", "").replace("ratp.fr", "")
    
    # Mots-clés pour perturbations globales sur toute la ligne
    global_keywords = [
        'ensemble de la ligne', 
        'toute la ligne', 
        'toutes les gares',
        'ligne a est interrompu',
        'ligne a est perturbe',
        'ligne a est ralenti'
    ]
    if any(kw in text_clean for kw in global_keywords):
        return True
        
    # Par défaut, exclure
    return False


def detect_impacted_stations(summary, description):
    """
    Détecte quelles gares surveillées par Rachid sont mentionnées dans le message.
    """
    text = (summary + " " + description).lower()
    stations = []
    
    if 'torcy' in text:
        stations.append("Torcy")
    if 'bussy' in text:
        stations.append("Bussy-Saint-Georges")
    if 'val d\'europe' in text:
        stations.append("Val d'Europe")
    if any(kw in text for kw in ['chessy', 'marne-la-vallée', 'marne la vallee', 'marne-la-vallee', 'marne la vallée', 'mlv']):
        stations.append("Chessy - Marne-la-Vallée")
        
    if stations:
        return stations
        
    # Si aucune gare principale n'est citée, chercher les autres gares de la branche A4
    if any(kw in text for kw in ['noisy', 'noisiel', 'lognes', 'neuilly-plaisance', 'bry-sur-marne', 'fontenay']):
        stations.append("Branche Marne-la-Vallée (Noisy / Lognes / Fontenay...)")
        return stations
        
    # Si la branche Marne-la-Vallée est mentionnée globalement
    if any(kw in text for kw in ['a4', 'marne-la-vallée', 'marne la vallee', 'marne-la-vallee', 'marne la vallée', 'mlv']):
        return ["Branche Marne-la-Vallée (toutes les gares)"]
        
    # Détection des autres branches ou gares spécifiques
    if any(kw in text for kw in ['cergy', 'poissy', 'maisons-laffitte', 'sartrouville', 'conflans', 'achères']):
        return ["Branche Cergy / Poissy"]
    if 'nation' in text:
        return ["Nation"]
    if 'étoile' in text or 'etoile' in text:
        return ["Charles de Gaulle - Étoile"]
    if 'auber' in text:
        return ["Auber"]
    if 'châtelet' in text or 'chatelet' in text:
        return ["Châtelet - Les Halles"]
    if 'gare de lyon' in text:
        return ["Gare de Lyon"]
        
    # Par défaut, c'est global à l'ensemble du RER A
    return ["Ensemble de la ligne RER A"]


def is_in_sending_window():
    """
    Renvoie True si l'heure actuelle à Paris se situe dans la plage d'envoi active (5h00 - 1h00).
    Renvoie False en période de silence nocturne (1h01 - 4h59).
    """
    now_paris = datetime.now(PARIS_TZ)
    current_time = now_paris.time()
    
    start_send = datetime.strptime("05:00", "%H:%M").time()
    end_send = datetime.strptime("01:00", "%H:%M").time()
    
    # Plage d'envoi traversant minuit (ex: 22h00 ou 00h30 sont valides, 02h00 ne l'est pas)
    if current_time >= start_send or current_time <= end_send:
        return True
    return False


def extract_disruptions_from_json(data):
    """
    Parcourt le JSON de l'API PRIM avec précaution pour en extraire les perturbations formatées.
    Prévient tout crash lié à une clé absente ou un format inattendu.
    """
    disruptions = []
    if not isinstance(data, dict):
        return disruptions
        
    siri = data.get("Siri")
    if not isinstance(siri, dict):
        return disruptions
        
    service_delivery = siri.get("ServiceDelivery")
    if not isinstance(service_delivery, dict):
        return disruptions
        
    general_msg_deliveries = service_delivery.get("GeneralMessageDelivery")
    if not isinstance(general_msg_deliveries, list):
        return disruptions
        
    for delivery in general_msg_deliveries:
        if not isinstance(delivery, dict):
            continue
        info_messages = delivery.get("InfoMessage")
        if not isinstance(info_messages, list):
            continue
            
        for msg in info_messages:
            if not isinstance(msg, dict):
                continue
                
            item_id = msg.get("ItemIdentifier", "")
            recorded_at = msg.get("RecordedAtTime", "")
            valid_until = msg.get("ValidUntilTime", "")
            
            content = msg.get("Content")
            if not isinstance(content, dict):
                continue
                
            pt_situation = content.get("PtSituationElement")
            if isinstance(pt_situation, dict):
                # Clés uniques de situation
                situation_num = pt_situation.get("SituationNumber", item_id)
                creation_time = pt_situation.get("CreationTime", recorded_at)
                
                # Période de validité
                validity_periods = pt_situation.get("ValidityPeriod", [])
                start_time = None
                end_time = None
                if isinstance(validity_periods, list) and len(validity_periods) > 0:
                    first_period = validity_periods[0]
                    if isinstance(first_period, dict):
                        start_time = first_period.get("StartTime")
                        end_time = first_period.get("EndTime")
                elif isinstance(validity_periods, dict):
                    start_time = validity_periods.get("StartTime")
                    end_time = validity_periods.get("EndTime")
                    
                if not end_time:
                    end_time = valid_until
                    
                summary = extract_text(pt_situation.get("Summary"))
                description = extract_text(pt_situation.get("Description"))
                
                if not summary and not description:
                    continue
                    
                disruptions.append({
                    "id": situation_num,
                    "summary": summary,
                    "description": description,
                    "start_time": start_time or creation_time,
                    "end_time": end_time,
                    "creation_time": creation_time
                })
            elif "Message" in content:
                messages = content.get("Message", [])
                short_msg = ""
                long_msg = ""
                for m in messages:
                    if not isinstance(m, dict):
                        continue
                    m_type = m.get("MessageType")
                    m_text_dict = m.get("MessageText")
                    m_text = ""
                    if isinstance(m_text_dict, dict):
                        m_text = m_text_dict.get("value", "")
                    elif isinstance(m_text_dict, str):
                        m_text = m_text_dict
                        
                    if m_type == "SHORT_MESSAGE":
                        short_msg = m_text
                    elif m_type == "TEXT_ONLY":
                        long_msg = m_text
                
                summary = short_msg or long_msg[:100]
                description = long_msg or short_msg
                
                if not summary and not description:
                    continue
                    
                # Extraire l'ID du message
                info_msg_id = msg.get("InfoMessageIdentifier")
                if isinstance(info_msg_id, dict):
                    situation_num = info_msg_id.get("value", item_id)
                else:
                    situation_num = str(info_msg_id) if info_msg_id else item_id
                    
                disruptions.append({
                    "id": situation_num,
                    "summary": summary,
                    "description": description,
                    "start_time": recorded_at,
                    "end_time": valid_until,
                    "creation_time": recorded_at
                })
            
    return disruptions


def calculate_disruption_hash(disruption):
    """
    Génère un hash unique basé sur le contenu textuel et de validité de la perturbation.
    Sert à identifier les mises à jour (ex: modification de texte ou d'horaires).
    """
    content_str = f"{disruption['summary']}|{disruption['description']}|{disruption['end_time']}"
    return hashlib.sha256(content_str.encode('utf-8')).hexdigest()


def format_alert_message(disruption, is_update=False):
    """
    Formatte le message Telegram en Markdown strict selon les préférences de Rachid.
    """
    stations = detect_impacted_stations(disruption['summary'], disruption['description'])
    stations_str = "\n".join([f"• {station}" for station in stations])
    
    start_str = format_datetime_paris(disruption['start_time'])
    end_str = format_datetime_paris(disruption['end_time'])
    
    title = disruption['summary'].strip()
    if not title:
        title = "Information Perturbation"
        
    info_text = disruption['description'].strip()
    if not info_text:
        info_text = title
    elif len(info_text) > 400:
        info_text = info_text[:397] + "..."
        
    # Échapper les champs contenant du texte dynamique pour éviter les crashs de parse_mode Markdown
    title_esc = escape_markdown(title)
    info_text_esc = escape_markdown(info_text)
    stations_str_esc = escape_markdown(stations_str)
    
    # En-tête du message
    if is_update:
        prefix = f"🔄 *Mise à jour : {title_esc}*"
    else:
        prefix = f"🚨 *RER A - {title_esc}*"
        
    message = (
        f"{prefix}\n\n"
        f"📍 *Gares concernées :*\n"
        f"{stations_str_esc}\n\n"
        f"⏰ *Début :* {start_str}\n"
        f"🕐 *Fin prévue :* {end_str}\n\n"
        f"ℹ️ {info_text_esc}\n\n"
        f"🔗 [ratp.fr/horaires/perturbations](https://www.ratp.fr/horaires/perturbations)"
    )
    return message


def load_history(filepath):
    """
    Charge le fichier alerts_history.json. Initialise un dictionnaire vide en cas d'erreur.
    """
    if not os.path.exists(filepath):
        return {}
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ Erreur chargement historique ({e}). Démarrage avec historique vierge.")
        return {}


def save_history(filepath, history):
    """
    Enregistre l'historique des alertes dans le fichier alerts_history.json.
    """
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
        print("💾 Historique alerts_history.json sauvegardé.")
    except Exception as e:
        print(f"❌ Erreur lors de la sauvegarde de l'historique : {e}")


def purge_old_alerts(history, retention_hours=48):
    """
    Supprime de l'historique les alertes résolues (non actives) depuis plus de 48h.
    """
    now = datetime.now(PARIS_TZ)
    keys_to_delete = []
    
    for key, info in history.items():
        # Une alerte en cours n'est pas purgée
        if info.get("active", True):
            continue
            
        last_seen_str = info.get("last_seen")
        if not last_seen_str:
            keys_to_delete.append(key)
            continue
            
        last_seen = parse_iso_datetime(last_seen_str)
        if not last_seen:
            keys_to_delete.append(key)
            continue
            
        if last_seen.tzinfo is None:
            last_seen = pytz.utc.localize(last_seen)
        last_seen_paris = last_seen.astimezone(PARIS_TZ)
        
        diff = now - last_seen_paris
        if diff.total_seconds() > retention_hours * 3600:
            keys_to_delete.append(key)
            
    for key in keys_to_delete:
        print(f"🧹 Purge de l'alerte obsolète historisée (>48h inactive) : {key}")
        del history[key]


def run_diagnostics(prim_key, tg_token, tg_chat_id):
    """
    Exécute le mode diagnostic (--test) pour s'assurer que les clés de configuration
    sont correctes, et affiche l'état actuel des flux de données.
    """
    print("\n=================== BOT DIAGNOSTIC MODE ===================")
    errors = 0
    
    # 1. Vérification des configurations environnementales
    print("\n[1/4] Validation des variables d'environnement...")
    for var_name, var_val in [("PRIM_API_KEY", prim_key), ("TELEGRAM_BOT_TOKEN", tg_token), ("TELEGRAM_CHAT_ID", tg_chat_id)]:
        if not var_val:
            print(f"❌ Erreur : La variable {var_name} est absente.")
            errors += 1
        else:
            masked = var_val[:6] + "..." if len(var_val) > 6 else "***"
            print(f"✅ Variable {var_name} configurée : {masked}")
            
    if errors > 0:
        print("❌ Diagnostic arrêté : des variables d'environnement cruciales manquent.")
        return False
        
    # 2. Test du bot Telegram (getMe)
    print("\n[2/4] Test de connexion avec Telegram (getMe)...")
    tg_me_url = f"https://api.telegram.org/bot{tg_token}/getMe"
    try:
        response = make_request_with_retry(tg_me_url, "GET", retries=2)
        if response.status_code == 200:
            bot_name = response.json().get("result", {}).get("first_name", "Inconnu")
            print(f"✅ Connexion Telegram établie ! Nom du bot : {bot_name}")
        else:
            print(f"❌ Échec getMe. HTTP {response.status_code} : {response.text}")
            errors += 1
    except Exception as e:
        print(f"❌ Exception lors du getMe Telegram : {e}")
        errors += 1
        
    # 3. Requête PRIM general-message
    print("\n[3/4] Interrogation de l'API PRIM (general-message)...")
    prim_url = "https://prim.iledefrance-mobilites.fr/marketplace/general-message"
    headers = {"apikey": prim_key}
    params = {"LineRef": "STIF:Line::C01742:"}
    disruptions = []
    try:
        response = make_request_with_retry(prim_url, "GET", headers=headers, params=params, retries=2)
        if response.status_code == 200:
            print("✅ Connexion à l'API PRIM réussie !")
            data = response.json()
            disruptions = extract_disruptions_from_json(data)
            print(f"🔎 Nombre de perturbations totales détectées : {len(disruptions)}")
        else:
            print(f"❌ Échec API PRIM. HTTP {response.status_code} : {response.text}")
            errors += 1
    except Exception as e:
        print(f"❌ Exception lors de la requête PRIM : {e}")
        errors += 1

    # 4. Envoi du dernier message RER A (réel ou simulé) au groupe Telegram
    print("\n[4/4] Préparation et envoi du dernier message RER A au groupe Telegram...")
    
    # Trouver une perturbation pertinente ou prendre la toute dernière perturbation du RER A
    target_disruption = None
    is_mock = False
    
    if disruptions:
        # Essayer d'abord d'en trouver une pertinente pour la branche A4
        relevant = [d for d in disruptions if is_alert_relevant(d['summary'], d['description'])]
        if relevant:
            target_disruption = relevant[0]
            print(f"📢 Utilisation d'une perturbation active de la branche A4 : {target_disruption['id']}")
        else:
            # Sinon prendre la première perturbation générale RER A
            target_disruption = disruptions[0]
            print(f"📢 Aucune alerte sur A4. Utilisation de la dernière alerte générale RER A : {target_disruption['id']}")
    else:
        # Si aucune perturbation du tout, simuler une perturbation test
        from datetime import timedelta
        now_paris = datetime.now(PARIS_TZ)
        target_disruption = {
            "id": "SIMULATED-TEST-A4",
            "summary": "Message de Test - Trafic ralenti",
            "description": "Ceci est un message de test automatique. Incident technique sur les installations de signalisation à Bussy-Saint-Georges. Le trafic est ralenti sur la branche Marne-la-Vallée.",
            "start_time": now_paris.isoformat(),
            "end_time": (now_paris + timedelta(hours=2)).isoformat(),
            "creation_time": now_paris.isoformat()
        }
        is_mock = True
        print("📢 Aucun trafic perturbé détecté sur le RER A. Génération d'une fausse perturbation pour tester le format d'envoi.")

    # Formater et envoyer l'alerte
    try:
        msg_text = format_alert_message(target_disruption, is_update=False)
        if is_mock:
            msg_text = "🧪 *[MESSAGE DE TEST]*\n" + msg_text
        else:
            msg_text = "📡 *[MESSAGE DE TEST RÉEL]*\n" + msg_text
            
        tg_send_url = f"https://api.telegram.org/bot{tg_token}/sendMessage"
        payload = {
            "chat_id": tg_chat_id,
            "text": msg_text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True
        }
        
        response = make_request_with_retry(tg_send_url, "POST", json_data=payload, retries=2)
        if response.status_code == 200:
            print("✅ Message RER A de test envoyé avec succès à Telegram !")
        else:
            print(f"❌ Échec de l'envoi du message RER A. HTTP {response.status_code} : {response.text}")
            errors += 1
    except Exception as e:
        print(f"❌ Exception lors de l'envoi du message RER A : {e}")
        errors += 1
        
    print("\n=======================================================")
    if errors == 0:
        print("🎉 DIAGNOSTIC REUSSI : Le bot RER A est 100% opérationnel !")
        return True
    else:
        print(f"❌ DIAGNOSTIC ECHOUE : {errors} erreur(s) détectée(s).")
        return False


def main():
    parser = argparse.ArgumentParser(description="Bot RER A - Alertes de perturbation Telegram")
    parser.add_argument('--test', action='store_true', help="Déclenche le mode diagnostic de validation")
    args = parser.parse_args()
    
    # Chargement des identifiants et clés d'accès
    prim_key = os.environ.get("PRIM_API_KEY")
    tg_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    tg_chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    if args.test:
        success = run_diagnostics(prim_key, tg_token, tg_chat_id)
        sys.exit(0 if success else 1)
        
    # Vérification des credentials en mode normal
    if not all([prim_key, tg_token, tg_chat_id]):
        print("❌ Configuration manquante. Renseignez PRIM_API_KEY, TELEGRAM_BOT_TOKEN et TELEGRAM_CHAT_ID.")
        sys.exit(1)
        
    history_file = "alerts_history.json"
    history = load_history(history_file)
    
    # 1. Requête API PRIM
    prim_url = "https://prim.iledefrance-mobilites.fr/marketplace/general-message"
    headers = {"apikey": prim_key}
    params = {"LineRef": "STIF:Line::C01742:"}
    
    try:
        print("📡 Récupération des informations sur l'API PRIM...")
        response = make_request_with_retry(prim_url, "GET", headers=headers, params=params)
        if response.status_code != 200:
            print(f"⚠️ Erreur HTTP PRIM ({response.status_code}). Sortie propre pour éviter les fausses alertes.")
            sys.exit(0)
        data = response.json()
    except Exception as e:
        print(f"⚠️ Erreur connexion API PRIM ({e}). Sortie propre pour préserver la stabilité.")
        sys.exit(0)
        
    # 2. Extraction et filtrage
    disruptions = extract_disruptions_from_json(data)
    relevant_disruptions = [d for d in disruptions if is_alert_relevant(d['summary'], d['description'])]
    
    print(f"📊 {len(disruptions)} alerte(s) reçue(s) | {len(relevant_disruptions)} alerte(s) conservée(s) après filtrage.")
    
    # Désactiver temporairement toutes les alertes de l'historique
    for key in history.keys():
        history[key]["active"] = False
        
    # 3. Détermination de la plage horaire d'envoi
    sending_allowed = is_in_sending_window()
    if not sending_allowed:
        print("🤫 Mode nuit actif (1h00 - 5h00 Europe/Paris) : pas d'envoi de messages.")
        
    now_str = datetime.now(PARIS_TZ).isoformat()
    
    # 4. Traitement des alertes
    for d in relevant_disruptions:
        d_id = d['id']
        d_hash = calculate_disruption_hash(d)
        
        is_new = d_id not in history
        is_update = False
        
        if not is_new:
            old_hash = history[d_id].get("hash")
            if old_hash != d_hash:
                is_update = True
                
        # Enregistrer l'état courant de l'alerte
        history[d_id] = {
            "last_seen": now_str,
            "hash": d_hash,
            "active": True
        }
        
        # Envoi Telegram
        if is_new or is_update:
            msg_text = format_alert_message(d, is_update=is_update)
            
            if sending_allowed:
                try:
                    print(f"📤 Envoi Telegram pour {d_id} (Nouveau={is_new}, MAJ={is_update})...")
                    tg_send_url = f"https://api.telegram.org/bot{tg_token}/sendMessage"
                    payload = {
                        "chat_id": tg_chat_id,
                        "text": msg_text,
                        "parse_mode": "Markdown",
                        "disable_web_page_preview": True
                    }
                    res = make_request_with_retry(tg_send_url, "POST", json_data=payload)
                    if res.status_code != 200:
                        print(f"⚠️ Échec Telegram (HTTP {res.status_code}). L'alerte sera réévaluée au prochain run.")
                        # On restaure l'état précédent du hash/de l'existence pour forcer la réévaluation
                        if is_new:
                            del history[d_id]
                        else:
                            history[d_id]["hash"] = old_hash
                except Exception as e:
                    print(f"⚠️ Erreur envoi Telegram ({e}). Restauration pour prochain essai.")
                    if is_new:
                        del history[d_id]
                    else:
                        history[d_id]["hash"] = old_hash
            else:
                action = "Nouvelle alerte" if is_new else "Mise à jour"
                print(f"🤫 Enregistrement silencieux ({action}) de l'alerte {d_id} pendant la nuit.")
                
    # 5. Nettoyage des alertes inactives depuis plus de 48 heures
    purge_old_alerts(history)
    
    # 6. Sauvegarde de l'historique mis à jour
    save_history(history_file, history)
    print("✅ Fin d'exécution propre.")


if __name__ == "__main__":
    main()

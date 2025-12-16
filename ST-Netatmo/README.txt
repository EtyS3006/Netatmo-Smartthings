SmartThings Netatmo Bridge
Ce projet permet de contrôler les vannes et thermostats Netatmo dans SmartThings avec un taux de rafraîchissement rapide (5 minutes) et une connexion locale fiable, remplaçant l'intégration officielle (lente et instable).

🎯 Objectifs
Rapidité : Mise à jour toutes les 5 min (vs 6h pour l'officiel).

Fiabilité : Architecture locale (LAN) avec surveillance automatique (Watchdog).

Fonctionnalités : Support complet des modes (Planning, Absent, Hors-gel) et changement de consigne.

Monitoring : Indicateurs visuels de l'état de la connexion (Hub ↔ Pi ↔ Netatmo).

🛠️ Pré-requis Matériels
Un Hub SmartThings.

Un serveur toujours allumé (Raspberry Pi, NAS Synology avec Docker, ou vieux PC Linux/Windows).

Python 3.x installé sur ce serveur.

📝 Étape 1 : Configuration Netatmo (API)
Nous devons créer une "fausse" application pour obtenir les droits d'accès.

Connectez-vous sur dev.netatmo.com avec votre compte Netatmo habituel.

Allez dans "My Apps" > "Create an App".

Name : SmartThings Bridge (ou autre).

Description : Integration Perso.

Redirect URI : http://localhost (Important, même si on ne l'utilise pas).

Validez.

Dans les paramètres de l'application créée, copiez précieusement :

Client ID

Client Secret

Génération du Token (Méthode facile) :

Dans la section "Token Generator" (en bas de page de votre app).

Sélectionnez les scopes : read_thermostat, write_thermostat.

Obtenir le Refresh Token (étape clé 🔑)

Netatmo utilise OAuth2.
Le refresh token permet à ton serveur de fonctionner sans interaction utilisateur.

🔁 Obtenir un authorization code

Dans ton navigateur, ouvre cette URL (en adaptant le client_id) :

https://api.netatmo.com/oauth2/authorize?client_id={CLIENT_ID}&redirect_uri=http://localhost&scope=read_thermostat write_thermostat&state=secure_state


👉 Tu es redirigé vers http://localhost/?code=XXXXX

📋 Copie la valeur code=

🔁 Échanger le code contre les tokens

Exécute cette commande (ou via Postman / curl) :

curl -X POST https://api.netatmo.com/oauth2/token \
  -d grant_type=authorization_code \
  -d client_id=CLIENT_ID \
  -d client_secret=CLIENT_SECRET \
  -d code=AUTHORIZATION_CODE \
  -d redirect_uri=http://localhost

✅ Réponse attendue :
{
  "access_token": "xxx",
  "refresh_token": "yyy",
  "expires_in": 10800
}


👉 Garde précieusement le refresh_token



🖥️ Étape 2 : Installation du Serveur (Raspberry Pi)
Ce script Python sert de passerelle. Il doit tourner en permanence.

1. Installation des fichiers
Créez un dossier (ex: netatmo_bridge) et copiez-y le contenu du dossier /server de ce dépôt.

2. Environnement Virtuel (Recommandé)

cd netatmo_bridge
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
3. Configuration des clés
Renommez le fichier .env.example en .env :

mv .env.example .env
nano .env
Remplissez avec vos informations récupérées à l'étape 1 :

CLIENT_ID=votre_client_id_ici
CLIENT_SECRET=votre_client_secret_ici
REFRESH_TOKEN=votre_refresh_token_ici

Dans app.py : 
Ligne POLL_INTERVAL permet de définir en secondes le délai de rafraichissement (demande des infos auprès de Netatmo) 
Ligne STALE_THRESHOLD permet de définir le délai avant de déclarer une erreur de connexion aux serveurs Netatmo 

4. Test manuel
Lancez le serveur pour vérifier :

python3 app.py
Si vous voyez Running on http://0.0.0.0:5000 et ✅ Auto-update complete, c'est bon ! (Arrêtez avec Ctrl+C).

5. Démarrage Automatique (Service Systemd)
Pour que le pont se lance tout seul si le Raspberry redémarre :

Éditez le fichier netatmo.service fourni pour adapter le chemin (si besoin).

Copiez-le et activez-le :

sudo cp netatmo.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable netatmo.service
sudo systemctl start netatmo.service


📱 Étape 3 : Installation du Driver SmartThings
C'est le logiciel qui s'installe sur votre Hub SmartThings. Pour l'installer, nous devons créer un "Canal de distribution" privé.

1. Configuration de l'IP
Ouvrez le fichier driver/src/init.lua. Modifiez la ligne suivante avec l'adresse IP de votre Raspberry Pi :

Lua

local PI_IP = "192.168.1.XX" -- <--- Mettez votre IP locale ici
2. Installation via CLI (Ligne de commande)
Ouvrez un terminal dans le dossier driver/ (là où se trouve le fichier config.yaml).

A. Créer votre Canal Personnel
Si vous n'avez jamais développé de driver, créez un canal :

Bash

smartthings edge:channels:create
Donnez-lui un nom (ex: Mon Canal Netatmo).

Notez l'ID du canal qui s'affiche (ex: 5985...).

B. Inscrire votre Hub au Canal (Enroll)
Il faut autoriser votre Hub à télécharger depuis ce canal :

Bash

smartthings edge:channels:enroll
Sélectionnez votre Hub dans la liste.

Sélectionnez le canal que vous venez de créer.

C. Empaqueter le Driver (Package)
Cela compile le code et prépare le driver.

Bash

smartthings edge:drivers:package .
Notez l'ID du Driver qui s'affiche (ex: aafd...).

D. Assigner le Driver au Canal
On met le paquet dans le camion de livraison :

Bash

smartthings edge:channels:assign
Sélectionnez le Driver (Netatmo Bridge-v2).

Sélectionnez votre Canal.

E. Installer le Driver sur le Hub
On livre le paquet :

Bash

smartthings edge:drivers:install
Sélectionnez le Driver.

Sélectionnez le Hub.

3. Découverte
Ouvrez l'appli SmartThings sur votre téléphone.

Allez dans l'onglet Appareils > + (Ajouter) > Scanner.

Le Netatmo Bridge va apparaître.

Quittez le scan, et revenez sur Scanner pour rajouter vos têtes thermostatiques.

Quelques secondes plus tard, vos pièces (Thermostats) apparaîtront automatiquement.

🩺 Dépannage & Indicateurs
Le module "Netatmo Bridge" dispose de deux voyants de diagnostic :

Liaison Hub ↔ Raspberry :

✅ Fermé : Le Hub communique bien avec le script Python.

❌ Ouvert (Alerte) : Le Hub ne trouve pas le Raspberry (Vérifiez l'IP ou si le script tourne).

Liaison Pi ↔ Netatmo :

✅ Fermé : Le script arrive à parler aux serveurs Netatmo.

❌ Ouvert (Alerte) : Erreur API ou coupure Internet sur le Raspberry.

Le bouton Retour Planning permet de remettre toutes les pièces selon le planning prédéfini (en retirant les boosts manuels) 
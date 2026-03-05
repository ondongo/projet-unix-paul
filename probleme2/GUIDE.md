# Guide – Déploiement d’une application Flask avec reverse proxy et protection contre le bruteforce

## 1. Objectif

Ce guide est une procédure à suivre pour obtenir une application web en Python avec :

- authentification via `/login`
- accès protégé via `/private`
- reverse proxy (Caddy)
- serveur d’application (Gunicorn)
- bannissement IP après trop d’échecs de connexion (Fail2ban)

Environnement cible : machine Debian, avec un utilisateur non root disposant de sudo.

---

## 2. Installation des dépendances système

**Objectif :** avoir Python 3, Fail2ban, Caddy et leurs services activés.

Mise à jour des paquets :

```bash
sudo apt update
```

Installation des paquets nécessaires (Python, fail2ban, caddy) :

```bash
sudo apt install -y python3 python3-venv python3-pip fail2ban caddy
```

Activation des services :

```bash
sudo systemctl enable --now fail2ban
sudo systemctl enable --now caddy
```


### Cas d’erreur possible : Caddy ne démarre pas

Lors du démarrage de Caddy (avec `sudo systemctl enable --now caddy` ou `sudo systemctl restart caddy`), il est possible d’obtenir l’erreur suivante :

```text
Job for caddy.service failed because the control process exited with error code.
See "systemctl status caddy.service" and "journalctl -xeu caddy.service" for details.
```

**Diagnostic**

Afficher la cause exacte avec `systemctl status` et `journalctl` :

```bash
sudo systemctl status caddy.service
sudo journalctl -xeu caddy.service
```

Dans la majorité des cas, l’erreur indique que le port 80 est déjà utilisé :

```text
listen tcp :80: bind: address already in use
```

Cela signifie qu’un autre serveur web (souvent `nginx` ou `apache2`) écoute déjà sur ce port.

**Solution**

Arrêter et désactiver les services qui utilisent le port 80 (`nginx`, `apache2`, etc.) :

```bash
sudo systemctl stop nginx
sudo systemctl disable nginx

sudo systemctl stop apache2
sudo systemctl disable apache2
```

Puis redémarrer Caddy :

```bash
sudo systemctl restart caddy
```

**Vérification**

Vérifier que Caddy fonctionne correctement :

```bash
sudo systemctl status caddy
```

---


Vérification du statut des services (une fois Caddy et Fail2ban OK) :

```bash
sudo systemctl status caddy
sudo systemctl status fail2ban
```

---

## 3. Création de l’application Flask

### 3.1 Environnement Python

Création du dossier de travail :

```bash
mkdir -p ~/gnulinux-probleme2/app
cd ~/gnulinux-probleme2/app
```

Création et activation de l’environnement virtuel :

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Installation des dépendances :

```bash
pip install flask gunicorn
pip freeze > requirements.txt
```

**Note :** Le fichier `requirements.txt` contient la liste des paquets installés dans le venv (Flask, Gunicorn et leurs dépendances). Il sert à réinstaller exactement les mêmes versions ailleurs (`pip install -r requirements.txt`). Un exemple de contenu minimal est fourni dans `requirements-example.txt`.

Les paquets sont installés dans `.venv` et non dans le Python système : on évite les conflits de versions et on ne modifie pas les paquets déjà présents sur la machine.

### 3.2 Implémentation de l’application

Créer le fichier `app.py` dans le dossier de l’app (ex. `~/gnulinux-probleme2/app`) :

```bash
touch app.py
```

Ouvrir le fichier avec un éditeur (`nano app.py`, `vim app.py`, etc.) et y recopier tout le contenu d’un des fichiers exemples fournis dans le dépôt : [app-example.py](probleme2/app/app-example.py) (version commentée) ou [app-example-no-coments.py](probleme2/app/app-example-no-coments.py) (même code sans commentaires).

L’application contient :

- des identifiants en dur ;
- une route `/private` protégée par un cookie de session ;
- l’écriture de chaque échec de connexion dans `/var/log/authapp.log` sur une ligne au format attendu par Fail2ban (voir section 7.2), par exemple : `FAILED_LOGIN ip=<IP> user=<username> time=<timestamp>`.

---

## 4. Configuration du journal d’authentification

**Objectif :** créer le fichier de log des échecs de connexion et en fixer les droits pour l’app et Fail2ban.

Création du fichier de log :

```bash
sudo touch /var/log/authapp.log
```

Droits pour que l’app puisse écrire et que Fail2ban puisse lire :

```bash
sudo chown www-data:adm /var/log/authapp.log
sudo chmod 640 /var/log/authapp.log
```

Fail2ban utilisera ce fichier pour détecter les tentatives de bruteforce.

**Note :** la fonction `log_failed_login` de l’exemple écrit déjà dans ce format (voir [app-example.py](probleme2/app/app-example.py)).

---

## 5. Déploiement avec Gunicorn

Test rapide à la main :

```bash
gunicorn -b 127.0.0.1:8000 app:app
```

Dans un autre terminal, test de la route login :

```bash
curl -i http://127.0.0.1:8000/login
```

Un statut `200` indique que l’app répond correctement.

### 5.1 Service systemd

Créer le fichier `/etc/systemd/system/authapp.service` et y coller le contenu suivant. Pour l’éditer avec nano (ou vim, etc.) :

```bash
sudo nano /etc/systemd/system/authapp.service
```

**Important :** dans le contenu ci-dessous, les chemins utilisent `paul` comme exemple. **Adapte en remplaçant `paul` par ton propre nom d’utilisateur** (celui sous lequel tu es connecté, ex. `prince` → `/home/prince/gnulinux-probleme2/app`). Sinon le service ne trouvera pas Gunicorn et échouera au démarrage.

Contenu du fichier :

```ini
[Unit]
Description=Application Flask
After=network.target

[Service]
User=www-data
WorkingDirectory=/home/paul/gnulinux-probleme2/app
Environment="PATH=/home/paul/gnulinux-probleme2/app/.venv/bin"
ExecStart=/home/paul/gnulinux-probleme2/app/.venv/bin/gunicorn \
  --workers 2 \
  --bind 127.0.0.1:8000 \
  app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

**Note :** ce service fait tourner l’application Flask (via Gunicorn) en arrière-plan : il démarre après le réseau, écoute en local sur le port 8000, se relance tout seul en cas de plantage, et peut être activé au démarrage de la machine.


Activer et démarrer le service authapp :

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now authapp
```

### Cas d’erreur possible : authapp ne démarre pas ou renvoie 500

**Diagnostic :** voir les logs du service :

```bash
sudo journalctl -u authapp -n 30 --no-pager
```

**1. Permission denied (CHDIR)** — « Changing to the requested working directory failed: Permission denied »

Le service tourne sous `www-data` et ne peut pas entrer dans ton répertoire personnel. Donner les droits de traversée et d’accès au dossier de l’app (remplacer `prince` par ton utilisateur si besoin) :

```bash
sudo chmod 711 /home/prince
sudo chmod 711 /home/prince/gnulinux-probleme2
sudo chmod 755 /home/prince/gnulinux-probleme2/app
sudo systemctl restart authapp
```

**2. 500 Internal Server Error** sur POST `/login`

L’app ne peut pas écrire dans le fichier de log. Corriger propriétaire et droits :

```bash
sudo chown www-data:adm /var/log/authapp.log
sudo chmod 640 /var/log/authapp.log
sudo systemctl restart authapp
```

**3. Port 8000 déjà utilisé** — « Address already in use » / « Connection in use »

Un autre processus (ou un ancien Gunicorn) occupe le port. Arrêter le service, vérifier qui utilise le port, relancer :

```bash
sudo systemctl stop authapp
sudo ss -tlnp | grep 8000
```

Si une ligne s’affiche, noter le(s) PID et tuer : `sudo kill <PID>`. Puis :

```bash
sudo systemctl start authapp
sudo systemctl status authapp
```

---

## 6. Configuration du reverse proxy Caddy

Caddy reçoit les requêtes HTTP sur le port 80 et les transmet à Gunicorn (port 8000). Il faut éditer sa configuration.

Ouvrir le Caddyfile :

```bash
sudo nano /etc/caddy/Caddyfile
```

Remplacer le contenu (ou la ligne `reverse_proxy`) par :

```text
:80 {
    reverse_proxy 127.0.0.1:8000
}
```

Enregistrer et quitter. Puis recharger Caddy pour appliquer la config :

```bash
sudo systemctl reload caddy
```

Vérifier que le site répond derrière Caddy. Depuis la machine où Caddy tourne :

```bash
prince@dbmysql:~$ curl http://localhost/login
```

Réponse attendue : une page HTML contenant un formulaire de connexion (titre « Login », champs username/password, bouton Connexion). Un statut HTTP 200 confirme que le reverse proxy transmet bien les requêtes à Gunicorn.

---

## 7. Mise en place de Fail2ban

Fail2ban surveille le fichier de log des échecs de connexion. Au-delà de **5 échecs en 120 secondes** pour une même IP, celle-ci est bannie pendant 600 secondes (10 min).

### 7.1 Filtre (reconnaissance des lignes de log)

Créer le fichier de filtre et y coller le contenu suivant :

```bash
sudo nano /etc/fail2ban/filter.d/authapp.conf
```

Contenu :

```ini
[Definition]
failregex = ^FAILED_LOGIN ip=(?P<host>\S+) user=.* time=.*$
ignoreregex =
```

Le filtre repère les lignes qui commencent par `FAILED_LOGIN ip=` ; `(?P<host>\S+)` capture l’IP (IPv4, IPv6 comme `::1`, etc.). L’app exemple écrit déjà dans ce format.

### 7.2 Jail (règle : quel log, combien d’échecs, durée du bannissement)

Créer le fichier de jail :

```bash
sudo nano /etc/fail2ban/jail.d/authapp.local
```

Contenu :

```ini
[authapp]
enabled = true
filter = authapp
logpath = /var/log/authapp.log
maxretry = 5
findtime = 120
bantime = 600
```

Enregistrer, quitter. Puis redémarrer Fail2ban pour charger la nouvelle jail :

```bash
sudo systemctl restart fail2ban
```

---

## 8. Test du mécanisme de protection

À faire depuis un terminal sur la machine où l’app et Caddy tournent (ou depuis une machine qui accède à l’URL du site).

**Étape 1 –** Simuler 6 tentatives de login échouées (coller la commande) :

```bash
for i in $(seq 1 6); do
  curl -X POST -d "username=paul&password=wrong" http://localhost/login
done
```

**Résultat attendu :** six fois `Unauthorized` (une par requête). Si vous voyez « 500 Internal Server Error » à la place, les erreurs apparaissent après ce test — voir le [cas d’erreur authapp (section 5.1)](#cas-derreur-possible--authapp-ne-démarre-pas-ou-renvoie-500) et le [cas d’erreur Fail2ban (section 8, ci-dessous)](#cas-derreur-possible--fail2ban-affiche-0-failed).

Pour afficher les échecs enregistrés dans le log :

```bash
sudo cat /var/log/authapp.log
```

Vous devriez voir six lignes du type `FAILED_LOGIN ip=... user=paul time=...`.

**Étape 2 –** Vérifier que l’IP est bannie :

```bash
sudo fail2ban-client status authapp
sudo cat /var/log/authapp.log
```

Dans la sortie, consulter la ligne « Banned IP list » : l’IP utilisée pour les requêtes (souvent `127.0.0.1` ou `::1`) doit y figurer. Si c’est le cas, la protection bruteforce fonctionne.

**Cas d’erreur possible : Fail2ban affiche 0 failed**

Si `sudo fail2ban-client status authapp` affiche « Currently failed: 0 » alors que vous venez de faire les 6 requêtes, vérifier le log (lecture réservée à root) :

```bash
sudo cat /var/log/authapp.log
```

Exemple de sortie (avec `curl localhost`, l’IP est souvent `::1` en IPv6) :

```text
FAILED_LOGIN ip=::1 user=paul time=2026-03-05T21:45:45Z
FAILED_LOGIN ip=::1 user=paul time=2026-03-05T21:45:45Z
...
```

Le motif standard `<HOST>` de Fail2ban ne reconnaît que les IPv4, donc les lignes avec `::1` ne sont pas comptées. **Solution :** le filtre doit utiliser un groupe nommé pour l’IP, par exemple `(?P<host>\S+)`, comme indiqué en section 7.1. Vérifier que le contenu de `/etc/fail2ban/filter.d/authapp.conf` correspond bien à celui de la section 7.1, puis exécuter `sudo systemctl restart fail2ban` et refaire le test.

**Pour débannir une IP** (ex. après un test) : `sudo fail2ban-client set authapp unbanip <IP>` (remplacer `<IP>` par l’adresse).


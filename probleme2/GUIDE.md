# Guide – Déploiement d’une application Flask avec reverse proxy et protection contre le bruteforce

## 1. Objectif

Ce guide décrit la mise en place d’une application web en Python avec :

- authentification via `/login`
- accès protégé via `/private`
- reverse proxy (Caddy)
- serveur d’application (Gunicorn)
- bannissement IP après trop d’échecs de connexion (Fail2ban)

L’environnement cible est une machine Debian disposant de sudo.

---

## 2. Installation des dépendances système

Mise à jour des paquets :

```bash
sudo apt update
```

Installation des paquets nécessaires :

```bash
sudo apt install -y python3 python3-venv python3-pip fail2ban caddy
```

Activation des services :

```bash
sudo systemctl enable --now fail2ban
sudo systemctl enable --now caddy
```

Gunicorn sera utilisé comme serveur WSGI pour exécuter l’application Flask en production.
Caddy servira de reverse proxy afin de ne pas exposer directement Gunicorn.
Fail2ban permettra de détecter et bloquer les tentatives répétées d’authentification échouée.

Vérification du statut des services :

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

Les paquets sont installés dans `.venv` et non dans le Python système : on évite les conflits de versions entre projets et on ne modifie pas les paquets déjà présents sur la machine.

### 3.2 Implémentation de l’application

Créer un fichier `app.py`. L’application doit :

- utiliser des identifiants en dur dans le code (le sujet ne demande pas de base de données)
- protéger `/private` avec un cookie de session
- écrire les échecs de connexion dans `/var/log/authapp.log` pour Fail2ban

---

## 4. Configuration du journal d’authentification

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

Un statut 200 indique que l’app répond correctement.

### 5.1 Service systemd

Créer le fichier `/etc/systemd/system/authapp.service` :

```ini
[Unit]
Description=Application Flask sécurisée
After=network.target

[Service]
User=www-data
WorkingDirectory=/home/user/gnulinux-probleme2/app
Environment="PATH=/home/user/gnulinux-probleme2/app/.venv/bin"
ExecStart=/home/user/gnulinux-probleme2/app/.venv/bin/gunicorn \
  --workers 2 \
  --bind 127.0.0.1:8000 \
  app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

Puis activer et démarrer le service :

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now authapp
```

*(Adapter les chemins si l’utilisateur n’est pas `user`.)*

---

## 6. Configuration du reverse proxy Caddy

Éditer `/etc/caddy/Caddyfile` et configurer le site :

```
:80 {
    reverse_proxy 127.0.0.1:8000
}
```

Recharger Caddy :

```bash
sudo systemctl reload caddy
```

Test :

```bash
curl http://localhost/login

Le reverse proxy permet d’isoler l’application interne et de centraliser les accès HTTP (Le trafic HTTP passe par Caddy, qui relaie vers Gunicorn.).


---

## 7. Mise en place de Fail2ban

### 7.1 Règle de détection

On considère comme suspect : **5 tentatives de connexion échouées en moins de 120 secondes**. L’IP sera bannie (ex. 600 s).

### 7.2 Filtre

Créer `/etc/fail2ban/filter.d/authapp.conf` :

```ini
[Definition]
failregex = ^FAILED_LOGIN ip=<HOST> user=.* time=.*$
ignoreregex =
```

### 7.3 Jail

Créer `/etc/fail2ban/jail.d/authapp.local` :

```ini
[authapp]
enabled = true
filter = authapp
logpath = /var/log/authapp.log
maxretry = 5
findtime = 120
bantime = 600
```

Redémarrer Fail2ban :

```bash
sudo systemctl restart fail2ban
```

---

## 8. Test du mécanisme de protection

Simuler 6 tentatives échouées :

```bash
for i in $(seq 1 6); do
  curl -X POST -d "username=alice&password=wrong" http://localhost/login
done
```

Vérifier que l’IP est bannie :

```bash
sudo fail2ban-client status authapp
```

L’IP doit apparaître dans la liste des bannis. Cela confirme que la jail et la protection bruteforce fonctionnent.

---

## 9. Validation finale

Le déploiement est correct si :

- `/login` est accessible
- `/private` n’est accessible qu’après authentification
- Gunicorn tourne sous systemd
- Caddy fait bien le reverse proxy vers Gunicorn
- Fail2ban bannit les IP après 5 échecs dans la fenêtre définie

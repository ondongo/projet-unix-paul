# Évaluation GNU/Linux Avancé – Problème 2

## Problème choisi

Problème 2 – Configuration d’une application web avec reverse proxy, gestionnaire de processus et détection d’activité malveillante.

---

## Membre(s) du groupe

- Prince De Gloire ONDONGO

*(Travail réalisé individuellement)*

---

## Remarques / Commentaires / Motivations

J’ai choisi le problème 2 car il permet de travailler des notions concrètes d’administration système : gestion de processus, reverse proxy et sécurisation d’un service exposé.

J’ai l’habitude de mettre en place ce type d’architecture avec PHP. J’ai donc volontairement choisi Python afin de mieux comprendre comment configurer un reverse proxy et un serveur applicatif (Gunicorn) dans un environnement différent.

Flask m’a permis d’aller rapidement à l’essentiel, car je le maîtrise déjà. Cela m’a laissé plus de temps pour me concentrer sur la configuration système (systemd, Caddy, Fail2ban) et sur la compréhension du fonctionnement global de l’architecture.

---

## Références

- Documentation Flask : https://flask.palletsprojects.com/
- Documentation Gunicorn : https://gunicorn.org/
- Documentation Caddy : https://caddyserver.com/docs/
- Documentation Fail2ban : https://www.fail2ban.org/wiki/
# Présentation orale : partie API et base de données (Marouan)

Copie des quatre slides ajoutés au Canva (pages 14 à 17) avec leurs notes orales, pour les garder avec le code. Les chiffres viennent du code : 37 tests, bornes des mesures dans `app/main.py`, schéma dans `app/database.py`.

## Slide 14 : Stack technique

Backend : Python 3, FastAPI (routes REST, WebSockets, documentation `/docs`), Pydantic (validation), Uvicorn (serveur ASGI).
Base de données et sécurité : SQLite (7 tables, un seul fichier), sqlite3 (requêtes paramétrées), hashlib (PBKDF2-SHA256), unittest avec TestClient (37 tests sur base temporaire).
Message du bandeau : 2 dépendances déclarées seulement (FastAPI, Uvicorn), le reste vient de Python.

Notes orales :

Avant d'entrer dans le détail, voici les outils que j'ai utilisés pour le serveur et la base de données.

Côté serveur, tout est écrit en Python. Pour construire l'API, on utilise FastAPI : c'est un framework web qui permet de définir facilement les routes, de gérer les WebSockets pour le temps réel, et qui génère automatiquement une page de documentation à l'adresse /docs, pratique pour tester. Pydantic vérifie les données reçues : par exemple il refuse une tension de 500 ou un formulaire mal rempli, avant même d'écrire dans la base. Et Uvicorn est le serveur qui fait tourner l'application, de façon asynchrone, ce qui permet de garder plusieurs connexions WebSocket ouvertes en même temps.

Côté base de données, SQLite : une base de sept tables dans un seul fichier, sans rien installer. On l'utilise avec le module sqlite3 déjà inclus dans Python, avec des requêtes paramétrées pour éviter l'injection SQL. La sécurité des mots de passe vient de hashlib, aussi inclus dans Python : on y utilise PBKDF2 avec SHA-256. Enfin, pour tester, on utilise unittest avec le TestClient de FastAPI : 37 tests automatiques, lancés sur une base temporaire pour ne pas toucher aux vraies données.

Le point important : on a volontairement très peu de dépendances. Seulement deux sont déclarées, FastAPI et Uvicorn. Tout le reste vient de Python lui-même. Cela rend l'installation simple et le code facile à expliquer. Je vais maintenant détailler les trois parties : l'API, la validation et la sécurité, puis la base de données.

## Slide 15 : L'API REST du serveur

Trois familles de routes (comptes et sessions, constantes et consentement, alertes et consultations), deux WebSockets (`/ws/events`, `/ws/signaling/{room}`), et le chemin d'une requête : navigateur, vérification de la session et du rôle, Pydantic, SQLite, réponse JSON.

Notes orales :

Ma partie, c'est le cœur du serveur : l'API et la base de données. Le serveur est écrit avec FastAPI, un outil Python, et Pydantic pour vérifier les données.

Une API REST, c'est un ensemble d'adresses que le navigateur appelle pour demander ou envoyer quelque chose. Chez nous, il y en a trois familles. Les comptes et sessions : se connecter, créer un compte patient, se déconnecter. Les constantes et le consentement : le patient envoie ses mesures et son accord, le médecin lit la liste des patients et le tableau de bord. Et les alertes et consultations : le médecin acquitte une alerte, démarre ou termine une téléconsultation.

En plus, il y a deux WebSockets, des connexions qui restent ouvertes. La première, /ws/events, envoie en direct les alertes et les invitations. La seconde, /ws/signaling, sert seulement à faire passer les messages de négociation de la vidéo. Le serveur ne voit jamais l'image : elle passe directement d'un navigateur à l'autre.

En bas, le chemin d'une requête : le navigateur envoie, le serveur vérifie qui est connecté et son rôle, Pydantic vérifie les données, SQLite enregistre, et le serveur répond en JSON. FastAPI génère aussi automatiquement une documentation à l'adresse /docs, pratique pour tester.

## Slide 16 : Validation et accès protégés

Bornes acceptées : tension systolique 70 à 250, diastolique 40 à 160, fréquence cardiaque 30 à 220, SpO2 70 à 100 %, température 32 à 43 °C. Codes : 401 (pas de session), 403 (mauvais rôle ou dossier d'un autre patient), 409 (consultation sans consentement), 422 (valeur impossible ou formulaire invalide), 429 (trop de tentatives). Fonctions de contrôle : `current_user`, `doctor_only`, `ensure_patient_access`.

Notes orales :

Cette slide explique comment le serveur se protège. Le principe : le serveur ne fait jamais confiance au navigateur. L'interface cache certains menus pour le confort, mais c'est le serveur qui décide vraiment.

D'abord la validation. Chaque mesure envoyée est vérifiée par Pydantic avec des bornes physiologiques : tension systolique de 70 à 250, diastolique de 40 à 160, fréquence cardiaque de 30 à 220, oxygène de 70 à 100 pour cent, température de 32 à 43 degrés. En dehors de ces bornes, la valeur est impossible : le serveur répond 422 et n'enregistre rien. Ce n'est pas la même chose qu'une valeur dangereuse, comme 188 de tension : elle, elle est enregistrée et déclenche une alerte.

Ensuite les codes de réponse, qui disent pourquoi une demande est refusée. 401 : pas de session valide, donc pas connecté. 403 : mauvais rôle, par exemple un patient qui essaie de lire les alertes, ou le dossier d'un autre patient. 409 : le médecin essaie de démarrer une téléconsultation alors que le patient n'a pas donné son consentement. 422 : valeur impossible ou formulaire invalide. 429 : trop de tentatives, après 8 échecs de connexion en 5 minutes ou trop d'inscriptions depuis la même adresse.

En bas, trois petites fonctions sont appelées par chaque route : current_user vérifie qui est connecté, doctor_only réserve la route au médecin, et ensure_patient_access fait qu'un patient ne voit que son propre dossier. Ces règles sont vérifiées par nos 37 tests automatiques.

## Slide 17 : Base de données SQLite

Sept tables (`patients`, `users`, `sessions`, `consents`, `vitals`, `alerts`, `consultations`), trois protections (mots de passe hachés avec sel, jetons stockés sous forme d'empreinte, requêtes paramétrées) et le choix assumé de SQLite plutôt que PostgreSQL.

Notes orales :

Ici, la base de données. Nous utilisons SQLite : toute la base tient dans un seul fichier, sans rien installer, donc la démo marche sur n'importe quel ordinateur.

Il y a sept tables. patients contient le dossier : nom, année de naissance, motif du suivi. users contient les comptes, avec le rôle médecin ou patient. sessions garde les connexions ouvertes, pendant 8 heures. consents garde l'accord du patient, avec la date et la finalité. vitals contient toutes les mesures. alerts contient les alertes, avec leur gravité et leur statut, ouverte ou acquittée. Et consultations garde le médecin, le patient, le code de salle aléatoire, le début et la fin. Les tables sont reliées entre elles par des clés étrangères : par exemple chaque mesure appartient à un patient.

Ce n'est pas qu'un stockage, il y a trois protections. Un : les mots de passe ne sont jamais stockés en clair. On utilise PBKDF2 avec SHA-256, 200 000 itérations et un sel aléatoire différent pour chaque compte, donc deux mêmes mots de passe n'ont pas le même résultat. Deux : pour les sessions, on ne stocke pas le jeton lui-même mais son empreinte SHA-256, donc si quelqu'un vole la base, il ne peut pas se connecter. Trois : toutes les requêtes SQL sont paramétrées, les valeurs ne sont jamais collées dans le texte de la requête, ce qui empêche l'injection SQL.

Enfin, si on nous demande pourquoi SQLite et pas PostgreSQL : c'est un choix assumé. SQLite suffit pour un seul serveur et rend la démo reproductible. Sa limite, c'est qu'il ne convient pas à plusieurs serveurs ou à beaucoup d'utilisateurs en même temps. Dans ce cas il faudrait migrer vers PostgreSQL, et ce serait facile parce que tout l'accès à la base passe par une seule fonction de connexion. Merci.

## À ajouter au script si la question est posée

Transport : le TLS est fourni par le tunnel ou l'hébergeur ; l'application impose HTTPS avec `SAHALINK_FORCE_HTTPS=1` et envoie l'en-tête HSTS. Loi 09-08, article 24 : contrôles d'accès, de transmission et de transport pour les données de santé (détail dans `docs/security-and-compliance.md`).

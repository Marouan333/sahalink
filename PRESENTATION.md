# Présentation orale - SahaLink

Plan de préparation : trame des diapositives, script de démonstration, questions probables et points à relire. Le sujet précise que chaque membre doit pouvoir répondre sur l'ensemble du projet : le tableau de répartition indique qui présente quoi et où se trouve le code correspondant, mais tout le monde doit connaître tout le parcours.

## Format proposé (à adapter à la durée donnée)

Exposé d'environ 15 minutes, démonstration comprise, puis questions.

| Diapositive | Contenu | Durée | Orateur proposé |
|---|---|---|---|
| 1 | Titre, équipe, sujet | 0,5 min | Marouan |
| 2 | Contexte de soins et problème traité | 1 min | Hiba |
| 3 | Acteurs et besoins (tableau B1 à B10) | 1 min | Mohammed |
| 4 | Cadre normatif : WebRTC, OMS, loi 131-13 (art. 99 à 102), loi 09-08 | 1,5 min | Houssam |
| 5 | Architecture et flux (schéma légendé) | 1,5 min | Marouan |
| 6 | Modèle de données et BPMN | 1,5 min | Marouan |
| 7 | Démonstration en direct | 5 min | Tous |
| 8 | Alertes temps réel et données simulées | 1 min | Zaid |
| 9 | Sécurité, confidentialité, consentement | 1,5 min | Houssam |
| 10 | Validation et résultats chiffrés | 1,5 min | Zaid |
| 11 | Limites et perspectives | 1 min | Aymane |
| 12 | Conclusion | 0,5 min | Marouan |

## Répartition de l'équipe et où regarder dans le code

Répartition issue du plan d'équipe. Chacun doit savoir ouvrir ces fichiers et expliquer les fonctions citées.

| Membre | Domaine | À savoir expliquer | Fichiers et fonctions |
|---|---|---|---|
| Marouan | API et base de données | Routes REST, validation, schéma SQL, rôles | `app/main.py`, `app/database.py` |
| Aymane | WebRTC | Signalisation, offre/réponse, ICE, STUN/TURN, DTLS/SRTP | `static/app.js` (`createPeerConnection`, `handleSignal`), `app/main.py` (`signaling_socket`) |
| Mohammed | Interface patient | Connexion, consentement, saisie, invitation, rejoindre | `static/index.html`, `static/app.js` (`submitConsent`, `submitVital`, `joinFromPatientSide`) |
| Hiba | Interface médecin | Tableau de bord, alertes, démarrage de la consultation | `static/app.js` (`refreshDashboard`, `alertMarkup`, `ensureConsultation`) |
| Zaid | Alertes et données simulées | Seuils, envoi temps réel, jeu de données | `app/main.py` (`alert_for`, `send_event`), `docs/data-simulation.md` |
| Houssam | Sécurité | Hachage, sessions, contrôle des rôles, consentement, lois | `app/auth.py`, `app/main.py` (`current_user`, `doctor_only`), `docs/security-and-compliance.md` |

### Écarts entre le plan d'équipe et le prototype (à assumer à l'oral)

- **PostgreSQL** était prévu ; nous avons gardé **SQLite**, en connaissance de cause : aucune installation, démonstration reproductible, suffisant pour un serveur unique à faible charge. Les limites (un seul serveur en écriture, pas de réplication) sont assumées, et tout l'accès à la base passe par une seule fonction de connexion, donc le passage à PostgreSQL serait localisé.
- **Inscription du patient** : réalisée (formulaire validé côté client et serveur, rôle patient imposé par le serveur, limitation de débit).
- **Graphiques des constantes** : réalisés (quatre graphiques avec lignes de seuil, mis à jour en temps réel).
- **Plusieurs patients** : le médecin dispose d'une liste de patients avec alertes ouvertes, consentement et dernière mesure.
- **Chiffrement** : le média est chiffré par WebRTC (DTLS/SRTP) et les mots de passe sont hachés ; le chiffrement des données au repos n'est pas implémenté.

## Contenu des diapositives

1. **Titre** : SahaLink, plateforme de téléconsultation avec suivi à distance. Mini-projet 2, filière INDIA, ENSAM Rabat.
2. **Contexte** : service de cardiologie ou de médecine générale. Entre deux visites, une constante anormale peut passer inaperçue. Question posée : comment rendre visible une situation clinique qui demande l'attention du médecin, et ouvrir tout de suite un canal vidéo ?
3. **Acteurs et besoins** : patient (Amal, 54 ans, hypertension), médecin (Dr. Benali), plateforme. Montrer le tableau de besoins du rapport.
4. **Cadre normatif** : WebRTC (vidéo pair à pair). OMS (Global Observatory for eHealth) comme référence. Loi 131-13, section 4 sur la télémédecine : art. 99 (télémédecine autorisée, y compris la surveillance de l'état des patients, dans le respect de la protection des données), art. 100 (actes et identité du médecin consignés), art. 101 (consentement exprès, libre et éclairé, y compris électronique), art. 102 (conditions techniques par voie réglementaire). Loi 09-08 pour les données personnelles.
5. **Architecture** : afficher le schéma de `docs/architecture.md`. REST pour les données, WebSocket pour alertes et invitations, WebRTC pour la vidéo. Insister : la vidéo ne passe pas par le serveur.
6. **Modèle de données et BPMN** : afficher le diagramme entité-association (7 tables) et le BPMN à trois couloirs avec les cas dégradés.
7. **Démonstration** : voir le script ci-dessous.
8. **Alertes et données** : seuils (tension systolique >= 180 ou diastolique >= 120, SpO2 < 90 %, fréquence cardiaque < 45 ou > 130, température >= 39 degrés), envoi au médecin seul, données entièrement fictives et documentées.
9. **Sécurité** : mots de passe hachés (PBKDF2), sessions à jeton révocable, rôles contrôlés par le serveur sur chaque route, consentement bloquant (HTTP 409), WebSockets authentifiés avec vérification d'origine, salle vidéo liée à un médecin et un patient, verrouillage après échecs de connexion, protection XSS (échappement et CSP). Tableau article par article de la loi 131-13.
10. **Validation** : 37 tests automatisés, 6 profils cliniques détectés sur 6, 3 valeurs impossibles rejetées sur 3, latences mesurées (médiane d'écriture 30,9 ms), scénario complet dans deux fenêtres, score SUS avec des testeurs (à ajouter quand disponible).
11. **Limites** : pas de second facteur, comptes de démonstration, un seul compte médecin, STUN public sans relais TURN, capture caméra testée à la main, pas de validation clinique des seuils.
12. **Conclusion** : le prototype valide le parcours complet sans prétendre remplacer une plateforme médicale certifiée.

## Script de démonstration (5 minutes)

### Avant de commencer (à faire 10 minutes avant)

1. Lancer le serveur (`uvicorn app.main:app --host 127.0.0.1 --port 8000`) et vérifier `http://127.0.0.1:8000`.
2. Pour une démo sur deux ordinateurs : lancer `cloudflared tunnel --url http://127.0.0.1:8000` et ouvrir l'adresse affichée des deux côtés (elle change à chaque lancement).
3. Pour une démo sur un seul ordinateur : deux fenêtres du même navigateur (la session est gardée par onglet).
4. Fermer Camo, Iriun, Teams et toute application qui utilise la caméra.
5. Repartir d'une base propre : arrêter le serveur, supprimer `telecare.db`, relancer. Elle est recréée avec les deux comptes et la mesure de départ.
6. Autoriser la caméra et le micro dans les deux fenêtres avant le début.
7. Préparer une capture d'écran ou une courte vidéo de la démo réussie comme plan de secours.

### Déroulé

| Étape | Qui | Action | Résultat à montrer |
|---|---|---|---|
| 0 | Patient | « Créer un compte » : saisir un nom, un identifiant, une année de naissance et un mot de passe (ou connexion `amal`) | Compte créé, espace patient ouvert ; le nouveau patient apparaît dans la liste du médecin |
| 1 | Patient | Connexion `amal` (ou le compte créé) | Espace patient, menu réduit à deux entrées |
| 2 | Médecin | Connexion `dr.benali`, choisir le patient dans la liste, clic « Démarrer une consultation » | Refus : le patient n'a pas donné son consentement (cas dégradé n° 1, art. 101) |
| 3 | Patient | Cocher le consentement et enregistrer | Badge « Confirmé » ; le tableau de bord du médecin passe à « Confirmé » |
| 4 | Patient | Envoyer une mesure normale | Aucune alerte ; ligne ajoutée à l'historique du médecin |
| 5 | Patient | « Simuler une alerte » puis envoyer (188/122, SpO2 89 %) | Cas dégradé n° 2 : alerte critique immédiate chez le médecin ; les quatre graphiques montrent le point au-dessus du seuil |
| 6 | Médecin | Acquitter l'alerte | Compteur à zéro, statut « acquittée » |
| 7 | Médecin | « Démarrer une consultation » | Le patient voit l'invitation sans recharger |
| 8 | Patient | « Rejoindre » | Vidéo des deux côtés, statut « Consultation connectée » |
| 9 | Médecin | Couper la caméra, puis la rallumer | Le patient est informé de l'état de la caméra |
| 10 | Médecin | « Terminer » | Le patient est prévenu, les caméras s'arrêtent |

Cas dégradés optionnels si le temps le permet : essayer une valeur impossible (tension 500, refusée par le serveur) ; choisir une caméra virtuelle dans la liste pour montrer le message d'image noire.

### Plan B si la vidéo échoue

- Vérifier qu'aucune autre application n'utilise la caméra, puis choisir la webcam dans la liste « Caméra ».
- Si les deux ordinateurs sont sur des réseaux différents et que la vidéo ne s'établit pas, utiliser deux fenêtres sur un seul ordinateur.
- En dernier recours, passer à la vidéo ou aux captures préparées et expliquer le mécanisme avec le schéma.

## Questions probables et éléments de réponse

| Question | Réponse courte |
|---|---|
| Pourquoi WebRTC plutôt que de passer la vidéo par le serveur ? | Norme imposée par le sujet ; le flux est pair à pair, chiffré DTLS/SRTP, donc le serveur ne voit ni ne stocke la vidéo et supporte peu de charge. |
| À quoi sert le serveur dans l'appel ? | Il authentifie les deux participants et relaie la signalisation (offre, réponse, candidats ICE). Le média passe directement entre navigateurs. |
| Que sont STUN, TURN et ICE ? | ICE cherche un chemin réseau entre les deux navigateurs ; STUN leur apprend leur adresse publique ; TURN relaie le flux quand aucun chemin direct n'existe (réseaux stricts). Ici STUN par défaut, TURN configurable. |
| Pourquoi SQLite alors que le plan prévoyait PostgreSQL ? | Choix assumé : sans installation, reproductible, suffisant pour un serveur unique. L'accès passe par une seule fonction de connexion ; PostgreSQL serait nécessaire pour plusieurs serveurs ou une forte charge simultanée. |
| Comment le consentement est-il appliqué ? | Il est enregistré avec date et finalité ; le serveur refuse de démarrer une consultation si le dernier consentement n'est pas une acceptation (HTTP 409). Cela répond à l'art. 101 de la loi 131-13 : consentement exprès, libre, éclairé, électronique accepté, droit de refus. |
| Que dit la loi 131-13 sur la télémédecine ? | Section 4, art. 99 à 102 : télémédecine autorisée, y compris la surveillance des patients, sous réserve de la protection des données (99) ; actes et identité du médecin consignés (100) ; consentement du patient (101) ; conditions techniques fixées par règlement (102). |
| Que fait la loi 09-08 ? | Elle protège les données personnelles. Les données de santé sont des données sensibles (art. 1). Le consentement doit être indubitable (art. 4). Droit à l'information (art. 5), d'accès, de rectification et d'opposition (art. 7 à 9). Les données de santé exigent une autorisation de la CNDP, ou une déclaration pour les soins par un praticien tenu au secret (art. 12, 21, 22). Mesures de sécurité (art. 23) et huit contrôles pour les données de santé (art. 24). |
| Quel article de la loi 09-08 justifie votre sécurité ? | L'article 24 : contrôle d'accès, d'utilisation, de transmission et de transport. Chez nous : rôles sur chaque route, sessions, WebSockets authentifiés, HTTPS imposé avec HSTS, média chiffré par WebRTC. |
| Que dit le rapport de l'OMS ? | Il définit la télémédecine par quatre éléments (soutien clinique, distance, TIC, résultats). 114 pays ont répondu (59 %). Seuls 20 % des pays ont une évaluation publiée, d'où notre évaluation chiffrée. Le coût est l'obstacle le plus cité ; les obstacles juridiques de confidentialité comptent beaucoup dans les pays développés. |
| Le trafic est-il chiffré ? | La vidéo l'est par WebRTC (DTLS/SRTP). Le reste passe en HTTPS grâce au proxy ou au tunnel TLS ; l'application impose HTTPS (redirection) et envoie HSTS. Les données au repos ne sont pas chiffrées. |
| Comment sont stockés les mots de passe ? | Hachés avec PBKDF2-SHA256, 200 000 itérations, sel aléatoire par compte, comparaison en temps constant. Les jetons de session sont stockés sous forme d'empreinte SHA-256. |
| Qu'est-ce qui empêche un patient de voir un autre dossier ou les alertes ? | Le serveur contrôle le rôle et l'identité sur chaque route (403). Les menus masqués ne sont qu'un confort. Tests V7 et V8. |
| Comment sont choisis les seuils ? | Valeurs usuelles simplifiées pour la démonstration ; ils ne sont pas validés cliniquement et devraient l'être avec un médecin. Le taux de détection de 100 % mesure la correction du code, pas la sensibilité clinique. |
| Pourquoi des WebSockets pour les alertes ? | Une alerte doit arriver tout de suite sans que le médecin interroge le serveur en boucle ; le même canal porte les invitations. |
| D'où viennent les données ? | Elles sont entièrement fictives : patient, médecin, comptes et mesures sont générés au démarrage ou saisis par les testeurs ; aucune donnée réelle. |
| Quelles sont les limites de sécurité ? | Pas de second facteur, verrouillage après échecs limité à un serveur, comptes de démonstration au mot de passe public, jeton gardé par onglet plutôt qu'en cookie HttpOnly, pas de chiffrement au repos. Tout est listé dans la note de sécurité. |
| Comment passer à l'échelle ? | PostgreSQL, plusieurs médecins avec affectation des patients, relais TURN, hébergement agréé pour données de santé, journal d'audit. |
| Comment avez-vous mesuré l'utilisabilité ? | Protocole SUS avec des testeurs en binôme (`docs/test-utilisabilite.md`) ; donner le score réel une fois les essais faits, sans extrapoler. |

## À relire avant l'oral

- **Loi 131-13**, section 4, articles 99 à 102 : lire le texte (Bulletin officiel n° 6344, lien dans la note de sécurité) pour pouvoir répondre sans notes.
- **Loi 09-08** : lire dans le texte officiel les articles 1, 3, 4, 5, 7 à 9, 12, 21 à 24 déjà résumés dans `docs/security-and-compliance.md`, surtout l'article 24 (sécurité des données de santé).
- **Rapport de l'OMS** : retenir les constats chiffrés déjà extraits (114 pays, 59 %, 33 % de téléradiologie, 30 % d'agences nationales, 20 % d'évaluations publiées) et la définition en quatre éléments.
- **Votre propre code** : chaque membre ouvre ses fichiers du tableau et sait dérouler un appel de bout en bout.

## Chiffres à connaître

- 37 tests automatisés, tous réussis ; 100 % de détection sur 6 profils ; 100 % de rejet sur 3 valeurs impossibles.
- Latences locales (voir réserves dans `docs/validation.md`) : écriture d'une mesure, médiane 30,9 ms ; création d'alerte, moyenne 25,8 ms ; acquittement, moyenne 28,2 ms.
- 7 tables, 2 comptes de démonstration plus inscription libre (200 comptes maximum), 2 participants maximum par salle, sessions de 8 heures.

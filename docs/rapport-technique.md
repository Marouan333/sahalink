# Rapport technique - SahaLink

Mini-projet 2 : Plateforme de téléconsultation avec suivi à distance
Filière INDIA, ENSAM Rabat, 2026/2027

## 1. Cadrage et contexte de soins

**Établissement cible** : service de cardiologie ou de médecine générale d'un centre de santé marocain.

**Acteurs** :
- Patients suivis pour hypertension artérielle (persona fictif de démonstration : Amal El Idrissi, 54 ans ; tout visiteur peut aussi créer son propre compte patient fictif).
- Médecin traitant (persona fictif : Dr. Benali), responsable du suivi et de la décision clinique.
- Plateforme SahaLink, qui relie les deux acteurs.

**Problème réel traité** : entre deux visites physiques, une dérive d'une constante physiologique (tension, SpO2, fréquence cardiaque, température) peut passer inaperçue. Le patient n'a pas de moyen simple de signaler une mesure anormale, et le médecin n'a pas de visibilité continue. SahaLink raccourcit ce délai de détection et ouvre un canal de téléconsultation immédiat en cas d'alerte.

**Cadre normatif et réglementaire** (détail et mise en œuvre dans `docs/security-and-compliance.md`) :
- **WebRTC** pour la vidéo et l'audio pair à pair.
- **Rapport de l'OMS, Global Observatory for eHealth** (*Telemedicine: opportunities and developments in Member States*) : référence institutionnelle sur la télémédecine, dont la définition de l'OMS sert de cadre au projet.
- **Loi 131-13 relative à l'exercice de la médecine**, section 4 « De la télémédecine », articles 99 à 102 : la télémédecine est autorisée, y compris la surveillance de l'état des patients (art. 99) ; les actes et l'identité du médecin sont consignés au dossier (art. 100) ; le consentement du patient doit être exprès, libre et éclairé, y compris par voie électronique, avec droit de refus (art. 101).
- **Loi 09-08** sur la protection des données à caractère personnel, à laquelle l'article 99 renvoie pour la confidentialité.

### Besoins formalisés

| ID | Besoin | Acteur | Réalisation dans SahaLink | Vérification |
|---|---|---|---|---|
| B1 | S'identifier de façon sûre et ne voir que ce qui me concerne | Patient, médecin | Connexion, sessions, contrôle d'accès par rôle | Tests V7, V8 |
| B2 | Donner ou refuser mon consentement avant la téléconsultation | Patient | Consentement horodaté avec finalité ; démarrage bloqué sans consentement | Test V9 |
| B3 | Transmettre mes constantes depuis chez moi | Patient | Formulaire de saisie, historique personnel | Test V2 |
| B4 | Être prévenu sans délai d'une constante anormale | Médecin | Seuils cliniques, alerte temps réel, acquittement | Tests V3, V4 |
| B5 | Rejeter les valeurs impossibles | Système | Validation serveur des bornes physiologiques | Test V5 |
| B6 | Joindre rapidement le patient en vidéo | Médecin | Invitation temps réel, code de salle aléatoire | Tests V10, V11 |
| B7 | Rejoindre sans saisir de code technique | Patient | Bannière d'invitation et bouton « Rejoindre » | Test V10 |
| B8 | Que personne d'autre n'entre dans la consultation | Patient, médecin | Salle liée à un médecin et un patient, deux participants au maximum | Test V11 |
| B9 | Retrouver une trace de l'acte | Médecin | Table des consultations, constantes, alertes et consentements horodatés | Voir art. 100 |
| B10 | Comprendre pourquoi la vidéo ne s'affiche pas | Patient, médecin | Choix de caméra, détection d'image noire, statut explicite | Test manuel |
| B11 | Créer mon propre compte patient | Patient | Formulaire d'inscription validé côté client et serveur, rôle patient imposé par le serveur, limitation de débit | Tests d'inscription, d'élévation de rôle et de limitation |
| B12 | Suivre plusieurs patients et voir l'évolution de leurs constantes | Médecin | Liste des patients avec indicateurs (alertes ouvertes, consentement, dernière mesure) et quatre graphiques avec seuils | Tests de liste et de tableau de bord par patient |

## 2. Modélisation du système

- **Architecture technique** : `docs/architecture.md` (schéma légende, composants, droits par rôle, flux clinique, choix de conception).
- **Modèle de données** : diagramme entité-association de sept tables (`patients`, `users`, `sessions`, `consents`, `vitals`, `alerts`, `consultations`) dans `docs/architecture.md`, schéma SQL dans `app/database.py`.
- **Parcours patient-médecin (BPMN)** : `docs/bpmn-parcours-patient.md` (couloirs Patient, Système, Médecin, décisions, cas dégradés).
- **Jeu de données simulé** : `docs/data-simulation.md` (origine, traçabilité, cas dégradé standard, comptes de démonstration).

## 3. Prototype réalisé

| Couche | Technologie | Rôle |
|---|---|---|
| Interface | HTML / CSS / JavaScript (graphiques en SVG intégré, sans bibliothèque) | Connexion, inscription, liste des patients, graphiques des constantes, salle vidéo |
| API | FastAPI (Python), Pydantic | Validation, règles de seuil, authentification, endpoints REST |
| Temps réel | WebSocket natif FastAPI | Alertes et invitations (`/ws/events`), relais de signalisation WebRTC |
| Média | WebRTC (RTCPeerConnection, STUN, TURN optionnel) | Vidéo pair à pair chiffrée DTLS/SRTP |
| Persistance | SQLite (fichier `telecare.db`) | Démonstration ; choix justifié en section 5 |

Le code source se trouve dans `app/` (backend) et `static/` (frontend). Installation et exécution : voir `README.md`. Dépôt : https://github.com/Marouan333/sahalink. Fichiers de déploiement : `Procfile`, `render.yaml`, `.python-version`, `requirements.txt`.

## 4. Validation et résultats chiffrés

Protocole et résultats détaillés : `docs/validation.md`. Synthèse :

- **Scénario clinique complet** exécuté dans deux fenêtres (médecin et patient) : connexion, refus de démarrage sans consentement, consentement, mesure normale, mesure critique, alerte temps réel, acquittement, invitation, téléconsultation vidéo dans les deux sens, fin de consultation.
- **Cas dégradés** : valeur impossible rejetée, constante hors seuil, consentement absent, troisième participant refusé, tiers sans jeton refusé, départ du correspondant.
- **Tests automatisés** : 35 tests (`tests/test_api.py`), tous réussis, sur une base de données temporaire distincte de la base de démonstration.
- **Détection du cas dégradé** : 6 profils cliniques, 100 % de détection (`scripts/benchmark.py`).
- **Rejet des entrées hors plage** : 100 % (3/3).
- **Latence** (serveur de test local, sans réseau) : écriture d'une mesure normale, médiane 30,9 ms ; création et diffusion d'une alerte, moyenne 25,8 ms ; acquittement, moyenne 28,2 ms. Ces valeurs varient d'une exécution à l'autre sur un poste chargé (voir `docs/validation.md`).
- **Utilisabilité** : protocole SUS prêt dans `docs/test-utilisabilite.md` ; les résultats sont à renseigner après les essais avec des utilisateurs.

## 5. Discussion critique et limites

- Le taux de détection de 100 % reflète une implémentation correcte de règles déterministes, pas une validation clinique des seuils eux-mêmes : ces seuils devraient être revus avec un médecin avant tout usage réel.
- Les latences mesurées excluent le réseau et la charge concurrente ; elles ne permettent pas d'extrapoler un comportement en production multi-patients.
- L'authentification est réelle (mots de passe hachés, sessions, rôles) mais reste une authentification simple : pas de second facteur, comptes de démonstration au mot de passe public, jeton gardé par onglet plutôt qu'en cookie `HttpOnly`. Le verrouillage après échecs (8 tentatives par 5 minutes, par adresse et identifiant) et la limitation des inscriptions sont en mémoire d'un seul serveur.
- Face à une plateforme certifiée (type Doctolib, Qare ou solution hospitalière), SahaLink ne traite ni la montée en charge, ni l'hébergement de données de santé agréé, ni la gestion du tuteur légal d'un patient mineur (article 101).
- Le prototype gère plusieurs patients (inscription libre, plafonnée à 200 comptes de démonstration) mais un seul compte médecin de démonstration ; il n'y a pas de gestion d'équipes soignantes ni d'affectation d'un patient à un médecin précis.
- **Choix de SQLite, assumé** : le sujet n'impose pas de moteur. SQLite évite toute installation, rend la démonstration reproductible sur n'importe quel poste et suffit pour un serveur unique à faible charge. Les limites sont connues : un seul serveur en écriture, pas de réplication, pas d'accès concurrent massif. Pour un déploiement multi-établissements, une migration vers PostgreSQL serait nécessaire ; elle est facilitée par une seule fonction de connexion (`app/database.py`) et un schéma SQL simple, mais elle n'est pas réalisée.
- Les appels entre réseaux différents s'appuient sur des serveurs STUN publics ; certains réseaux mobiles exigent un relais TURN, configurable mais non fourni par défaut.
- La capture vidéo réelle (caméra, microphone) ne peut pas être automatisée : elle est validée manuellement.
- Les qualifications du médecin (article 100) ne sont pas modélisées.

## 6. Sécurité, confidentialité et conformité

Traité dans `docs/security-and-compliance.md` : données fictives, authentification et sessions, contrôle d'accès par rôle sur chaque route, consentement horodaté bloquant, WebSockets authentifiés avec vérification d'origine, salle vidéo réservée, chiffrement média WebRTC natif, absence d'enregistrement vidéo, politique de sécurité du contenu (CSP) et échappement systématique des noms saisis par les utilisateurs (protection XSS), verrouillage après échecs de connexion, limitation des inscriptions, limites explicites avant tout déploiement réel, et correspondance article par article avec la loi 131-13 (articles 99 à 102) et la loi 09-08.

## 7. Conclusion

Le prototype SahaLink démontre, sur un périmètre volontairement restreint et avec des données exclusivement simulées, un parcours complet de suivi à distance et de téléconsultation entre un patient et un médecin identifiés : consentement, saisie de constantes, détection automatique d'un cas dégradé, alerte temps réel, invitation, consultation vidéo pair à pair et clôture. Les quatre dimensions demandées (technique, normative, organisationnelle, réglementaire) sont traitées, avec des limites explicitement documentées avant tout usage réel.

## Annexes

- `PRESENTATION.md` : trame de la présentation orale, script de démonstration et questions probables.
- `docs/architecture.md`, `docs/bpmn-parcours-patient.md`, `docs/data-simulation.md`, `docs/security-and-compliance.md`, `docs/validation.md`, `docs/test-utilisabilite.md`.
- `tests/test_api.py`, `scripts/benchmark.py` : preuves automatisées et chiffrées.

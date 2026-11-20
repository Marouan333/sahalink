# Rapport technique - SahaLink

Mini-projet 2 : Plateforme de teleconsultation avec suivi a distance
Filiere INDIA, ENSAM Rabat, 2026/2027

## 1. Cadrage et contexte de soins

**Etablissement cible** : service de cardiologie ou de medecine generale d'un centre de sante marocain.

**Acteurs** :
- Patient suivi pour hypertension arterielle (persona fictif : Amal El Idrissi, 54 ans).
- Medecin traitant (persona fictif : Dr. Benali), responsable du suivi et de la decision clinique.
- Plateforme SahaLink, qui relie les deux acteurs.

**Probleme reel traite** : entre deux visites physiques, une derive d'une constante physiologique (tension, SpO2, frequence cardiaque, temperature) peut passer inapercue. Le patient n'a pas de moyen simple de signaler une mesure anormale, et le medecin n'a pas de visibilite continue. SahaLink raccourcit ce delai de detection et ouvre un canal de teleconsultation immediat en cas d'alerte.

**Cadre normatif et reglementaire** (detail et mise en oeuvre dans `docs/security-and-compliance.md`) :
- **WebRTC** pour la video et l'audio pair a pair.
- **Rapport de l'OMS, Global Observatory for eHealth** (*Telemedicine: opportunities and developments in Member States*) : reference institutionnelle sur la telemedecine, dont la definition de l'OMS sert de cadre au projet.
- **Loi 131-13 relative a l'exercice de la medecine**, section 4 Â« De la telemedecine Â», articles 99 a 102 : la telemedecine est autorisee, y compris la surveillance de l'etat des patients (art. 99) ; les actes et l'identite du medecin sont consignes au dossier (art. 100) ; le consentement du patient doit etre expres, libre et eclaire, y compris par voie electronique, avec droit de refus (art. 101).
- **Loi 09-08** sur la protection des donnees a caractere personnel, a laquelle l'article 99 renvoie pour la confidentialite.

### Besoins formalises

| ID | Besoin | Acteur | Realisation dans SahaLink | Verification |
|---|---|---|---|---|
| B1 | S'identifier de facon sure et ne voir que ce qui me concerne | Patient, medecin | Connexion, sessions, controle d'acces par role | Tests V7, V8 |
| B2 | Donner ou refuser mon consentement avant la teleconsultation | Patient | Consentement horodate avec finalite ; demarrage bloque sans consentement | Test V9 |
| B3 | Transmettre mes constantes depuis chez moi | Patient | Formulaire de saisie, historique personnel | Test V2 |
| B4 | Etre prevenu sans delai d'une constante anormale | Medecin | Seuils cliniques, alerte temps reel, acquittement | Tests V3, V4 |
| B5 | Rejeter les valeurs impossibles | Systeme | Validation serveur des bornes physiologiques | Test V5 |
| B6 | Joindre rapidement le patient en video | Medecin | Invitation temps reel, code de salle aleatoire | Tests V10, V11 |
| B7 | Rejoindre sans saisir de code technique | Patient | Banniere d'invitation et bouton Â« Rejoindre Â» | Test V10 |
| B8 | Que personne d'autre n'entre dans la consultation | Patient, medecin | Salle liee a un medecin et un patient, deux participants au maximum | Test V11 |
| B9 | Retrouver une trace de l'acte | Medecin | Table des consultations, constantes, alertes et consentements horodates | Voir art. 100 |
| B10 | Comprendre pourquoi la video ne s'affiche pas | Patient, medecin | Choix de camera, detection d'image noire, statut explicite | Test manuel |

## 2. Modelisation du systeme

- **Architecture technique** : `docs/architecture.md` (schema legende, composants, droits par role, flux clinique, choix de conception).
- **Modele de donnees** : diagramme entite-association de sept tables (`patients`, `users`, `sessions`, `consents`, `vitals`, `alerts`, `consultations`) dans `docs/architecture.md`, schema SQL dans `app/database.py`.
- **Parcours patient-medecin (BPMN)** : `docs/bpmn-parcours-patient.md` (couloirs Patient, Systeme, Medecin, decisions, cas degrades).
- **Jeu de donnees simule** : `docs/data-simulation.md` (origine, tracabilite, cas degrade standard, comptes de demonstration).

## 3. Prototype realise

| Couche | Technologie | Role |
|---|---|---|
| Interface | HTML / CSS / JavaScript | Connexion, espaces patient et medecin, salle video |
| API | FastAPI (Python), Pydantic | Validation, regles de seuil, authentification, endpoints REST |
| Temps reel | WebSocket natif FastAPI | Alertes et invitations (`/ws/events`), relais de signalisation WebRTC |
| Media | WebRTC (RTCPeerConnection, STUN, TURN optionnel) | Video pair a pair chiffree DTLS/SRTP |
| Persistance | SQLite (fichier `telecare.db`) | Demonstration, migrable vers PostgreSQL |

Le code source se trouve dans `app/` (backend) et `static/` (frontend). Installation et execution : voir `README.md`. Depot : https://github.com/Marouan333/sahalink. Fichiers de deploiement : `Procfile`, `render.yaml`, `.python-version`, `requirements.txt`.

## 4. Validation et resultats chiffres

Protocole et resultats detailles : `docs/validation.md`. Synthese :

- **Scenario clinique complet** execute dans deux fenetres (medecin et patient) : connexion, refus de demarrage sans consentement, consentement, mesure normale, mesure critique, alerte temps reel, acquittement, invitation, teleconsultation video dans les deux sens, fin de consultation.
- **Cas degrades** : valeur impossible rejetee, constante hors seuil, consentement absent, troisieme participant refuse, tiers sans jeton refuse, depart du correspondant.
- **Tests automatises** : 25 tests (`tests/test_api.py`), tous reussis, sur une base de donnees temporaire distincte de la base de demonstration.
- **Detection du cas degrade** : 6 profils cliniques, 100 % de detection (`scripts/benchmark.py`).
- **Rejet des entrees hors plage** : 100 % (3/3).
- **Latence** (serveur de test local, sans reseau) : ecriture d'une mesure normale, mediane 30,9 ms ; creation et diffusion d'une alerte, moyenne 25,8 ms ; acquittement, moyenne 28,2 ms. Ces valeurs varient d'une execution a l'autre sur un poste charge (voir `docs/validation.md`).
- **Utilisabilite** : protocole SUS pret dans `docs/test-utilisabilite.md` ; les resultats sont a renseigner apres les essais avec des utilisateurs.

## 5. Discussion critique et limites

- Le taux de detection de 100 % reflete une implementation correcte de regles deterministes, pas une validation clinique des seuils eux-memes : ces seuils devraient etre revus avec un medecin avant tout usage reel.
- Les latences mesurees excluent le reseau et la charge concurrente ; elles ne permettent pas d'extrapoler un comportement en production multi-patients.
- L'authentification est reelle (mots de passe haches, sessions, roles) mais reste une authentification simple : pas de second facteur, pas de verrouillage apres echecs, comptes de demonstration au mot de passe public, jeton garde par onglet plutot qu'en cookie `HttpOnly`.
- Face a une plateforme certifiee (type Doctolib, Qare ou solution hospitaliere), SahaLink ne traite ni la montee en charge, ni l'hebergement de donnees de sante agree, ni la gestion du tuteur legal d'un patient mineur (article 101).
- Le perimetre est limite a un patient fictif et un medecin ; le tableau de bord suit un seul dossier. Plusieurs paires de testeurs simultanes se partagent donc les deux comptes.
- Les appels entre reseaux differents s'appuient sur des serveurs STUN publics ; certains reseaux mobiles exigent un relais TURN, configurable mais non fourni par defaut.
- La capture video reelle (camera, microphone) ne peut pas etre automatisee : elle est validee manuellement.
- Les qualifications du medecin (article 100) ne sont pas modelisees.

## 6. Securite, confidentialite et conformite

Traite dans `docs/security-and-compliance.md` : donnees fictives, authentification et sessions, controle d'acces par role sur chaque route, consentement horodate bloquant, WebSockets authentifies avec verification d'origine, salle video reservee, chiffrement media WebRTC natif, absence d'enregistrement video, limites explicites avant tout deploiement reel, et correspondance article par article avec la loi 131-13 (articles 99 a 102) et la loi 09-08.

## 7. Conclusion

Le prototype SahaLink demontre, sur un perimetre volontairement restreint et avec des donnees exclusivement simulees, un parcours complet de suivi a distance et de teleconsultation entre un patient et un medecin identifies : consentement, saisie de constantes, detection automatique d'un cas degrade, alerte temps reel, invitation, consultation video pair a pair et cloture. Les quatre dimensions demandees (technique, normative, organisationnelle, reglementaire) sont traitees, avec des limites explicitement documentees avant tout usage reel.

## Annexes

- `PRESENTATION.md` : trame de la presentation orale, script de demonstration et questions probables.
- `docs/architecture.md`, `docs/bpmn-parcours-patient.md`, `docs/data-simulation.md`, `docs/security-and-compliance.md`, `docs/validation.md`, `docs/test-utilisabilite.md`.
- `tests/test_api.py`, `scripts/benchmark.py` : preuves automatisees et chiffrees.

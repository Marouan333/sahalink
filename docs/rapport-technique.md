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

**Etat de l'art et references** : rapport de l'OMS *Global Observatory for eHealth, Telemedicine: opportunities and developments in Member States* (continuite du suivi, consentement, tracabilite comme conditions de maturite) ; loi marocaine 131-13 relative a l'exercice de la medecine (encadrement de la teleconsultation) ; loi 09-08 (protection des donnees personnelles). Voir `docs/security-and-compliance.md` pour le detail de l'application de chaque texte.

## 2. Modelisation du systeme

- **Architecture technique** : `docs/architecture.md` (schema legende, composants, flux clinique, choix de conception).
- **Parcours patient (BPMN)** : `docs/bpmn-parcours-patient.md` (couloirs Patient / Systeme / Medecin, decisions, cas degrade).
- **Modele de donnees** : quatre entites (`patients`, `consents`, `vitals`, `alerts`), schema SQL dans `app/database.py`, relations par cle etrangere `patient_id` et `vital_id`.
- **Jeu de donnees simule** : `docs/data-simulation.md` (origine, traçabilite, cas degrade standard).

## 3. Prototype realise

| Couche | Technologie | Role |
|---|---|---|
| Interface | HTML / CSS / JavaScript vanilla | Espaces patient et medecin, salle video |
| API | FastAPI (Python), Pydantic | Validation, regles de seuil, endpoints REST |
| Temps reel | WebSocket natif FastAPI | Diffusion des alertes, relais de signalisation WebRTC |
| Media | WebRTC (RTCPeerConnection, STUN) | Video pair-a-pair chiffree DTLS/SRTP |
| Persistance | SQLite (fichier `telecare.db`) | Demonstration locale, migrable vers PostgreSQL |

Le code source complet se trouve dans `app/` (backend) et `static/` (frontend). Installation et execution : voir `README.md` (`pip install -r requirements.txt`, puis `uvicorn app.main:app --reload`).

## 4. Validation et resultats chiffres

Protocole et resultats detailles : `docs/validation.md`. Synthese :

- Scenario clinique complet verifie par cinq cas (sante -> mesure normale -> mesure critique -> acquittement -> rejet d'entree invalide) et un sixieme cas de signalisation video entre deux pairs, tous automatises dans `tests/test_api.py` (6/6 tests reussis).
- Cas degrade : 6 profils cliniques distincts testes, **100 % de detection** (`scripts/benchmark.py`).
- Rejet des entrees hors plage physiologique absolue : **100 %** (3/3).
- Latence mesuree (serveur de test local, sans reseau) : ecriture d'une mesure normale, mediane 47,5 ms ; creation et diffusion d'une alerte, moyenne 42,9 ms ; acquittement d'une alerte, moyenne 58,1 ms.

## 5. Discussion critique et limites

- Le taux de detection de 100 % refleter une implementation correcte de regles deterministes, pas une validation clinique des seuils eux-memes : ces seuils devraient etre revus avec un medecin avant tout usage reel.
- Les latences mesurees excluent le reseau et la charge concurrente ; elles ne permettent pas d'extrapoler un comportement en production multi-patients.
- Face a une plateforme certifiee (type Doctolib, Qare, ou une solution hospitaliere), SahaLink ne traite ni l'authentification forte, ni la montee en charge, ni l'hebergement de donnees de sante agree. L'objectif du prototype est de demontrer le parcours fonctionnel bout-en-bout sur un perimetre volontairement restreint, pas de remplacer ces plateformes.
- Le perimetre est limite a un seul patient fictif et a un seul medecin ; aucune gestion multi-tenant, aucun annuaire d'acteurs.

## 6. Securite, confidentialite et conformite

Traite integralement dans `docs/security-and-compliance.md` : donnees fictives, consentement horodate, validation serveur, chiffrement media WebRTC natif, non-enregistrement des flux video, limites explicites avant tout deploiement reel, et correspondance avec la loi 09-08 et la loi 131-13.

## 7. Conclusion

Le prototype SahaLink demontre, sur un perimetre volontairement restreint et avec des donnees exclusivement simulees, un parcours complet de suivi a distance et de teleconsultation : consentement, saisie de constantes, detection automatique d'un cas degrade, alerte temps reel au medecin et consultation video pair-a-pair. Les quatre dimensions demandees (technique, normative, organisationnelle, reglementaire) sont traitees, avec des limites explicitement documentees avant tout usage reel.

## Annexes

- `PRESENTATION.md` : trame de la presentation orale.
- `docs/architecture.md`, `docs/bpmn-parcours-patient.md`, `docs/data-simulation.md`, `docs/security-and-compliance.md`, `docs/validation.md`.
- `tests/test_api.py`, `scripts/benchmark.py` : preuves automatisees et chiffrees.

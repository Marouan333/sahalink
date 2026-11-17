# Protocole de validation

## Objectif

Verifier le fonctionnement de bout en bout, y compris un cas degrade, avec des resultats chiffrables.

## Scenarios

| ID | Action | Resultat attendu | Indicateur |
|---|---|---|---|
| V1 | Ouvrir `/api/health` | Service disponible | HTTP 200 |
| V2 | Envoyer une mesure normale | Mesure dans l'historique, sans alerte | 1 ecriture, 0 alerte |
| V3 | Envoyer SpO2 89 % | Alerte critique creee et visible | 1 alerte, WebSocket diffuse |
| V4 | Acquitter l'alerte | Etat passe a `acknowledged` | 1 modification |
| V5 | Envoyer une valeur hors plage API | Rejet de la mesure | HTTP 422 |
| V6 | Medecin et patient connectes dans deux fenetres, le medecin demarre, le patient accepte l'invitation | Negociation video WebRTC | Flux local et distant actifs (procedure manuelle detaillee dans `README.md`, section *Testing the full workflow*) |
| V7 | Appel d'une route de sante sans session | Acces refuse | HTTP 401 |
| V8 | Le patient lit les alertes, acquitte une alerte ou lit un autre dossier | Acces refuse | HTTP 403 |
| V9 | Le medecin demarre une teleconsultation avant le consentement du patient | Demarrage bloque | HTTP 409 |
| V10 | Le medecin demarre une teleconsultation apres consentement | Invitation recue en temps reel par le patient | Evenement `invitation` sur `/ws/events` |
| V11 | Connexion a une salle video sans jeton valide ou par un tiers | Connexion refusee | `auth-failed` ou `forbidden` |
| V12 | Le medecin termine la consultation | Le patient est notifie, la salle est fermee | Evenement `consultation-ended`, plus de consultation active |

## Resultats chiffres (mesures reelles, bande de test FastAPI, machine locale)

Ces chiffres proviennent d'un script de benchmark execute localement contre l'API (`TestClient`), pas d'une estimation. Ils caracterisent le prototype, pas une charge de production. Depuis l'ajout de l'authentification, chaque requete inclut la verification de la session (une lecture SQLite supplementaire) : le patient envoie les mesures, le medecin acquitte les alertes.

| Indicateur | Protocole | Resultat |
|---|---|---|
| Taux de detection du cas degrade | 6 profils cliniques distincts (tension, SpO2, bradycardie, tachycardie, fievre, combinaison critique) envoyes un par un | **6/6 soit 100 %** |
| Taux de rejet des valeurs hors plage absolue | 3 entrees hors bornes Pydantic (tension 500, SpO2 150, temperature 60) | **3/3 soit 100 %** |
| Latence d'ecriture d'une mesure normale | 30 envois successifs d'une mesure normale, session patient | moyenne **44,5 ms**, mediane **30,9 ms**, min **24,0 ms**, max **118,7 ms** |
| Latence creation + diffusion d'une alerte | 6 mesures degradees, session patient | moyenne **25,8 ms**, min **23,4 ms**, max **28,2 ms** |
| Latence d'acquittement d'une alerte | 10 cycles creation puis acquittement, session medecin | moyenne **28,2 ms**, min **25,3 ms**, max **33,3 ms** |

## Discussion et limites des resultats

- La latence mesuree inclut le serveur de test en memoire sans reseau ; elle minore la latence reelle sur un reseau mobile ou avec PostgreSQL distant.
- Les mesures varient fortement d'une execution a l'autre sur un poste charge : un premier passage le meme jour, avec d'autres traitements lourds en cours sur la machine, donnait une moyenne de 178 ms pour l'ecriture normale. Le tableau ci-dessus correspond a une machine moins chargee ; un protocole plus rigoureux repeterait le benchmark et publierait la mediane des executions.
- L'ecart entre la mediane (30,9 ms) et le maximum (118,7 ms) sur l'ecriture normale vient de la premiere requete qui initialise la connexion SQLite.
- Le taux de detection de 100 % est attendu car les regles de seuil sont deterministes et codees en dur (`app/main.py::alert_for`) : il mesure la correction de l'implementation, pas une sensibilite clinique au sens d'un dispositif medical valide.
- Aucun essai de charge concurrente (plusieurs patients, plusieurs medecins simultanes) n'est revendique pour ce prototype.
- Comparaison : une plateforme de teleconsultation certifiee (ex. Doctolib, Qare) ajoute une authentification forte, une architecture multi-tenant et un hebergement de donnees de sante agree, absents ici par choix de perimetre pedagogique ; SahaLink demontre le parcours fonctionnel complet, pas une alternative a ces plateformes.

## Resultat attendu de l'automatisation

Le test `tests/test_api.py` (21 tests) controle V1 a V5 et V7 a V12 par API et WebSocket, ainsi que le relais de signalisation WebRTC entre le medecin et le patient authentifies. La video est une validation manuelle car elle demande deux navigateurs et des autorisations materiel. Le script de benchmark (`scripts/benchmark.py`) reproduit les mesures chiffrees ci-dessus.


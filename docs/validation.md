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
| V6 | Deux navigateurs, meme salle | Negociation video WebRTC | Flux local et distant actifs (procedure manuelle detaillee dans `README.md`, section *Testing the video call*) |

## Resultats chiffres (mesures reelles, bande de test FastAPI, machine locale)

Ces chiffres proviennent d'un script de benchmark execute localement contre l'API (`TestClient`), pas d'une estimation. Ils caracterisent le prototype, pas une charge de production.

| Indicateur | Protocole | Resultat |
|---|---|---|
| Taux de detection du cas degrade | 6 profils cliniques distincts (tension, SpO2, bradycardie, tachycardie, fievre, combinaison critique) envoyes un par un | **6/6 soit 100 %** |
| Taux de rejet des valeurs hors plage absolue | 3 entrees hors bornes Pydantic (tension 500, SpO2 150, temperature 60) | **3/3 soit 100 %** |
| Latence d'ecriture d'une mesure normale | 30 envois successifs d'une mesure normale | moyenne **65,4 ms**, mediane **47,5 ms**, min **28,9 ms**, max **223,1 ms** |
| Latence creation + diffusion d'une alerte | 6 mesures degradees | moyenne **42,9 ms**, min **30,5 ms**, max **78,6 ms** |
| Latence d'acquittement d'une alerte | 10 cycles creation puis acquittement | moyenne **58,1 ms**, min **28,2 ms**, max **123,0 ms** |

## Discussion et limites des resultats

- La latence mesuree inclut le serveur de test en memoire sans reseau ; elle minore la latence reelle sur un reseau mobile ou avec PostgreSQL distant.
- L'ecart entre la mediane (47,5 ms) et le maximum (223,1 ms) sur l'ecriture normale vient de la premiere requete qui initialise la connexion SQLite ; en excluant ce demarrage a froid, la latence se stabilise sous 50 ms.
- Le taux de detection de 100 % est attendu car les regles de seuil sont deterministes et codees en dur (`app/main.py::alert_for`) : il mesure la correction de l'implementation, pas une sensibilite clinique au sens d'un dispositif medical valide.
- Aucun essai de charge concurrente (plusieurs patients, plusieurs medecins simultanes) n'est revendique pour ce prototype.
- Comparaison : une plateforme de teleconsultation certifiee (ex. Doctolib, Qare) ajoute une authentification forte, une architecture multi-tenant et un hebergement de donnees de sante agree, absents ici par choix de perimetre pedagogique ; SahaLink demontre le parcours fonctionnel complet, pas une alternative a ces plateformes.

## Resultat attendu de l'automatisation

Le test `tests/test_api.py` controle V1, V2, V3, V4 et V5 par API, ainsi que la relance de signalisation WebRTC entre deux pairs. La video est une validation manuelle car elle demande deux navigateurs et des autorisations materiel. Le script de benchmark (`scripts/benchmark.py`) reproduit les mesures chiffrees ci-dessus.


# Protocole de validation

## Objectif

Vérifier le fonctionnement de bout en bout, y compris un cas dégradé, avec des résultats chiffrables.

## Scénarios

| ID | Action | Résultat attendu | Indicateur |
|---|---|---|---|
| V1 | Ouvrir `/api/health` | Service disponible | HTTP 200 |
| V2 | Envoyer une mesure normale | Mesure dans l'historique, sans alerte | 1 écriture, 0 alerte |
| V3 | Envoyer SpO2 89 % | Alerte critique créée et visible | 1 alerte, WebSocket diffuse |
| V4 | Acquitter l'alerte | L'état passe à `acknowledged` | 1 modification |
| V5 | Envoyer une valeur hors plage API | Rejet de la mesure | HTTP 422 |
| V6 | Médecin et patient connectés dans deux fenêtres, le médecin démarre, le patient accepte l'invitation | Négociation vidéo WebRTC | Flux local et distant actifs (procédure manuelle détaillée dans `README.md`, section *Testing the full workflow*) |
| V7 | Appel d'une route de santé sans session | Accès refusé | HTTP 401 |
| V8 | Le patient lit les alertes, acquitte une alerte ou lit un autre dossier | Accès refusé | HTTP 403 |
| V9 | Le médecin démarre une téléconsultation avant le consentement du patient | Démarrage bloqué | HTTP 409 |
| V10 | Le médecin démarre une téléconsultation après consentement | Invitation reçue en temps réel par le patient | Événement `invitation` sur `/ws/events` |
| V11 | Connexion a une salle vidéo sans jeton valide ou par un tiers | Connexion refusée | `auth-failed` ou `forbidden` |
| V12 | Le médecin termine la consultation | Le patient est notifié, la salle est fermée | Événement `consultation-ended`, plus de consultation active |
| V13 | Le patient donne son consentement ou envoie une mesure normale | Le tableau de bord du médecin se met à jour sans rechargement | Événements `consent` et `vital` sur `/ws/events`, jamais envoyés au patient |
| V14 | Un visiteur crée un compte patient avec des données valides | Compte créé, session ouverte, le médecin voit le nouveau patient sans recharger | HTTP 201, événement `patient-registered` |
| V15 | Inscription avec identifiant ou nom invalide, nom contenant du balisage, mot de passe trop court, identifiant déjà pris, ou tentative de choisir le rôle médecin | Compte refusé ; le rôle reste toujours patient | HTTP 422 ou 409 ; aucun compte médecin créé |
| V16 | Le médecin ouvre la liste des patients puis le tableau de bord d'un patient précis ; un patient tente la même chose | Liste et tableau de bord corrects par patient ; patient refusé | HTTP 200 pour le médecin, 403 pour le patient, 404 pour un dossier inconnu |
| V17 | Huit connexions échouées de suite, puis inscriptions répétées depuis la même adresse | Verrouillage temporaire de la connexion, plafond d'inscriptions | HTTP 429 |
| V18 | Chargement de la page et injection d'un nom contenant un script | En-têtes de sécurité présents, script inerte affiché comme texte, scripts et connexions externes bloqués | En-tête `Content-Security-Policy`, test manuel dans le navigateur |
| V19 | Le médecin démarre une consultation avec un second patient alors qu'une est déjà ouverte | L'ancienne consultation est fermée et son patient prévenu | Événement `consultation-ended` puis `invitation` |
| V20 | Requête HTTPS derrière un proxy, puis requête HTTP avec l'imposition de HTTPS activée | En-tête HSTS sur HTTPS ; redirection 308 vers HTTPS sur HTTP (sauf santé du service et hôtes locaux) | En-tête `Strict-Transport-Security`, HTTP 308 |

## Résultats chiffrés (mesures réelles, bande de test FastAPI, machine locale)

Ces chiffres proviennent d'un script de benchmark exécuté localement contre l'API (`TestClient`), pas d'une estimation. Ils caractérisent le prototype, pas une charge de production. Depuis l'ajout de l'authentification, chaque requête inclut la vérification de la session (une lecture SQLite supplémentaire) : le patient envoie les mesures, le médecin acquitte les alertes.

| Indicateur | Protocole | Résultat |
|---|---|---|
| Taux de détection du cas dégradé | 6 profils cliniques distincts (tension, SpO2, bradycardie, tachycardie, fièvre, combinaison critique) envoyés un par un | **6/6 soit 100 %** |
| Taux de rejet des valeurs hors plage absolue | 3 entrées hors bornes Pydantic (tension 500, SpO2 150, température 60) | **3/3 soit 100 %** |
| Latence d'écriture d'une mesure normale | 30 envois successifs d'une mesure normale, session patient | moyenne **44,5 ms**, médiane **30,9 ms**, min **24,0 ms**, max **118,7 ms** |
| Latence création + diffusion d'une alerte | 6 mesures dégradées, session patient | moyenne **25,8 ms**, min **23,4 ms**, max **28,2 ms** |
| Latence d'acquittement d'une alerte | 10 cycles création puis acquittement, session médecin | moyenne **28,2 ms**, min **25,3 ms**, max **33,3 ms** |

## Discussion et limites des résultats

- La latence mesurée inclut le serveur de test en mémoire sans réseau ; elle minore la latence réelle sur un réseau mobile ou avec PostgreSQL distant.
- Les mesures varient fortement d'une exécution à l'autre sur un poste chargé : un premier passage le même jour, avec d'autres traitements lourds en cours sur la machine, donnait une moyenne de 178 ms pour l'écriture normale. Le tableau ci-dessus correspond à une machine moins chargée ; un protocole plus rigoureux répéterait le benchmark et publierait la médiane des exécutions.
- L'écart entre la médiane (30,9 ms) et le maximum (118,7 ms) sur l'écriture normale vient de la première requête qui initialise la connexion SQLite.
- Le taux de détection de 100 % est attendu car les règles de seuil sont déterministes et codées en dur (`app/main.py::alert_for`) : il mesure la correction de l'implémentation, pas une sensibilité clinique au sens d'un dispositif médical valide.
- Aucun essai de charge concurrente (plusieurs patients, plusieurs médecins simultanés) n'est revendiqué pour ce prototype.
- Comparaison : une plateforme de téléconsultation certifiée (ex. Doctolib, Qare) ajoute une authentification forte, une architecture multi-tenant et un hébergement de données de santé agréé, absents ici par choix de périmètre pédagogique ; SahaLink démontre le parcours fonctionnel complet, pas une alternative à ces plateformes.

## Résultat attendu de l'automatisation

Le test `tests/test_api.py` (37 tests) contrôle V1 à V5 et V7 à V17, V19 et V20 par API et WebSocket, ainsi que le relais de signalisation WebRTC entre le médecin et le patient authentifiés. La vidéo est une validation manuelle car elle demande deux navigateurs et des autorisations matériel. Le script de benchmark (`scripts/benchmark.py`) reproduit les mesures chiffrées ci-dessus.

Le script `scripts/smoke_test.py` rejoue tout le parcours médecin-patient (connexion, refus, consentement, alerte, invitation, signalisation, fin) contre n'importe quelle adresse, y compris le lien public : il a été exécuté avec succès sur le serveur local et sur le lien public Cloudflare. Il ne vérifie pas la capture vidéo réelle.


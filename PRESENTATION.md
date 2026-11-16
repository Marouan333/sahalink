# Presentation orale - SahaLink

## Slide 1 - Problematique

Comment permettre le suivi de constantes a distance et une teleconsultation, tout en rendant visible une situation clinique qui demande l'attention du medecin ?

## Slide 2 - Contexte et acteurs

Etablissement cible : service de cardiologie ou de medecine generale. Acteurs : patient suivi pour hypertension, medecin, plateforme de teleconsultation. Probleme : retard possible dans la detection d'une constante anormale entre deux visites.

## Slide 3 - Solution proposee

SahaLink offre une interface patient pour le consentement et la saisie des constantes, et une interface medecin pour visualiser l'historique et les alertes. Une salle WebRTC permet une consultation video de demonstration.

## Slide 4 - Architecture et standards

Afficher le schema de `docs/architecture.md`. Expliquer REST pour les donnees, WebSocket pour les alertes et la signalisation, et WebRTC pour les medias. Souligner que le flux video ne passe pas par le serveur applicatif.

## Slide 5 - Modele de donnees et donnees simulees

Entites : Patient, Consentement, Constante, Alerte. Les donnees sont fictives, tracees par source et horodatees. Aucun dossier medical reel n'est utilise.

## Slide 6 - Demonstration patient-medecin

1. Le patient enregistre son consentement.
2. Il envoie une mesure normale.
3. Il active le cas degrade avec SpO2 89 %.
4. Le medecin voit l'alerte en direct, consulte les constantes puis l'acquitte.
5. Les deux acteurs rejoignent la meme salle WebRTC.

## Slide 7 - Validation

Montrer le tableau de `docs/validation.md`, le test automatisé et le cas degrade. Indiquer 100 % de detection sur les seuils codes et les limites de l'experience.

## Slide 8 - Securite et conformite

Consentement explicite, donnees simulees, validation des entrees, medias WebRTC chiffres et absence d'enregistrement video. Citer loi 09-08 et loi 131-13, puis presenter les limites avant tout deploiement reel.

## Slide 9 - Limites et prochaines etapes

Authentification forte, PostgreSQL, HTTPS, audit, validation clinique des seuils, hebergement conforme et tests de charge. Conclure : le prototype valide le parcours complet sans pretendre remplacer une plateforme medicale certifiee.


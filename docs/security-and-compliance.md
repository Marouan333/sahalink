# Sécurité, confidentialité et conformité

## Mesures effectivement implémentées dans le prototype

- Données strictement fictives et locales.
- Authentification par identifiant et mot de passe ; les mots de passe sont stockés hachés (PBKDF2-SHA256, 200 000 itérations, sel aléatoire par compte) et comparés en temps constant.
- Sessions serveur de 8 heures : le jeton aléatoire n'est conservé en base que sous forme d'empreinte SHA-256, et la déconnexion le revoque immédiatement.
- Contrôle d'accès par rôle sur chaque route : le patient n'accède qu'à son propre dossier, seul le médecin consulte et acquitte les alertes, seul le patient concerné donne ou retiré son consentement.
- Consentement explicite, accepté ou refusé, avec objet et horodatage ; une téléconsultation ne peut pas démarrer sans consentement valide du patient (refus HTTP 409).
- WebSockets authentifiés : le jeton est transmis dans le premier message, jamais dans l'URL, et l'origine de la page est vérifiée pour bloquer le détournement de WebSocket depuis un autre site.
- Inscription patient contrôlée : le rôle est toujours « patient » (jamais choisi par le client), identifiant et nom validés côté serveur, noms contenant du balisage refusés, mot de passe d'au moins 8 caractères, 10 inscriptions par heure et par adresse, 200 comptes au maximum.
- Verrouillage après échecs : 8 connexions échouées en 5 minutes pour un même couple adresse et identifiant entraînent un refus temporaire (HTTP 429).
- Protection XSS : les noms saisis par les patients arrivent sur l'écran du médecin ; ils sont validés, échappés avant tout affichage, et une politique de sécurité du contenu (CSP) interdit les scripts en ligne, les scripts externes et les connexions vers d'autres hôtes. En-têtes complémentaires : `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, `Permissions-Policy` limitée à la caméra et au microphone.
- Salle vidéo réservée : seul le médecin et le patient de la consultation ouverte peuvent y entrer, deux participants au maximum ; le code de salle est aléatoire et généré par le serveur.
- Validation serveur des valeurs de constantes.
- WebRTC chiffre les médias entre pairs avec DTLS/SRTP lorsque le navigateur établit la connexion.
- Aucune vidéo n'est enregistrée par l'application.
- Les alertes peuvent être acquittées pour démontrer le suivi organisationnel.

## Limites connues

Ce prototype n'est pas un dispositif médical ni une plateforme prête à recevoir des données réelles. Avant tout usage réel, il faut au minimum :

- une authentification multifacteur, un verrouillage partagé entre serveurs (celui du prototype est en mémoire d'un seul serveur) et un journal d'audit inviolable des accès ;
- un jeton de session en cookie `HttpOnly` et `Secure` plutôt que dans le stockage de l'onglet : le prototype garde le jeton par onglet pour permettre de démontrer le médecin et le patient dans un même navigateur, au prix d'une exposition plus forte en cas de faille XSS ;
- des comptes réels gérés par l'établissement, avec vérification de l'identité et du statut de médecin, à la place des comptes de démonstration (mot de passe public) et de l'inscription libre des patients ;
- HTTPS, chiffrement des données au repos, rotation des secrets et sauvegardes ;
- une analyse d'impact, des politiques de conservation et l'exercice des droits des personnes ;
- une validation clinique des seuils et une gouvernance médicale ;
- un hébergement, des contrats et des procédures conformes aux exigences applicables.

## Cadre à présenter

Deux textes marocains encadrent le projet :

- la **loi 09-08** relative à la protection des personnes physiques à l'égard du traitement des données à caractère personnel (dahir n° 1-09-15 du 18 février 2009, contrôle par la CNDP) ;
- la **loi 131-13** relative à l'exercice de la médecine (dahir n° 1-15-26 du 19 février 2015, B.O. n° 6344 du 19 mars 2015), dont la section 4 est consacrée à la télémédecine.

Les exigences concrètes doivent être validées avec les sources officielles et les responsables compétents avant un déploiement réel.

## Norme technique et institutionnelle du sujet

Le sujet impose trois références normatives, toutes trois effectivement traitées dans ce prototype :

| Norme | Application dans SahaLink |
|---|---|
| **Technologie WebRTC** | Flux média patient-médecin en pair-à-pair, chiffré DTLS/SRTP, signalisation SDP/ICE relayée par `/ws/signaling/{room}` après authentification (voir `docs/architecture.md`). |
| **Rapport de l'OMS, Global Observatory for eHealth** (*Telemedicine: opportunities and developments in Member States*, série Global Observatory for eHealth, vol. 2, 2010) | Référence institutionnelle de contexte sur la télémédecine dans les États membres de l'OMS. SahaLink s'inscrit dans la définition de l'OMS : usage des technologies de l'information et de la communication pour échanger à distance des informations utiles au diagnostic, au traitement et au suivi, quand la distance est un facteur critique. Le prototype couvre deux usages : la consultation vidéo patient-médecin et le suivi à distance de constantes avec alerte. |
| **Loi marocaine 131-13**, section 4 *De la télémédecine* (articles 99 à 102) | Voir le détail article par article ci-dessous. |

### Loi 131-13 : articles 99 à 102 et mise en œuvre

Texte lu directement dans le Bulletin officiel n° 6344 (copie scannée du site du Ministère de la Santé).

| Article | Ce que dit la loi | Mise en œuvre dans SahaLink | Limite connue |
|---|---|---|---|
| **99** | Les médecins et les établissements de santé peuvent recourir à la télémédecine, dans le respect de la protection des données personnelles et de la confidentialité du dossier médical. La télémédecine permet notamment un diagnostic, un avis spécialisé ou *une surveillance de l'état des patients*. | Suivi à distance des constantes avec alertes et téléconsultation vidéo. Confidentialité : authentification, accès par rôle, WebSockets authentifiés, salle vidéo réservée au médecin et au patient. | Chiffrement des données au repos et HTTPS maîtrisé par l'hébergeur à prévoir pour un usage réel. |
| **100** | Les actes de télémédecine, ainsi que l'identité et les qualifications des médecins intervenants, sont consignés dans le dossier médical du patient. | Table `consultations` (médecin, patient, début, fin), plus constantes, alertes et consentements horodatés. | Les qualifications du médecin (spécialité, numéro d'ordre) ne sont pas modélisées. |
| **101** | Aucun acte de télémédecine sans consentement exprès, libre et éclairé du patient, écrit par tout moyen y compris électronique ; droit de refus ; pour un mineur ou une personne protégée, consentement du tuteur ou du représentant légal. | Consentement électronique horodaté avec finalité ; acceptation ou refus enregistrés ; démarrage de la téléconsultation refusé tant que le dernier consentement n'est pas une acceptation (HTTP 409). | Pas de gestion du tuteur légal ni de consentement écrit signé. |
| **102** | Les actes de télémédecine et leurs conditions techniques sont fixés par voie réglementaire. | Renvoie à un texte réglementaire que le prototype ne traite pas. | À vérifier auprès des sources officielles avant tout déploiement. |

Sources officielles de référence :

- [CNDP - textes et lois, loi 09-08](https://www.cndp.ma/textes-et-lois/)
- [Ministère de la Santé - loi 131-13 relative à l'exercice de la médecine](https://www.sante.gov.ma/Reglementation/PRATIQUEDESMETIERSDESANTEDANSLESECTEURPRIVE/Loi_131.13_Fr.pdf)
- [OMS - Global Observatory for eHealth](https://www.who.int/observatories/global-observatory-for-ehealth) (page de l'observatoire, qui liste les enquêtes mondiales dont celle de 2009)

## Consentement dans le scénario

Le consentement est une étape visible avant la saisie de constantes. Le texte indique la finalité, le caractère pédagogique, l'utilisation de données simulées et la possibilité de ne pas accepter. Pour un usage réel, l'information patient, les finalités, la durée de conservation, les destinataires et les droits doivent être plus détaillés.


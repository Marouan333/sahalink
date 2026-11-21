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
- Transport sécurisé : avec `SAHALINK_FORCE_HTTPS=1`, toute requête HTTP non locale est redirigée vers HTTPS (code 308, sauf `/api/health`) ; l'en-tête `Strict-Transport-Security` est envoyé dès qu'une requête arrive en HTTPS, directement ou derrière un proxy ou un tunnel TLS (`X-Forwarded-Proto`). Le chiffrement TLS lui-même est assuré par l'hébergeur ou le tunnel (Cloudflare pour le lien de démonstration), pas par l'application.
- Aucune vidéo n'est enregistrée par l'application.
- Les alertes peuvent être acquittées pour démontrer le suivi organisationnel.

## Limites connues

Ce prototype n'est pas un dispositif médical ni une plateforme prête à recevoir des données réelles. Avant tout usage réel, il faut au minimum :

- une authentification multifacteur, un verrouillage partagé entre serveurs (celui du prototype est en mémoire d'un seul serveur) et un journal d'audit inviolable des accès ;
- un jeton de session en cookie `HttpOnly` et `Secure` plutôt que dans le stockage de l'onglet : le prototype garde le jeton par onglet pour permettre de démontrer le médecin et le patient dans un même navigateur, au prix d'une exposition plus forte en cas de faille XSS ;
- des comptes réels gérés par l'établissement, avec vérification de l'identité et du statut de médecin, à la place des comptes de démonstration (mot de passe public) et de l'inscription libre des patients ;
- chiffrement des données au repos, rotation des secrets et sauvegardes (le TLS reste à la charge de l'hébergeur ou du tunnel : l'application impose HTTPS et HSTS mais ne gère pas de certificat) ;
- une analyse d'impact, des politiques de conservation et l'exercice des droits des personnes ;
- une validation clinique des seuils et une gouvernance médicale ;
- un hébergement, des contrats et des procédures conformes aux exigences applicables.

## Cadre à présenter

Deux textes marocains encadrent le projet :

- la **loi 09-08** relative à la protection des personnes physiques à l'égard du traitement des données à caractère personnel (dahir n° 1-09-15 du 18 février 2009, contrôle par la CNDP) ;
- la **loi 131-13** relative à l'exercice de la médecine (dahir n° 1-15-26 du 19 février 2015, B.O. n° 6344 du 19 mars 2015), dont la section 4 est consacrée à la télémédecine.

Les articles utiles de la loi 09-08 et les constats du rapport de l'OMS sont détaillés plus bas, après lecture des textes. Les exigences concrètes doivent encore être validées avec les responsables compétents (formalités CNDP) avant un déploiement réel.

## Norme technique et institutionnelle du sujet

Le sujet impose trois références normatives, toutes trois effectivement traitées dans ce prototype :

| Norme | Application dans SahaLink |
|---|---|
| **Technologie WebRTC** | Flux média patient-médecin en pair-à-pair, chiffré DTLS/SRTP, signalisation SDP/ICE relayée par `/ws/signaling/{room}` après authentification (voir `docs/architecture.md`). |
| **Rapport de l'OMS, Global Observatory for eHealth** (*Telemedicine: opportunities and developments in Member States*, série Global Observatory for eHealth, vol. 2, 2010) | Référence institutionnelle de contexte sur la télémédecine dans les États membres de l'OMS. SahaLink s'inscrit dans la définition de l'OMS : usage des technologies de l'information et de la communication pour échanger à distance des informations utiles au diagnostic, au traitement et au suivi, quand la distance est un facteur critique. Le prototype couvre deux usages : la consultation vidéo patient-médecin et le suivi à distance de constantes avec alerte. |
| **Loi marocaine 131-13**, section 4 *De la télémédecine* (articles 99 à 102) | Voir le détail article par article ci-dessous. |

### Constats du rapport de l'OMS exploités

Rapport lu en entier : *Telemedicine: opportunities and developments in Member States. Report on the second global survey on eHealth*, Global Observatory for eHealth series, vol. 2, OMS, 2010 (ISBN 978 92 4 156414 4).

| Constat du rapport | Comment SahaLink en tient compte |
|---|---|
| Définition de l'OMS (section 1.1) : prestation de soins à distance, par des professionnels de santé, avec les TIC. Quatre éléments : un soutien clinique, le dépassement de la distance, l'usage des TIC, l'amélioration des résultats de santé. | Soutien clinique : alertes sur seuils. Distance : consultation vidéo. TIC : WebRTC et WebSockets. Résultats : détection plus rapide d'une constante anormale entre deux visites. |
| Résumé exécutif (p. 7) : 114 pays ont répondu (59 % des États membres) ; la téléradiologie est le domaine le plus établi (33 %) ; environ 30 % des pays ont une agence nationale de télémédecine. | Contexte pour la section de cadrage : la téléconsultation avec suivi de constantes est un usage encore peu documenté par l'enquête. |
| Résumé exécutif (p. 7) : seuls 20 % des pays déclarent une évaluation publiée depuis 2006 ; l'évaluation est jugée essentielle. | Le projet fournit une évaluation chiffrée : taux de détection, taux de rejet, latences, tests automatisés (`docs/validation.md`). |
| Résumé exécutif (p. 7) : le coût perçu est l'obstacle le plus cité ; les pays développés citent davantage les questions juridiques de vie privée et de confidentialité. | Choix d'une pile légère, sans installation, et traitement explicite de la confidentialité et du consentement. |
| Revue de la littérature (p. 11) : les obstacles juridiques incluent le manque de règles sur la confidentialité lors du transfert, du stockage et du partage des données, l'authentification des professionnels de santé et la responsabilité médicale. | Transfert protégé (HTTPS, HSTS, WebSockets authentifiés), accès par rôle, consentement bloquant. Limite : le statut de médecin n'est pas vérifié (compte de démonstration). |
| Résumé exécutif (p. 7) : la télémédecine doit renforcer les autres services de santé, non les concurrencer. | SahaLink complète les visites physiques : il signale les dérives entre deux consultations. |

### Loi 09-08 : articles lus et mise en œuvre

Texte lu directement dans la version officielle publiée par le Ministère de la Justice (dahir n° 1-09-15 du 18 février 2009, avec les renvois au décret d'application n° 2-09-165). Seuls les articles utiles au projet sont repris.

| Article | Ce que dit la loi | Mise en œuvre dans SahaLink | Limite connue |
|---|---|---|---|
| **1, alinéa 3** | Les « données sensibles » incluent les données relatives à la santé. | Les constantes et le suivi sont des données sensibles : ils justifient les mesures ci-dessous. Les données du prototype sont fictives. | Aucune donnée réelle ne doit être saisie. |
| **3** | Données traitées loyalement, collectées pour des finalités déterminées, explicites et légitimes, adéquates et non excessives, exactes, conservées pour une durée limitée. | Finalité écrite dans chaque consentement ; seules quelques constantes, le nom, l'année de naissance et le motif du suivi sont collectés ; bornes physiologiques contre les valeurs fausses. | Pas de durée de conservation ni de suppression automatique. |
| **4** | Le traitement exige que la personne ait donné indubitablement son consentement ; communication à un tiers soumise à son consentement préalable. | Consentement explicite, horodaté, accepté ou refusé ; la téléconsultation est refusée sans acceptation (HTTP 409) ; aucune donnée n'est transmise à un tiers. | Pas de consentement écrit signé. |
| **5** | Information préalable de la personne : identité du responsable, finalités, destinataires, droits. | Le texte de consentement donne la finalité et le caractère simulé des données. | L'identité du responsable de traitement et la liste des droits ne sont pas affichées. |
| **7, 8, 9** | Droits d'accès, de rectification et d'opposition. | Le patient consulte son propre historique et peut retirer son consentement. | Pas de fonction de rectification ni de suppression du compte. |
| **12, 21, 22** | Les données de santé exigent une autorisation préalable de la CNDP, ou une simple déclaration lorsque le traitement a pour seule finalité les soins et est fait par un praticien tenu au secret professionnel. | Sans objet pour un prototype à données fictives. | Toute mise en service réelle exige ces formalités auprès de la CNDP. |
| **23** | Mesures techniques et organisationnelles appropriées contre l'accès non autorisé et la diffusion, notamment lorsque des données transitent par un réseau. | Mots de passe hachés (PBKDF2), jetons stockés hachés, rôles contrôlés par le serveur, HTTPS imposé et HSTS (voir ci-dessous). | Pas de chiffrement des données au repos. |
| **24** | Pour les données de santé, huit contrôles : entrée, supports, insertion, utilisation, accès, transmission, vérification a posteriori, transport. | Voir le tableau ci-dessous. | Le journal d'audit est partiel. |

Détail de l'article 24 (données relatives à la santé) :

| Contrôle (art. 24, 1) | Mesure dans SahaLink |
|---|---|
| a, b : entrée dans les installations, supports de données | Relève de l'hébergeur ; hors périmètre du prototype. |
| c : insertion | Seuls un patient (pour son dossier) ou le médecin peuvent ajouter une constante ; valeurs validées côté serveur. |
| d : utilisation du système | Toute route exige une session authentifiée. |
| e : accès | Rôles médecin et patient contrôlés sur chaque route ; un patient ne voit que son dossier (HTTP 403 sinon). |
| f : transmission | WebSockets authentifiés avec contrôle d'origine ; salle vidéo réservée aux deux participants de la consultation. |
| g : vérification a posteriori (quelles données, quand, pour qui) | Constantes, consentements, alertes et consultations horodatés et rattachés au patient ; pas de journal d'audit complet des lectures. |
| h : transport | TLS : HTTPS imposé par la variable `SAHALINK_FORCE_HTTPS=1` (redirection 308) et en-tête HSTS dès qu'une requête arrive en HTTPS ; média chiffré par WebRTC (DTLS/SRTP). Testé. |

### Loi 131-13 : articles 99 à 102 et mise en œuvre

Texte lu directement dans le Bulletin officiel n° 6344 (copie scannée du site du Ministère de la Santé).

| Article | Ce que dit la loi | Mise en œuvre dans SahaLink | Limite connue |
|---|---|---|---|
| **99** | Les médecins et les établissements de santé peuvent recourir à la télémédecine, dans le respect de la protection des données personnelles et de la confidentialité du dossier médical. La télémédecine permet notamment un diagnostic, un avis spécialisé ou *une surveillance de l'état des patients*. | Suivi à distance des constantes avec alertes et téléconsultation vidéo. Confidentialité : authentification, accès par rôle, WebSockets authentifiés, salle vidéo réservée au médecin et au patient. | Chiffrement des données au repos à prévoir ; TLS fourni par l'hébergeur ou le tunnel. |
| **100** | Les actes de télémédecine, ainsi que l'identité et les qualifications des médecins intervenants, sont consignés dans le dossier médical du patient. | Table `consultations` (médecin, patient, début, fin), plus constantes, alertes et consentements horodatés. | Les qualifications du médecin (spécialité, numéro d'ordre) ne sont pas modélisées. |
| **101** | Aucun acte de télémédecine sans consentement exprès, libre et éclairé du patient, écrit par tout moyen y compris électronique ; droit de refus ; pour un mineur ou une personne protégée, consentement du tuteur ou du représentant légal. | Consentement électronique horodaté avec finalité ; acceptation ou refus enregistrés ; démarrage de la téléconsultation refusé tant que le dernier consentement n'est pas une acceptation (HTTP 409). | Pas de gestion du tuteur légal ni de consentement écrit signé. |
| **102** | Les actes de télémédecine et leurs conditions techniques sont fixés par voie réglementaire. | Renvoie à un texte réglementaire que le prototype ne traite pas. | À vérifier auprès des sources officielles avant tout déploiement. |

Sources officielles de référence :

- [Ministère de la Justice - loi 09-08, texte officiel avec décret d'application](https://adala.justice.gov.ma/api/uploads/2024/04/30/Protection%20des%20personnes%20physiques-1714464099884.pdf)
- [CNDP - textes et lois, loi 09-08](https://www.cndp.ma/textes-et-lois/)
- [Ministère de la Santé - loi 131-13 relative à l'exercice de la médecine](https://www.sante.gov.ma/Reglementation/PRATIQUEDESMETIERSDESANTEDANSLESECTEURPRIVE/Loi_131.13_Fr.pdf)
- [OMS - rapport complet Telemedicine: opportunities and developments in Member States (2010)](https://www.afro.who.int/sites/default/files/2017-06/AHO-goe_telemedicine_2010_0.pdf)
- [OMS - Global Observatory for eHealth](https://www.who.int/observatories/global-observatory-for-ehealth)

## Consentement dans le scénario

Le consentement est une étape visible avant la saisie de constantes. Le texte indique la finalité, le caractère pédagogique, l'utilisation de données simulées et la possibilité de ne pas accepter. Pour un usage réel, l'information patient, les finalités, la durée de conservation, les destinataires et les droits doivent être plus détaillés.


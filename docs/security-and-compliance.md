# Securite, confidentialite et conformite

## Mesures effectivement implementees dans le prototype

- Donnees strictement fictives et locales.
- Authentification par identifiant et mot de passe ; les mots de passe sont stockes haches (PBKDF2-SHA256, 200 000 iterations, sel aleatoire par compte) et compares en temps constant.
- Sessions serveur de 8 heures : le jeton aleatoire n'est conserve en base que sous forme d'empreinte SHA-256, et la deconnexion le revoque immediatement.
- Controle d'acces par role sur chaque route : le patient n'accede qu'a son propre dossier, seul le medecin consulte et acquitte les alertes, seul le patient concerne donne ou retire son consentement.
- Consentement explicite, accepte ou refuse, avec objet et horodatage ; une teleconsultation ne peut pas demarrer sans consentement valide du patient (refus HTTP 409).
- WebSockets authentifies : le jeton est transmis dans le premier message, jamais dans l'URL, et l'origine de la page est verifiee pour bloquer le detournement de WebSocket depuis un autre site.
- Salle video reservee : seul le medecin et le patient de la consultation ouverte peuvent y entrer, deux participants au maximum ; le code de salle est aleatoire et genere par le serveur.
- Validation serveur des valeurs de constantes.
- WebRTC chiffre les medias entre pairs avec DTLS/SRTP lorsque le navigateur etablit la connexion.
- Aucune video n'est enregistree par l'application.
- Les alertes peuvent etre acquittees pour demonstrer le suivi organisationnel.

## Limites connues

Ce prototype n'est pas un dispositif medical ni une plateforme prete a recevoir des donnees reelles. Avant tout usage reel, il faut au minimum :

- une authentification multifacteur, un verrouillage apres echecs repetes et un journal d'audit inviolable des acces ;
- un jeton de session en cookie `HttpOnly` et `Secure` plutot que dans le stockage de l'onglet : le prototype garde le jeton par onglet pour permettre de demontrer le medecin et le patient dans un meme navigateur, au prix d'une exposition plus forte en cas de faille XSS ;
- des comptes reels geres par l'etablissement, a la place des deux comptes de demonstration dont le mot de passe est public ;
- HTTPS, chiffrement des donnees au repos, rotation des secrets et sauvegardes ;
- une analyse d'impact, des politiques de conservation et l'exercice des droits des personnes ;
- une validation clinique des seuils et une gouvernance medicale ;
- un hebergement, des contrats et des procedures conformes aux exigences applicables.

## Cadre a presenter

Deux textes marocains encadrent le projet :

- la **loi 09-08** relative a la protection des personnes physiques a l'egard du traitement des donnees a caractere personnel (dahir n° 1-09-15 du 18 fevrier 2009, controle par la CNDP) ;
- la **loi 131-13** relative a l'exercice de la medecine (dahir n° 1-15-26 du 19 fevrier 2015, B.O. n° 6344 du 19 mars 2015), dont la section 4 est consacree a la telemedecine.

Les exigences concretes doivent etre validees avec les sources officielles et les responsables competents avant un deploiement reel.

## Norme technique et institutionnelle du sujet

Le sujet impose trois references normatives, toutes trois effectivement traitees dans ce prototype :

| Norme | Application dans SahaLink |
|---|---|
| **Technologie WebRTC** | Flux media patient-medecin en pair-a-pair, chiffre DTLS/SRTP, signalisation SDP/ICE relayee par `/ws/signaling/{room}` apres authentification (voir `docs/architecture.md`). |
| **Rapport de l'OMS, Global Observatory for eHealth** (*Telemedicine: opportunities and developments in Member States*, serie Global Observatory for eHealth, vol. 2, 2010) | Reference institutionnelle de contexte sur la telemedecine dans les Etats membres de l'OMS. SahaLink s'inscrit dans la definition de l'OMS : usage des technologies de l'information et de la communication pour echanger a distance des informations utiles au diagnostic, au traitement et au suivi, quand la distance est un facteur critique. Le prototype couvre deux usages : la consultation video patient-medecin et le suivi a distance de constantes avec alerte. |
| **Loi marocaine 131-13**, section 4 *De la telemedecine* (articles 99 a 102) | Voir le detail article par article ci-dessous. |

### Loi 131-13 : articles 99 a 102 et mise en oeuvre

Texte lu directement dans le Bulletin officiel n° 6344 (copie scannee du site du Ministere de la Sante).

| Article | Ce que dit la loi | Mise en oeuvre dans SahaLink | Limite connue |
|---|---|---|---|
| **99** | Les medecins et les etablissements de sante peuvent recourir a la telemedecine, dans le respect de la protection des donnees personnelles et de la confidentialite du dossier medical. La telemedecine permet notamment un diagnostic, un avis specialise ou *une surveillance de l'etat des patients*. | Suivi a distance des constantes avec alertes et teleconsultation video. Confidentialite : authentification, acces par role, WebSockets authentifies, salle video reservee au medecin et au patient. | Chiffrement des donnees au repos et HTTPS maitrise par l'hebergeur a prevoir pour un usage reel. |
| **100** | Les actes de telemedecine, ainsi que l'identite et les qualifications des medecins intervenants, sont consignes dans le dossier medical du patient. | Table `consultations` (medecin, patient, debut, fin), plus constantes, alertes et consentements horodates. | Les qualifications du medecin (specialite, numero d'ordre) ne sont pas modelisees. |
| **101** | Aucun acte de telemedecine sans consentement expres, libre et eclaire du patient, ecrit par tout moyen y compris electronique ; droit de refus ; pour un mineur ou une personne protegee, consentement du tuteur ou du representant legal. | Consentement electronique horodate avec finalite ; acceptation ou refus enregistres ; demarrage de la teleconsultation refuse tant que le dernier consentement n'est pas une acceptation (HTTP 409). | Pas de gestion du tuteur legal ni de consentement ecrit signe. |
| **102** | Les actes de telemedecine et leurs conditions techniques sont fixes par voie reglementaire. | Renvoie a un texte reglementaire que le prototype ne traite pas. | A verifier aupres des sources officielles avant tout deploiement. |

Sources officielles de reference :

- [CNDP - textes et lois, loi 09-08](https://www.cndp.ma/textes-et-lois/)
- [Ministere de la Sante - loi 131-13 relative a l'exercice de la medecine](https://www.sante.gov.ma/Reglementation/PRATIQUEDESMETIERSDESANTEDANSLESECTEURPRIVE/Loi_131.13_Fr.pdf)
- [OMS - Global Observatory for eHealth](https://www.who.int/observatories/global-observatory-for-ehealth) (page de l'observatoire, qui liste les enquetes mondiales dont celle de 2009)

## Consentement dans le scenario

Le consentement est une etape visible avant la saisie de constantes. Le texte indique la finalite, le caractere pedagogique, l'utilisation de donnees simulees et la possibilite de ne pas accepter. Pour un usage reel, l'information patient, les finalites, la duree de conservation, les destinataires et les droits doivent etre plus detailles.


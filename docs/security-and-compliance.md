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

La presentation cite la loi marocaine 09-08 relative a la protection des personnes physiques a l'egard du traitement des donnees a caractere personnel, ainsi que la loi 131-13 relative a l'exercice de la medecine et de la telemedecine. Les exigences concretes doivent etre validees avec les sources officielles et les responsables competents avant un deploiement reel.

## Norme technique et institutionnelle du sujet

Le sujet impose trois references normatives, toutes trois effectivement traitees dans ce prototype :

| Norme | Application dans SahaLink |
|---|---|
| **Technologie WebRTC** | Flux media patient-medecin en pair-a-pair, chiffre DTLS/SRTP, signalisation SDP/ICE relayee par `/ws/signaling/{room}` (voir `docs/architecture.md`). |
| **Rapport OMS, Global Observatory for eHealth** (serie *Telemedicine: opportunities and developments in Member States*, OMS, Geneve) | Sert de reference pour le perimetre fonctionnel retenu : continuite du suivi entre deux visites, teleconsultation synchrone video, et necessite d'un consentement explicite et d'une tracabilite des donnees echangees a distance, trois axes que le rapport identifie comme conditions de maturite d'un programme de telesante. Le prototype restreint volontairement son perimetre a ces axes plutot qu'a l'ensemble des 7 composantes du rapport (infrastructure, politique, financement, etc.), qui depassent le cadre d'un prototype pedagogique. |
| **Loi marocaine 131-13** relative a l'exercice de la medecine (telemedecine, art. 2 et 98 a 106) | Justifie l'exigence de consentement prealable du patient, l'identification des acteurs (patient, medecin) avant toute teleconsultation, et la tracabilite de l'acte via l'horodatage des constantes et des alertes. |

Sources officielles de reference :

- [CNDP - textes et lois, loi 09-08](https://www.cndp.ma/textes-et-lois/)
- [Ministere de la Sante - loi 131-13 relative a l'exercice de la medecine](https://www.sante.gov.ma/Reglementation/PRATIQUEDESMETIERSDESANTEDANSLESECTEURPRIVE/Loi_131.13_Fr.pdf)
- [OMS - Global Observatory for eHealth, Telemedicine: opportunities and developments in Member States](https://www.who.int/publications/i/item/9789241564144)

## Consentement dans le scenario

Le consentement est une etape visible avant la saisie de constantes. Le texte indique la finalite, le caractere pedagogique, l'utilisation de donnees simulees et la possibilite de ne pas accepter. Pour un usage reel, l'information patient, les finalites, la duree de conservation, les destinataires et les droits doivent etre plus detailles.


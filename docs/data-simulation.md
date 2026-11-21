# Données simulées

## Règle de projet

Le prototype ne contient aucune donnée de patient réel. Toutes les données sont fictives et locales.

## Jeu de démonstration

| Champ | Valeur initiale | Origine |
|---|---:|---|
| Patient | Amal El Idrissi, 54 ans | Persona fictive |
| Parcours | Suivi hypertension artérielle | Scénario pédagogique |
| Tension | 128 / 78 mmHg | Mesure simulée normale |
| Fréquence cardiaque | 72 bpm | Mesure simulée normale |
| SpO2 | 98 % | Mesure simulée normale |
| Température | 36.7 °C | Mesure simulée normale |

## Comptes de démonstration

Deux comptes fictifs sont créés automatiquement au premier démarrage (`app/database.py`). Ils ne correspondent à aucune personne réelle et leur mot de passe est public.

| Rôle | Identifiant | Nom affiché | Dossier lié |
|---|---|---|---|
| Médecin | `dr.benali` | Dr. Benali | aucun |
| Patient | `amal` | Amal El Idrissi | patient n° 1 |

Les patients qui s'inscrivent eux-mêmes créent un compte et un dossier supplémentaires (nom, année de naissance, motif du suivi : valeurs fictives saisies par le testeur ; aucun autre champ personnel n'est demandé). Ces comptes sont plafonnés à 200.

Les mots de passe sont stockés hachés (PBKDF2-SHA256, sel aléatoire par compte). Le patient, sa mesure de départ et les comptes sont générés une seule fois par le code de démarrage ; les mesures suivantes viennent de la saisie des testeurs (`source = manual`) ou du bouton « Simuler une alerte » (valeurs pré-remplies).

## Cas dégradé valide pendant la démonstration

Le bouton **Simuler une alerte** pré-remplit une mesure critique : tension 188/122 mmHg, fréquence cardiaque 138 bpm, SpO2 89 % et température 39.2 °C. L'envoi de cette mesure doit créer et diffuser une alerte clinique au médecin.

## Traçabilité

Chaque constante conserve sa source (`manual` ou `simulated`) et sa date. Chaque consentement et chaque alerte possèdent également un horodatage UTC.


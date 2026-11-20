# Donnees simulees

## Regle de projet

Le prototype ne contient aucune donnee de patient reel. Toutes les donnees sont fictives et locales.

## Jeu de demonstration

| Champ | Valeur initiale | Origine |
|---|---:|---|
| Patient | Amal El Idrissi, 54 ans | Persona fictive |
| Parcours | Suivi hypertension arterielle | Scenario pedagogique |
| Tension | 128 / 78 mmHg | Mesure simulee normale |
| Frequence cardiaque | 72 bpm | Mesure simulee normale |
| SpO2 | 98 % | Mesure simulee normale |
| Temperature | 36.7 deg C | Mesure simulee normale |

## Comptes de demonstration

Deux comptes fictifs sont crees automatiquement au premier demarrage (`app/database.py`). Ils ne correspondent a aucune personne reelle et leur mot de passe est public.

| Role | Identifiant | Nom affiche | Dossier lie |
|---|---|---|---|
| Medecin | `dr.benali` | Dr. Benali | aucun |
| Patient | `amal` | Amal El Idrissi | patient n° 1 |

Les mots de passe sont stockes hache (PBKDF2-SHA256, sel aleatoire par compte). Le patient, sa mesure de depart et les comptes sont generes une seule fois par le code de demarrage ; les mesures suivantes viennent de la saisie des testeurs (`source = manual`) ou du bouton « Simuler une alerte » (valeurs pre-remplies).

## Cas degrade valide pendant la demonstration

Le bouton **Simuler une alerte** pre-remplit une mesure critique : tension 188/122 mmHg, frequence cardiaque 138 bpm, SpO2 89 % et temperature 39.2 deg C. L'envoi de cette mesure doit creer et diffuser une alerte clinique au medecin.

## Traçabilite

Chaque constante conserve sa source (`manual` ou `simulated`) et sa date. Chaque consentement et chaque alerte possedent egalement un horodatage UTC.


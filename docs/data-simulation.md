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

## Cas degrade valide pendant la demonstration

Le bouton **Simuler une alerte** pre-remplit une mesure critique : tension 188/122 mmHg, frequence cardiaque 138 bpm, SpO2 89 % et temperature 39.2 deg C. L'envoi de cette mesure doit creer et diffuser une alerte clinique au medecin.

## Traçabilite

Chaque constante conserve sa source (`manual` ou `simulated`) et sa date. Chaque consentement et chaque alerte possedent egalement un horodatage UTC.


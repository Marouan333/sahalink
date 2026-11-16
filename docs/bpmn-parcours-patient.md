# Parcours patient (BPMN)

## Objectif

Formaliser le processus metier de bout en bout, avec un couloir par acteur (notation BPMN : evenement de depart en cercle fin, tache en rectangle, decision en losange, evenement de fin en cercle epais), incluant le cas degrade (constante hors seuil).

## Diagramme

```mermaid
flowchart TD
    subgraph Patient["Couloir : Patient"]
        A((Debut)) --> B[Consulter le texte de consentement]
        B --> C{Consentement accepte ?}
        C -- Non --> Z1((Fin : acces refuse))
        C -- Oui --> D[Saisir une constante physiologique]
        D --> E[Envoyer la mesure a l'API]
    end

    subgraph Systeme["Couloir : Systeme SahaLink"]
        E --> F[Valider les bornes physiologiques - Pydantic]
        F --> G{Valeur hors plage absolue ?}
        G -- Oui --> H[Rejeter HTTP 422]
        H --> D
        G -- Non --> I[Enregistrer la mesure horodatee en base]
        I --> J{Seuil clinique depasse ?}
        J -- Non --> K[Mettre a jour l'historique patient]
        J -- Oui : cas degrade --> L[Creer une alerte - severite + message]
        L --> M[Diffuser l'alerte en temps reel - WebSocket /ws/alerts]
    end

    subgraph Medecin["Couloir : Medecin"]
        K --> N[Consulter le tableau de bord]
        M --> O[Recevoir la notification d'alerte]
        O --> P[Consulter l'historique et la mesure a l'origine de l'alerte]
        P --> Q{Situation necessite une teleconsultation ?}
        Q -- Oui --> R[Rejoindre la salle WebRTC commune]
        R --> S[Realiser la teleconsultation video]
        S --> T[Acquitter l'alerte]
        Q -- Non --> T
        T --> Z2((Fin : alerte traitee))
        N --> Z3((Fin : suivi courant))
    end
```

## Legende des elements

| Symbole | Signification BPMN | Occurrence dans le processus |
|---|---|---|
| Cercle fin | Evenement de debut | Arrivee du patient sur l'application |
| Rectangle | Tache utilisateur ou systeme | Saisie, validation, enregistrement, diffusion, consultation |
| Losange | Passerelle de decision exclusive (XOR) | Consentement accepte ou non ; valeur hors plage ou non ; seuil clinique depasse ou non ; teleconsultation necessaire ou non |
| Cercle epais | Evenement de fin | Acces refuse, suivi courant cloture, alerte traitee |

## Lien avec le cas degrade exige par le cadrage

Le cas degrade (donnee anormale) correspond a la branche `J -- Oui`. Il est reproductible via le bouton **Simuler une alerte** de l'interface patient et verifie automatiquement par `tests/test_api.py::test_critical_vital_creates_an_alert`. Un second cas degrade, le rejet d'une valeur hors plage absolue (`G -- Oui`), est verifie par `test_invalid_vital_is_rejected`.

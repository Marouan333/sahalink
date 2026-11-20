# Test d'utilisabilité

## Objectif

Mesurer l'utilisabilité de SahaLink avec de vrais utilisateurs, comme le demande le sujet (« score d'utilisabilité ou autre indicateur pertinent »). Les indicateurs retenus sont le taux de réussite des tâches, le temps par tâche et le score SUS (System Usability Scale).

Aucun résultat n'est inscrit dans ce document tant que les essais n'ont pas eu lieu : les tableaux ci-dessous sont à remplir avec les mesures réelles.

## Participants et déroulement

- Au moins 5 testeurs, en binôme : un testeur joue le patient, l'autre le médecin, chacun sur son ordinateur, avec le lien de la plateforme.
- Chaque binôme fait le scénario une fois, puis échange les rôles si le temps le permet.
- L'animateur ne donne aucune aide pendant les tâches. Il note le temps (chronomètre) et la réussite, puis le testeur remplit le questionnaire SUS.
- Les testeurs utilisent uniquement les comptes de démonstration : `dr.benali` (médecin) et `amal` (patient). Aucune donnée personnelle réelle n'est saisie.

## Tâches

| ID | Rôle | Tâche donnée au testeur | Réussite si | Temps max |
|---|---|---|---|---|
| T1 | Patient et médecin | Se connecter avec son compte | L'espace du rôle s'affiche | 1 min |
| T2 | Patient | Donner son consentement à la téléconsultation | Le badge indique « Confirmé » | 2 min |
| T3 | Patient | Envoyer une mesure normale | Message « Mesure enregistrée » | 2 min |
| T4 | Patient | Envoyer une mesure critique avec « Simuler une alerte » | Le médecin voit l'alerte | 2 min |
| T5 | Médecin | Repérer l'alerte et l'acquitter | L'alerte passe à « acquittée » | 2 min |
| T6 | Médecin | Démarrer la téléconsultation | Le patient reçoit l'invitation | 2 min |
| T7 | Patient | Rejoindre la consultation depuis l'invitation | Vidéo des deux côtés | 3 min |
| T8 | Médecin | Terminer la consultation | Le patient est prévenu | 1 min |

## Résultats par tâche (à remplir)

| Testeur | Rôle | T1 | T2 | T3 | T4 | T5 | T6 | T7 | T8 |
|---|---|---|---|---|---|---|---|---|---|
| | | | | | | | | | |

Pour chaque case, noter la réussite (O ou N) et le temps en secondes, par exemple « O 42 s ».

Taux de réussite global = nombre de tâches réussies divisé par le nombre de tâches tentées.

## Questionnaire SUS

Pour chaque énoncé, le testeur répond de 1 (pas du tout d'accord) à 5 (tout à fait d'accord).

1. Je pense que j'aimerais utiliser ce système fréquemment.
2. J'ai trouvé ce système inutilement complexe.
3. J'ai trouvé ce système facile à utiliser.
4. Je pense que j'aurais besoin de l'aide d'une personne technique pour utiliser ce système.
5. J'ai trouvé que les différentes fonctions de ce système étaient bien intégrées.
6. J'ai trouvé qu'il y avait trop d'incohérences dans ce système.
7. Je pense que la plupart des gens apprendraient très vite à utiliser ce système.
8. J'ai trouvé ce système très lourd à utiliser.
9. Je me suis senti(e) très confiant(e) en utilisant ce système.
10. J'ai eu besoin d'apprendre beaucoup de choses avant de pouvoir utiliser ce système.

### Calcul du score

- Énoncés impairs (1, 3, 5, 7, 9) : points = réponse moins 1.
- Énoncés pairs (2, 4, 6, 8, 10) : points = 5 moins la réponse.
- Score SUS = somme des 10 points multipliée par 2,5, soit un score de 0 à 100.
- Repères usuels : environ 68 correspond à une utilisabilité moyenne, plus de 80 à une très bonne utilisabilité.

Les réponses sont saisies dans `docs/sus-resultats.csv` (une ligne par testeur : nom, rôle, puis q1 à q10), puis le calcul se fait avec :

```powershell
python scripts/sus_score.py docs/sus-resultats.csv
```

## Résultats SUS (à remplir)

| Nombre de testeurs | Score SUS moyen | Minimum | Maximum |
|---|---|---|---|
| | | | |

## Interprétation et limites (à compléter après les essais)

- Un échantillon de quelques amis n'est pas représentatif de patients et de médecins réels : le score indique si le parcours est compréhensible, pas s'il est adapté à un usage clinique.
- Noter les difficultés observées (étape où le testeur hésite, message incompris) et les corrections apportées ensuite.

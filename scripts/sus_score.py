"""Calcule les scores SUS (System Usability Scale) depuis un fichier CSV.

Usage: python scripts/sus_score.py docs/sus-resultats.csv

Colonnes attendues : testeur, role, q1 a q10 (reponses de 1 a 5).
"""
import csv
import statistics
import sys


def sus_score(answers):
    points = [(a - 1) if index % 2 == 0 else (5 - a) for index, a in enumerate(answers)]
    return sum(points) * 2.5


def read_rows(path):
    with open(path, newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            if not any((value or "").strip() for value in row.values()):
                continue
            answers = [int(row[f"q{number}"]) for number in range(1, 11)]
            if any(a < 1 or a > 5 for a in answers):
                raise ValueError(f"Reponse hors de 1 a 5 pour {row.get('testeur', '?')}")
            yield row.get("testeur", "?"), row.get("role", "?"), answers


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    results = [(name, role, sus_score(answers)) for name, role, answers in read_rows(sys.argv[1])]
    if not results:
        sys.exit("Aucune ligne de reponses dans le fichier.")
    for name, role, score in results:
        print(f"{name:<20} {role:<10} SUS = {score:5.1f}")
    scores = [score for _, _, score in results]
    print(f"\n{len(scores)} testeur(s) : moyenne {statistics.mean(scores):.1f}, min {min(scores):.1f}, max {max(scores):.1f}")


if __name__ == "__main__":
    main()

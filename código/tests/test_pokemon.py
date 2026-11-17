import csv
import unittest
from pathlib import Path

EXPECTED_COUNTS = {
    # A tabela de custos omite Unown, Koraidon e Miraidon.
    "unique_species": 1022,
    "mega_evolutions": 46,
    "gigantamax_forms": 0,
    "arceus_forms": 15,
    "regional_forms": 55,
    "deoxys_forms": 3,
    "rotom_appliances": 5,
    "therian_forms": 4,
    "fusion_forms": 4,
    "lycanroc_forms": 2,
    # Formas adicionais presentes neste CSV:
    # Hoopa-Unbound, Shaymin-Sky, Ursaluna-Bloodmoon, Urshifu-Rapid-Strike.
    "additional_forms": 4,
}


class TestPokemon(unittest.TestCase):
    def test_costs_pokemon_count(self):
        csv_path = Path(__file__).resolve().parents[1] / "costs_pokemon.csv"

        with csv_path.open(encoding="utf-8-sig", newline="") as file:
            rows = csv.reader(file)
            next(rows)  # Cabeçalho com os custos de 30 a 1.
            actual_count = sum(
                1 for row in rows for name in row if name.strip()
            )

        self.assertEqual(actual_count, sum(EXPECTED_COUNTS.values()))

    def test_stats_pokemon_count(self):
        csv_path = Path(__file__).resolve().parents[1] / "stats_pokemon.csv"

        with csv_path.open(encoding="utf-8-sig", newline="") as file:
            actual_count = sum(1 for row in csv.DictReader(file))

        self.assertEqual(actual_count, sum(EXPECTED_COUNTS.values()))


if __name__ == "__main__":
    unittest.main()

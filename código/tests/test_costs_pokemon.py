import csv
import unittest
from pathlib import Path

from pokemon_counts import assert_pokemon_counts

EXPECTED_COUNTS = {
    # The cost table omits Unown, Koraidon and Miraidon.
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
    # Additional forms in this CSV:
    # Hoopa-Unbound, Shaymin-Sky, Ursaluna-Bloodmoon, Urshifu-Rapid-Strike.
    "additional_forms": 4,
}

class TestCostsPokemon(unittest.TestCase):
    def test_total_pokemon_count(self):
        csv_path = Path(__file__).resolve().parents[1] / "costs_pokemon.csv"

        with csv_path.open(encoding="utf-8-sig", newline="") as file:
            rows = csv.reader(file)
            next(rows)  # Cost headers from 30 to 1.
            names = [name.strip() for row in rows for name in row if name.strip()]

        assert_pokemon_counts(
            self, names, EXPECTED_COUNTS, ADDITIONAL_FORMS, SPECIES_REPRESENTATIVES
        )


if __name__ == "__main__":
    unittest.main()

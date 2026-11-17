import csv
import unittest
from pathlib import Path

from pokemon_counts import assert_pokemon_counts


# The cost table omits Unown, Koraidon and Miraidon.
UNIQUE_SPECIES_COUNT = 1022
MEGA_EVOLUTION_COUNT = 46
GIGANTAMAX_FORM_COUNT = 0
ARCEUS_FORM_COUNT = 15

# Additional forms in this CSV:
# Hoopa-Unbound, Shaymin-Sky, Ursaluna-Bloodmoon, Urshifu-Rapid-Strike.
ADDITIONAL_FORM_COUNT = 4
ADDITIONAL_FORMS = {
    "Hoopa-Unbound",
    "Shaymin-Sky",
    "Ursaluna-Bloodmoon",
    "Urshifu-Rapid-Strike",
}

EXPECTED_COUNTS = {
    "unique_species": UNIQUE_SPECIES_COUNT,
    "mega_evolutions": MEGA_EVOLUTION_COUNT,
    "gigantamax_forms": GIGANTAMAX_FORM_COUNT,
    "arceus_forms": ARCEUS_FORM_COUNT,
    "regional_forms": 55,
    "deoxys_forms": 3,
    "rotom_appliances": 5,
    "therian_forms": 4,
    "fusion_forms": 4,
    "lycanroc_forms": 2,
    "additional_forms": ADDITIONAL_FORM_COUNT,
}

# Each of these entries represents a species whose base form is absent.
SPECIES_REPRESENTATIVES = {"Arceus-Ground", "Primal Kyogre"}


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

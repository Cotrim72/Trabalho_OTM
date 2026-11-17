import csv
import unittest
from pathlib import Path


UNIQUE_SPECIES_COUNT = 1025
MEGA_EVOLUTION_COUNT = 46
GIGANTAMAX_FORM_COUNT = 0
# Uma forma tipada representa a espécie Arceus; as outras 15 são formas extras.
ARCEUS_FORM_COUNT = 15
# Formas adicionais: variantes de Alola, Galar, Hisui e Paldea, além das formas
# Primal, Origin, Therian, Crowned, Hero, School, Ash, White/Black e outras
# variantes de sexo, item, postura, fusão ou batalha presentes na tabela.
ADDITIONAL_FORM_COUNT = 74


class TestCostsPokemon(unittest.TestCase):
    def test_total_pokemon_count(self):
        csv_path = Path(__file__).parents[1] / "costs_pokemon.csv"

        with csv_path.open(encoding="utf-8-sig", newline="") as file:
            rows = csv.reader(file)
            next(rows)  # Cost headers from 30 to 1.
            actual_count = sum(
                1 for row in rows for pokemon in row if pokemon.strip()
            )

        expected_count = (
            UNIQUE_SPECIES_COUNT
            + MEGA_EVOLUTION_COUNT
            + GIGANTAMAX_FORM_COUNT
            + ARCEUS_FORM_COUNT
            + ADDITIONAL_FORM_COUNT
        )
        self.assertEqual(actual_count, expected_count)


if __name__ == "__main__":
    unittest.main()

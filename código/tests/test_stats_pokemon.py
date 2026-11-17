import csv
import unittest
from pathlib import Path


UNIQUE_SPECIES_COUNT = 1025
MEGA_EVOLUTION_COUNT = 97
GIGANTAMAX_FORM_COUNT = 34
# A forma Normal está incluída nas espécies únicas; estas são as outras 17 formas tipadas.
ARCEUS_FORM_COUNT = 17
# Formas adicionais: variantes regionais, de sexo, item, clima, postura, fusão,
# batalha e Terastal, além de formas especiais (Totem, Primal, Ash, Origin,
# Therian, Ultra, Crowned, Eternamax, Pokestar e MissingNo.).
ADDITIONAL_FORM_COUNT = 262


class TestStatsPokemon(unittest.TestCase):
    def test_total_pokemon_count(self):
        csv_path = Path(__file__).parents[1] / "stats_pokemon.csv"

        with csv_path.open(encoding="utf-8-sig", newline="") as file:
            actual_count = sum(1 for _ in csv.DictReader(file))

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

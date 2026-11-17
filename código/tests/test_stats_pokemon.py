import csv
import unittest
from pathlib import Path


QUANTIDADE_ESPECIES_UNICAS = 1025
QUANTIDADE_MEGA_EVOLUCOES = 97
QUANTIDADE_FORMAS_GIGANTAMAX = 34
# A forma Normal está incluída nas espécies únicas; estas são as outras 17 formas tipadas.
QUANTIDADE_FORMAS_ARCEUS = 17
# Formas adicionais: variantes regionais, de sexo, item, clima, postura, fusão,
# batalha e Terastal, além de formas especiais (Totem, Primal, Ash, Origin,
# Therian, Ultra, Crowned, Eternamax, Pokestar e MissingNo.).
QUANTIDADE_FORMAS_ADICIONAIS = 262


class TestStatsPokemon(unittest.TestCase):
    def test_quantidade_total_de_pokemon(self):
        caminho_csv = Path(__file__).parents[1] / "stats_pokemon.csv"

        with caminho_csv.open(encoding="utf-8-sig", newline="") as arquivo:
            quantidade_no_arquivo = sum(1 for _ in csv.DictReader(arquivo))

        quantidade_esperada = (
            QUANTIDADE_ESPECIES_UNICAS
            + QUANTIDADE_MEGA_EVOLUCOES
            + QUANTIDADE_FORMAS_GIGANTAMAX
            + QUANTIDADE_FORMAS_ARCEUS
            + QUANTIDADE_FORMAS_ADICIONAIS
        )
        self.assertEqual(quantidade_no_arquivo, quantidade_esperada)


if __name__ == "__main__":
    unittest.main()

import csv
import unittest
from pathlib import Path


QUANTIDADE_ESPECIES_UNICAS = 1025
QUANTIDADE_MEGA_EVOLUCOES = 46
QUANTIDADE_FORMAS_GIGANTAMAX = 0
# Uma forma tipada representa a espécie Arceus; as outras 15 são formas extras.
QUANTIDADE_FORMAS_ARCEUS = 15
# Formas adicionais: variantes de Alola, Galar, Hisui e Paldea, além das formas
# Primal, Origin, Therian, Crowned, Hero, School, Ash, White/Black e outras
# variantes de sexo, item, postura, fusão ou batalha presentes na tabela.
QUANTIDADE_FORMAS_ADICIONAIS = 74


class TestCostsPokemon(unittest.TestCase):
    def test_quantidade_total_de_pokemon(self):
        caminho_csv = Path(__file__).parents[1] / "costs_pokemon.csv"

        with caminho_csv.open(encoding="utf-8-sig", newline="") as arquivo:
            linhas = csv.reader(arquivo)
            next(linhas)  # Cabeçalho com os custos de 30 a 1.
            quantidade_no_arquivo = sum(
                1 for linha in linhas for pokemon in linha if pokemon.strip()
            )

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

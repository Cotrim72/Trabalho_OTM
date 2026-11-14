#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Melhor time para um duelo (modelo de counter).

    max  Z = sum_{i in R} ( sum_{j in O} P_j * Advantage(i,j) ) x_i
    s.a. sum_i x_i = K ,  x_i in {0,1}

Uso:
    python pokemon_duel.py --roster meu_roster.txt --opponent adversario.txt -K 6
    python pokemon_duel.py --roster "Terrakion,Diancie,Kleavor,Archeops" \
                           --opponent "Kyurem,Rillaboom,Iron Jugulis" -K 3

--roster / --opponent aceitam um arquivo (um Pokémon por linha) ou uma lista
separada por vírgulas. Os nomes devem existir no arquivo de custos.

Requer o arquivo pokemon_draft.py na mesma pasta (reaproveita a leitura dos
CSVs, a tabela de tipos e as tiers) e: pip install pandas numpy scipy
"""

import argparse
import os
import sys

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp

from model1 import advantage, find_pokemon, load_data


def read_names(arg):
    if os.path.isfile(arg):
        with open(arg, encoding="utf-8") as f:
            names = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    else:
        names = [n.strip() for n in arg.split(",") if n.strip()]
    return names


def to_indices(df, names, label):
    idx = []
    for n in names:
        i = find_pokemon(df, n)
        if i is None:
            sys.exit(f"Erro: '{n}' ({label}) não encontrado no arquivo de custos.")
        if df["name"].iloc[i].lower() != n.lower():
            print(f"Aviso: '{n}' interpretado como '{df['name'].iloc[i]}'.")
        if i not in idx:
            idx.append(i)
    return idx


def best_team(df, R, O, K):
    """Resolve o MILP e devolve (índices do time, Z, score individual de cada i em R)."""
    Pj = df["P"].values[O]
    types = df["types"].values
    score = np.array([sum(Pj[k] * advantage(types[i], types[j]) for k, j in enumerate(O))
                      for i in R])
    n = len(R)
    res = milp(c=-score,
               constraints=[LinearConstraint(np.ones((1, n)), K, K)],
               integrality=np.ones(n),
               bounds=Bounds(0, 1))
    if not res.success:
        sys.exit("Modelo inviável (K maior que o tamanho do roster?).")
    chosen = [k for k in range(n) if res.x[k] > 0.5]
    chosen.sort(key=lambda k: -score[k])
    return chosen, -res.fun, score


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--roster", required=True, help="seu roster (arquivo ou lista com vírgulas)")
    ap.add_argument("--opponent", required=True, help="Pokémon do adversário (arquivo ou lista)")
    ap.add_argument("-K", type=int, default=6, help="nº de Pokémon no time (padrão 6)")
    ap.add_argument("--costs", default="costs_pokemon.csv")
    ap.add_argument("--stats", default="stats_pokemon.csv")
    args = ap.parse_args()

    df, _ = load_data(args.costs, args.stats)
    R = to_indices(df, read_names(args.roster), "roster")
    O = to_indices(df, read_names(args.opponent), "adversário")
    if args.K > len(R):
        sys.exit(f"Erro: K={args.K} é maior que o roster ({len(R)} Pokémon).")

    chosen, Z, score = best_team(df, R, O, args.K)

    print(f"Adversário ({len(O)}): " + ", ".join(
        f"{df['name'].iloc[j]} (P={df['P'].iloc[j]:.2f})" for j in O))
    print(f"\nMelhor time de {args.K} (Z = {Z:.2f}):")
    for k in chosen:
        i = R[k]
        advs = ", ".join(f"{advantage(df['types'].iloc[i], df['types'].iloc[j]):+d} {df['name'].iloc[j]}"
                         for j in O)
        print(f"  {df['name'].iloc[i]:<22} {'/'.join(df['types'].iloc[i]):<17} "
              f"score {score[k]:+.2f}   [{advs}]")


if __name__ == "__main__":
    main()
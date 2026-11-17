#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Melhor time para um duelo (modelo de counter).

    max  Z = sum_{i in R} ( beta*d_i + gamma*r_i ) x_i
        d_i = sum_{j in O} Advantage(i,j) / (4 |O|)   (vantagem ofensiva)
        r_i = sum_{j in O} Resist(i,j)    / (4 |O|)   (resistência de tipo)
        Resist(i,j) = -Advantage(j,i)
    s.a. sum_i x_i = K
         sum_{i in Mega} x_i <= 1      (só uma Mega evolução por partida)
         x_i in {0,1}

Com beta=1 e gamma=0 (padrão) obtém-se o mesmo time do modelo original de
vantagem pura (a normalização é uma constante positiva e só muda a escala de Z).

Uso:
    python model2.py --roster meu_roster.txt --opponent adversario.txt -K 6
    python model2.py --roster "Terrakion,Diancie,Kleavor,Archeops,Mega Gengar" \
                     --opponent "Corviknight,Gholdengo" -K 4 --gamma 0.5

--roster / --opponent aceitam um arquivo (um Pokémon por linha) ou uma lista
separada por vírgulas. Os nomes devem existir no arquivo de custos.

Requer o arquivo model1.py na mesma pasta (reaproveita a leitura dos
CSVs, a tabela de tipos e as tiers) e: pip install pandas numpy scipy
"""

import argparse
import os
import sys

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp

from model1 import advantage, find_pokemon, load_data, resistance


def normalize_mega_name(name):
    """Padroniza variações de nomes de Mega para o formato do dataset."""
    n = name.strip()
    # Exemplo: Se o usuário digitar 'Mega Gengar' ou 'Gengar-Mega' ou 'Mega-Gengar'
    if n.lower().startswith("mega "):
        base = n[5:].strip()
        return f"{base}-Mega"  # Ajuste conforme o padrão do seu CSV (ex: Gengar-Mega)
    elif n.lower().endswith(" (mega)"):
        base = n[:-7].strip()
        return f"{base}-Mega"
    return n

def read_names(arg):
    if os.path.isfile(arg):
        with open(arg, encoding="utf-8") as f:
            names = [normalize_mega_name(line.strip()) for line in f if line.strip() and not line.startswith("#")]
    else:
        names = [normalize_mega_name(n) for n in arg.split(",") if n.strip()]
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


def best_team(df, R, O, K, beta=1.0, gamma=0.0, max_mega=1):
    """Resolve o MILP e devolve (índices do time, Z, escore individual s_i de cada i em R)."""
    norm = 4.0 * len(O)
    types = df["types"].values
    d = np.array([sum(advantage(types[i], types[j]) for j in O)
                  for i in R]) / norm
    r = np.array([sum(resistance(types[i], types[j]) for j in O)
                  for i in R]) / norm
    score = beta * d + gamma * r
    n = len(R)
    constraints = [LinearConstraint(np.ones((1, n)), K, K)]
    mega = df["mega"].values[R].astype(float)
    if max_mega is not None and mega.any():           # sum_{i in Mega} x_i <= max_mega
        constraints.append(LinearConstraint(mega.reshape(1, -1), -np.inf, max_mega))
    res = milp(c=-score,
               constraints=constraints,
               integrality=np.ones(n),
               bounds=Bounds(0, 1))
    if not res.success:
        sys.exit("Modelo inviável (K maior que o roster, ou Megas demais para o limite?).")
    chosen = [k for k in range(n) if res.x[k] > 0.5]
    chosen.sort(key=lambda k: -score[k])
    return chosen, -res.fun, score


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--roster", required=True, help="seu roster (arquivo ou lista com vírgulas)")
    ap.add_argument("--opponent", required=True, help="Pokémon do adversário (arquivo ou lista)")
    ap.add_argument("-K", type=int, default=6, help="nº de Pokémon no time (padrão 6)")
    ap.add_argument("--beta", type=float, default=1.0, help="peso da vantagem ofensiva (0-1, padrão 1)")
    ap.add_argument("--gamma", type=float, default=0.0, help="peso da resistência de tipos (0-1, padrão 0)")
    ap.add_argument("--max-mega", type=int, default=1, help="máx. de Mega evoluções no time (padrão 1)")
    ap.add_argument("--costs", default="costs_pokemon.csv")
    ap.add_argument("--stats", default="stats_pokemon.csv")
    args = ap.parse_args()

    df, _, _ = load_data(args.costs, args.stats)
    R = to_indices(df, read_names(args.roster), "roster")
    O = to_indices(df, read_names(args.opponent), "adversário")
    if args.K > len(R):
        sys.exit(f"Erro: K={args.K} é maior que o roster ({len(R)} Pokémon).")

    beta, gamma = min(max(args.beta, 0), 1), min(max(args.gamma, 0), 1)
    chosen, Z, score = best_team(df, R, O, args.K, beta, gamma, args.max_mega)

    print(f"Adversário ({len(O)}): " + ", ".join(
        f"{df['name'].iloc[j]} ({df['Tier'].iloc[j]})" for j in O))
    print(f"\nMelhor time de {args.K} (Z = {Z:.3f}; beta={beta:g}, gamma={gamma:g}):")
    for k in chosen:
        i = R[k]
        advs = ", ".join(f"{advantage(df['types'].iloc[i], df['types'].iloc[j]):+d} {df['name'].iloc[j]}"
                         for j in O)
        ress = ", ".join(f"{resistance(df['types'].iloc[i], df['types'].iloc[j]):+d} {df['name'].iloc[j]}"
                         for j in O)
        print(f"  {df['name'].iloc[i]:<22} {'/'.join(df['types'].iloc[i]):<17} "
              f"score {score[k]:+.3f}\n      ataque  [{advs}]\n      defesa  [{ress}]")


if __name__ == "__main__":
    main()
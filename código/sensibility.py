#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sensibilidade aos pesos (alpha, beta, gama) no MODO GAME do model1.py.

Para cada semente é sorteado UM conjunto de times adversários (n-1 times de G
Pokémon, dentro do orçamento C). Esse MESMO conjunto é usado nos quatro cenários,
então qualquer diferença entre os times recomendados vem só dos pesos:

    alpha dominante : (d, o, o)      d = --dominant (padrão 0.70), o = (1-d)/2
    beta  dominante : (o, d, o)
    gama  dominante : (o, o, d)
    iguais          : (1/3, 1/3, 1/3)

alpha pesa a força de ataque (v_i), beta a vantagem ofensiva de tipos (d_i) e
gama a resistência de tipos (r_i), como no model1.py. O modelo resolvido é o do
modo game: M = G, A = vazio, U = união dos Pokémon de todos os adversários.

Saída: (1) detalhe dos times nas primeiras sementes, (2) métricas médias por
cenário, (3) sobreposição média entre os times dos cenários, (4) tipos mais
frequentes por cenário e, opcionalmente, (5) um CSV com tudo.

Os adversários são sorteados como "profissionais" (peso P_j^tau + sinergia de tipos,
ver model1.py; controle com --opp-sharpness / --opp-synergy) e o time recomendado
respeita o limite E de Megas (--max-mega).

Atenção: Z NÃO é comparável entre cenários (os pesos mudam a escala do objetivo);
compare os times pelas métricas, que não dependem dos pesos.

Requer o model1.py na mesma pasta.
Uso:  python sensibility.py --costs costs_pokemon.csv --stats stats_pokemon.csv
      python sensibility.py --players 4 --G 6 --C 80 --seeds 20 --ban-illegal --out resultado.csv
"""

import argparse
import csv
import itertools
import sys
from collections import Counter
from dataclasses import replace

import numpy as np

from model1 import (Config, advantage, fmt_types, load_data, objective_coeffs,
                    random_team, resistance, solve)


# --------------------------------------------------------------------------
# Cenários
# --------------------------------------------------------------------------
def make_scenarios(dom):
    o = (1.0 - dom) / 2.0
    return {
        "alpha dominante": (dom, o, o),
        "beta dominante": (o, dom, o),
        "gama dominante": (o, o, dom),
        "iguais": (1 / 3, 1 / 3, 1 / 3),
    }


# --------------------------------------------------------------------------
# Métricas de um time (independentes dos pesos)
# --------------------------------------------------------------------------
def team_metrics(df, T, U, adv_t, res_t):
    types = df["types"].values
    pairs = [(i, j) for i in T for j in U]
    off_pos = np.mean([advantage(types[i], types[j]) > 0 for i, j in pairs])
    def_neg = np.mean([resistance(types[i], types[j]) < 0 for i, j in pairs])
    return {
        "custo": float(df["cost"].values[T].sum()),
        "atk_medio": float(df["attack"].values[T].mean()),
        "d_medio": float(adv_t[T].mean()),          # vantagem ofensiva média (P-ponderada)
        "r_medio": float(res_t[T].mean()),          # resistência média (P-ponderada)
        "pares_ofensivos_%": 100.0 * float(off_pos),   # % pares (meu, adv) com vantagem ofensiva
        "pares_defensivos_ruins_%": 100.0 * float(def_neg),
        "megas": float(df["mega"].values[T].sum()),  # % pares em que sou atingido super efetivo
        "tipos_distintos": len({t for i in T for t in types[i]}),
    }


METRIC_COLS = ["custo", "atk_medio", "d_medio", "r_medio",
               "pares_ofensivos_%", "pares_defensivos_ruins_%", "tipos_distintos", "megas"]
METRIC_HEAD = ["custo", "atk", "d", "r", "%of+", "%df-", "tipos", "megas"]


# --------------------------------------------------------------------------
# Impressão
# --------------------------------------------------------------------------
def print_seed_detail(df, seed, opp, results, U, adv_t, res_t):
    print("\n" + "=" * 100)
    print(f" SEMENTE {seed}  -  adversários (mesmos para todos os cenários)")
    print("=" * 100)
    for k, team in enumerate(opp, 1):
        print(f"  Adv {k}: " + ", ".join(f"{df['name'].iloc[j]} ({fmt_types(df['types'].iloc[j])})"
                                         for j in team))
    for name, r in results.items():
        a, b, g = r["w"]
        print(f"\n  >> {name}  (alpha={a:.2f}, beta={b:.2f}, gama={g:.2f})")
        if r["team"] is None:
            print("     modelo inviável.")
            continue
        m = r["metrics"]
        print(f"     Z={r['Z']:.3f}  custo={m['custo']:.0f}  atk_médio={m['atk_medio']:.0f}  "
              f"d_médio={m['d_medio']:+.2f}  r_médio={m['r_medio']:+.2f}")
        for i in r["team"]:
            row = df.iloc[i]
            print(f"       {row['name']:<22} {fmt_types(row['types']):<17} tier {row['Tier']:<7} "
                  f"custo {int(row['cost']):>2}  atk {int(row['attack']):>3}  "
                  f"d={adv_t[i]:+.2f} r={res_t[i]:+.2f}")


def print_metric_table(agg, scen_names):
    print("\n" + "=" * 100)
    print(" MÉTRICAS MÉDIAS POR CENÁRIO (média sobre as sementes)")
    print("=" * 100)
    head = f"{'cenário':<18}" + "".join(f"{h:>10}" for h in METRIC_HEAD)
    print(head)
    print("-" * len(head))
    for name in scen_names:
        if name not in agg:
            continue
        row = agg[name]
        print(f"{name:<18}" + "".join(f"{row[c]:>10.2f}" for c in METRIC_COLS))
    print("\n  d, r: vantagem ofensiva / resistência médias do time (escala [-1,1], ponderadas por P_j)."
          "\n  %of+ : % dos pares (meu Pokémon, Pokémon adversário) em que ataco com vantagem de tipo."
          "\n  %df- : % dos pares em que sou atingido super efetivamente.")


def print_overlap(shared, scen_names, G):
    print("\n" + "=" * 100)
    print(f" SOBREPOSIÇÃO MÉDIA ENTRE OS TIMES (nº de Pokémon em comum, de {G})")
    print("=" * 100)
    print(f"{'':<18}" + "".join(f"{n[:16]:>18}" for n in scen_names))
    for a in scen_names:
        cells = []
        for b in scen_names:
            v = shared.get((a, b))
            cells.append(f"{v:>18.2f}" if v is not None else f"{'-':>18}")
        print(f"{a:<18}" + "".join(cells))


def print_type_freq(freq, scen_names, topn=6):
    print("\n" + "=" * 100)
    print(f" TIPOS MAIS FREQUENTES NOS TIMES RECOMENDADOS (top {topn}, somando todas as sementes)")
    print("=" * 100)
    for name in scen_names:
        c = freq.get(name)
        if not c:
            continue
        print(f"  {name:<18} " + ", ".join(f"{t} ({k})" for t, k in c.most_common(topn)))


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--costs", default="costs_pokemon.csv")
    ap.add_argument("--stats", default="stats_pokemon.csv")
    ap.add_argument("--players", type=int, default=4, help="n = você + n-1 adversários (padrão 4)")
    ap.add_argument("--G", type=int, default=6, help="Pokémon por time (padrão 6)")
    ap.add_argument("--C", type=float, default=80.0, help="orçamento (padrão 80)")
    ap.add_argument("--dominant", type=float, default=0.70,
                    help="peso do parâmetro dominante nos 3 primeiros cenários (padrão 0.70)")
    ap.add_argument("--seeds", type=int, default=10, help="nº de conjuntos de adversários sorteados")
    ap.add_argument("--seed", type=int, default=0, help="primeira semente (usa seed..seed+seeds-1)")
    ap.add_argument("--show-seeds", type=int, default=1,
                    help="quantas sementes detalhar na tela (padrão 1)")
    ap.add_argument("--attack", choices=["max", "atk", "spa"], default="max")
    ap.add_argument("--allow-ubers", action="store_true", help="libera Uber/AG")
    ap.add_argument("--ban-illegal", action="store_true", help="remove o tier Illegal do pool")
    ap.add_argument("--uniform-opponent", action="store_true",
                    help="adversários sorteiam uniformemente (ignora tier e sinergia)")
    ap.add_argument("--opp-sharpness", type=float, default=2.0,
                    help="tau: peso P_j^tau na escolha dos adversários (padrão 2)")
    ap.add_argument("--opp-synergy", type=float, default=1.0,
                    help="sigma: sinergia de tipos dos adversários (0 desliga; padrão 1)")
    ap.add_argument("--max-mega", type=int, default=1, help="E: máx. de Megas por time (padrão 1)")
    ap.add_argument("--out", default=None, help="CSV de saída com todos os resultados")
    args = ap.parse_args()

    if not 1 / 3 <= args.dominant < 1.0:
        sys.exit("--dominant deve estar em [0.34, 1).")

    df, missing, n_illegal = load_data(args.costs, args.stats, args.attack, args.ban_illegal)
    pool = len(df) - (0 if args.allow_ubers else int(df["banned"].sum()))
    if args.players * args.G > pool:
        sys.exit(f"Pool insuficiente: {args.players}x{args.G} > {pool}.")

    base = Config(n_players=args.players, G=args.G, C=args.C, allow_ubers=args.allow_ubers,
                  E=args.max_mega, opp_sharp=args.opp_sharpness, opp_synergy=args.opp_synergy)
    scen = make_scenarios(args.dominant)
    names = list(scen)
    n_opp = args.players - 1

    print("=" * 100)
    print(" SENSIBILIDADE DE alpha / beta / gama  -  modo GAME")
    print("=" * 100)
    print(f"{len(df)} Pokémon no pool | n={args.players} ({n_opp} adversários) | G={args.G} | "
          f"C={args.C:.0f} | E={args.max_mega} | {args.seeds} sementes | dominante={args.dominant:.2f}")
    print(f"adversários: tau={args.opp_sharpness:g}, sigma={args.opp_synergy:g}"
          f"{' (uniforme)' if args.uniform_opponent else ''}")
    for n_, (a, b, g) in scen.items():
        print(f"  {n_:<16} alpha={a:.2f}  beta={b:.2f}  gama={g:.2f}")

    all_results = {}     # (seed, cenário) -> dict
    for s in range(args.seed, args.seed + args.seeds):
        rng = np.random.default_rng(s)
        opp, taken = [], set()
        for _ in range(n_opp):
            team = random_team(df, taken, base, rng, args.uniform_opponent)
            opp.append(team)
            taken |= set(team)
        U = [j for t in opp for j in t]
        _, adv_t, res_t = objective_coeffs(df, U, base)   # termos de tipo não dependem dos pesos

        results = {}
        for name, (a, b, g) in scen.items():
            cfg = replace(base, alpha=a, beta=b, gamma=g)
            chosen, Z = solve(df, [], U, cfg.G, cfg)       # modo game: M = G, A = vazio
            if chosen is None:
                results[name] = {"w": (a, b, g), "team": None, "Z": None, "metrics": None}
                continue
            c, _, _ = objective_coeffs(df, U, cfg)
            chosen = sorted(chosen, key=lambda i: -c[i])
            results[name] = {"w": (a, b, g), "team": chosen, "Z": Z,
                             "metrics": team_metrics(df, chosen, U, adv_t, res_t)}
        for name, r in results.items():
            all_results[(s, name)] = r
        if s - args.seed < args.show_seeds:
            print_seed_detail(df, s, opp, results, U, adv_t, res_t)

    # ---- agregação ----
    seeds = list(range(args.seed, args.seed + args.seeds))
    agg, freq = {}, {}
    for name in names:
        rs = [all_results[(s, name)] for s in seeds if all_results[(s, name)]["team"] is not None]
        if not rs:
            continue
        agg[name] = {c: float(np.mean([r["metrics"][c] for r in rs])) for c in METRIC_COLS}
        cnt = Counter()
        for r in rs:
            for i in r["team"]:
                cnt.update(df["types"].iloc[i])
        freq[name] = cnt

    shared = {}
    for a, b in itertools.product(names, names):
        vals = [len(set(all_results[(s, a)]["team"]) & set(all_results[(s, b)]["team"]))
                for s in seeds
                if all_results[(s, a)]["team"] is not None and all_results[(s, b)]["team"] is not None]
        if vals:
            shared[(a, b)] = float(np.mean(vals))

    print_metric_table(agg, names)
    print_overlap(shared, names, args.G)
    print_type_freq(freq, names)

    # ---- CSV ----
    if args.out:
        with open(args.out, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["seed", "cenario", "alpha", "beta", "gama", "Z", "time"] + METRIC_COLS)
            for s in seeds:
                for name in names:
                    r = all_results[(s, name)]
                    a, b, g = r["w"]
                    if r["team"] is None:
                        w.writerow([s, name, a, b, g, "", "inviavel"] + [""] * len(METRIC_COLS))
                        continue
                    w.writerow([s, name, f"{a:.4f}", f"{b:.4f}", f"{g:.4f}", f"{r['Z']:.4f}",
                                ";".join(df["name"].values[r["team"]])]
                               + [f"{r['metrics'][c]:.4f}" for c in METRIC_COLS])
        print(f"\nResultados salvos em {args.out}")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nEncerrado.")
        sys.exit(0)
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Draft de Pokémon com recomendação por otimização (MILP).

Modelo (resumo):
    max  Z = alpha * sum_i v_i x_i
           + beta  * sum_i ( sum_{j in U} P_j * Advantage(i,j) ) x_i
    s.a. sum_i x_i = M                  (M = rodada atual)
         sum_i w_i x_i <= C             (orçamento)
         x_i = 1  para i em A           (meus Pokémon já escolhidos)
         x_i = 0  para i em U ∪ Ubers   (escolhidos pelos outros / banidos)
         x_i ∈ {0,1}

A cada rodada: o adversário escolhe um Pokémon aleatório -> o modelo é
resolvido -> o programa recomenda (Top-N) o seu próximo Pokémon.

Dependências:  pip install pandas numpy scipy
Uso:           python pokemon_draft.py  [--costs costs_pokemon.csv --stats stats_pokemon.csv]
"""

import argparse
import difflib
import re
import sys
import unicodedata
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.optimize import Bounds, LinearConstraint, milp

# --------------------------------------------------------------------------
# 1. Tabela de tipos (ataque -> defesa).  Só os multiplicadores != 1.
# --------------------------------------------------------------------------
TYPES = ["Normal", "Fire", "Water", "Electric", "Grass", "Ice", "Fighting", "Poison",
         "Ground", "Flying", "Psychic", "Bug", "Rock", "Ghost", "Dragon", "Dark",
         "Steel", "Fairy"]

_SE = {  # super efetivo (x2)
    "Fire": ["Grass", "Ice", "Bug", "Steel"],
    "Water": ["Fire", "Ground", "Rock"],
    "Electric": ["Water", "Flying"],
    "Grass": ["Water", "Ground", "Rock"],
    "Ice": ["Grass", "Ground", "Flying", "Dragon"],
    "Fighting": ["Normal", "Ice", "Rock", "Dark", "Steel"],
    "Poison": ["Grass", "Fairy"],
    "Ground": ["Fire", "Electric", "Poison", "Rock", "Steel"],
    "Flying": ["Grass", "Fighting", "Bug"],
    "Psychic": ["Fighting", "Poison"],
    "Bug": ["Grass", "Psychic", "Dark"],
    "Rock": ["Fire", "Ice", "Flying", "Bug"],
    "Ghost": ["Psychic", "Ghost"],
    "Dragon": ["Dragon"],
    "Dark": ["Psychic", "Ghost"],
    "Steel": ["Ice", "Rock", "Fairy"],
    "Fairy": ["Fighting", "Dragon", "Dark"],
}
_NVE = {  # pouco efetivo (x0.5)
    "Normal": ["Rock", "Steel"],
    "Fire": ["Fire", "Water", "Rock", "Dragon"],
    "Water": ["Water", "Grass", "Dragon"],
    "Electric": ["Electric", "Grass", "Dragon"],
    "Grass": ["Fire", "Grass", "Poison", "Flying", "Bug", "Dragon", "Steel"],
    "Ice": ["Fire", "Water", "Ice", "Steel"],
    "Fighting": ["Poison", "Flying", "Psychic", "Bug", "Fairy"],
    "Poison": ["Poison", "Ground", "Rock", "Ghost"],
    "Ground": ["Grass", "Bug"],
    "Flying": ["Electric", "Rock", "Steel"],
    "Psychic": ["Psychic", "Steel"],
    "Bug": ["Fire", "Fighting", "Poison", "Flying", "Ghost", "Steel", "Fairy"],
    "Rock": ["Fighting", "Ground", "Steel"],
    "Ghost": ["Dark"],
    "Dragon": ["Steel"],
    "Dark": ["Fighting", "Dark", "Fairy"],
    "Steel": ["Fire", "Water", "Electric", "Steel"],
    "Fairy": ["Fire", "Poison", "Steel"],
}
_IMMUNE = {  # imune (x0)
    "Normal": ["Ghost"], "Electric": ["Ground"], "Fighting": ["Ghost"],
    "Poison": ["Steel"], "Ground": ["Flying"], "Psychic": ["Dark"],
    "Ghost": ["Normal"], "Dragon": ["Fairy"],
}


def type_multiplier(atk: str, defenders) -> float:
    m = 1.0
    for d in defenders:
        if d in _IMMUNE.get(atk, []):
            return 0.0
        if d in _SE.get(atk, []):
            m *= 2.0
        elif d in _NVE.get(atk, []):
            m *= 0.5
    return m


def advantage(types_i, types_j) -> int:
    """Advantage(i,j) ∈ {-4,-2,0,2,4}: para cada tipo de i (ataque), +2 se for
    super efetivo contra j, -2 se for resistido/imune, 0 se neutro."""
    total = 0
    for t in types_i:
        m = type_multiplier(t, types_j)
        total += 2 if m > 1 else (-2 if m < 1 else 0)
    return total


# --------------------------------------------------------------------------
# 2. Tiers -> probabilidade de uso P_j
# --------------------------------------------------------------------------
TIER_GROUP = {  # tier do CSV -> tier "de uso" do modelo
    "OU": "OU", "UUBL": "OU", "Uber": "OU", "AG": "OU",
    "UU": "UU", "RUBL": "UU",
    "RU": "RU", "NUBL": "RU",
    "NU": "NU", "PUBL": "NU",
    "PU": "PU", "ZUBL": "PU",
    "ZU": "ZU", "LC": "ZU", "NFE": "ZU", "CAP": "ZU", "CAP LC": "ZU",
    "CAP NFE": "ZU", "Illegal": "ZU",
}
P_TIER = {"OU": 0.95, "UU": 0.80, "RU": 0.60, "NU": 0.40, "PU": 0.20, "ZU": 0.05}
UBER_TIERS = {"Uber", "AG"}  # conjunto "Ubers" (banidos)


# --------------------------------------------------------------------------
# 3. Carga dos dados
# --------------------------------------------------------------------------
def _clean(s: str) -> str:
    s = unicodedata.normalize("NFC", str(s)).strip()
    return s.replace("'", "’")


_ALIASES = {
    "Primal Kyogre": "Kyogre-Primal", "Primal Groudon": "Groudon-Primal",
    "Landorus-Incarnate": "Landorus", "Thundurus-Incarnate": "Thundurus",
    "Tornadus-Incarnate": "Tornadus", "Enamorus-Incarnate": "Enamorus",
    "Calyrex-Ice-Rider": "Calyrex-Ice", "Calyrex-Shadow-Rider": "Calyrex-Shadow",
    "Urshifu-Single-Strike": "Urshifu", "Lycanroc-Midday": "Lycanroc",
    "Nidoran-Female": "Nidoran-F", "Nidoran-Male": "Nidoran-M",
    "Paldean Tauros": "Tauros-Paldea-Combat",
}


def _to_stats_name(n: str) -> str:
    """Converte o nome do arquivo de custos para o nome usado no arquivo de stats."""
    n = _clean(n)
    if n in _ALIASES:
        return _ALIASES[n]
    m = re.match(r"^Mega (.+?)( [XY])?$", n)
    if m:
        return m.group(1) + "-Mega" + ("-" + m.group(2).strip() if m.group(2) else "")
    for prefix, suf in [("Alolan ", "-Alola"), ("Galarian ", "-Galar"),
                        ("Hisuian ", "-Hisui"), ("Paldean ", "-Paldea")]:
        if n.startswith(prefix):
            return n[len(prefix):] + suf
    return n


def load_data(costs_path, stats_path, attack_mode="max"):
    costs_wide = pd.read_csv(costs_path)
    rows = [(n, int(col)) for col in costs_wide.columns for n in costs_wide[col].dropna()]
    costs = pd.DataFrame(rows, columns=["raw_name", "cost"])
    costs["key"] = costs["raw_name"].map(_to_stats_name)

    stats = pd.read_csv(stats_path)
    stats["key"] = stats["Pokemon"].map(_clean)
    stats = stats.drop_duplicates("key")

    df = costs.merge(stats, on="key", how="left")
    missing = df[df["Type 1"].isna()]["raw_name"].tolist()
    df = df.dropna(subset=["Type 1"]).reset_index(drop=True)

    df["name"] = df["raw_name"]
    df["types"] = df.apply(
        lambda r: tuple(t for t in (r["Type 1"], r["Type 2"]) if isinstance(t, str)), axis=1)
    df["tier_group"] = df["Tier"].map(TIER_GROUP).fillna("ZU")
    df["P"] = df["tier_group"].map(P_TIER)
    df["banned"] = df["Tier"].isin(UBER_TIERS)
    if attack_mode == "atk":
        df["attack"] = df["Atk"]
    elif attack_mode == "spa":
        df["attack"] = df["SpA"]
    else:
        df["attack"] = df[["Atk", "SpA"]].max(axis=1)
    rng = df["attack"].max() - df["attack"].min()
    df["v"] = (df["attack"] - df["attack"].min()) / (rng if rng else 1)  # normalizado em [0,1]
    cols = ["name", "types", "Tier", "tier_group", "P", "cost", "attack", "v", "banned",
            "HP", "Atk", "Def", "SpA", "SpD", "Spe"]
    return df[cols], missing


# --------------------------------------------------------------------------
# 4. Modelo de otimização
# --------------------------------------------------------------------------
@dataclass
class Config:
    G: int = 6                # nº total de Pokémon por jogador
    C: float = 80.0           # orçamento
    alpha: float = 0.5
    beta: float = 0.5
    reserve_budget: bool = True   # reserva custo mínimo p/ as rodadas futuras
    lookahead: bool = False       # resolve o time completo (sum x = G) em vez de sum x = M
    allow_ubers: bool = False


def objective_coeffs(df, U_idx, cfg):
    """c_i = alpha*v_i + beta*(sum_j P_j Adv(i,j) / (4 sum_j P_j))   (termo da vantagem
    normalizado para [-1,1] para ficar na mesma escala de v_i)."""
    n = len(df)
    adv_term = np.zeros(n)
    if U_idx:
        Pj = df["P"].values[U_idx]
        norm = 4.0 * Pj.sum()
        types = df["types"].values
        for i in range(n):
            adv_term[i] = sum(Pj[k] * advantage(types[i], types[j])
                              for k, j in enumerate(U_idx)) / norm
    return cfg.alpha * df["v"].values + cfg.beta * adv_term, adv_term


def solve(df, A_idx, U_idx, M, cfg, extra_ban=()):
    """Resolve o MILP. Retorna (índices escolhidos, Z) ou (None, None) se inviável."""
    n = len(df)
    c, _ = objective_coeffs(df, U_idx, cfg)
    w = df["cost"].values.astype(float)

    lb, ub = np.zeros(n), np.ones(n)
    lb[A_idx] = 1
    forbidden = set(U_idx) | set(extra_ban)
    if not cfg.allow_ubers:
        forbidden |= set(np.where(df["banned"].values)[0])
    forbidden -= set(A_idx)
    for i in forbidden:
        ub[i] = 0

    size = cfg.G if cfg.lookahead else M
    budget = cfg.C
    if cfg.reserve_budget and not cfg.lookahead:
        # deixa reservado o custo dos (G-M) Pokémon mais baratos ainda disponíveis
        free_costs = sorted(w[i] for i in range(n) if ub[i] == 1 and lb[i] == 0)
        budget -= sum(free_costs[: max(cfg.G - M, 0)])

    res = milp(
        c=-c,  # milp minimiza
        constraints=[LinearConstraint(np.ones((1, n)), size, size),
                     LinearConstraint(w.reshape(1, -1), -np.inf, budget)],
        integrality=np.ones(n),
        bounds=Bounds(lb, ub),
    )
    if not res.success:
        return None, None
    chosen = [i for i in range(n) if res.x[i] > 0.5]
    return chosen, -res.fun


def recommend(df, A_idx, U_idx, M, cfg, top_k=5):
    """Top-k recomendações: resolve, bane a sugestão e resolve de novo."""
    recs, banned_now = [], []
    for _ in range(top_k):
        chosen, Z = solve(df, A_idx, U_idx, M, cfg, extra_ban=banned_now)
        if chosen is None:
            break
        new = [i for i in chosen if i not in A_idx]
        if not new:
            break
        if cfg.lookahead:  # time completo: sugere o novo membro de maior contribuição individual
            c, _ = objective_coeffs(df, U_idx, cfg)
            pick = max(new, key=lambda i: c[i])
        else:
            pick = new[0]
        recs.append((pick, Z, chosen))
        banned_now.append(pick)
    return recs


# --------------------------------------------------------------------------
# 5. Interface de terminal
# --------------------------------------------------------------------------
def fmt_types(t):
    return "/".join(t)


def describe(df, i, U_idx):
    r = df.iloc[i]
    advs = ", ".join(f"{advantage(r['types'], df.iloc[j]['types']):+d} vs {df.iloc[j]['name']}"
                     for j in U_idx) or "-"
    return (f"{r['name']:<22} {fmt_types(r['types']):<17} tier {r['Tier']:<7} "
            f"custo {int(r['cost']):>2}  atk {int(r['attack']):>3}  [{advs}]")


def find_pokemon(df, text, exclude=()):
    text = text.strip().lower()
    names = df["name"].tolist()
    exact = [i for i, n in enumerate(names) if n.lower() == text and i not in exclude]
    if exact:
        return exact[0]
    close = difflib.get_close_matches(text, [n.lower() for n in names], n=1, cutoff=0.6)
    if close:
        i = [n.lower() for n in names].index(close[0])
        return i if i not in exclude else None
    return None


def ask(prompt, default, cast):
    raw = input(f"{prompt} [{default}]: ").strip()
    if not raw:
        return default
    try:
        return cast(raw)
    except ValueError:
        print("  valor inválido, usando o padrão.")
        return default


def opponent_pick(df, taken, cfg, rng, uniform=False):
    avail = [i for i in range(len(df)) if i not in taken and (cfg.allow_ubers or not df["banned"].iloc[i])]
    p = np.ones(len(avail)) if uniform else df["P"].values[avail]
    return int(rng.choice(avail, p=p / p.sum()))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--costs", default="costs_pokemon.csv")
    ap.add_argument("--stats", default="stats_pokemon.csv")
    ap.add_argument("--seed", type=int, default=None, help="semente aleatória (reprodutível)")
    ap.add_argument("--attack", choices=["max", "atk", "spa"], default="max",
                    help="v_i = max(Atk,SpA) (padrão), só Atk, ou só SpA")
    ap.add_argument("--uniform-opponent", action="store_true",
                    help="adversário sorteia uniformemente (padrão: ponderado por P_j)")
    ap.add_argument("--manual-opponent", action="store_true",
                    help="você digita a escolha do adversário em vez de sortear")
    ap.add_argument("--allow-ubers", action="store_true", help="não banir Uber/AG")
    ap.add_argument("--no-reserve", action="store_true",
                    help="modelo literal: não reserva orçamento p/ rodadas futuras")
    ap.add_argument("--lookahead", action="store_true",
                    help="resolve o time inteiro (sum x = G) e sugere o melhor novo membro")
    ap.add_argument("--top", type=int, default=5, help="nº de recomendações exibidas")
    args = ap.parse_args()

    df, missing = load_data(args.costs, args.stats, args.attack)
    rng = np.random.default_rng(args.seed)
    print("=" * 78)
    print(" DRAFT POKÉMON  -  recomendador por otimização")
    print("=" * 78)
    print(f"{len(df)} Pokémon carregados ({int(df['banned'].sum())} Ubers/AG"
          f"{' liberados' if args.allow_ubers else ' banidos'}).")
    if missing:
        print(f"Aviso: {len(missing)} nomes do arquivo de custos sem stats foram ignorados.")

    cfg = Config(allow_ubers=args.allow_ubers, reserve_budget=not args.no_reserve,
                 lookahead=args.lookahead)
    cfg.G = ask("Nº total de Pokémon por jogador (G)", cfg.G, int)
    cfg.C = ask("Orçamento total (C)", cfg.C, float)
    cfg.alpha = ask("Peso da força de ataque (alpha, 0-1)", cfg.alpha, float)
    cfg.beta = ask("Peso da vantagem de tipos (beta, 0-1)", cfg.beta, float)
    cfg.alpha, cfg.beta = min(max(cfg.alpha, 0), 1), min(max(cfg.beta, 0), 1)

    A, U = [], []
    print("\nComandos a cada rodada:  ENTER = aceitar #1 | número = aceitar essa opção |"
          "\n  nome = escolher outro Pokémon | time = ver times | q = sair\n")

    for rnd in range(1, cfg.G + 1):
        print("-" * 78)
        print(f" RODADA {rnd}/{cfg.G}   orçamento restante: "
              f"{cfg.C - df['cost'].values[A].sum():.0f}/{cfg.C:.0f}")
        print("-" * 78)

        # --- adversário escolhe ---
        if args.manual_opponent:
            while True:
                j = find_pokemon(df, input("Pokémon escolhido pelo adversário: "), exclude=set(A) | set(U))
                if j is not None:
                    break
                print("  não encontrado / já escolhido.")
        else:
            j = opponent_pick(df, set(A) | set(U), cfg, rng, args.uniform_opponent)
        U.append(j)
        r = df.iloc[j]
        print(f"Adversário escolheu: {r['name']}  ({fmt_types(r['types'])}, tier {r['Tier']}, "
              f"P={r['P']:.2f})")

        # --- modelo recomenda ---
        recs = recommend(df, A, U, rnd, cfg, top_k=args.top)
        if not recs:
            print("\nO modelo ficou inviável (orçamento insuficiente). Escolha manualmente"
                  " um Pokémon barato ou use 'q' para sair.")
            options = []
        else:
            print("\nRecomendações (modelo de otimização):")
            options = [i for i, _, _ in recs]
            for k, (i, Z, _) in enumerate(recs, 1):
                print(f"  #{k}  Z={Z:6.3f}  {describe(df, i, U)}")

        # --- minha escolha ---
        while True:
            cmd = input("\nSua escolha > ").strip()
            low = cmd.lower()
            if low in ("q", "sair", "quit"):
                print("Encerrado.")
                return
            if low in ("time", "times"):
                print("  Meu time:        ", ", ".join(df["name"].values[A]) or "-")
                print("  Time do adversário:", ", ".join(df["name"].values[U[:-1]]) + (", " if len(U) > 1 else "")
                      + df["name"].values[U[-1]])
                continue
            if cmd == "" and options:
                pick = options[0]
            elif cmd.isdigit() and 1 <= int(cmd) <= len(options):
                pick = options[int(cmd) - 1]
            else:
                pick = find_pokemon(df, cmd, exclude=set(A) | set(U)) if cmd else None
                if pick is None:
                    print("  entrada inválida / Pokémon indisponível.")
                    continue
                if not cfg.allow_ubers and df["banned"].iloc[pick]:
                    print("  esse Pokémon é Uber/AG (banido).")
                    continue
            if df["cost"].values[A].sum() + df["cost"].iloc[pick] > cfg.C:
                print("  estoura o orçamento!")
                continue
            break
        A.append(pick)
        print(f"  ✔ Você escolheu {df['name'].iloc[pick]} (custo {int(df['cost'].iloc[pick])})")

    # --- resumo ---
    print("\n" + "=" * 78)
    print(" TIMES FINAIS")
    print("=" * 78)
    print("Meu time:")
    for i in A:
        print("  ", describe(df, i, []))
    print(f"  custo total: {df['cost'].values[A].sum():.0f}/{cfg.C:.0f}")
    print("Time do adversário:")
    for j in U:
        print("  ", describe(df, j, []))


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nEncerrado.")
        sys.exit(0)

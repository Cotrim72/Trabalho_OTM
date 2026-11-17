#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pokémon: recomendação por otimização (MILP) para n jogadores.

Modelo (resumo):
    max  Z = sum_i ( alpha*v_i + beta*d_i + gamma*r_i ) x_i
        d_i = sum_{j in U}* Advantage(i,j) / (4 sum_j )   (vantagem ofensiva)
        r_i = sum_{j in U}* Resist(i,j)    / (4 sum_j )   (resistência de tipo)
        Resist(i,j) = -Advantage(j,i)
    s.a. sum_i x_i = M                  (M = tamanho do time nesta decisão)
         sum_i w_i x_i <= C             (orçamento)
         sum_{i in Mega} x_i <= E       (no máximo E Mega evoluções por time)
         x_i = 1  para i em A           (meus Pokémon já escolhidos)
         x_i = 0  para i em U ∪ Ubers   (dos adversários / banidos)
         x_i ∈ {0,1}

U é a união dos Pokémon de TODOS os adversários (n-1 adversários).

Adversários simulados ("profissionais"): cada escolha é sorteada com peso
    w_j = P_j^tau * exp( sigma * (0.25*cobertura_nova - 0.5*sobreposição_de_fraquezas) )
onde P_j é a probabilidade de uso do tier (tau = --opp-sharpness concentra a
escolha nos tiers altos; tau=1 reproduz o sorteio ponderado simples). O termo de
sinergia (sigma = --opp-synergy, 0 desliga) favorece quem acrescenta tipos ainda
não cobertos ofensivamente e evita empilhar fraquezas em comum. Os times respeitam
o orçamento C, o limite E de Megas e, na última vaga, gastam o orçamento restante.
--uniform-opponent ignora tudo isso (sorteio uniforme).

Há dois modos de jogo (--mode):

  draft  Você + (n-1) adversários aleatórios. A cada rodada cada adversário
         escolhe um Pokémon, o modelo é resolvido com M = rodada atual e o
         programa recomenda (Top-N) o seu próximo Pokémon.

  game   Não há draft. Os n-1 times adversários (G Pokémon cada) já existem
         (sorteados ou digitados) e o modelo é resolvido uma única vez com
         M = G, devolvendo o melhor time completo para enfrentá-los
         (e os Top-N melhores times alternativos).

Dependências:  pip install pandas numpy scipy
Uso:           python model1.py --costs costs_pokemon.csv --stats stats_pokemon.csv
               python model1.py --mode game --players 4 --ban-illegal
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


def resistance(types_i, types_j) -> int:
    """Resist(i,j) = -Advantage(j,i): os tipos de j atacam i; o sinal é invertido
    (+ se i resiste/é imune, - se i é super efetivamente atingido)."""
    return -advantage(types_j, types_i)


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


def load_data(costs_path, stats_path, attack_mode="max", ban_illegal=False):
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

    n_illegal = 0
    if ban_illegal:  # tier "Illegal" sai do pool: ninguém (nem adversários) pode escolher
        n_illegal = int((df["Tier"] == "Illegal").sum())
        df = df[df["Tier"] != "Illegal"].reset_index(drop=True)

    df["name"] = df["raw_name"]
    df["types"] = df.apply(
        lambda r: tuple(t for t in (r["Type 1"], r["Type 2"]) if isinstance(t, str)), axis=1)
    df["tier_group"] = df["Tier"].map(TIER_GROUP).fillna("ZU")
    df["P"] = df["tier_group"].map(P_TIER)
    df["banned"] = df["Tier"].isin(UBER_TIERS)
    df["mega"] = df["name"].str.match(r"^Mega ")      # conjunto "Mega"
    if attack_mode == "atk":
        df["attack"] = df["Atk"]
    elif attack_mode == "spa":
        df["attack"] = df["SpA"]
    else:
        df["attack"] = df[["Atk", "SpA"]].max(axis=1)
    rng = df["attack"].max() - df["attack"].min()
    df["v"] = (df["attack"] - df["attack"].min()) / (rng if rng else 1)  # normalizado em [0,1]
    cols = ["name", "types", "Tier", "tier_group", "P", "cost", "attack", "v", "banned", "mega",
            "HP", "Atk", "Def", "SpA", "SpD", "Spe"]
    return df[cols], missing, n_illegal


# --------------------------------------------------------------------------
# 4. Modelo de otimização
# --------------------------------------------------------------------------
@dataclass
class Config:
    n_players: int = 2        # nº de jogadores (você + n-1 adversários)
    G: int = 6                # nº total de Pokémon por jogador
    C: float = 80.0           # orçamento
    alpha: float = 0.5        # peso da força de ataque
    beta: float = 0.5         # peso da vantagem ofensiva de tipos
    gamma: float = 0.0        # peso da resistência de tipos (0 = desligado)
    reserve_budget: bool = True   # reserva custo mínimo p/ as rodadas futuras (draft)
    lookahead: bool = False       # (draft) resolve o time completo (sum x = G) em vez de sum x = M
    allow_ubers: bool = False
    E: int = 1                # nº máximo de Mega evoluções por time
    opp_sharp: float = 2.0    # tau: expoente aplicado a P_j na escolha dos adversários
    opp_synergy: float = 1.0  # sigma: peso da sinergia de tipos dos adversários (0 = desliga)


def objective_coeffs(df, U_idx, cfg):
    """c_i = alpha*v_i + beta*d_i + gamma*r_i, com
        d_i = sum_j P_j Adv(i,j)    / (4 sum_j P_j)   (vantagem ofensiva, em [-1,1])
        r_i = sum_j P_j Resist(i,j) / (4 sum_j P_j)   (resistência de tipo, em [-1,1])
    Os termos de tipo são normalizados para ficar na mesma escala de v_i.
    U_idx = Pokémon de todos os adversários.
    Retorna (c, adv_term, res_term)."""
    n = len(df)
    adv_term = np.zeros(n)
    res_term = np.zeros(n)
    if U_idx:
        Pj = df["P"].values[U_idx]
        norm = 4.0 * Pj.sum()
        types = df["types"].values
        for i in range(n):
            adv_term[i] = sum(Pj[k] * advantage(types[i], types[j])
                              for k, j in enumerate(U_idx)) / norm
            res_term[i] = sum(Pj[k] * resistance(types[i], types[j])
                              for k, j in enumerate(U_idx)) / norm
    c = cfg.alpha * df["v"].values + cfg.beta * adv_term + cfg.gamma * res_term
    return c, adv_term, res_term


def solve(df, A_idx, U_idx, M, cfg, extra_ban=(), exclude_sets=()):
    """Resolve o MILP. Retorna (índices escolhidos, Z) ou (None, None) se inviável.

    extra_ban     : Pokémon proibidos nesta resolução (usado no Top-k do draft).
    exclude_sets  : times já encontrados; para cada um é adicionado o corte
                    sum_{i in time} x_i <= |time|-1, o que proíbe repetir o time
                    (usado no Top-k de times do modo 'game')."""
    n = len(df)
    c, _, _ = objective_coeffs(df, U_idx, cfg)
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

    constraints = [LinearConstraint(np.ones((1, n)), size, size),
                   LinearConstraint(w.reshape(1, -1), -np.inf, budget)]
    mega = df["mega"].values.astype(float)
    if cfg.E is not None and mega.any():             # sum_{i in Mega} x_i <= E
        constraints.append(LinearConstraint(mega.reshape(1, -1), -np.inf, cfg.E))
    for team in exclude_sets:
        row = np.zeros((1, n))
        row[0, list(team)] = 1
        constraints.append(LinearConstraint(row, -np.inf, len(team) - 1))

    res = milp(
        c=-c,  # milp minimiza
        constraints=constraints,
        integrality=np.ones(n),
        bounds=Bounds(lb, ub),
    )
    if not res.success:
        return None, None
    chosen = [i for i in range(n) if res.x[i] > 0.5]
    return chosen, -res.fun


def recommend(df, A_idx, U_idx, M, cfg, top_k=5):
    """Top-k recomendações (draft): resolve, bane a sugestão e resolve de novo."""
    recs, banned_now = [], []
    for _ in range(top_k):
        chosen, Z = solve(df, A_idx, U_idx, M, cfg, extra_ban=banned_now)
        if chosen is None:
            break
        new = [i for i in chosen if i not in A_idx]
        if not new:
            break
        if cfg.lookahead:  # time completo: sugere o novo membro de maior contribuição individual
            c, _, _ = objective_coeffs(df, U_idx, cfg)
            pick = max(new, key=lambda i: c[i])
        else:
            pick = new[0]
        recs.append((pick, Z, chosen))
        banned_now.append(pick)
    return recs


def best_teams(df, U_idx, cfg, top_k=3):
    """Modo 'game': melhores times completos (M = G) contra os adversários U_idx.
    Os Top-k times são obtidos com cortes 'no-good' (nunca repete o mesmo time)."""
    teams, cuts = [], []
    for _ in range(top_k):
        chosen, Z = solve(df, [], U_idx, cfg.G, cfg, exclude_sets=cuts)
        if chosen is None:
            break
        teams.append((chosen, Z))
        cuts.append(chosen)
    return teams


# --------------------------------------------------------------------------
# 5. Adversários (sorteio / digitação)
# --------------------------------------------------------------------------
def _affordable(costs, budget, slots_left):
    """Máscara dos Pokémon que ainda deixam o time completável dentro do orçamento:
    custo_i + (soma dos (slots_left-1) mais baratos restantes) <= budget."""
    n = len(costs)
    order = np.argsort(costs, kind="stable")
    rank = np.empty(n, dtype=int)
    rank[order] = np.arange(n)
    pref = np.concatenate([[0.0], np.cumsum(costs[order])])
    k = max(slots_left - 1, 0)
    rest = np.where(rank < k, pref[min(k + 1, n)] - costs, pref[min(k, n)])
    return costs + rest <= budget


_TYPE_CACHE = {}


def type_matrices(df):
    """W[i,t] = True se o Pokémon i é fraco ao tipo t (multiplicador > 1);
    S[i,u] = True se algum tipo de i (STAB) é super efetivo contra o tipo puro u."""
    c = _TYPE_CACHE.get(id(df))
    if c is not None and c[0] is df:
        return c[1], c[2]
    types = df["types"].values
    W = np.array([[type_multiplier(t, ti) > 1 for t in TYPES] for ti in types], dtype=bool)
    S = np.array([[any(type_multiplier(a, (u,)) > 1 for a in ti) for u in TYPES]
                  for ti in types], dtype=bool)
    _TYPE_CACHE[id(df)] = (df, W, S)
    return W, S


def opponent_weights(df, avail, team, cfg, budget_left, slots_left):
    """Pesos de sorteio dos candidatos 'avail' para um adversário que já tem 'team'.
        w_j = P_j^tau * exp(sigma*(0.25*cobertura_nova - 0.5*sobreposição))
    cobertura_nova: nº de tipos defensores que j acerta super efetivamente e o time ainda não;
    sobreposição  : média, sobre o time, de fraquezas de tipo em comum com j."""
    w = df["P"].values[avail] ** cfg.opp_sharp
    if cfg.opp_synergy > 0 and len(team):
        W, S = type_matrices(df)
        t = np.array(team, dtype=int)
        overlap = (W[avail].astype(int) @ W[t].astype(int).T).mean(axis=1)
        new_cov = (S[avail] & ~S[t].any(axis=0)).sum(axis=1)
        w = w * np.exp(cfg.opp_synergy * (0.25 * new_cov - 0.5 * overlap))
    if budget_left is not None and slots_left == 1:      # última vaga: não deixa orçamento sobrando
        w = w * np.exp(-0.3 * np.maximum(budget_left - df["cost"].values[avail], 0))
    return w


def opponent_pick(df, taken, cfg, rng, uniform=False, budget_left=None, slots_left=1, team=()):
    """Sorteia um Pokémon para um adversário que já possui 'team'. Só entram candidatos
    livres, não banidos, que respeitam o limite E de Megas e que mantêm o time completável
    dentro do orçamento (times legais). Os pesos vêm de opponent_weights()."""
    n = len(df)
    ok = np.ones(n, dtype=bool)
    if len(taken):
        ok[np.array(list(taken), dtype=int)] = False
    if not cfg.allow_ubers:
        ok &= ~df["banned"].values
    mega = df["mega"].values
    if cfg.E is not None and len(team) and mega[np.array(team, dtype=int)].sum() >= cfg.E:
        ok &= ~mega
    avail = np.flatnonzero(ok)
    if budget_left is not None:
        costs = df["cost"].values[avail].astype(float)
        mask = _affordable(costs, budget_left, slots_left)
        if mask.any():
            avail = avail[mask]
        else:  # não há como caber: escolhe o mais barato para minimizar o estouro
            return int(avail[np.argmin(costs)])
    p = np.ones(len(avail)) if uniform else opponent_weights(df, avail, team, cfg,
                                                              budget_left, slots_left)
    if not np.isfinite(p).all() or p.sum() <= 0:
        p = df["P"].values[avail]
    return int(rng.choice(avail, p=p / p.sum()))


def random_team(df, taken, cfg, rng, uniform=False):
    """Time adversário completo (G Pokémon) sorteado, respeitando o orçamento C e o limite E de Megas."""
    team = []
    for s in range(cfg.G):
        spent = df["cost"].values[team].sum() if team else 0.0
        team.append(opponent_pick(df, set(taken) | set(team), cfg, rng, uniform,
                                  budget_left=cfg.C - spent, slots_left=cfg.G - s, team=team))
    return team


def read_opponent_team(df, k, G, C, taken, E=None):
    """Digitação manual de um time adversário completo."""
    team = []
    print(f"\nAdversário {k + 1}: digite {G} Pokémon")
    while len(team) < G:
        j = find_pokemon(df, input(f"  Pokémon {len(team) + 1}/{G}: "),
                         exclude=set(taken) | set(team))
        if j is None:
            print("  não encontrado / já escolhido.")
            continue
        team.append(j)
        print(f"    -> {df['name'].iloc[j]}")
    if df["cost"].values[team].sum() > C:
        print(f"  aviso: esse time custa {df['cost'].values[team].sum():.0f}, acima do orçamento C={C:.0f}.")
    if E is not None and df["mega"].values[team].sum() > E:
        print(f"  aviso: esse time tem {int(df['mega'].values[team].sum())} Megas, acima do limite E={E}.")
    return team


# --------------------------------------------------------------------------
# 6. Interface de terminal (utilidades)
# --------------------------------------------------------------------------
def fmt_types(t):
    return "/".join(t)


def describe(df, i, vs=(), terms=None):
    """Linha descritiva de um Pokémon. vs = Pokémon contra os quais mostrar a
    vantagem de tipo; terms = (adv_term, res_term) para mostrar d_i e r_i."""
    r = df.iloc[i]
    s = (f"{r['name']:<22} {fmt_types(r['types']):<17} tier {r['Tier']:<7} "
         f"custo {int(r['cost']):>2}  atk {int(r['attack']):>3}")
    if terms is not None:
        s += f"  d={terms[0][i]:+.2f} r={terms[1][i]:+.2f}"
    if len(vs):
        s += "  [" + ", ".join(f"{advantage(r['types'], df.iloc[j]['types']):+d} vs {df.iloc[j]['name']}"
                               for j in vs) + "]"
    return s


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


def ask_yes_no(prompt, default=False):
    """Pergunta sim/não. ENTER = padrão."""
    hint = "S/n" if default else "s/N"
    while True:
        raw = input(f"{prompt} [{hint}]: ").strip().lower()
        if not raw:
            return default
        if raw in ("s", "sim", "y", "yes"):
            return True
        if raw in ("n", "nao", "não", "no"):
            return False
        print("  responda s ou n.")


def print_teams(df, A, opp):
    print("  Meu time:        ", ", ".join(df["name"].values[A]) or "-")
    for k, team in enumerate(opp, 1):
        print(f"  Adversário {k}:".ljust(19), ", ".join(df["name"].values[team]) or "-")


def print_opponent_teams(df, opp, C=None):
    for k, team in enumerate(opp, 1):
        cost = df["cost"].values[team].sum()
        flag = f"  <-- acima do orçamento {C:.0f}" if C is not None and cost > C else ""
        print(f"\nAdversário {k}  (custo {cost:.0f}){flag}:")
        for j in team:
            print("  ", describe(df, j))


def choose_mode(arg):
    if arg:
        return arg
    print("Modos de jogo:")
    print("  1) draft - você e n-1 adversários aleatórios escolhem Pokémon rodada a rodada")
    print("  2) game  - times adversários já prontos; o modelo monta o melhor time contra eles")
    while True:
        raw = input("Escolha o modo [1]: ").strip().lower()
        if raw in ("", "1", "draft"):
            return "draft"
        if raw in ("2", "game", "jogo"):
            return "game"
        print("  opção inválida.")


def configure(args, df, allow_ubers):
    cfg = Config(allow_ubers=allow_ubers, reserve_budget=not args.no_reserve,
                 lookahead=args.lookahead, E=args.max_mega,
                 opp_sharp=args.opp_sharpness, opp_synergy=args.opp_synergy)
    cfg.n_players = max(ask("Nº de jogadores (n = você + n-1 adversários)", args.players, int), 2)
    cfg.G = max(ask("Nº total de Pokémon por jogador (G)", cfg.G, int), 1)
    cfg.C = ask("Orçamento total (C)", cfg.C, float)
    cfg.E = max(ask("Máx. de Mega evoluções por time (E)", cfg.E, int), 0)
    cfg.alpha = ask("Peso da força de ataque (alpha, 0-1)", cfg.alpha, float)
    cfg.beta = ask("Peso da vantagem de tipos (beta, 0-1)", cfg.beta, float)
    cfg.gamma = ask("Peso da resistência de tipos (gamma, 0-1)", cfg.gamma, float)
    cfg.alpha, cfg.beta, cfg.gamma = (min(max(w, 0), 1) for w in (cfg.alpha, cfg.beta, cfg.gamma))

    pool = len(df) - (0 if cfg.allow_ubers else int(df["banned"].sum()))
    if cfg.n_players * cfg.G > pool:
        sys.exit(f"Pool insuficiente: {cfg.n_players} jogadores x {cfg.G} Pokémon = "
                 f"{cfg.n_players * cfg.G} > {pool} disponíveis.")
    return cfg


# --------------------------------------------------------------------------
# 7. Modo 1: DRAFT com n jogadores
# --------------------------------------------------------------------------
def play_draft(df, cfg, args, rng):
    n_opp = cfg.n_players - 1
    A = []
    opp = [[] for _ in range(n_opp)]

    print(f"\nModo DRAFT: você + {n_opp} adversário(s).")
    print("Comandos a cada rodada:  ENTER = aceitar #1 | número = aceitar essa opção |"
          "\n  nome = escolher outro Pokémon | time = ver times | q = sair\n")

    for rnd in range(1, cfg.G + 1):
        print("-" * 78)
        print(f" RODADA {rnd}/{cfg.G}   orçamento restante: "
              f"{cfg.C - df['cost'].values[A].sum():.0f}/{cfg.C:.0f}")
        print("-" * 78)

        # --- cada adversário escolhe ---
        this_round = []
        for k in range(n_opp):
            taken = set(A) | {j for team in opp for j in team}
            if args.manual_opponent:
                while True:
                    j = find_pokemon(df, input(f"Pokémon escolhido pelo adversário {k + 1}: "),
                                     exclude=taken)
                    if j is not None:
                        break
                    print("  não encontrado / já escolhido.")
            else:
                spent = df["cost"].values[opp[k]].sum() if opp[k] else 0.0
                j = opponent_pick(df, taken, cfg, rng, args.uniform_opponent,
                                  budget_left=cfg.C - spent, slots_left=cfg.G - len(opp[k]),
                                  team=opp[k])
            if df["cost"].values[opp[k]].sum() + df["cost"].iloc[j] > cfg.C:
                print(f"  aviso: o time do adversário {k + 1} passa do orçamento C={cfg.C:.0f}.")
            if df["mega"].values[opp[k] + [j]].sum() > cfg.E:
                print(f"  aviso: o time do adversário {k + 1} passa do limite de Megas E={cfg.E}.")
            opp[k].append(j)
            this_round.append(j)
            r = df.iloc[j]
            print(f"Adversário {k + 1} escolheu: {r['name']}  ({fmt_types(r['types'])}, "
                  f"tier {r['Tier']}, P={r['P']:.2f})")

        U = [j for team in opp for j in team]

        # --- modelo recomenda ---
        recs = recommend(df, A, U, rnd, cfg, top_k=args.top)
        _, adv_t, res_t = objective_coeffs(df, U, cfg)
        if not recs:
            print("\nO modelo ficou inviável (orçamento insuficiente). Escolha manualmente"
                  " um Pokémon barato ou use 'q' para sair.")
            options = []
        else:
            print("\nRecomendações (modelo de otimização):")
            options = [i for i, _, _ in recs]
            for k, (i, Z, _) in enumerate(recs, 1):
                print(f"  #{k}  Z={Z:6.3f}  {describe(df, i, vs=this_round, terms=(adv_t, res_t))}")

        # --- minha escolha ---
        while True:
            cmd = input("\nSua escolha > ").strip()
            low = cmd.lower()
            if low in ("q", "sair", "quit"):
                print("Encerrado.")
                return
            if low in ("time", "times"):
                print_teams(df, A, opp)
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
            if df["mega"].values[A].sum() + df["mega"].iloc[pick] > cfg.E:
                print(f"  passa do limite de Mega evoluções (E={cfg.E}).")
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
        print("  ", describe(df, i))
    print(f"  custo total: {df['cost'].values[A].sum():.0f}/{cfg.C:.0f}")
    print_opponent_teams(df, opp, cfg.C)


# --------------------------------------------------------------------------
# 8. Modo 2: JOGO com times adversários já prontos
# --------------------------------------------------------------------------
def print_matchups(df, team, opp):
    """Tabela ofensa/defesa de cada Pokémon meu contra cada time adversário:
    soma de Advantage(i,j) / soma de Resist(i,j) sobre os Pokémon j do time."""
    print("\nConfronto de tipos (ofensa/defesa, somado sobre cada time adversário):")
    print(" " * 22 + "".join(f"{'Adv ' + str(k):>10}" for k in range(1, len(opp) + 1)))
    types = df["types"].values
    for i in team:
        cells = []
        for t in opp:
            off = sum(advantage(types[i], types[j]) for j in t)
            dfn = sum(resistance(types[i], types[j]) for j in t)
            cells.append(f"{off:+d}/{dfn:+d}".rjust(10))
        print(f"{df['name'].iloc[i]:<22}" + "".join(cells))


def show_game_result(df, teams, U, opp, cfg):
    c, adv_t, res_t = objective_coeffs(df, U, cfg)
    chosen, Z = teams[0]
    chosen = sorted(chosen, key=lambda i: -c[i])
    print("\n" + "=" * 78)
    print(f" MELHOR TIME CONTRA {len(opp)} ADVERSÁRIO(S)   Z = {Z:.3f}")
    print("=" * 78)
    for i in chosen:
        print("  ", describe(df, i, terms=(adv_t, res_t)))
    print(f"  custo total: {df['cost'].values[chosen].sum():.0f}/{cfg.C:.0f}")
    print_matchups(df, chosen, opp)
    if len(teams) > 1:
        print("\nTimes alternativos:")
        for k, (t, z) in enumerate(teams[1:], 2):
            t = sorted(t, key=lambda i: -c[i])
            print(f"  #{k}  Z={z:6.3f}  custo {df['cost'].values[t].sum():.0f}/{cfg.C:.0f}  "
                  + ", ".join(df["name"].values[t]))


def play_game(df, cfg, args, rng):
    n_opp = cfg.n_players - 1
    print(f"\nModo JOGO: {n_opp} time(s) adversário(s) de {cfg.G} Pokémon; "
          f"o modelo monta o seu time (M = G = {cfg.G}).")

    while True:
        # --- times adversários (disjuntos entre si) ---
        opp, taken = [], set()
        for k in range(n_opp):
            team = (read_opponent_team(df, k, cfg.G, cfg.C, taken, cfg.E) if args.manual_opponent
                    else random_team(df, taken, cfg, rng, args.uniform_opponent))
            opp.append(team)
            taken |= set(team)
        print_opponent_teams(df, opp, cfg.C)
        U = [j for team in opp for j in team]

        # --- modelo: M = G, A = vazio ---
        teams = best_teams(df, U, cfg, top_k=args.top)
        if not teams:
            print("\nO modelo ficou inviável (orçamento C insuficiente para G Pokémon).")
        else:
            show_game_result(df, teams, U, opp, cfg)

        if args.manual_opponent:
            break
        if input("\nSortear novos adversários? [s/N]: ").strip().lower() not in ("s", "sim", "y"):
            break


# --------------------------------------------------------------------------
# 9. main
# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--costs", default="costs_pokemon.csv")
    ap.add_argument("--stats", default="stats_pokemon.csv")
    ap.add_argument("--mode", choices=["draft", "game"], default=None,
                    help="draft (escolhas rodada a rodada) ou game (times adversários prontos); "
                         "se omitido, pergunta no terminal")
    ap.add_argument("--players", type=int, default=2,
                    help="nº de jogadores n = você + n-1 adversários (padrão 2)")
    ap.add_argument("--seed", type=int, default=None, help="semente aleatória (reprodutível)")
    ap.add_argument("--attack", choices=["max", "atk", "spa"], default="max",
                    help="v_i = max(Atk,SpA) (padrão), só Atk, ou só SpA")
    ap.add_argument("--uniform-opponent", action="store_true",
                    help="adversários sorteiam uniformemente (ignora tier e sinergia)")
    ap.add_argument("--opp-sharpness", type=float, default=2.0,
                    help="tau: adversários sorteiam com peso P_j^tau (1 = ponderado simples; "
                         "maior = mais concentrado nos tiers altos; padrão 2)")
    ap.add_argument("--opp-synergy", type=float, default=1.0,
                    help="sigma: força da sinergia de tipos nas escolhas dos adversários "
                         "(0 = só tier; padrão 1)")
    ap.add_argument("--max-mega", type=int, default=1,
                    help="E: nº máximo de Mega evoluções por time (padrão 1)")
    ap.add_argument("--manual-opponent", action="store_true",
                    help="você digita as escolhas dos adversários em vez de sortear")
    ap.add_argument("--allow-ubers", action="store_true", help="libera Uber/AG (sem a flag, o programa pergunta)")
    ap.add_argument("--ban-illegal", action="store_true",
                    help="remove os Pokémon do tier Illegal do pool (sem a flag, o programa pergunta)")
    ap.add_argument("--no-reserve", action="store_true",
                    help="(draft) modelo literal: não reserva orçamento p/ rodadas futuras")
    ap.add_argument("--lookahead", action="store_true",
                    help="(draft) resolve o time inteiro (sum x = G) e sugere o melhor novo membro")
    ap.add_argument("--top", type=int, default=5,
                    help="nº de recomendações (draft) ou de times alternativos (game)")
    args = ap.parse_args()

    rng = np.random.default_rng(args.seed)
    print("=" * 78)
    print(" POKÉMON  -  recomendador por otimização")
    print("=" * 78)

    # Escolhas de pool: a flag da linha de comando vale e dispensa a pergunta;
    # sem a flag, o programa pergunta (ENTER = não).
    mode = choose_mode(args.mode)
    allow_ubers = args.allow_ubers or ask_yes_no("Liberar os Pokémon Uber/AG (por padrão são banidos)?")
    ban_illegal = args.ban_illegal or ask_yes_no("Banir os Pokémon do tier Illegal?")

    df, missing, n_illegal = load_data(args.costs, args.stats, args.attack, ban_illegal)
    print(f"\n{len(df)} Pokémon carregados ({int(df['banned'].sum())} Ubers/AG"
          f"{' liberados' if allow_ubers else ' banidos'}).")
    if ban_illegal:
        print(f"{n_illegal} Pokémon do tier Illegal removidos do pool.")
    if missing:
        print(f"Aviso: {len(missing)} nomes do arquivo de custos sem stats foram ignorados.")

    cfg = configure(args, df, allow_ubers)
    if mode == "draft":
        play_draft(df, cfg, args, rng)
    else:
        play_game(df, cfg, args, rng)


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nEncerrado.")
        sys.exit(0)
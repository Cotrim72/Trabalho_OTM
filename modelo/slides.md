---
title: "Otimização de Equipes em Pokémon Draft Leagues"
subtitle: "Recomendação sequencial e montagem de times via Programação Linear Inteira (MILP)"
author: "Grupo: [nomes]"
institute: "Disciplina: [nome]"
date: "[dd/mm/aaaa]"
lang: pt-BR
aspectratio: 169
fontsize: 16pt
---

# 1. Introdução: O Problema das Draft Leagues

- **Contexto:** Pokémon (1996, Nintendo/Game Freak) possui um cenário competitivo estruturado em comunidades como a *Smogon University* (tiers de uso desde meados dos anos 2000).
- **Formato Draft League:** Jogadores escolhem equipes exclusivas em rodadas alternadas, respeitando um **orçamento fixo de pontos** (cada Pokémon tem um custo proporcional à sua força).
- **Desafio de decisão:** A cada rodada, o pool encolhe e as escolhas dos adversários alteram quais tipos e estatísticas são mais valiosos.
- **Aplicações atuais:** O problema é isomorfo ao **Problema da Mochila com Cardinalidade** (*Cardinality-Constrained Knapsack*), usado em *fantasy sports* (NBA, NFL, Cartola), alocação de portfólios e montagem de equipes sob restrição orçamentária.

---

# 2. Modelo Matemático: Probabilidade de Uso por Tier ($P_j$)

Nem todo Pokémon do elenco adversário $U$ tem a mesma chance de entrar em batalha. Para ponderar as ameaças mais prováveis, cada Pokémon $j$ recebe uma **probabilidade de uso** $P_j$ conforme sua *tier* competitiva na Smogon:

| Grupo de Tier | Tiers incluídas | Probabilidade ($P_j$) |
|:--------------|:----------------|:---------------------:|
| **OU** (*OverUsed*) | OU, UUBL, Uber, AG | **0,95** |
| **UU** (*UnderUsed*) | UU, RUBL | **0,80** |
| **RU** (*RarelyUsed*) | RU, NUBL | **0,60** |
| **NU** (*NeverUsed*) | NU, PUBL | **0,40** |
| **PU** (*PartiallyUsed*) | PU, ZUBL | **0,20** |
| **ZU** (*ZeroUsed*) | ZU, LC, NFE, Illegal, etc. | **0,05** |

- **Parametrização arbitrária:** Os valores de $P_j \in [0{,}05;\; 0{,}95]$ foram atribuídos de forma **arbitrária** (heurística monotônica), refletindo apenas a hierarquia qualitativa de força e frequência de uso entre as divisões.

---

# 2. Modelo Matemático: Vantagem e Resistência de Tipos

Seja $T_i$ o conjunto de tipos (1 ou 2) do Pokémon $i$. Para um tipo atacante $t \in T_i$ contra o defensor $j$, o multiplicador total é $m(t,j) = \prod_{d \in T_j} f(t,d)$, onde $f \in \{0, \frac{1}{2}, 1, 2\}$.

Definimos o escore do tipo $t$ contra $j$ e a **vantagem ofensiva** $\text{Advantage}(i,j)$:

$$
s(t,j) = \begin{cases}
+2, & \text{se } m(t,j) > 1 \quad (\text{super efetivo}) \\
-2, & \text{se } m(t,j) < 1 \quad (\text{resistido ou imune}) \\
\phantom{+}0, & \text{se } m(t,j) = 1 \quad (\text{neutro})
\end{cases}
\qquad
\text{Advantage}(i,j) = \sum_{t \in T_i} s(t,j) \in [-4, 4]
$$

- **Resistência defensiva:** Espelho da vantagem ofensiva quando os tipos de $j$ atacam $i$:
  $$\text{Resist}(i,j) = -\text{Advantage}(j,i) = -\sum_{t \in T_j} s(t,i)$$
- **Aproximação chave:** Os golpes de cada Pokémon são aproximados apenas pelos seus **tipos base** (efeito STAB), mantendo o modelo linear.

---

# 2. Modelo Matemático: Construção dos Coeficientes

Para cada Pokémon $i \in N$, agregamos três critérios normalizados na mesma escala:

1. **Força de ataque ($v_i \in [0,1]$):** maior atributo ofensivo ($a_i = \max(\text{Atk}_i, \text{SpA}_i)$) normalizado via min-max:
   $$v_i = \frac{a_i - \min_k a_k}{\max_k a_k - \min_k a_k}$$
2. **Vantagem ofensiva normalizada ($d_i \in [-1,1]$):** eficácia contra o conjunto adversário $U$, ponderada pela probabilidade arbitrária $P_j$ e dividida pelo máximo teórico ($4 \sum P_j$):
   $$d_i = \frac{\sum_{j \in U} P_j \,\text{Advantage}(i,j)}{4 \sum_{j \in U} P_j}$$
3. **Resistência defensiva normalizada ($r_i \in [-1,1]$):**
   $$r_i = \frac{\sum_{j \in U} P_j \,\text{Resist}(i,j)}{4 \sum_{j \in U} P_j}$$

*(Caso $U = \emptyset$, define-se $d_i = r_i = 0$.)*

---

# 2. Modelo Matemático: Função Objetivo

A função objetivo maximiza a qualidade agregada do time por meio de uma **soma ponderada multiobjetivo**:

$$
\max Z = \sum_{i \in N} c_i x_i, \quad \text{onde} \quad c_i = \alpha v_i + \beta d_i + \gamma r_i
$$

- **Por que somar os termos?** Como $v_i \in [0,1]$ e $d_i, r_i \in [-1,1]$ estão na mesma ordem de grandeza, os pesos $\alpha, \beta, \gamma \in [0,1]$ controlam diretamente o *trade-off* estratégico entre **poder bruto** ($\alpha$), **pressão ofensiva de tipos** ($\beta$) e **solidez defensiva** ($\gamma$).
- **Papel dos parâmetros:** Apenas a proporção entre $(\alpha, \beta, \gamma)$ altera a equipe ótima; zerar um peso desliga o critério correspondente.
- **Preservação da linearidade:** Por serem parâmetros fixos definidos *a priori* (e não variáveis de decisão), o coeficiente $c_i$ é constante para cada candidato $i$, garantindo que $Z$ permaneça estritamente linear.

---

# 2. Modelo Matemático: Todas as Restrições do Draft

Considerando a rodada atual $M \in \{1, \dots, G\}$ e o conjunto livre $F = \{i \in N : i \notin U \cup \text{Ubers}\} \setminus A$:

1. **Número de escolhas na rodada:** A cada rodada adiciona-se exatamente um novo integrante, logo o time deve possuir exatamente $M$ Pokémon:
   $$\sum_{i \in N} x_i = M$$
2. **Orçamento com reserva futura:** O custo acumulado não pode exceder $B_M$, que reserva saldo para contratar os $G - M$ Pokémon mais baratos ainda disponíveis ($w_{(1)} \le w_{(2)} \le \dots$):
   $$\sum_{i \in N} w_i x_i \le B_M, \quad \text{onde } B_M = C - \sum_{k=1}^{G-M} w_{(k)}$$
3. **Permanência das escolhas anteriores:** Pokémon já contratados pelo jogador permanecem obrigatoriamente na equipe:
   $$x_i = 1 \quad \forall i \in A$$
4. **Exclusividade e banimentos:** Pokémon já escolhidos pelos adversários ($U$) ou banidos ($\text{Ubers}$) são bloqueados:
   $$x_i = 0 \quad \forall i \in (U \cup \text{Ubers}) \setminus A$$
5. **Domínio binário:** Cada candidato é escolhido integralmente ou descartado:
   $$x_i \in \{0, 1\} \quad \forall i \in N$$

---

# 2. Modelo Matemático: Formulação Final (MILP)

Agrupando a função objetivo (com pesos fixos $\alpha, \beta, \gamma \in [0,1]$) e todas as restrições do problema na rodada $M$:

$$
\begin{aligned}
\max \quad & Z = \sum_{i \in N} (\alpha v_i + \beta d_i + \gamma r_i) x_i \\
\text{s.a.} \quad & \sum_{i \in N} x_i = M \\
& \sum_{i \in N} w_i x_i \le B_M \\
& x_i = 1 && \forall i \in A \\
& x_i = 0 && \forall i \in (U \cup \text{Ubers}) \setminus A \\
& x_i \in \{0, 1\} && \forall i \in N
\end{aligned}
$$

- **Garantia de viabilidade:** A reserva $B_M$ impede que o modelo gaste todo o orçamento cedo e fique sem saldo para completar os $G$ integrantes nas rodadas finais.

---

# 3. Solução: Arquitetura e Implementação

- **Base de dados oficial:** Os testes utilizam dados oficiais de **status** (*stats*) e tabelas de **custos** extraídos do site oficial da **Smogon**, uma das principais plataformas e referências competitivas em *Draft Leagues* de Pokémon.
- **Stack em Python:** Manipulação de dados e álgebra matricial com `pandas` e `numpy`; otimização via `scipy.optimize.milp`.
- **Algoritmo de Programação Inteira:** O `scipy.optimize.milp` utiliza o solver **HiGHS**, baseado no método **Branch-and-Cut** (com relaxações lineares via Simplex/Pontos Interiores, planos de corte e heurísticas primais).
- **Estrutura em 3 scripts:**
  1. **Simulador principal (`model1.py`):** Possui dois modos — *Draft* (você + $n-1$ adversários aleatórios escolhendo rodada a rodada) e *Game* (gera $n-1$ equipes prontas e calcula o melhor time completo contra elas). **Ambos utilizam exatamente o mesmo MILP**, alterando apenas os parâmetros $M$ (rodada atual vs. $G$) e $B_M$ (com reserva vs. orçamento total $C$).
  2. **Análise de sensibilidade (`sensibility.py`):** Avalia o impacto da variação dos pesos ($\alpha$, $\beta$ e $\gamma$) sobre custo, ataque e vantagem/resistência de tipos frente aos mesmos adversários.
  3. **Abordagem de duelo:** Dado o *roster* de $n$ Pokémon já conquistados na liga, seleciona o melhor subconjunto de $m$ Pokémon ($m \le n$) para enfrentar o time do adversário na batalha.

---

# 3. Solução: Demonstração em Rodada de Draft

Configuração: $G = 6$ Pokémon, orçamento $C = 80$, pesos $(\alpha, \beta, \gamma) = (0{,}5;\; 0{,}5;\; 0)$, semente 17.

- **Escolha do adversário (Rodada 1):** *Hisuian Typhlosion* (Fogo/Fantasma, tier RU, $P_j = 0{,}60$).
- **Top #1 Recomendado pelo MILP:** **Mega Tyranitar**
  - **Tipos:** Rocha / Sombrio (super efetivo contra ambos os tipos do oponente $\rightarrow \text{Advantage} = +4$, $d_i = +1{,}00$).
  - **Poder ofensivo:** $\text{Atk} = 164$ ($v_i = 0{,}85$).
  - **Custo:** $w_i = 6$ (preserva $74$ pontos para as 5 vagas restantes).

---

# 3. Solução: Análise de Sensibilidade dos Pesos

Fixamos 3 adversários (18 Pokémon; tipos mais frequentes: Lutador, Terra, Fantasma, Fogo) e resolvemos o time completo ($M = G = 6$, $C = 80$) variando $(\alpha, \beta, \gamma)$:

| Cenário $(\alpha, \beta, \gamma)$ | Custo | Atk médio | $d$ médio | $r$ médio | Perfil dominante do time |
|:----------------------------------|:-----:|:---------:|:---------:|:---------:|:-------------------------|
| **$\alpha$ dom.** $(0{,}70;\; 0{,}15;\; 0{,}15)$ | 76 | **175** | +0,10 | +0,08 | Megas ofensivos (Mewtwo X/Y, Alakazam) |
| **$\beta$ dom.** $(0{,}15;\; 0{,}70;\; 0{,}15)$ | 59 | 135 | **+0,28** | +0,31 | Núcleo Fada/Voador (Altaria, Togekiss) |
| **$\gamma$ dom.** $(0{,}15;\; 0{,}15;\; 0{,}70)$ | **40** | 118 | +0,27 | **+0,35** | Defensivo econômico (Primarina, Togetic) |
| **Iguais** $(0{,}33;\; 0{,}33;\; 0{,}33)$ | 59 | 135 | +0,28 | +0,31 | Mesmo time de $\beta$ dominante |

*Nota:* O valor absoluto de $Z$ não é comparável entre cenários pois a escala muda com os pesos; avaliamos o trade-off pelas métricas físicas.

---

# 3. Solução: Abordagem de Duelo (Problema Trivial)

Na etapa de batalha, o jogador já possui um *roster* $R$ ($|R| = n$) pago no draft e precisa escolher $m$ Pokémon ($m \le n$) contra o elenco adversário $O$:

$$
\max \quad Z = \sum_{i \in R} (\beta d_i + \gamma r_i) x_i \qquad \text{s.a.} \quad \sum_{i \in R} x_i = m, \quad x_i \in \{0, 1\}
$$

- **Por que o problema se torna trivial?**
  1. **Sem restrição de orçamento:** Os custos $w_i$ já foram pagos no draft; não há mochila (*knapsack*), apenas a cardinalidade fixa $m$.
  2. **Separabilidade linear:** O escore $s_i = \beta d_i + \gamma r_i$ de cada Pokémon $i \in R$ é independente dos demais escolhidos.
- **Solução exata sem Branch-and-Cut:** Resolver o MILP é matematicamente equivalente a **ordenar** os $n$ Pokémon do *roster* em ordem decrescente de $s_i$ e selecionar os **$m$ primeiros** — complexidade $\mathcal{O}(n \log n)$.

---

# 4. Discussão: Limitações, Casos Especiais e Extensões

- **Limitação (Separabilidade):** Como $c_i$ depende apenas do Pokémon $i$ e não dos pares $(i, k)$ do próprio time, o modelo pode recomendar **tipos repetidos** (ex.: 5 Fadas em $\beta$ dominante) sem penalizar redundância.
- **Aproximações de combate e calibragem:** Desconsidera golpes de cobertura (*coverage moves*), velocidade (*Speed tiers*), habilidades/itens e utiliza probabilidades de uso $P_j$ arbitradas manualmente.
- **Casos especiais:**
  - *Rodada 1 sem histórico ($U = \emptyset$):* $d_i = r_i = 0$, reduzindo o problema ao critério puro de poder/custo.
  - *Abordagem de Duelo:* Sem orçamento e com função separável, colapsa em uma simples **ordenação** ($\mathcal{O}(n \log n)$).
- **Generalizações futuras:**
  - **Programação Quadrática Binária (MIQP):** Adicionar termos de sinergia $-\lambda \sum_{i < k} \text{Overlap}(T_i, T_k) x_i x_k$ para diversificar tipos.
  - **Calibragem empírica de $P_j$ e Lookahead:** Estimar $P_j$ a partir de estatísticas reais de uso da Smogon e simular escolhas futuras dos adversários (já prototipado via flag `--lookahead`).

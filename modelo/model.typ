#set page(paper: "a4", margin: (x: 2.5cm, y: 2.5cm))
#set text(font: "New Computer Modern", size: 11pt, lang: "pt")
#set heading(numbering: "1.1")
#show math.equation: set text(font: "New Computer Modern Math")

#align(center)[
  #block(width: 80%)[
    #text(weight: "bold", size: 14pt)[Modelo Matemático: Otimização de Equipe em Draft Leagues]\
    #text(size: 10pt, fill: luma(100))[Programação Linear Inteira (MILP) Aplicada a Pokémon]
  ]
]

#v(1em)

= Definições comuns

Estas definições valem para os dois modelos (draft e duelo).

== Tiers e probabilidade de uso

Cada Pokémon $j$ pertence a uma tier do arquivo de dados, que é agrupada em uma das seis tiers de uso da Smogon. A probabilidade de uso $P_j$ depende apenas desse grupo:

- $"OU"$ (OverUsed): a tier principal do competitivo, com os Pokémon mais usados e fortes.
- $"UU"$ (UnderUsed): não tiveram uso suficiente para ficar em OU, mas ainda são muito competitivos.
- $"RU"$ (RarelyUsed): Pokémon que caíram de UU, de poder intermediário.
- $"NU"$ (NeverUsed): estatísticas ou tipagens mais limitadas, mas viáveis entre si.
- $"PU"$ (PartiallyUsed): uma das tiers mais baixas baseadas em uso.
- $"ZU"$ (ZeroUsed): Pokémon que não atingiram uso nem em PU (evoluções intermediárias, Pokémon muito fracos etc.).

#figure(
  table(
    columns: (auto, auto, auto),
    align: center,
    [*Tier no arquivo*], [*Grupo de uso*], [*$P_j$*],
    [OU, UUBL, Uber, AG], [OU], [0,95],
    [UU, RUBL], [UU], [0,80],
    [RU, NUBL], [RU], [0,60],
    [NU, PUBL], [NU], [0,40],
    [PU, ZUBL], [PU], [0,20],
    [ZU, LC, NFE, CAP, CAP LC, CAP NFE, Illegal], [ZU], [0,05],
  ),
  caption: [Mapeamento de tiers para probabilidade de uso. Tiers ausentes da tabela são tratadas como ZU.],
)

== Vantagem de tipo (ataque)

Seja $T_i$ o conjunto de tipos (um ou dois) do Pokémon $i$. Para um tipo atacante $t$ e o Pokémon defensor $j$, o multiplicador de dano é o produto, sobre os tipos $d in T_j$, de $f(t,d)$, onde $f = 2$ (super efetivo), $f = 1/2$ (pouco efetivo), $f = 0$ (imune) ou $f = 1$ (neutro). Se houver imunidade, o multiplicador total é $0$. Denotando-o por $m(t,j)$, definimos o escore de um tipo:

$ s(t,j) = cases(
  +2 & "se" m(t,j) > 1,
  -2 & "se" m(t,j) < 1 quad ("resistência ou imunidade"),
   0 & "se" m(t,j) = 1
) $

A vantagem do Pokémon $i$ sobre o Pokémon $j$ é a soma sobre os tipos de $i$ (ataque com bônus de mesmo tipo):

$ "Advantage"(i,j) = sum_(t in T_i) s(t,j) $

Assim, $"Advantage"(i,j) in {-4, -2, 0, 2, 4}$ para Pokémon de dois tipos, e $in {-2, 0, 2}$ para Pokémon de tipo único.

== Resistência de tipo (defesa)

A resistência mede o quanto os tipos de $i$ aguentam os ataques de $j$. Ela é o espelho da vantagem: os tipos de $j$ atacam $i$, e o sinal é invertido (resistir é bom para $i$, ser super efetivamente atingido é ruim):

$ "Resist"(i,j) = - "Advantage"(j,i) = - sum_(t in T_j) s(t,i) $

Os valores possíveis são os mesmos de $"Advantage"$. *Observação:* os ataques de $j$ são aproximados pelos seus tipos. Golpes de cobertura de outros tipos não são considerados.

== Termos normalizados

Dado um conjunto $S$ de Pokémon adversários (o conjunto $U$ no draft, o conjunto $O$ no duelo), definimos, para cada Pokémon $i$, os termos de vantagem e de resistência normalizados para $[-1, 1]$:

$ d_i = (sum_(j in S) P_j "Advantage"(i,j)) / (4 sum_(j in S) P_j), quad
  r_i = (sum_(j in S) P_j "Resist"(i,j)) / (4 sum_(j in S) P_j) $

Se $S = emptyset$, definem-se $d_i = r_i = 0$.

== Pesos

Os pesos $alpha, beta, gamma in [0,1]$ são *parâmetros fixos*, definidos antes de resolver o modelo (não são variáveis de decisão, o que manteria o problema linear). Eles controlam o tradeoff entre os critérios:

- $alpha$: peso da força de ataque ($v_i$, definido no draft);
- $beta$: peso da vantagem ofensiva de tipos ($d_i$);
- $gamma$: peso da resistência de tipos ($r_i$).

Só a proporção entre os pesos altera a solução. Um peso igual a $0$ desliga o critério correspondente.

= Escolha de Pokémon (draft)

== Conjuntos e parâmetros

- $N$: conjunto de todos os Pokémon disponíveis ($i = 1, dots.h, n$).
- $A$: Pokémon já escolhidos por mim.
- $U$: Pokémon já escolhidos pelo adversário (um novo a cada rodada).
- $"Ubers"$: Pokémon banidos (tiers Uber e AG).
- $G$: número total de Pokémon que cada jogador escolhe.
- $M$: rodada atual ($M in {1, dots.h, G}$).
- $C$: orçamento total de pontos.
- $w_i$: custo em pontos do Pokémon $i$.
- $a_i = max("Atk"_i, "SpA"_i)$: poder de ataque do Pokémon $i$.
- $v_i$: valor de ataque normalizado em $[0,1]$:
  $ v_i = (a_i - min_k a_k) / (max_k a_k - min_k a_k) $
- $d_i$ e $r_i$: calculados com $S = U$ (definições comuns).

== Variáveis de decisão

$ x_i = cases(
  1 & "se o Pokémon" i "for escolhido para o time",
  0 & "caso contrário"
) quad forall i in N $

== Função objetivo

O objetivo combina a força de ataque do time, sua vantagem sobre os Pokémon do adversário e sua resistência aos ataques deles, ponderadas pela probabilidade de uso de cada um. Os três termos estão na mesma escala ($v_i in [0,1]$ e $d_i, r_i in [-1,1]$):

$ max Z = sum_(i in N) c_i x_i, quad
  c_i = alpha v_i + beta d_i + gamma r_i $

== Restrições

1. *Número de escolhas:* a cada rodada o jogador escolhe exatamente um novo Pokémon, logo o time tem $M$ integrantes:
   $ sum_(i in N) x_i = M $

2. *Orçamento:* o custo total não pode ultrapassar o orçamento disponível $B_M$:
   $ sum_(i in N) w_i x_i <= B_M $
   Para garantir que ainda seja possível completar o time, o orçamento da rodada $M$ reserva o custo dos $G - M$ Pokémon mais baratos ainda disponíveis. Seja $F = {i in N : i in.not U union "Ubers"} backslash A$ o conjunto dos Pokémon livres e $w_((1)) <= w_((2)) <= dots.h$ seus custos em ordem crescente:
   $ B_M = C - sum_(k=1)^(G-M) w_((k)) $
   Na versão literal (sem reserva), $B_M = C$.

3. *Pokémon já escolhidos por mim:*
   $ x_i = 1 quad forall i in A $

4. *Pokémon escolhidos pelo adversário ou banidos:*
   $ x_i = 0 quad forall i in (U union "Ubers") backslash A $

== Modelo final

$
  &"max" && Z = sum_(i in N) (alpha v_i + beta d_i + gamma r_i) x_i \
  &"s.a." && sum_(i in N) x_i = M \
  &       && sum_(i in N) w_i x_i <= B_M \
  &       && x_i = 1 quad forall i in A \
  &       && x_i = 0 quad forall i in (U union "Ubers") backslash A \
  &       && x_i in {0,1} quad forall i in N
$

== Variantes usadas na recomendação

- *Top-$k$ de recomendações:* resolve-se o modelo, o Pokémon sugerido (o novo integrante, $i in.not A$) é temporariamente proibido ($x_i = 0$) e o modelo é resolvido de novo, repetindo $k$ vezes.
- *Lookahead:* resolve-se o time completo, com $sum_(i in N) x_i = G$ e $B_M = C$ (sem reserva). O novo integrante sugerido é aquele de maior coeficiente $c_i$ entre os que ainda não estão em $A$.

= Escolha de equipe para duelo

== Conjuntos e parâmetros

- $R$: conjunto de todos os Pokémon do meu roster na liga.
- $O$: conjunto de Pokémon do adversário.
- $K$: número exato de Pokémon a escolher para a batalha ($K <= |R|$).
- $d_i$ e $r_i$: calculados com $S = O$ (definições comuns).
- $beta, gamma$: pesos da vantagem ofensiva e da resistência.

== Variáveis de decisão

$ x_i = cases(
  1 & "se o Pokémon" i "for escolhido para o duelo",
  0 & "caso contrário"
) quad forall i in R $

== Função objetivo

O objetivo é montar a equipe com a melhor combinação de vantagem ofensiva e resistência de tipos frente aos Pokémon do adversário, ponderados pela probabilidade de uso de cada um:

$ max Z = sum_(i in R) (beta d_i + gamma r_i) x_i $

Com $beta = 1$ e $gamma = 0$, obtém-se o modelo original de vantagem pura, $sum_(i in R) (sum_(j in O) P_j "Advantage"(i,j)) x_i$. A normalização por $4 sum_(j in O) P_j$ é uma constante positiva e não altera o time ótimo, apenas a escala de $Z$.

== Restrições

1. *Tamanho do time (exatamente $K$ integrantes):*
   $ sum_(i in R) x_i = K $

== Modelo final

$
  &"max" && Z = sum_(i in R) (beta d_i + gamma r_i) x_i \
  &"s.a." && sum_(i in R) x_i = K \
  &       && x_i in {0,1} quad forall i in R
$

== Observação

Como o escore $s_i = beta d_i + gamma r_i$ de cada Pokémon não depende dos demais, o problema é separável: a solução ótima consiste em escolher os $K$ Pokémon de maior $s_i$. O MILP é equivalente a ordenar o roster por esse escore. Por isso, o modelo não captura cobertura nem sinergia, e pode selecionar um time com tipos repetidos.

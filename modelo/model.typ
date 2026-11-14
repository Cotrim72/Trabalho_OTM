#set page(paper: "a4", margin: (x: 2.5cm, y: 2.5cm))
#set text(font: "New Computer Modern", size: 11pt, lang: "pt")
#show math.equation: set text(font: "New Computer Modern Math")

#align(center)[
  #block(width: 80%)[
    #text(weight: "bold", size: 14pt)[Modelo Matemático: Otimização de Equipe em Draft Leagues]\
    #text(size: 10pt, fill: luma(100))[Programação Linear Inteira (MILP) Aplicada a Pokémon]
  ]
]

#v(1em)
= Escolha de Pokemon
== 1. Conjuntos e Parâmetros

- $N$: Conjunto de todos os Pokémon disponíveis na tier list ($i = 1, dots.h, n$).
- $A$: Conjunto com os pokemons já escolhidos por mim
- $U$: Conjunto com os pokemons já escolhidos por outros jogadores
- $G$: o número de pokemons totais a ser escolhidos
- $M$: O número da rodada atual (M $in$ {1,..,G})
- $C$: Orçamento total de pontos disponível para a equipe.
- $w_i$: Custo em pontos do Pokémon $i$.
- $v_i$: Valor de Attk $i$.
- $"Ubers"$: Tier list dos pokemons banidos.
- $"OU"$ $"(OverUsed)"$: A tier principal e padrão do competitivo. Reúne os Pokémon mais usados e fortes do jogo comum.
- $"UU"$ $"(UnderUsed)"$: Pokémon que não tiveram uso suficiente para ficar em OU, mas ainda são muito competitivos.
- $"RU"$ $"(RarelyUsed)"$: Pokémon que caíram de UU. O nível de poder é intermediário.
- $"NU"$ $"(NeverUsed)"$: Pokémon com estatísticas ou tipagens mais limitadas, mas viáveis entre si.
- $"PU"$ $"(PartiallyUsed)"$: Uma das tiers mais baixas baseadas em uso (a sigla não tem um significado oficial original, mas foi adotada assim).
- $"ZU"$ $"(ZeroUsed)"$: Onde ficam os Pokémon que não atingiram uso nem mesmo em PU (ex: evoluções intermediárias ou Pokémon muito fracos).

== 2. Variáveis de Decisão

Como cada Pokémon pode ser escolhido no máximo uma vez para compor o time, definimos variáveis binárias:

$ x_i = cases(
  1 & "se o Pokémon" i "for escolhido para o time",
  0 & "caso contrário"
) quad forall i in N $

Haverá também uma matriz $"Advantage"(i,j)$ que simboliza a vantagem de tipo que meu pokemon i tenho contra o pokemon j do oponente.

$ "Advantage"(i,j) = cases(
  -4 & "se o Pokémon" i "tiver desvantagem nos dois tipos dele" ,
  -2 & "se o Pokémon" i "tiver desvantagem em um tipo dele" ,
   0 & "se as vantagens e desvantagens se compense" ,
   2 & "se o Pokémon" i "tiver vantagem em um tipo dele",
   4 & "se o Pokémon" i "tiver vantagem nos dois tipos dele"
)
$

Além de uma probabilidade($P_j$) de uso do Pokémon $j$ do oponente com base nas tier de uso da Smogon.
$ P_j = cases(
  0.95 & quad j in "OU",
  0.80 & quad j in "UU",
  0.60 & quad j in "RU",
  0.40 & quad j in "NU",
  0.20 & quad j in "PU",
  0.05 & quad j in "ZU",
) quad forall j in U
$

== 3. Função Objetivo

O objetivo é maximizar a força total da equipe selecionada e a vantagem sobre os pokemons dos adversários, respeitando os limites de orçamento e composição:

$ max Z = alpha sum_{i in N} v_i x_i + beta sum_{i in N} (sum_{j in U} P_j "Advantage"(i,j) )x_i $

== 4. Restrições do Modelo

1. *Restrição de escolha, a cada rodada cada jogador escolhe um pokemon:*
   $ sum_{i in N} x_i = M $

2. *Restrição de Orçamento (Budget):*
   O custo total dos Pokémon escolhidos não pode ultrapassar o orçamento máximo $C$.
   $ sum_{i in N} w_i x_i <= C $
3. *Restrição em relação aos pokemons já escolhidos por mim:*
    $ x_i = 1 quad forall i in A $
4. *Restrição em relação aos pokemons já escolhidos por outros jogadores:*
    $ x_i = 0 quad forall i in U union "Ubers" $

== 5. Modelo Final
  $ 
    &"max" && Z = alpha sum_{i in N} v_i x_i + beta sum_{i in N} (sum_{j in U} P_j "Advantage"(i,j) )x_i  \
    &"subject to:" && sum_{i in N} x_i = M \
    &              && sum_{i in N} w_i x_i <= C\
    &              && x_i = 1 quad forall i in A \
    &              && x_i = 0 quad forall i in U union "Ubers"\
    &              && x_i in {0,1} quad forall i in N\
    &              && alpha in [0,1] quad beta in [0,1]
 $

= Escolha de equipe para duelo
== 1. Conjuntos e Parâmetros
- $R$: O conjunto de todos os Pokémon que você tem no seu roster inteiro da liga.
- $O$: O conjunto de Pokémon que o seu adversário tem disponível.
- $K$: O número exato de Pokémon que você precisa escolher para a batalha.
- $"OU"$ $"(OverUsed)"$: A tier principal e padrão do competitivo. Reúne os Pokémon mais usados e fortes do jogo comum.
- $"UU"$ $"(UnderUsed)"$: Pokémon que não tiveram uso suficiente para ficar em OU, mas ainda são muito competitivos.
- $"RU"$ $"(RarelyUsed)"$: Pokémon que caíram de UU. O nível de poder é intermediário.
- $"NU"$ $"(NeverUsed)"$: Pokémon com estatísticas ou tipagens mais limitadas, mas viáveis entre si.
- $"PU"$ $"(PartiallyUsed)"$: Uma das tiers mais baixas baseadas em uso (a sigla não tem um significado oficial original, mas foi adotada assim).
- $"ZU"$ $"(ZeroUsed)"$: Onde ficam os Pokémon que não atingiram uso nem mesmo em PU (ex: evoluções intermediárias ou Pokémon muito fracos).

== 2. Variáveis de Decisão

Como cada Pokémon pode ser escolhido no máximo uma vez para compor o time, definimos variáveis binárias:

$ x_i = cases(
  1 & "se o Pokémon" i "for escolhido para o time",
  0 & "caso contrário"
) quad forall i in R $

Haverá também uma matriz $"Advantage"(i,j)$ que simboliza a vantagem de tipo que meu pokemon i tenho contra o pokemon j do oponente.

$ "Advantage"(i,j) = cases(
  -4 & "se o Pokémon" i "tiver desvantagem nos dois tipos dele" ,
  -2 & "se o Pokémon" i "tiver desvantagem em um tipo dele" ,
   0 & "se as vantagens e desvantagens se compense" ,
   2 & "se o Pokémon" i "tiver vantagem em um tipo dele",
   4 & "se o Pokémon" i "tiver vantagem nos dois tipos dele"
)
$

Além de uma probabilidade($P_j$) de uso do Pokémon $j$ do oponente com base nas tier de uso da Smogon.
$ P_j = cases(
  0.95 & quad j in "OU",
  0.80 & quad j in "UU",
  0.60 & quad j in "RU",
  0.40 & quad j in "NU",
  0.20 & quad j in "PU",
  0.05 & quad j in "ZU"
)
$

== 3. Função Objetivo

O objetivo é criar a equipe o mais counter possível da equipe mais provável do adversário.

$ max Z = sum_{i in R} (sum_{j in O} P_j "Advantage"(i,j) )x_i $

== 4. Restrições do Modelo
1. *Restrição de Tamanho do Time (Exatamente K integrantes):*
   $ sum_{i in R} x_i = K $

== 5. Modelo Final
  $ 
    &"max" && Z = sum_{i in R} (sum_{j in O} P_j "Advantage"(i,j) )x_i \
    &"subject to:" && sum_{i in R} x_i = K \
    &              && x_i in {0,1} quad forall i in R
 $

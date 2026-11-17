// Apresentação em Typst nativo. Compilar a partir da raiz do repositório:
// typst compile modelo/slides.typ modelo/slides.pdf
#set document(title: "Otimização de Equipes em Pokémon Draft Leagues")
#set page(
  width: 960pt, height: 540pt,
  margin: (x: 36pt, top: 28pt, bottom: 36pt),
  footer: context align(right, text(size: 10pt, fill: luma(110))[
    #counter(page).display() / #counter(page).final().first()
  ]),
)
#set text(font: "New Computer Modern", size: 16pt, lang: "pt")
#set par(leading: 0.55em, spacing: 0.7em)
#set list(spacing: 0.8em)
#set enum(spacing: 0.65em)
#show math.equation: set text(font: "New Computer Modern Math")
#set table(inset: 7pt, stroke: 0.5pt + luma(190), fill: (x, y) => if y == 0 { rgb("e7edf4") })
#show figure.where(kind: table): set text(size: 14pt)
#let slide(title, body) = [
  #pagebreak()
  #text(size: 25pt, weight: "bold", fill: rgb("203b58"))[#title]
  #v(8pt)
  #line(length: 100%, stroke: 1pt + rgb("9db2c7"))
  #v(10pt)
  #body
]

#align(center + horizon)[
  #text(size: 34pt, weight: "bold", fill: rgb("203b58"))[
    Otimização de Equipes em Pokémon Draft Leagues
  ]
  #v(18pt)
  #text(size: 21pt)[Recomendação sequencial e montagem de times via Programação Linear Inteira (MILP)]
  #v(32pt)
  Grupo: [nomes] \
  Disciplina: [nome] \
  [dd/mm/aaaa]
]
#slide[1. Introdução: O Problema das Draft Leagues][
- #strong[Contexto:] Pokémon (1996, Nintendo/Game Freak) possui um
  cenário competitivo estruturado em comunidades como a #emph[Smogon
  University] (tiers de uso desde meados dos anos 2000).
- #strong[Formato Draft League:] Jogadores escolhem equipes exclusivas
  em rodadas alternadas, respeitando um #strong[orçamento fixo de
  pontos] (cada Pokémon tem um custo proporcional à sua força).
- #strong[Desafio de decisão:] A cada rodada, o pool encolhe e as
  escolhas dos adversários alteram quais tipos e estatísticas são mais
  valiosos.
- #strong[Aplicações atuais:] O problema é isomorfo ao #strong[Problema
  da Mochila com Cardinalidade] (#emph[Cardinality-Constrained
  Knapsack]), usado em #emph[fantasy sports] (NBA, NFL, Cartola),
  alocação de portfólios e montagem de equipes sob restrição
  orçamentária.
]

#slide[2. Modelo Matemático: Probabilidade de Uso por Tier ($P_j$)][
Nem todo Pokémon do elenco adversário $U$ tem a mesma chance de entrar
em batalha. Para ponderar as ameaças mais prováveis, cada Pokémon $j$
recebe uma #strong[probabilidade de uso] $P_j$ conforme sua #emph[tier]
competitiva na Smogon:

#figure(
  align(center)[#table(
    columns: 3,
    align: (left,left,center,),
    table.header([Grupo de Tier], [Tiers incluídas], [Probabilidade
      ($P_j$)],),
    table.hline(),
    [#strong[OU] (#emph[OverUsed])], [OU, UUBL, Uber,
    AG], [#strong[0,95]],
    [#strong[UU] (#emph[UnderUsed])], [UU, RUBL], [#strong[0,80]],
    [#strong[RU] (#emph[RarelyUsed])], [RU, NUBL], [#strong[0,60]],
    [#strong[NU] (#emph[NeverUsed])], [NU, PUBL], [#strong[0,40]],
    [#strong[PU] (#emph[PartiallyUsed])], [PU, ZUBL], [#strong[0,20]],
    [#strong[ZU] (#emph[ZeroUsed])], [ZU, LC, NFE, Illegal,
    etc.], [#strong[0,05]],
  )]
  , kind: table
  )

- #strong[Parametrização arbitrária:] Os valores de
  $P_j in\[0,05; quad 0,95\]$ foram atribuídos de forma
  #strong[arbitrária] (heurística monotônica), refletindo apenas a
  hierarquia qualitativa de força e frequência de uso entre as divisões.
]

#slide[2. Modelo Matemático: Vantagem e Resistência de Tipos][
Seja $T_i$ o conjunto de tipos (1 ou 2) do Pokémon $i$. Para um tipo
atacante $t in T_i$ contra o defensor $j$, o multiplicador total é
$m(t,j)= product_(d in T_j) f(t,d)$, onde
$f in { 0,1 / 2,1,2 }$.

Definimos o escore do tipo $t$ contra $j$ e a #strong[vantagem ofensiva]
$upright("Advantage")(i,j)$:

$ s(t,j) = cases(
  +2 & "se" m(t,j) > 1 quad ("super efetivo"),
  -2 & "se" m(t,j) < 1 quad ("resistido ou imune"),
  0 & "se" m(t,j) = 1 quad ("neutro")
) $
$ "Advantage"(i,j) = sum_(t in T_i) s(t,j) in [-4,4] $

- #strong[Resistência defensiva:] Espelho da vantagem ofensiva quando os
  tipos de $j$ atacam $i$:
  $ upright("Resist")(i,j)= - upright("Advantage")(j,i)= - sum_(t in T_j) s(t,i) $
- #strong[Aproximação chave:] Os golpes de cada Pokémon são aproximados
  apenas pelos seus #strong[tipos base] (efeito STAB), mantendo o modelo
  linear.
]

#slide[2. Modelo Matemático: Construção dos Coeficientes][
Para cada Pokémon $i in N$, agregamos três critérios normalizados na
mesma escala:

+ #strong[Força de ataque ($v_i in\[0,1\]$):] maior atributo ofensivo
  ($a_i = max(upright("Atk")_i,upright("SpA")_i)$) normalizado via
  min-max: $ v_i = frac(a_i - min_k a_k, max_k a_k - min_k a_k) $
+ #strong[Vantagem ofensiva normalizada ($d_i in\[- 1,1\]$):] eficácia
  contra o conjunto adversário $U$, ponderada pela probabilidade
  arbitrária $P_j$ e dividida pelo máximo teórico ($4 sum P_j$):
  $ d_i = frac(sum_(j in U) P_j thin upright("Advantage")(i,j), 4 sum_(j in U) P_j) $
+ #strong[Resistência defensiva normalizada ($r_i in\[- 1,1\]$):]
  $ r_i = frac(sum_(j in U) P_j thin upright("Resist")(i,j), 4 sum_(j in U) P_j) $

#emph[(Caso $U = emptyset$, define-se $d_i = r_i = 0$\.)]
]

#slide[2. Modelo Matemático: Função Objetivo][
A função objetivo maximiza a qualidade agregada do time por meio de uma
#strong[soma ponderada multiobjetivo]:

$ max Z = sum_(i in N) c_i x_i,quad upright("onde") quad c_i = alpha v_i + beta d_i + gamma r_i $

- #strong[Por que somar os termos?] Como $v_i in\[0,1\]$ e
  $d_i,r_i in\[- 1,1\]$ estão na mesma ordem de grandeza, os pesos
  $alpha,beta,gamma in\[0,1\]$ controlam diretamente o
  #emph[trade-off] estratégico entre #strong[poder bruto] ($alpha$),
  #strong[pressão ofensiva de tipos] ($beta$) e #strong[solidez
  defensiva] ($gamma$).
- #strong[Papel dos parâmetros:] Apenas a proporção entre
  $(alpha,beta,gamma)$ altera a equipe ótima; zerar um peso desliga
  o critério correspondente.
- #strong[Preservação da linearidade:] Por serem parâmetros fixos
  definidos #emph[a priori] (e não variáveis de decisão), o coeficiente
  $c_i$ é constante para cada candidato $i$, garantindo que $Z$
  permaneça estritamente linear.
]

#slide[2. Modelo Matemático: Todas as Restrições do Draft (1/2)][
Considerando a rodada atual $M in { 1,dots.h,G }$ e o conjunto livre
$F = { i in N : i in.not U union upright("Ubers") } backslash A$:

+ #strong[Número de escolhas na rodada:] A cada rodada adiciona-se
  exatamente um novo integrante, logo o time deve possuir exatamente $M$
  Pokémon: $ sum_(i in N) x_i = M $
+ #strong[Orçamento com reserva futura:] O custo acumulado não pode
  exceder $B_M$, que reserva saldo para contratar os $G - M$ Pokémon
  mais baratos ainda disponíveis
  ($w_((1)) lt.eq w_((2)) lt.eq dots.h$):
  $ sum_(i in N) w_i x_i lt.eq B_M,quad upright("onde ") B_M = C - sum_(k = 1)^(G - M) w_((k)) $
]

#slide[2. Modelo Matemático: Todas as Restrições do Draft (2/2)][
#set enum(start: 3)
+ #strong[Permanência das escolhas anteriores:] Pokémon já contratados
  pelo jogador permanecem obrigatoriamente na equipe:
  $ x_i = 1 quad forall i in A $
+ #strong[Exclusividade e banimentos:] Pokémon já escolhidos pelos
  adversários ($U$) ou banidos ($upright("Ubers")$) são bloqueados:
  $ x_i = 0 quad forall i in(U union upright("Ubers")) backslash A $
+ #strong[Domínio binário:] Cada candidato é escolhido integralmente ou
  descartado: $ x_i in { 0,1 } quad forall i in N $
]

#slide[2. Modelo Matemático: Formulação Final (MILP)][
Agrupando a função objetivo (com pesos fixos
$alpha,beta,gamma in\[0,1\]$) e todas as restrições do problema na
rodada $M$:

$ max quad & Z = sum_(i in N)(alpha v_i + beta d_i + gamma r_i)x_i\
upright("s.a.") quad & sum_(i in N) x_i = M\
 & sum_(i in N) w_i x_i lt.eq B_M\
 & x_i = 1 &  & forall i in A\
 & x_i = 0 &  & forall i in(U union upright("Ubers")) backslash A\
 & x_i in { 0,1 } &  & forall i in N $

- #strong[Garantia de viabilidade:] A reserva $B_M$ impede que o modelo
  gaste todo o orçamento cedo e fique sem saldo para completar os $G$
  integrantes nas rodadas finais.
]

#slide[3. Solução: Arquitetura e Implementação][
- #strong[Base de dados oficial:] Os testes utilizam dados oficiais de
  #strong[status] (#emph[stats]) e tabelas de #strong[custos] extraídos
  do site oficial da #strong[Smogon], uma das principais plataformas e
  referências competitivas em #emph[Draft Leagues] de Pokémon.
- #strong[Stack em Python:] Manipulação de dados e álgebra matricial com
  `pandas` e `numpy`; otimização via `scipy.optimize.milp`.
- #strong[Algoritmo de Programação Inteira:] O `scipy.optimize.milp`
  utiliza o solver #strong[HiGHS], baseado no método
  #strong[Branch-and-Cut] (com relaxações lineares via Simplex/Pontos
  Interiores, planos de corte e heurísticas primais).
]

#slide[3. Solução: Estrutura em 3 scripts][
+ #strong[Simulador principal (`model1.py`):] Possui dois modos ---
  #emph[Draft] (você + $n - 1$ adversários aleatórios escolhendo
  rodada a rodada) e #emph[Game] (gera $n - 1$ equipes prontas e
  calcula o melhor time completo contra elas). #strong[Ambos utilizam
  exatamente o mesmo MILP], alterando apenas os parâmetros $M$ (rodada
  atual vs.~$G$) e $B_M$ (com reserva vs.~orçamento total $C$).
+ #strong[Análise de sensibilidade (`sensibility.py`):] Avalia o
  impacto da variação dos pesos ($alpha$, $beta$ e $gamma$) sobre
  custo, ataque e vantagem/resistência de tipos frente aos mesmos
  adversários.
+ #strong[Abordagem de duelo:] Dado o #emph[roster] de $n$ Pokémon já
  conquistados na liga, seleciona o melhor subconjunto de $m$ Pokémon
  ($m lt.eq n$) para enfrentar o time do adversário na batalha.
]

#slide[3. Solução: Demonstração em Rodada de Draft][
Configuração: $G = 6$ Pokémon, orçamento $C = 80$, pesos
$(alpha,beta,gamma)=(0,5; quad 0,5; quad 0)$, semente 17.

- #strong[Escolha do adversário (Rodada 1):] #emph[Hisuian Typhlosion]
  (Fogo/Fantasma, tier RU, $P_j = 0,60$).
- #strong[Top \#1 Recomendado pelo MILP:] #strong[Mega Tyranitar]
  - #strong[Tipos:] Rocha / Sombrio (super efetivo contra ambos os tipos
    do oponente $arrow.r upright("Advantage") = + 4$, $d_i = + 1,00$).
  - #strong[Poder ofensivo:] $upright("Atk") = 164$ ($v_i = 0,85$).
  - #strong[Custo:] $w_i = 6$ (preserva $74$ pontos para as 5 vagas
    restantes).
]

#slide[3. Solução: Análise de Sensibilidade dos Pesos][
Fixamos 3 adversários (18 Pokémon; tipos mais frequentes: Lutador,
Terra, Fantasma, Fogo) e resolvemos o time completo ($M = G = 6$,
$C = 80$) variando $(alpha,beta,gamma)$:

#figure(
  align(center)[#table(
    columns: (29%, 7%, 10%, 9%, 9%, 36%),
    align: (left,center,center,center,center,left,),
    table.header([Cenário $(alpha,beta,gamma)$], [Custo], [Atk
      médio], [$d$ médio], [$r$ médio], [Perfil dominante do time],),
    table.hline(),
    [#strong[$alpha$ dom.]
    $(0,70; quad 0,15; quad 0,15)$], [76], [#strong[175]], [+0,10], [+0,08], [Megas
    ofensivos (Mewtwo X/Y, Alakazam)],
    [#strong[$beta$ dom.]
    $(0,15; quad 0,70; quad 0,15)$], [59], [135], [#strong[\+0,28]], [+0,31], [Núcleo
    Fada/Voador (Altaria, Togekiss)],
    [#strong[$gamma$ dom.]
    $(0,15; quad 0,15; quad 0,70)$], [#strong[40]], [118], [+0,27], [#strong[\+0,35]], [Defensivo
    econômico (Primarina, Togetic)],
    [#strong[Iguais]
    $(0,33; quad 0,33; quad 0,33)$], [59], [135], [+0,28], [+0,31], [Mesmo
    time de $beta$ dominante],
  )]
  , kind: table
  )

#emph[Nota:] O valor absoluto de $Z$ não é comparável entre cenários
pois a escala muda com os pesos; avaliamos o trade-off pelas métricas
físicas.
]

#slide[3. Solução: Abordagem de Duelo (Problema Trivial)][
Na etapa de batalha, o jogador já possui um #emph[roster] $R$
($\|R\|= n$) pago no draft e precisa escolher $m$ Pokémon ($m lt.eq n$)
contra o elenco adversário $O$:

$ max quad Z = sum_(i in R)(beta d_i + gamma r_i)x_i #h(2em) upright("s.a.") quad sum_(i in R) x_i = m,quad x_i in { 0,1 } $

- #strong[Por que o problema se torna trivial?]
  + #strong[Sem restrição de orçamento:] Os custos $w_i$ já foram pagos
    no draft; não há mochila (#emph[knapsack]), apenas a cardinalidade
    fixa $m$.
  + #strong[Separabilidade linear:] O escore
    $s_i = beta d_i + gamma r_i$ de cada Pokémon $i in R$ é independente
    dos demais escolhidos.
- #strong[Solução exata sem Branch-and-Cut:] Resolver o MILP é
  matematicamente equivalente a #strong[ordenar] os $n$ Pokémon do
  #emph[roster] em ordem decrescente de $s_i$ e selecionar os
  #strong[$m$ primeiros] --- complexidade $cal(O)(n log n)$.
]

#slide[4. Discussão: Limitações e Casos Especiais][
- #strong[Limitação (Separabilidade):] Como $c_i$ depende apenas do
  Pokémon $i$ e não dos pares $(i,k)$ do próprio time, o modelo pode
  recomendar #strong[tipos repetidos] (ex.: 5 Fadas em $beta$ dominante)
  sem penalizar redundância.
- #strong[Aproximações de combate e calibragem:] Desconsidera golpes de
  cobertura (#emph[coverage moves]), velocidade (#emph[Speed tiers]),
  habilidades/itens e utiliza probabilidades de uso $P_j$ arbitradas
  manualmente.
- #strong[Casos especiais:]
  - #emph[Rodada 1 sem histórico ($U = emptyset$):] $d_i = r_i = 0$,
    reduzindo o problema ao critério puro de poder/custo.
  - #emph[Abordagem de Duelo:] Sem orçamento e com função separável,
    colapsa em uma simples #strong[ordenação] ($cal(O)(n log n)$).
]

#slide[4. Discussão: Generalizações futuras][
- #strong[Programação Quadrática Binária (MIQP):] Adicionar termos de
  sinergia
  $- lambda sum_(i < k) upright("Overlap")(T_i,T_k)x_i x_k$ para
  diversificar tipos.
- #strong[Calibragem empírica de $P_j$ e Lookahead:] Estimar $P_j$ a
  partir de estatísticas reais de uso da Smogon e simular escolhas
  futuras dos adversários (já prototipado via flag `--lookahead`).
]

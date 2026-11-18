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
#set text(font: "New Computer Modern", size: 20pt, lang: "pt")
#set par(leading: 0.55em, spacing: 0.7em)
#set list(spacing: 2.0em)
#set enum(spacing: 2.0em)
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
  Grupo: Eduardo Freire e João Pedro Cotrim \
  Disciplina: Otimização \
  18/11/2026
]
#slide[1. Introdução: O Problema das Draft Leagues][
- #strong[Contexto:] Pokémon (1996, Nintendo/Game Freak) possui um
  cenário competitivo estruturado em comunidades como a #emph[Smogon
  University] (tiers de uso desde meados dos anos 2000).
- #strong[Formato Draft League:] Jogadores escolhem equipes exclusivas
  em rodadas alternadas, respeitando um #strong[orçamento fixo de
  pontos] (cada Pokémon tem um custo).
- #strong[Desafio de decisão:] A cada rodada, as
  escolhas dos adversários alteram quais tipos e estatísticas são mais
  valiosos.
- #strong[Aplicações atuais:] O problema é isomorfo ao #strong[Problema
  da Mochila com Cardinalidade] (#emph[Cardinality-Constrained
  Knapsack]), usado em #emph[fantasy sports] (ex.: Cartola),
  alocação de portfólios e montagem de equipes sob restrição
  orçamentária.
]

#slide[2. Modelo Matemático: Do Pokémon ao time][
Para cada Pokémon $i$ do conjunto de candidatos $N$, combinamos três fatores:

$ c_i = alpha v_i + beta d_i + gamma r_i $

#grid(columns: (1fr, 1fr, 1fr), gutter: 20pt,
  [*Força de ataque* \ $v_i$: poder ofensivo bruto.],
  [*Vantagem ofensiva* \ $d_i$: eficácia contra os adversários já selecionados.],
  [*Resistência defensiva* \ $r_i$: proteção contra os ataques dos adversários já selecionados.],
)

Os pesos $alpha, beta, gamma$ definem a importância de cada fator.

$ max Z = sum_(i in N) c_i x_i $

Escolhemos o time com a maior soma de escores.
$x_i = 1$ se o Pokémon $i$ for escolhido e $x_i = 0$ caso contrário.
]

#slide[2. Modelo Matemático: Força de ataque ($v_i$)][
O poder bruto de cada Pokémon é seu maior atributo ofensivo:

$ a_i = max("Atk"_i, "SpA"_i) $

*Atk* mede ataque físico; *SpA*, ataque especial.
Usamos o maior dos dois para contemplar ambos os perfis ofensivos.

Normalizamos entre o menor e o maior valor dos candidatos:

$ v_i = frac(a_i - min_(k in N) a_k, max_(k in N) a_k - min_(k in N) a_k) $

Assim, $v_i in [0,1]$: maior força de ataque corresponde a maior $v_i$.
]

#slide[2. Modelo Matemático: Vantagem ofensiva ($d_i$)][
$T_i$ contém os tipos (um ou dois) de $i$; $j$ é um adversário.
O multiplicador de um tipo atacante $t$ contra $j$ é:

$ m(t,j) = product_(q in T_j) f(t,q), quad f(t,q) in {0, 1/2, 1, 2} $

Cada tipo defensor $q$ pode tornar o ataque imune, resistido, neutro ou super efetivo:

$ s(t,j) = cases(
  +2 & "se" m(t,j) > 1 quad ("super efetivo"),
  -2 & "se" m(t,j) < 1 quad ("resistido ou imune"),
  0 & "se" m(t,j) = 1 quad ("neutro")
) $

$ "Advantage"(i,j) = sum_(t in T_i) s(t,j) in [-4,4] $

Para o conjunto adversário $U$, com $|U|$ Pokémon:
$ d_i = frac(sum_(j in U) "Advantage"(i,j), 4 |U|) in [-1,1] $
]

#slide[2. Modelo Matemático: Resistência defensiva ($r_i$)][
Agora invertemos os papéis: os tipos do adversário $j$ atacam o Pokémon $i$.

$ "Resist"(i,j) = -"Advantage"(j,i) = -sum_(t in T_j) s(t,i) $

Agregamos a resistência contra todos os Pokémon adversários:

$ r_i = frac(sum_(j in U) "Resist"(i,j), 4 |U|) in [-1,1] $

*Sem adversários conhecidos:* se $U = emptyset$, definimos $d_i = r_i = 0$.

*Aproximação de combate:* os ataques são representados apenas pelos tipos base
de cada Pokémon (STAB); golpes de cobertura não são considerados.
]

#slide[2. Modelo Matemático: Objetivo e restrições][
Com os três fatores calculados, somamos os escores dos Pokémon escolhidos:

$ max Z = sum_(i in N) c_i x_i, quad c_i = alpha v_i + beta d_i + gamma r_i $

- *Escalas comparáveis:* $v_i in [0,1]$ e $d_i, r_i in [-1,1]$.
- *Pesos fixos:* $alpha, beta, gamma in [0,1]$ expressam a estratégia.
  Só sua proporção altera a solução; peso zero desliga um critério.
- *Objetivo linear:* fatores e pesos são calculados ou definidos antes
  da otimização; cada $c_i$ é constante.

*Quais times podemos escolher?* A seguir, impomos as restrições de tamanho,
orçamento, permanência, exclusividade e limite de mega-evoluções.
]

#slide[2. Modelo Matemático: Todas as Restrições do Draft (1/2)][
Considerando a rodada atual $M in { 1,dots.h,G }$ e o conjunto livre
$F = { i in N : i in.not U union upright("Ubers") } backslash A$:

+ #strong[Número de escolhas na rodada:] A cada rodada adiciona-se
  exatamente um novo integrante, logo o time deve possuir exatamente $M$
  Pokémon: $ sum_(i in N) x_i = M $
+ #strong[Orçamento com reserva futura:] O custo acumulado não pode
  exceder $B_M$, que reserva saldo para escolher os $G - M$ Pokémon
  mais baratos ainda disponíveis
  ($w_((1)) lt.eq w_((2)) lt.eq dots.h$):
  $ sum_(i in N) w_i x_i lt.eq B_M,quad upright("onde ") B_M = C - sum_(k = 1)^(G - M) w_((k)) $
]

#slide[2. Modelo Matemático: Todas as Restrições do Draft (2/2)][
#set enum(start: 3)
+ #strong[Permanência das escolhas anteriores:] Pokémon já selecionados
  pelo jogador permanecem obrigatoriamente na equipe:
  $ x_i = 1 quad forall i in A $
+ #strong[Exclusividade e banimentos:] Pokémon já escolhidos pelos
  adversários ($U$) ou banidos ($upright("Ubers")$) são bloqueados:
  $ x_i = 0 quad forall i in(U union upright("Ubers")) backslash A $
+ #strong[Limite de mega-evoluções:] $"Mega"$ é o conjunto de mega-evoluções;
  $E$ é o máximo permitido por equipe (por exemplo, $E = 1$):
  $ sum_(i in "Mega") x_i <= E $
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
 & sum_(i in "Mega") x_i <= E\
 & x_i = 1 &  & forall i in A\
 & x_i = 0 &  & forall i in(U union upright("Ubers")) backslash A\
 & x_i in { 0,1 } &  & forall i in N $

- #strong[Garantia de viabilidade:] A reserva $B_M$ impede que o modelo
  gaste todo o orçamento cedo e fique sem saldo para completar os $G$
  integrantes nas rodadas finais.
]

#slide[3. Solução: Arquitetura e Implementação][
- #strong[Base de dados:] Os testes utilizam dados de
  #strong[status] (#emph[stats]) e tabelas de #strong[custos] extraídos
  do site da #strong[Smogon], uma das principais plataformas e
  referências competitivas em #emph[Draft Leagues] de Pokémon.
- #strong[Stack em Python:] Manipulação de dados e álgebra matricial com
  `pandas` e `numpy`; otimização via `scipy.optimize.milp`.
- #strong[Algoritmo de Programação Inteira:] O `scipy.optimize.milp`
  utiliza o solver #strong[HiGHS], baseado no método
  #strong[Branch-and-Cut] (com relaxações lineares via Simplex/Pontos
  Interiores, planos de corte e heurísticas primais).
]

#slide[3. Solução: Estrutura][
#set par(leading: 0.3em, spacing: 0pt)
#text(size: 17pt)[*Simulador (`model1.py`):* seleção entre os modos Draft e Game]
#v(5pt)
#align(center)[#image("imagens/print1.png", width: 76%)]
#v(8pt)
#text(size: 17pt)[*Draft:* escolhas por rodada, com cinco recomendações do MILP]
#v(5pt)
#align(center)[#image("imagens/print2.png", width: 100%)]
]

#slide[3. Solução: Estrutura do Modo Game][
#grid(columns: (285pt, 1fr), gutter: 20pt,
  [
    #set text(size: 18pt)
    #set par(leading: 0.45em, spacing: 0.8em)
    *Game (`model1.py`)* \
    Gera $n - 1$ equipes adversárias e calcula o melhor time completo contra elas.

    *Mesmo MILP nos dois modos* \
    Draft: $M$ é a rodada atual e $B_M$ reserva saldo futuro. \
    Game: $M = G$ e $B_M = C$.

    *Sensibilidade (`sensibility.py`)* \
    Varia os pesos $(alpha,beta,gamma)$ e compara custo, ataque e vantagem/resistência frente aos mesmos adversários.
  ],
  align(center)[#image("imagens/print3.png", height: 390pt)],
)
]

#slide[3. Solução: Demonstração em Rodada de Draft][
Configuração: $G = 6$ Pokémon, orçamento $C = 80$, pesos
$(alpha,beta,gamma)=(0,5; quad 0,5; quad 0)$, semente 17.

- #strong[Escolha do adversário (Rodada 1):] #emph[Hisuian Typhlosion]
  (Fogo/Fantasma, tier RU).
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

#slide[3. Solução: Funcionalidades Adicionais][
- #strong[Interface interativa no terminal:] Sorteia Pokémon oponentes e mostra o modelo em ação em cada rodada.
- #strong[Mais de 1 recomendação:] Apresenta ao usuário a cada rodada os 5 Pokémon com o maior valor de $Z$ e permite que ele escolha um.
- #strong[Modelo mais simples para a seleção de Pokémon para uma batalha específica:] Depois do draft, existe um novo problema de decisão a cada batalha, agora com um único time adversário, sem custo por Pokémon e restrito à equipe do draft.
]

#slide[4. Discussão: Limitações, Casos Especiais e Generalizações Futuras][
- #strong[Limitação (Separabilidade):] Como $c_i$ depende apenas do
  Pokémon $i$ e não dos pares $(i,k)$ do próprio time, o modelo pode
  recomendar #strong[tipos repetidos] (ex.: 5 Fadas em $beta$ dominante)
  sem penalizar redundância.
- #strong[Aproximações de combate:] Desconsidera golpes de
  cobertura (#emph[coverage moves]), velocidade (#emph[Speed tiers]),
  habilidades e itens.
- #strong[Casos especiais:]
  - #emph[Rodada 1 sem histórico ($U = emptyset$):] $d_i = r_i = 0$,
    reduzindo o problema ao critério puro de poder.
- #strong[Generalizações futuras:]
  - #emph[Programação Quadrática Binária (MIQP)]: Adicionar termos de sinergia
    $- lambda sum_(i < k) upright("Overlap")(T_i,T_k)x_i x_k$ para
    diversificar tipos.
]

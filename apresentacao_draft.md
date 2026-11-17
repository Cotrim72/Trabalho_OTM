---
title: "Otimização de Equipes em Draft Pokémon"
subtitle: "Recomendação de escolhas com programação linear inteira"
author: "Grupo: [nomes]"
institute: "Disciplina: [nome]"
date: "[dd/mm/aaaa]"
lang: pt-BR
aspectratio: 169
fontsize: 18pt
---

# O draft no nosso modelo

- Dois jogadores montam seus times alternadamente.
- Em cada rodada, cada jogador adiciona um Pokémon ao próprio time.
- Depois da escolha do adversário, o modelo recomenda nossa próxima escolha.

# A decisão em cada rodada

1. O modelo recebe os Pokémon escolhidos, a escolha do adversário e o orçamento restante.
2. A nova escolha do adversário muda quais tipos e opções merecem atenção.
3. O resolvedor encontra a melhor próxima escolha dentro das regras do draft.

O processo se repete até completar o time.

# O que torna uma escolha boa

$$
q_i = \alpha\,\text{Poder}_i
    + \beta\,\text{Vantagem}_i
    + \gamma\,\text{Resistência}_i
$$

- **Poder de ataque:** força ofensiva do Pokémon.
- **Vantagem de tipos:** como os tipos do Pokémon atacam os escolhidos pelo adversário.
- **Resistência de tipos:** como os tipos do Pokémon suportam os ataques esperados do adversário.

Os pesos $\alpha$, $\beta$ e $\gamma$ definem a prioridade de cada critério.

# O modelo de otimização

Variável binária:

$$
x_i =
\begin{cases}
1, & \text{Pokémon } i \text{ escolhido} \\
0, & \text{caso contrário}
\end{cases}
$$

O objetivo seleciona a equipe de maior escore:

$$
\max \sum_i q_i x_i
$$

# Restrições do draft

- Quantidade de Pokémon definida para a rodada.
- Custo total dentro do orçamento.
- Pokémon do adversário e banidos ficam indisponíveis.

As variáveis binárias tornam o problema um MILP.

# Uma rodada de simulação

- **Escolha do adversário:** Hisuian Typhlosion
  - Tipos: Fogo/Fantasma
- **Recomendação:** Mega Tyranitar
  - Tipos: Rocha/Sombrio
  - Poder de ataque: 164
  - Custo: 6
  - Vantagem de tipos contra o adversário: +4

Teste reproduzível: 6 escolhas por jogador, orçamento 80, $\alpha=0{,}5$, $\beta=0{,}5$, $\gamma=0$ e semente 17.

# Resultado

O modelo entrega:

- Uma recomendação atualizada após cada escolha do adversário.
- Uma seleção compatível com o orçamento e as opções disponíveis.
- Pesos ajustáveis para representar a estratégia desejada.

# Limites do modelo

- O modelo usa poder de ataque e tipos para aproximar o combate.
- Ele não considera golpes específicos, velocidade ou sinergias complexas.

Cada rodada produz uma escolha viável e justificável.

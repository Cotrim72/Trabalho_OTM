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

\begin{columns}[T,onlytextwidth]
\column{0.47\textwidth}

\begin{block}{Regra básica}
Dois jogadores montam seus times alternadamente. Em cada rodada, cada jogador adiciona um Pokémon ao próprio time.
\end{block}

\column{0.47\textwidth}

\begin{block}{Papel do modelo}
Depois da escolha do adversário, o modelo indica qual Pokémon acrescentar ao nosso time.
\end{block}
\end{columns}

\vfill

\begin{center}
\Large
Escolha do adversário \quad \textcolor{PokemonRed}{\textbf{depois}} \quad recomendação para nossa escolha
\end{center}

<!-- Tempo: 50 s. Fala: o foco é a decisão repetida a cada rodada, não os detalhes de uma liga completa. -->

# A decisão em cada rodada

\begin{columns}[T,onlytextwidth]
\column{0.31\textwidth}
\begin{block}{1. Estado atual}
O modelo recebe os Pokémon já escolhidos por nós, as escolhas do adversário e o orçamento restante.
\end{block}

\column{0.31\textwidth}
\begin{block}{2. Nova informação}
A escolha mais recente do adversário altera quais tipos e quais opções merecem atenção.
\end{block}

\column{0.31\textwidth}
\begin{block}{3. Recomendação}
O resolvedor procura a melhor próxima escolha que respeita as regras do draft.
\end{block}
\end{columns}

\vfill

\begin{center}
\large O mesmo processo se repete até completar o time.
\end{center}

<!-- Tempo: 1 min. Fala: reforçar que o modelo se adapta ao histórico do draft, rodada após rodada. -->

# O que torna uma escolha boa

\begin{center}
\Large
\[
q_i = \alpha\,\text{Poder}_i
      + \beta\,\text{Vantagem}_i
      + \gamma\,\text{Resistência}_i
\]
\end{center}

\begin{columns}[T,onlytextwidth]
\column{0.31\textwidth}
\begin{block}{Poder de ataque}
Representa a força ofensiva do Pokémon.
\end{block}

\column{0.31\textwidth}
\begin{block}{Vantagem de tipos}
Mede como seus tipos atacam os Pokémon já escolhidos pelo adversário.
\end{block}

\column{0.31\textwidth}
\begin{block}{Resistência de tipos}
Mede como seus tipos suportam os ataques esperados do adversário.
\end{block}
\end{columns}

\vfill

\begin{center}
Os pesos \(\alpha\), \(\beta\) e \(\gamma\) ajustam a prioridade de cada critério.
\end{center}

<!-- Tempo: 1 min 20 s. Fala: os três termos são normalizados para que os pesos controlem a preferência sem um termo dominar por unidade de medida. -->

# O modelo de otimização

\begin{columns}[T,onlytextwidth]
\column{0.44\textwidth}

\begin{block}{Decisão}
\[
x_i =
\begin{cases}
1, & \text{se } i \text{ é escolhido}\\
0, & \text{caso contrário}
\end{cases}
\]
\end{block}

\begin{alertblock}{Objetivo}
\[
\max \sum_i q_i x_i
\]
\end{alertblock}

\column{0.51\textwidth}

\begin{block}{Regras do draft}
\begin{itemize}
  \item O time tem exatamente a quantidade de escolhas correspondente à rodada.
  \item O custo total respeita o orçamento e preserva recursos para completar o time.
  \item Pokémon já usados pelo adversário ou banidos não podem ser escolhidos.
\end{itemize}
\end{block}

\vspace{0.35cm}
As variáveis são binárias, portanto formulamos o problema como um \alert{MILP}.
\end{columns}

<!-- Tempo: 1 min 20 s. Fala: explicar que o solver avalia as alternativas e devolve a combinação de maior escore que ainda é viável. -->

# Uma rodada de simulação

\begin{columns}[T,onlytextwidth]
\column{0.43\textwidth}

\begin{block}{Escolha do adversário}
\Large\textbf{Hisuian Typhlosion}\normalsize

Tipos: Fogo / Fantasma
\end{block}

\column{0.52\textwidth}

\begin{alertblock}{Primeira recomendação}
\Large\textbf{Mega Tyranitar}\normalsize

Tipos: Rocha / Sombrio

Poder de ataque: \textbf{164} \qquad Custo: \textbf{6}

Vantagem de tipos contra a escolha adversária: \textbf{+4}
\end{alertblock}
\end{columns}

\vfill

\begin{center}
\small Teste reproduzível: 6 escolhas por jogador, orçamento 80, \(\alpha=0{,}5\), \(\beta=0{,}5\), \(\gamma=0\), semente 17.
\end{center}

<!-- Tempo: 1 min 10 s. Fala: esta é a primeira rodada da execução do programa. O resultado mostra uma recomendação concreta e explica por que ela aparece no topo. -->

# Resultado e limites

\begin{columns}[T,onlytextwidth]
\column{0.47\textwidth}

\begin{block}{O que o modelo entrega}
\begin{itemize}
  \item Uma recomendação atualizada após cada escolha adversária.
  \item Uma seleção compatível com o orçamento e as opções disponíveis.
  \item Pesos ajustáveis para refletir a prioridade da estratégia.
\end{itemize}
\end{block}

\column{0.47\textwidth}

\begin{block}{Simplificações assumidas}
O modelo aproxima o combate pelo poder de ataque e pelos tipos. Ele não considera golpes específicos, velocidade ou sinergias complexas entre Pokémon.
\end{block}
\end{columns}

\vfill

\begin{center}
\Large A cada rodada, o modelo transforma o estado do draft em uma escolha viável e justificável.
\end{center}

<!-- Tempo: 1 min. Fala: encerrar retomando o ganho central: uma decisão objetiva, adaptada ao adversário e limitada pelos recursos do draft. -->

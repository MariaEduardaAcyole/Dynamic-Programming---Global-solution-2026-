# Orbital Guardian

Orbital Guardian e um projeto academico para rastreamento orbital e alerta de aproximacao entre satelites. A aplicacao usa dados publicos do CelesTrak, calcula posicoes orbitais aproximadas e mostra possiveis conjuncoes em uma interface web.

O projeto possui duas versoes:

- `app.py`: versao web principal, com painel visual, mapa orbital em canvas, alertas locais e consulta ao SOCRATES.
- `front_faculdade.py` + `projeto_faculdade.py`: versao simplificada para apresentacao em sala, destacando as estruturas de dados usadas.

## Funcionalidades

- Download automático de dados orbitais do CelesTrak.
- Armazenamento em cache local.
- Cálculo de órbitas simplificadas utilizando elementos orbitais públicos.
- Simulação temporal da movimentação dos satélites.
- Detecção de aproximações entre objetos orbitais.
- Classificação de risco das aproximações.
- Visualização dos resultados em interface web.
- Consulta de dados públicos do SOCRATES.
- Demonstração prática de estruturas de dados e algoritmos.

## Tecnologias

- Python 3
- HTML
- CSS
- JavaScript
- Servidor HTTP nativo do Python
- Dados publicos do CelesTrak

Nao ha dependencias externas obrigatorias. O projeto usa apenas bibliotecas padrao do Python.

## Estrutura do projeto

```text
GS-DP/ 
├── app.py 
├── projeto_faculdade.py 
├── front_faculdade.py 
├── estruturas_dados.py 
├── buscas.py 
    ├── static/ │ 
    ├── index.html │ 
    ├── app.js 
    │ └── styles.css 
├── front_faculdade/ │ 
    ├── index.html │ 
    ├── script.js 
    │ └── style.css 
└── data/ 
    └── cache/
```
## Arquitetura da Solução
**app.py** - Responsável pela versão principal da aplicação.

Funções:
- Servidor HTTP 
- API REST 
- Consulta de satélites 
- Consulta de alertas 
- Integração com SOCRATES 
- Comunicação com o frontend 
 
**projeto_faculdade.py** - Contém toda a lógica acadêmica da aplicação.

Responsável por:
- Download dos dados orbitais
- Processamento dos satélites
- Simulação orbital
- Busca de aproximações
- Aplicação das estruturas de dados
- Aplicação das buscas 

**front_faculdade.py** - Versão simplificada criada para apresentação acadêmica.

Permite demonstrar:
- Estruturas de dados 
- Busca 
- Ordenação 
- Simulação orbital

**estruturas_dados.py** - Arquivo responsável pelas implementações manuais das estruturas de dados exigidas pela disciplina.

Contém:
- Pilha 
- Fila FIFO 
- Lista Ligada

**buscas.py** - Arquivo responsável pelos algoritmos implementados manualmente.

Contém:
- Busca Linear
- Bubble Sort

## Atendimento aos Requisitos da Disciplina

**Lista Ligada** 

````
lista_ligada_satelites = ListaLigada()

for satelite in satelites:
    lista_ligada_satelites.adicionar(satelite)
````

Objetivo: Armazenar dinamicamente os satélites carregados durante a simulação.

**Fila FIFO**

````fila_processamento.enqueue(alerta)
alerta = fila_processamento.dequeue()
````

Objetivo: Processar alertas na mesma ordem em que são encontrados.

**Pilha**

``
historico_alertas.push(alerta)
``

Objetivo: Armazenar o histórico dos alertas encontrados.

**Dicionário (Hash Map)**

``
indice_por_norad = { satelite["norad"]: satelite for satelite in satelites }
``

Objetivo: Utilizado para indexação rápida dos satélites através do NORAD ID.

**Matriz**

```matriz_posicoes```

Objtivo: Utilizada para armazenar as posições calculadas dos satélites ao longo da simulação.
Cada linha representa um instante de tempo analisado.

**Tuplas**

`(x, y, z)`

Objetivo: Utilizadas para representar coordenadas espaciais tridimensionais.

**Busca Linear**

Implementada no arquivo  **_buscas.py_**

`busca_linear_satelite()`

Aplicação

`resultado_busca = busca_linear_satelite(
    satelites,
    primeiro_norad
)`

**Bubble Sort**

Implementada no arquivo  **_buscas.py_**

`bubble_sort_alertas()
`

Aplicação

`alertas = bubble_sort_alertas(alertas)`

**Manipulação de Arquivos**: 
O projeto realiza leitura, armazenamento e reutilização de arquivos CSV contendo dados orbitais reais.

**Tratamento de Exceções**:
O sistema utiliza blocos try/except para garantir robustez durante a execução.

## Complexidade Computacional


| Operação     | Complexidade |
|:-------------|:------------:| 
| Busca Linear |     O(n)     | 
| Bubble Sort  |    O(n²)     | 
| Busca Hash  |     O(1)     | 
| Inserção em Pilha |    	O(1)     | 
| Inserção em Fila  |    O(1)     |
| Inserção em Lista Ligada |    O(n)     |


## Como executar

Primeiro, tenha o Python instalado. Depois, no terminal, acesse a pasta do projeto:

```bash
cd GS-DP
```

### Versao principal

Execute:

```bash
python app.py
```

Abra no navegador:

```text
http://127.0.0.1:8000
```

Essa versao permite escolher grupo orbital, quantidade de satelites, horizonte de analise, passo da simulacao e limite de alerta em km.

### Versao simples para apresentacao

Execute:

```bash
python front_faculdade.py
```

Abra no navegador:

```text
http://127.0.0.1:8080
```

Essa versao mostra de forma mais direta as estruturas de dados usadas no trabalho.

### Versao pelo terminal

Tambem e possivel rodar a logica didatica diretamente:

```bash
python projeto_faculdade.py
```

## Fontes de dados

O projeto usa fontes publicas do CelesTrak:

- GP/OMM CSV: `https://celestrak.org/NORAD/elements/gp.php`
- SOCRATES: `https://celestrak.org/SOCRATES/table-socrates.php`

Os arquivos baixados ficam em cache em `data/cache`. Se a internet falhar, o sistema tenta usar os dados ja salvos.

## Endpoints da versao principal

Quando `app.py` esta rodando, os principais endpoints sao:

- `GET /api/groups`: lista os grupos orbitais disponiveis.
- `GET /api/satellites?group=starlink&limit=100`: retorna satelites de um grupo.
- `GET /api/positions?group=starlink&limit=220`: retorna posicoes 3D aproximadas.
- `GET /api/scan?group=starlink&limit=180&hours=12&step=10&threshold=20`: gera alertas locais de aproximacao.
- `GET /api/socrates?order=MINRANGE&max=50`: consulta registros publicos do SOCRATES.

## Como a analise funciona
## Como a Análise Funciona

1. O sistema realiza o download dos elementos orbitais públicos do CelesTrak ou utiliza os dados armazenados em cache local.
2. Cada linha do arquivo CSV é convertida em um objeto satélite contendo informações orbitais como NORAD ID, inclinação, excentricidade, período orbital, apogeu e perigeu.
3. Os satélites carregados são armazenados em uma Lista Ligada. 
4. O sistema calcula posições tridimensionais aproximadas dos satélites para diversos instantes futuros dentro do horizonte de análise definido pelo usuário.
5. Para cada instante analisado, é calculada a distância entre os pares de satélites elegíveis para comparação.
6. Quando a distância calculada fica abaixo do limite configurado, um alerta é criado e inserido em uma Fila FIFO para processamento.
7. Após o processamento da fila, os alertas são ordenados utilizando o algoritmo Bubble Sort, da menor para a maior distância.
8. Os alertas ordenados são armazenados em uma Pilha, representando um histórico de eventos encontrados durante a execução.
9. O sistema classifica cada alerta em níveis de risco (Baixo, Atenção, Moderado, Alto ou Crítico) e apresenta os resultados ao usuário.
10. Uma Busca Linear pode ser utilizada para localizar satélites pelo NORAD ID durante a execução da aplicação.


## Limites tecnicos

Este projeto e educacional. Ele usa uma propagacao Kepleriana simplificada a partir de elementos orbitais publicos. Para operacoes reais de prevencao de colisao seriam necessarios SGP4 validado, covariancia, telemetria do operador, avaliacao oficial de conjuncao e processos operacionais especializados.

## Alinhamento com Objetivos de Desenvolvimento Sustentavel (ODS)

O projeto Orbital Guardian contribui para diversos Objetivos de Desenvolvimento Sustentavel da Agenda 2030 da ONU:

### ODS 4: Educacao de Qualidade
- Projeto academico que ensina mecanica orbital, estruturas de dados e programacao
- Versao didatica para apresentacao em sala de aula, demonstrando conceitos complexos de forma acessivel
- Acesso livre aos codigos-fonte e documentacao para fins educacionais
- Promove compreensao sobre tecnologia espacial e sua relevancia pratica

### ODS 9: Industria, Inovacao e Infraestrutura
- Desenvolve competencias em tecnologia de rastreamento e monitoramento orbital
- Demonstra aplicacao de mecanica celeste e calculo cientifico
- Simula sistemas reais de prevencao de colisao entre satelites
- Contribui para a formacao de profissionais na area aeroespacial

### ODS 13: Acao Climatica
- Satélites sao ferramentas essenciais para monitoramento climatico e ambiental
- O projeto inclui satelites meteorologicos e permite analise de constelaçoes como Starlink
- Capacita profissionais a compreender o papel da tecnologia orbital no monitoramento ambiental
- Facilita o acesso a dados publicos sobre objetos orbitais utilizados em observacao da Terra

### ODS 17: Parcerias para os Objetivos
- Utiliza dados publicos e abertos do CelesTrak (orbits, elementos orbitais, informacoes SOCRATES)
- Promove colaboracao atraves do compartilhamento de dados nao proprietarios
- Integra padroes internacionais de notacao orbital (elementos Two-Line Element)
- Encoraja o desenvolvimento de solucoes baseadas em dados abertos

## Autores

- ***563359*** - Arthur Marcio de Barros Silva
- ***562291*** - Gabriela Abdelnor Tavares
- ***566337*** - Maria Eduarda Sousa Acyole De Oliveira
- ***566407*** - Matheus Goes Da Silva
- ***562680*** - Mayke Costa Santos

Projeto desenvolvido para fins academicos.

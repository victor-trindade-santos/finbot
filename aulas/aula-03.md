# Aula 3 — Memória com LangGraph + MongoDB e prompts versionados

> **Ao final desta aula** o FinBot lembra das conversas mesmo se a API reiniciar, conhece o perfil de cada usuário e busca os prompts no Langfuse: dá para mudar o comportamento do app **sem novo deploy**.
>
> 🛠️ Deu erro? Consulte [Problemas comuns](problemas-comuns.md).

## Sumário

- Conceitos: persistência, MongoDB, grafo (State, Node, Edge), memória curta × longa, versionamento de prompts
- MongoDB Atlas (gratuito)
- Repository + primeiro grafo com checkpointer
- Perfil (memória de longo prazo) e API/front
- Prompts no Langfuse
- Testes, commit, push (deploy automático)

---

## Parte 1 — Conceitos

### O problema da Aula 2

A memória estava num dicionário Python, na RAM da API. Reiniciou → perdeu tudo. No Render, a API **dorme** após 15 min, então perde tudo de novo. Precisamos de **persistência**: guardar em disco, num banco de dados.

### MongoDB

Banco de dados **NoSQL orientado a documentos**:

| SQL (ex.: MySQL) | MongoDB |
|---|---|
| tabela | **coleção** |
| linha | **documento** (um JSON) |
| colunas fixas | cada documento pode ter campos diferentes |

**Por que Mongo para um chat?** Mensagens, estados de agentes e perfis têm formatos que mudam com o tempo (hoje uma mensagem tem `agente`; amanhã terá `fontes`). Documentos JSON acomodam isso sem migrações. O **MongoDB Atlas** tem um plano gratuito permanente (M0).

### O que é um grafo

Antes de falar do LangGraph, vale entender a palavra que dá nome a ele. Na matemática e na computação, um **grafo** é um conjunto de **pontos** ligados por **linhas**:

- os pontos se chamam **nós** (ou vértices);
- as linhas se chamam **arestas**.

![À esquerda, um grafo com cinco nós (A a E) ligados por arestas, com setas indicando o que é nó e o que é aresta. À direita, um grafo direcionado: Receber pergunta, Pensar, Usar ferramenta e Responder, com um ciclo entre Pensar e Usar ferramenta](imagens/grafo-exemplo.png)

Só isso. O que torna os grafos tão úteis é que muita coisa do dia a dia tem esse formato:

| Exemplo | Nós | Arestas |
|---|---|---|
| Mapa do metrô | estações | os trilhos entre duas estações |
| Rede social | pessoas | "segue" ou "é amigo de" |
| Rotas do GPS | cruzamentos | as ruas entre eles |
| Fluxograma | as etapas de um processo | as setas de "depois disso, faça aquilo" |

> **Curiosidade:** a teoria dos grafos nasceu em 1736, quando o matemático Leonhard Euler estudou se era possível atravessar as sete pontes da cidade de Königsberg passando por cada uma só uma vez. Ele trocou o mapa por pontos (as margens e ilhas) e linhas (as pontes), e mostrou que era impossível.

**Arestas com direção.** Quando a ligação tem sentido, como numa rua de mão única, a aresta vira uma **seta**: dá para ir de A para B, mas não necessariamente de B para A. Esse é o **grafo direcionado**, e é o tipo que o LangGraph usa: cada seta diz **o que acontece depois**.

```mermaid
flowchart LR
    A[Receber a pergunta] --> B[Chamar o LLM] --> C[Entregar a resposta]
```

**Ciclos.** Quando as setas formam um caminho que **volta** para um nó anterior, o grafo tem um **ciclo** (um loop). É assim que, na Aula 4, o agente vai poder chamar uma ferramenta, ler o resultado e pensar de novo, quantas vezes precisar:

```mermaid
flowchart LR
    P[Pensar] -->|precisa de um dado| F[Usar ferramenta]
    F -->|resultado| P
    P -->|já sabe responder| R[Responder]
```

Num fluxograma de processo, como esses, cada **nó** é uma **etapa do trabalho** e cada **aresta** é a **ordem** entre as etapas. É exatamente essa a ideia do LangGraph: desenhar o "caminho" que o FinBot percorre para responder.

### O que é o LangGraph e para que serve

O **LangGraph** é uma biblioteca da mesma equipe do LangChain. A [documentação oficial](https://langchain-ai.github.io/langgraph/) o apresenta como um framework de **orquestração** para construir agentes **com estado**, ou seja, aplicações que lembram em que ponto estão e podem continuar de onde pararam. Orquestrar é decidir **quem faz o quê, em que ordem e com quais informações**.

Até a Aula 2, o FinBot fazia sempre a mesma coisa: montar as mensagens e chamar o LLM. Um único passo, escrito em Python comum. Mas nas próximas aulas ele vai precisar de mais:

- **Aula 4:** chamar uma ferramenta, ler o resultado e decidir se chama outra (um **loop**);
- **Aula 6:** escolher qual especialista responde a cada pergunta (um **desvio**);
- **Aula 7:** passar a resposta por um revisor antes de entregar (mais uma **etapa**).

Escrever isso com `if` e `while` espalhados funciona no começo, mas vira um emaranhado difícil de entender, testar e depurar. O LangGraph organiza o fluxo como um **grafo**: um desenho de **caixas** (os passos) ligadas por **setas** (quem vem depois), parecido com um fluxograma.

**LangChain × LangGraph:**

| | LangChain (Aulas 1 e 2) | LangGraph (a partir de hoje) |
|---|---|---|
| Papel | as **peças**: modelos, mensagens, prompts, ferramentas | a **montagem**: em que ordem as peças rodam |
| Pergunta que responde | "como eu chamo o LLM?" | "o que acontece antes e depois de chamar o LLM?" |
| No FinBot | `ChatGroq`, `SystemMessage`, `HumanMessage` | o grafo `START → chatbot → END` |

Um não substitui o outro: os nós do grafo continuam usando o LangChain por dentro.

#### Analogia: a cozinha do restaurante

Na Aula 2, a **cozinha** (o agente) recebia o pedido e preparava o prato. O LangGraph é a **organização dessa cozinha**:

- cada **estação** (entrada, prato principal, sobremesa) é um **nó**;
- a ordem em que o pedido passa pelas estações são as **arestas**;
- a **comanda** que acompanha o pedido, anotada por cada estação, é o **estado**;
- o caderno do chefe, onde fica registrado em que ponto está cada pedido, é o **checkpointer**: se o turno trocar no meio, a equipe nova continua de onde parou.

É exatamente esse caderno que resolve o problema da Aula 2: com o checkpointer salvando o estado no MongoDB, a conversa não se perde quando a API reinicia.

**O que o LangGraph nos dá, prontos:**

- **estado compartilhado** entre os passos, sem variáveis globais;
- **memória** (checkpointer) salva a cada passo, separada por conversa;
- **caminhos condicionais e loops**, declarados em vez de escondidos em `if`;
- **desenho do fluxo** gerado a partir do código (`python -m app.agents.grafo` imprime o grafo em Mermaid);
- **integração com o Langfuse**: cada nó aparece no trace.

**Como o grafo do FinBot vai crescer:**

| Aula | Grafo |
|---|---|
| 3 (hoje) | `START → chatbot → END` |
| 4 | um agente com o loop `pensar ⇄ ferramentas` |
| 6 | `classificar → (mercado \| conhecimento \| conversa)`: um roteador escolhe o especialista |
| 7 | os especialistas passam por um `revisor` antes do `END` |

A API e o front não mudam em nenhuma dessas etapas: só o grafo cresce.

### Grafo: State, Node, Edge

Agora, os termos que o LangGraph usa para cada parte do grafo:

| Conceito | Definição | No código |
|---|---|---|
| **State** | O "bastão" que passa de nó em nó: um dicionário tipado, a única fonte da verdade | `class EstadoChat(TypedDict)` |
| **Node** | Função que recebe o estado e devolve **só o que mudou** | `def no_chatbot(estado) -> dict` |
| **Edge** | Quem vem depois de quem. Fixa (A → B) ou condicional (decide pelo estado) | `g.add_edge(START, "chatbot")` |
| **Reducer** | Como juntar o que o nó devolveu com o que já existia | `add_messages` **acrescenta** à lista em vez de substituir |
| **Compile** | Transforma a declaração num objeto executável (`.invoke()`, `.stream()`) | `g.compile(checkpointer=...)` |

Hoje o grafo é mínimo: `START → chatbot → END`. **Por que usar grafo para um nó só?** Pelo **checkpointer** e porque nas próximas aulas ele cresce sem precisar reescrever nada.

### Memória de curto prazo × longo prazo

| | Curto prazo | Longo prazo |
|---|---|---|
| Escopo | uma conversa (thread/sessão) | todas as conversas do usuário |
| Guarda | as mensagens e o estado do grafo | preferências e fatos do usuário |
| Mecanismo | **checkpointer** do LangGraph (identificado pelo `thread_id`) | um armazenamento à parte (coleção `perfis`) |
| Para quê | o agente lembrar do que foi dito agora | personalização |

O checkpointer salva o estado **a cada passo** do grafo. Além da memória, isso permite retomar depois de um erro e inspecionar a conversa passo a passo.

### Padrão Repository

Todo acesso ao banco fica em `app/repository/`. O resto do código chama `perfis.salvar_perfil(...)` sem saber que é Mongo. **Vantagens:** trocar de banco mexe numa pasta só, e nos testes usamos um Mongo falso em memória (`mongomock`).

### Versionamento de prompts

Hoje o prompt está no `.md` dentro do código. Mudar = commit + deploy. Pior: quando uma resposta sai errada, o trace mostra **o que** o modelo fez, mas não **qual versão da instrução** estava valendo.

Com o Langfuse:

- cada prompt é um **artefato identificado** (nome + versão: `finbot-sistema` v1, v2, v3...);
- o **rótulo** `production` diz qual versão o app usa. Para trocar, basta mover o rótulo, sem deploy;
- cada geração no trace fica **ligada à versão** do prompt. Dá para comparar custo e qualidade entre versões;
- o `.md` continua sendo a **semente** (primeira publicação) e a **reserva**: se o Langfuse cair, o app usa o arquivo local.

---

## Parte 2 — Mão na massa

> **Onde trabalhar:** continue na mesma pasta `finbot` aberta no VS Code desde a Aula 1; os arquivos criados nas aulas anteriores devem continuar nela. Abra o terminal integrado em **Terminal → Novo Terminal** (atalho ``Ctrl+` ``). No Windows, use **PowerShell**. Confira que está na pasta do projeto (`Get-Location` no PowerShell ou `pwd` no Linux/Mac) e ative o ambiente virtual: `.venv\Scripts\Activate.ps1` no PowerShell ou `source .venv/bin/activate` no Linux/Mac. Ative-o novamente sempre que abrir outro terminal.
>
> **Como criar/alterar arquivos:** use o painel **Explorer/Explorador** do VS Code. Abra as pastas do caminho indicado no título ou no comentário `# caminho/do/arquivo.py`; para arquivo novo, clique com o botão direito na pasta → **New File/Novo Arquivo**, digite o nome completo e cole o bloco de código. Salve com `Ctrl+S`. Quando um arquivo já existe e só muda um trecho, o bloco mostra esse trecho: o que você deve acrescentar fica entre os comentários `↓↓↓ NOVO` e `↑↑↑ fim do novo ↑↑↑` (ou logo abaixo de `↓ linha nova`), e o marcador diz depois de qual linha colar, e o restante serve para você achar o lugar no arquivo.

### Passo 1 — MongoDB Atlas (gratuito)

**Vocabulário do Atlas** (é aqui que todo mundo se confunde). O Atlas organiza tudo em "caixas" uma dentro da outra:

```text
Organização  (ex.: "Cintia's Org")      ← criada sozinha no cadastro
└── Projeto  ("Project 0")              ← já vem pronto: NÃO precisa criar outro
    └── Cluster  ("Cluster0")           ← VOCÊ cria, uma vez (o servidor grátis M0)
        ├── banco finbot_dev            ← o CÓDIGO cria (quando roda no seu computador)
        │   └── coleções: perfis, conversas, checkpoints...
        └── banco finbot                ← o CÓDIGO cria (quando roda no Render)
```

| Termo | O que é | Precisa criar? |
|---|---|---|
| **Organização** | Sua conta/empresa no Atlas | Não, é criada no cadastro |
| **Projeto** | Uma pasta que agrupa clusters. Plano grátis: **1 cluster M0 por projeto** | **Não**: use o "Project 0", que já vem pronto |
| **Cluster** | O servidor do MongoDB (é ele que é gratuito) | **Sim**, uma vez |
| **Usuário do banco** | Login e senha que o **código** usa (não é o seu login do site!) | **Sim** |
| **Banco (database)** | Agrupa coleções. Um cluster guarda vários bancos | **Não**, o código cria |
| **Coleção** | Equivale a uma tabela | **Não**, o código cria |

> **Onde entra o nome "finbot"?** Só em dois lugares: no **usuário do banco** (passo 1.3) e no **nome do banco** (`finbot_dev` e `finbot`, que o código cria sozinho). **Não existe um "projeto finbot" para criar**, e o cluster pode continuar com o nome `Cluster0`.

#### 1.1 — Criar a conta

1. Acesse [mongodb.com/cloud/atlas/register](https://www.mongodb.com/cloud/atlas/register).
2. Cadastre-se (dá para entrar com a conta Google).
3. Responda o questionário inicial como quiser (ex.: *Learn MongoDB*, *Python*).

#### 1.2 — Criar o cluster gratuito

1. Na tela **Deploy your cluster** (ou em **Clusters → Create**), escolha **M0 / Free**.
2. **Provider:** AWS. **Region:** São Paulo (`sa-east-1`), se aparecer.
3. **Name:** deixe `Cluster0` (o nome do cluster não importa para o código).
4. Clique em **Create Deployment** e aguarde 1 a 3 minutos.

Quando terminar, a página **Project 0 Overview** mostra o seu cluster com o selo verde **ACTIVE**:

![Página Project 0 Overview do MongoDB Atlas com o Cluster0 ativo, plano FREE, e o botão Connect](imagens/mongodb-cluster-ativo.png)

Repare no caminho no topo da tela: **Organization** (a sua organização) → **Project** (`Project 0`) → e, na página, o **cluster** (`Cluster0`), exatamente as caixas do vocabulário acima. Está tudo pronto para os próximos passos; não precisa criar projeto nem banco.

> A faixa azul **"We are deploying your changes"** aparece por alguns segundos sempre que você muda algo (criar o cluster, o usuário ou liberar o acesso de rede). Espere ela sumir antes do próximo passo. O aviso amarelo sobre "security and operations contacts" pode ser fechado no **X**: não é necessário para o curso.

> Já tem um cluster gratuito em outro projeto? **Pode reaproveitá-lo**: o FinBot cria o próprio banco, sem misturar com os outros. Para ter um cluster separado, crie um **projeto novo** (menu *Project 0* → **New Project**) e um M0 dentro dele.

#### 1.3 — Criar o usuário do banco

Logo após criar o cluster, o Atlas costuma abrir uma janela **Connect to cluster** pedindo um usuário. Se não abrir, crie pelo menu:

1. Confirme que você está **dentro do projeto**: o topo da tela deve mostrar **ORGANIZATION** e, ao lado, **PROJECT `Project 0`** (como na imagem do passo 1.2). Se aparecer só a organização, clique em **All Projects** → **Project 0**.
2. No menu lateral, **role até a seção SECURITY** (fica no fim do menu) → **Database & Network Access** (em versões mais antigas do Atlas: **Database Access**) → **Add New Database User**.

   ![Menu lateral do projeto no MongoDB Atlas, com a seção SECURITY e a opção Database & Network Access destacada](imagens/mongodb-menu-security.png)

> **Dados de exemplo:** se o painel do cluster mostrar algum tamanho de dados (ex.: *Data size: 45 MB*) logo depois de criado, é porque o Atlas carregou bancos de exemplo (`sample_mflix` e outros). Não atrapalham o FinBot e podem ficar.

> **Cuidado com a página "Users" da organização** (menu *Identity & Access* → **Users**). Ela lista as **pessoas** que entram no site do Atlas, como você mesma, e **não** é onde se cria o usuário do banco. O usuário do banco é o login que o **código** usa, e fica dentro do projeto, em **Database Access**.

Na janela **Add New Database User**, preencha:

![Janela Add New Database User do MongoDB Atlas, com o método Password, o usuário finbot, o campo de senha e o papel Read and write to any database](imagens/mongodb-novo-usuario.png)

1. **Authentication Method:** Password.
2. **Username:** `finbot`.
3. **Password:** **invente a sua**, com **12 caracteres ou mais** e **só letras e números**, e **anote**. Como o banco fica aberto para qualquer IP (passo 1.4), a senha é a única proteção: não use a de um colega nem uma de exemplo.
   > `@`, `:`, `/`, `#` e `%` quebram a URL de conexão. Evite.
4. **Database User Privileges:** em **Built-in Role**, escolha *Read and write to any database*. O campo **User Description** é opcional.
5. **Add User**.

Pronto: na página **Database Users** (em **DATABASE ACCESS**, no menu à esquerda), o usuário `finbot` aparece na lista com o papel **`readWriteAnyDatabase@admin`**, que é o *Read and write to any database* escolhido acima:

![Página Database Users do MongoDB Atlas com o usuário finbot criado, papel readWriteAnyDatabase@admin](imagens/mongodb-database-users.png)

> **Já apareceu um usuário que você não lembra de ter criado** (ex.: `seunome_db_user`)? O Atlas cria um automaticamente se você preencheu a janela **Connect to cluster** logo depois de criar o cluster. Você pode **usá-lo no lugar do `finbot`**, desde que saiba a senha: nos passos seguintes, troque `finbot` pelo nome dele na URL de conexão. Não lembra a senha? Clique em **EDIT** → **Edit Password**, defina uma nova (só letras e números) e clique em **Update User**.

#### 1.4 — Liberar o acesso de rede

Menu lateral → **SECURITY → Database & Network Access** (a mesma página do passo anterior) → aba ou seção **IP Access List** (em versões antigas: **Network Access**) → **Add IP Address** → **Allow access from anywhere** (preenche `0.0.0.0/0`) → **Confirm**.

Depois de alguns segundos (espere a faixa azul "We are deploying your changes" sumir), a lista deve ter a linha **`0.0.0.0/0`** com o status **Active**:

![Página IP Access List do MongoDB Atlas com a linha 0.0.0.0/0 ativa](imagens/mongodb-ip-access-list.png)

> Também pode aparecer uma segunda linha com o **IP da sua internet** e o comentário *"Created as part of the Auto Setup process"*: o Atlas a criou sozinho. Pode deixar, não atrapalha. O que importa é a linha `0.0.0.0/0`.

> **Por quê?** O Render (onde a API vai ficar) não tem IP fixo no plano grátis. A proteção passa a ser só usuário e senha. Por isso a senha nunca vai para o GitHub.

#### 1.5 — Copiar a URL de conexão

1. Volte para **Project 0 Overview** (ou menu lateral → **Clusters**) e, no seu cluster, clique em **Connect**.
2. O Atlas mostra três etapas no topo da janela. Se ele pedir algo em **Set up connection security**, você já fez nos passos 1.3 e 1.4: avance. Em **Choose a connection method**, escolha **Drivers**.
3. Na etapa **Connect**, deixe **Language: Python** e **Client Library: PyMongo**. Em **Use this connection string in your application**, clique no ícone de **copiar**, à direita da URL:

   ![Janela Connect to Cluster0 do MongoDB Atlas, com Python e PyMongo selecionados e a connection string com db_username e db_password](imagens/mongodb-connection-string.png)

   A URL copiada tem este formato:

```
mongodb+srv://<db_username>:<db_password>@cluster0.SEU_CODIGO.mongodb.net/
```

   > ⚠️ **`SEU_CODIGO` não é para digitar.** No lugar dele, a sua URL tem um código que é **só do seu cluster**, com letras e números (algo como `x7k2pq9`). Ele vem certo **somente** quando você copia a URL **do Atlas**. Por isso, **nunca monte a URL a partir dos exemplos desta aula**: copie sempre a sua, da tela **Connect**.

4. Na URL que **você** copiou, troque os dois campos, **apagando também os sinais `< >`**:
   - `<db_username>` → o usuário do passo 1.3 (`finbot`);
   - `<db_password>` → a senha desse usuário.

   **Não mexa no resto**, principalmente no trecho depois de `cluster0.`. O resultado tem este formato:

```
mongodb+srv://finbot:SUA_SENHA@cluster0.SEU_CODIGO.mongodb.net/
              ^^^^^^ ^^^^^^^^^          ^^^^^^^^^^
              usuário senha             veio do Atlas: NÃO troque
```

> Em algumas contas, a URL já vem com o nome do usuário preenchido (ex.: `mongodb+srv://finbot:<db_password>@...`) ou com um final como `?retryWrites=true&w=majority&appName=Cluster0`. Tudo bem: troque o que estiver entre `< >` e mantenha o resto como veio.

#### 1.6 — Colocar no `.env`

O seu `.env` **já tem** as linhas do MongoDB desde a Aula 1, apontando para um banco local. Você **não acrescenta** linhas novas: só **troca o valor** do `MONGO_URL`.

**Como está hoje** (desde a Aula 1):

```env
# MongoDB (Aula 3; localmente, o projeto usará finbot_dev)
MONGO_URL=mongodb://localhost:27017
MONGO_BANCO=finbot_dev
```

**Como deve ficar** (o formato; `SUA_SENHA` e `SEU_CODIGO` são os da **sua** URL):

```env
# MongoDB (Aula 3; localmente, o projeto usará finbot_dev)
MONGO_URL=mongodb+srv://finbot:Fatec2026finbot@cluster0.ab1cd.mongodb.net/ # não esqueça que essa é a senha que exemplifiquei lá em cima, a sua será outra
MONGO_BANCO=finbot_dev
```

> ⚠️ **Não copie a linha acima.** Ela só mostra o formato e **não funciona**. O que vai no `.env` é a URL que **você** copiou do Atlas no passo 1.5, com o usuário e a senha trocados.

1. Na linha `MONGO_URL=`, apague **só** o que vem depois do `=` (`mongodb://localhost:27017`).
2. No lugar, cole a **sua** URL do passo 1.5, já com o usuário e a senha trocados. **Sem aspas** e sem espaços.
3. Deixe o comentário e a linha `MONGO_BANCO=finbot_dev` como estão.
4. Salve com **Ctrl+S**.

> ⚠️ **Não deixe dois `MONGO_URL`** no arquivo (o antigo, `localhost`, e o novo, do Atlas). O `.env` deve ter **uma única** linha `MONGO_URL=`, com a URL do Atlas. Com duas, fica difícil saber qual o programa vai usar, e o erro mais comum é ele continuar tentando o `localhost`, onde não há banco nenhum (`ServerSelectionTimeoutError`).
>
> Use o **usuário e a senha do banco** (passo 1.3), e **não** o e-mail e a senha com que você entra no site do Atlas.

> **Não crie o banco nem as coleções no Atlas.** O banco `finbot_dev` e as coleções aparecem sozinhos na primeira vez que o código grava algo. Depois, confira em **Clusters → Browse Collections**.
>
> **Ambientes separados:** no seu computador, `finbot_dev`; no Render, `finbot`. Mesmo cluster, bancos diferentes: seus testes não bagunçam os dados do app no ar.

> 🔜 **O teste da conexão vem depois.** Para testar se a URL funciona, o projeto precisa da biblioteca `pymongo` (Passo 2) e do arquivo `app/repository/mongo.py` (Passo 3). Por isso, o teste fica no **fim do Passo 3**.

### Passo 2 — Dependências e configuração

> ✂️ **Como copiar:** o bloco mostra um trecho do arquivo. Acrescente no seu arquivo só o que está entre `↓↓↓ NOVO` e `↑↑↑ fim do novo ↑↑↑` (ou a linha logo abaixo de `↓ linha nova`). O próprio marcador diz **depois de qual linha** colar: procure essa linha no seu arquivo (`Ctrl+F`). As outras linhas já existem e servem para você achar o lugar. Ao colar, deixe o cursor **no começo da linha** (coluna 1, sem espaços antes), para o VS Code não mudar o recuo.

📄 Arquivo `requirements.txt` (trecho alterado na Aula 3):

```text
uvicorn>=0.30
langfuse>=4.0
# ↓↓↓ NOVO: cole logo abaixo de "langfuse>=4.0" ↓↓↓
# Aula 3 — memória (grafo + MongoDB)
langgraph>=1.0  # grafos de agentes (nós, arestas, estado) e memória por sessão
langgraph-checkpoint-mongodb>=0.3  # salva a memória do grafo no MongoDB
pymongo>=4.10  # conecta o Python ao MongoDB
# ↑↑↑ fim do novo ↑↑↑
```

> ✂️ **Como copiar:** o bloco mostra um trecho do arquivo. Acrescente no seu arquivo só o que está entre `↓↓↓ NOVO` e `↑↑↑ fim do novo ↑↑↑` (ou a linha logo abaixo de `↓ linha nova`). O próprio marcador diz **depois de qual linha** colar: procure essa linha no seu arquivo (`Ctrl+F`). As outras linhas já existem e servem para você achar o lugar. Ao colar, deixe o cursor **no começo da linha** (coluna 1, sem espaços antes), para o VS Code não mudar o recuo.

📄 Arquivo `requirements-dev.txt` (trecho alterado na Aula 3):

```text
pytest>=8.0
httpx>=0.27
# ↓ linha nova: cole logo abaixo de "httpx>=0.27"
mongomock>=4.1  # MongoDB falso, em memória, para os testes
```

> ✂️ **Como copiar:** o bloco mostra um trecho do arquivo. Acrescente no seu arquivo só o que está entre `↓↓↓ NOVO` e `↑↑↑ fim do novo ↑↑↑` (ou a linha logo abaixo de `↓ linha nova`). O próprio marcador diz **depois de qual linha** colar: procure essa linha no seu arquivo (`Ctrl+F`). As outras linhas já existem e servem para você achar o lugar. Ao colar, deixe o cursor **no começo da linha** (coluna 1, sem espaços antes), para o VS Code não mudar o recuo.

📄 Arquivo `app/config/settings.py` (trecho alterado na Aula 3):

```python
    api_url: str = "http://127.0.0.1:8000"

    # ↓↓↓ NOVO: cole logo abaixo de "api_url: str = "http://127.0.0.1:8000"" ↓↓↓
    # MongoDB
    # Estes são só valores PADRÃO: o valor real vem do .env (MONGO_URL e MONGO_BANCO)
    # no seu computador, e das variáveis de ambiente no Render. Se existir no .env, ele vale.
    # NUNCA coloque aqui a URL do Atlas: ela tem a senha do banco e este arquivo vai para o GitHub.
    mongo_url: str = "mongodb://localhost:27017"
    mongo_banco: str = "finbot"  # nome do banco de dados dentro do servidor
    # ↑↑↑ fim do novo ↑↑↑
    @property
    def modelo(self) -> str:
```

**Por que o código tem `localhost` e não a URL do Atlas?** O valor escrito no `settings.py` é só um **padrão**: quando o `.env` tem uma variável com o mesmo nome (`mongo_url` ↔ `MONGO_URL`), o pydantic-settings usa o valor do `.env`. A URL do Atlas tem a **senha do banco**, então ela fica **só** no `.env` (que não vai para o GitHub) e no painel do Render, nunca no código. É a mesma regra das chaves da Groq e do Langfuse.

As variáveis `MONGO_URL` e `MONGO_BANCO` já estão no `.env` desde a Aula 1. Depois de criar o cluster no Atlas, abra `.env` e substitua o **valor** de `MONGO_URL` pela URL de conexão do Atlas, como no passo 1.6 (uma única linha `MONGO_URL`, sem duplicar). Use `MONGO_BANCO=finbot_dev` no computador local. **Não** coloque a URL de conexão com senha no `.env.example`.

```bash
pip install -r requirements-dev.txt
```

### Passo 3 — Repository (`app/repository/`)

Crie a pasta com `__init__.py` vazio e os arquivos:

> 🎯 **Para que serve no projeto:** A pasta `repository/` concentra **todo o acesso ao banco de dados**: nenhum outro arquivo do projeto fala direto com o MongoDB. Este primeiro arquivo cria a conexão (uma só para o projeto inteiro), que os outros arquivos da pasta reaproveitam.

```python
# app/repository/mongo.py
"""Conexão com o MongoDB (uma só para o projeto inteiro)."""
from functools import lru_cache  # guarda o resultado da função para reaproveitar

from pymongo import MongoClient
from pymongo.database import Database

from app.config.settings import settings


# @lru_cache: na 1ª chamada cria a conexão; nas seguintes, devolve a mesma.
@lru_cache
def cliente() -> MongoClient:
    # serverSelectionTimeoutMS=5000: desiste em 5 s se o MongoDB não responder (em vez de travar).
    return MongoClient(settings.mongo_url, serverSelectionTimeoutMS=5000)


def banco() -> Database:
    # cliente()["finbot"] = o banco com esse nome dentro do servidor.
    return cliente()[settings.mongo_banco]
```

`@lru_cache` faz a função rodar **uma vez** e reaproveitar o resultado: uma conexão só para o projeto inteiro.

> 🎯 **Para que serve no projeto:** Cuida da **memória de curto prazo**: a conversa de cada sessão. O LangGraph salva o estado do grafo no MongoDB a cada passo. É isso que permite reiniciar a API (ou ter várias cópias dela no Render) sem perder a conversa, o problema que vimos com o dicionário da Aula 2.

```python
# app/repository/checkpointer.py
"""Memória de CURTO prazo: o checkpointer do LangGraph.

A cada passo do grafo, o estado (com todas as mensagens) é salvo no MongoDB,
identificado pelo thread_id (aqui, o id da sessão de chat).
Na próxima pergunta da mesma sessão, o grafo continua de onde parou.
"""
from langgraph.checkpoint.mongodb import MongoDBSaver

from app.config.settings import settings
from app.repository import mongo


def criar_checkpointer() -> MongoDBSaver:
    # O MongoDBSaver usa a mesma conexão e grava os estados do grafo no banco configurado.
    return MongoDBSaver(mongo.cliente(), db_name=settings.mongo_banco)
```

> 🎯 **Para que serve no projeto:** Cuida da **memória de longo prazo**: o perfil do usuário (nome, objetivo, experiência). Diferente da conversa, o perfil vale para **todas** as sessões do usuário e entra no prompt de sistema, para o FinBot adaptar os exemplos.

```python
# app/repository/perfis.py
"""Memória de LONGO prazo: o perfil do usuário.

Vale para TODAS as conversas do usuário (não só para uma sessão).
Fica numa coleção própria, fora do grafo: é o "BaseStore / banco externo" dos slides.
"""
from app.repository import mongo


def _colecao():
    # Coleção = a "tabela" do MongoDB; aqui fica um documento de perfil por usuário.
    return mongo.banco()["perfis"]


def salvar_perfil(usuario: str, dados: dict) -> None:
    # update_one com upsert=True: atualiza o perfil se ele existir; se não existir, cria.
    # "$set" grava os campos enviados; **dados espalha o dicionário (nome, objetivo...).
    _colecao().update_one({"usuario": usuario}, {"$set": {"usuario": usuario, **dados}}, upsert=True)


def obter_perfil(usuario: str) -> dict:
    # {"_id": 0} esconde o id interno do Mongo; se não achar, devolve só o nome do usuário.
    return _colecao().find_one({"usuario": usuario}, {"_id": 0}) or {"usuario": usuario}


def texto_perfil(usuario: str) -> str:
    """Perfil em texto, pronto para entrar no prompt de sistema."""
    p = obter_perfil(usuario)
    # Junta só os campos preenchidos, ex.: "nome: Ana; objetivo: aposentadoria".
    partes = [f"{campo}: {p[campo]}" for campo in ("nome", "objetivo", "experiencia") if p.get(campo)]
    return "; ".join(partes) or "não informado"
```

> 🎯 **Para que serve no projeto:** Guarda a **lista de conversas** de cada usuário, com título e data. É ela que aparece na barra lateral do chat, para o usuário voltar a uma conversa antiga.

```python
# app/repository/conversas.py
"""Lista de conversas de cada usuário (para a barra lateral do chat)."""
from datetime import datetime, timezone

from app.repository import mongo


def _colecao():
    # Coleção com um documento por conversa (sessão).
    return mongo.banco()["conversas"]


# Cria a conversa na 1ª pergunta; nas seguintes, só atualiza a data.
def registrar(sessao: str, usuario: str, primeira_pergunta: str) -> None:
    agora = datetime.now(timezone.utc)
    _colecao().update_one(
        {"sessao": sessao},
        # $set: sempre atualiza a data; $setOnInsert: título e criação só são gravados quando a conversa é nova.
        {"$set": {"atualizada_em": agora},
         "$setOnInsert": {"sessao": sessao, "usuario": usuario, "titulo": primeira_pergunta[:60], "criada_em": agora}},
        upsert=True,
    )


def listar(usuario: str) -> list[dict]:
    # Conversas do usuário, da mais recente para a mais antiga (-1), no máximo 20.
    return list(_colecao().find({"usuario": usuario}, {"_id": 0}).sort("atualizada_em", -1).limit(20))
```

`upsert=True` cria o documento se ele não existe, ou atualiza se existe. `$setOnInsert` só grava na criação, para o título não mudar a cada mensagem.

#### Testar a conexão com o MongoDB Atlas

Agora que `pymongo` está instalado e `app/repository/mongo.py` existe, confira se a URL do `.env` (passo 1.6) funciona.

**Antes de rodar, compare duas coisas** (leva 10 segundos e evita o erro mais comum):

1. No Atlas, abra **Connect** no seu cluster e olhe o trecho entre `cluster0.` e `.mongodb.net` na URL.
2. No `.env`, olhe o mesmo trecho na linha `MONGO_URL`.

Os dois têm que ser **iguais**. Se no `.env` estiver `SEU_CODIGO` ou qualquer outro código diferente do Atlas, você usou um exemplo: copie a URL do Atlas de novo (passo 1.5).

Depois, no terminal, com o ambiente virtual ativado:

```bash
python -c "from app.repository.mongo import cliente; print(cliente().admin.command('ping'))"
```

Deve imprimir `{'ok': 1}` (em algumas versões, `{'ok': 1.0, ...}`, com mais informações): o Atlas respondeu ao "ping", e a conexão está funcionando.

| Erro | Causa provável |
|---|---|
| `ModuleNotFoundError: No module named 'app.repository'` | a pasta `app/repository/` (ou o `__init__.py` dela) não foi criada neste passo |
| `ModuleNotFoundError: No module named 'pymongo'` | faltou o `pip install -r requirements-dev.txt` do Passo 2 |
| `The DNS query name does not exist: _mongodb._tcp.cluster0.....mongodb.net` | o endereço do cluster está errado: o trecho depois de `cluster0.` não é o do **seu** cluster. Quase sempre é porque a URL foi montada a partir de um exemplo, em vez de copiada do Atlas. Copie de novo (passo 1.5) |
| `bad auth : authentication failed` | usuário ou senha errados na URL, os `< >` ficaram, ou foi usado o login do **site** do Atlas em vez do usuário do **banco** |
| `ServerSelectionTimeoutError` | IP não liberado (passo 1.4), `MONGO_URL` ainda com `localhost` ou duplicado no `.env`, ou a rede da escola bloqueando a porta 27017 |
| `InvalidURI` | senha com caractere especial, ou espaço/aspas na URL |

> **Alternativa sem Atlas** (rede da escola bloqueando): com Docker, `docker run -d -p 27017:27017 mongo:7` e `MONGO_URL=mongodb://localhost:27017`.

### Passo 4 — Janela de contexto (`app/utils/mensagens.py`)

Crie `app/utils/` com `__init__.py` vazio:

> 🎯 **Para que serve no projeto:** Funções de apoio para o histórico. Como o checkpointer guarda tudo, aqui escolhemos o que realmente vai para o LLM: só perguntas e respostas, e só as mais recentes. Isso economiza tokens e evita confundir o modelo.

```python
# app/utils/mensagens.py
"""Ferramentas para lidar com o histórico de mensagens."""
from langchain_core.messages import AIMessage, AnyMessage, HumanMessage


def conversa_limpa(mensagens: list[AnyMessage], limite: int = 10) -> list[AnyMessage]:
    """Só perguntas do usuário e respostas finais (sem chamadas de ferramenta).

    Por quê? Janela de contexto: enviar tudo custa tokens e confunde o modelo.
    As últimas 'limite' mensagens bastam para manter o assunto.
    """
    # Fica com as perguntas (HumanMessage) e com as respostas que têm texto e não são pedidos de ferramenta.
    limpas = [
        m for m in mensagens
        if isinstance(m, HumanMessage) or (isinstance(m, AIMessage) and m.content and not m.tool_calls)
    ]
    return limpas[-limite:]  # só as últimas 'limite' mensagens
```

### Passo 5 — O prompt ganha uma variável

Abra `app/prompts/sistema.md` e acrescente **no final do arquivo**, depois da regra "- Se não souber, diga que não sabe.", uma linha em branco e estas duas linhas:

```markdown

Perfil do usuário (use para adaptar os exemplos, nunca para recomendar):
{{perfil}}
```

`{{perfil}}` é uma **variável de prompt**: o código troca pelo perfil do usuário na hora de montar a mensagem (`compile(perfil=...)`).

### Passo 6 — Prompts pelo Langfuse (`app/prompts/catalogo.py`)

> ✂️ **Como copiar:** o bloco mostra um trecho do arquivo. Acrescente no seu arquivo só o que está entre `↓↓↓ NOVO` e `↑↑↑ fim do novo ↑↑↑` (ou a linha logo abaixo de `↓ linha nova`). O próprio marcador diz **depois de qual linha** colar: procure essa linha no seu arquivo (`Ctrl+F`). As outras linhas já existem e servem para você achar o lugar. Ao colar, deixe o cursor **no começo da linha** (coluna 1, sem espaços antes), para o VS Code não mudar o recuo. A linha `# ...` indica um trecho do arquivo que foi pulado.

📄 Arquivo `app/prompts/catalogo.py` (trecho alterado na Aula 3):

```python

Cada prompt é um arquivo .md nesta pasta (ex.: sistema.md). Prompt é ARTEFATO, não texto solto no código.

# ↓↓↓ NOVO: cole logo abaixo de "Cada prompt é um arquivo .md nesta pasta (ex.: sistema.md..." ↓↓↓
Aula 3: o Langfuse passa a ser a "fonte da verdade". O arquivo .md vira:
  1. a semente: scripts/publicar_prompts.py envia para o Langfuse;
  2. a reserva: se o Langfuse estiver fora do ar, o código usa o .md.
# ↑↑↑ fim do novo ↑↑↑
"""
from pathlib import Path

# ↓ linha nova: cole logo abaixo de "from pathlib import Path"
from app.config.settings import settings

PASTA = Path(__file__).parent
    # ... (parte do arquivo que não muda)
    """Lê o texto do prompt local (arquivo app/prompts/<nome>.md)."""
    return (PASTA / f"{nome}.md").read_text(encoding="utf-8").strip()


# ↓↓↓ NOVO: cole logo abaixo de "return (PASTA / f"{nome}.md").read_text(encoding="utf-8")..." ↓↓↓
# Nomes dos prompts locais: sistema.md -> "sistema" (p.stem = nome do arquivo sem a extensão).
def nomes_locais() -> list[str]:
    return sorted(p.stem for p in PASTA.glob("*.md"))


# No Langfuse, os prompts do projeto ganham o prefixo "finbot-" (ex.: finbot-sistema).
def nome_langfuse(nome: str) -> str:
    return f"finbot-{nome}"


class PromptLocal:
    """Imita um prompt do Langfuse quando ele não está configurado ou não responde."""

    # Mesmos atributos de um prompt do Langfuse: o resto do código não precisa saber de onde veio.
    is_fallback = True
    version = "local"

    def __init__(self, texto: str):
        self.prompt = texto

    def compile(self, **variaveis) -> str:
        # Troca cada {{variavel}} do texto pelo valor recebido (ex.: {{perfil}} -> "iniciante").
        texto = self.prompt
        for chave, valor in variaveis.items():
            texto = texto.replace("{{" + chave + "}}", str(valor))
        return texto


def obter(nome: str):
    """Versão 'production' do prompt no Langfuse (60 s de cache). Sem Langfuse, usa o .md.

    Uso:  p = obter("sistema");  texto = p.compile(perfil="...")
    """
    local = carregar(nome)
    # Sem as chaves do Langfuse, usa direto o arquivo .md.
    if not settings.langfuse_ativo:
        return PromptLocal(local)
    try:
        from app.llm.observabilidade import cliente_langfuse
        # label="production": a versão marcada para uso; fallback: texto usado se o prompt não existir lá.
        # cache_ttl_seconds=60: guarda o prompt por 60 s para não buscar a cada pergunta.
        return cliente_langfuse().get_prompt(
            nome_langfuse(nome), label="production", fallback=local, cache_ttl_seconds=60
        )
    except Exception as erro:
        # Qualquer falha (sem internet, Langfuse fora do ar): avisa no terminal e usa o .md.
        print(f"[prompts] Langfuse indisponível ({erro}); usando {nome}.md")
        return PromptLocal(local)
# ↑↑↑ fim do novo ↑↑↑
```

E uma função para ligar a geração à versão do prompt:

> ✂️ **Como copiar:** o bloco mostra um trecho do arquivo. Acrescente no seu arquivo só o que está entre `↓↓↓ NOVO` e `↑↑↑ fim do novo ↑↑↑` (ou a linha logo abaixo de `↓ linha nova`). O próprio marcador diz **depois de qual linha** colar: procure essa linha no seu arquivo (`Ctrl+F`). As outras linhas já existem e servem para você achar o lugar. Ao colar, deixe o cursor **no começo da linha** (coluna 1, sem espaços antes), para o VS Code não mudar o recuo.

📄 Arquivo `app/llm/observabilidade.py` (trecho alterado na Aula 3):

```python
    with propagate_attributes(session_id=sessao, user_id=usuario, trace_name=nome):
        yield


# ↓↓↓ NOVO: cole no FINAL do arquivo, depois da função rastrear() ↓↓↓
def config_prompt(prompt) -> dict:
    """Liga a chamada do LLM à versão do prompt usada (aparece no trace e nas métricas do prompt)."""
    # Prompt local (fallback) não existe no Langfuse: não há versão para ligar.
    if getattr(prompt, "is_fallback", True):
        return {}
    # O CallbackHandler lê "langfuse_prompt" nos metadados e liga o trace à versão do prompt.
    return {"metadata": {"langfuse_prompt": prompt}}
# ↑↑↑ fim do novo ↑↑↑
```

### Passo 7 — O chatbot vira um nó

> 🎯 **Para que serve no projeto:** Este arquivo **substitui o da Aula 2**. O agente de conversa agora é um **nó do grafo**: em vez de receber histórico e pergunta, recebe o estado do grafo (mensagens + perfil) e devolve só a nova mensagem. O prompt também passa a vir do Langfuse, já com o perfil do usuário.

```python
# app/agents/chatbot.py
"""Agente de conversa geral: LLM + prompt de sistema (sem ferramentas).

Aula 3: vira um NÓ de grafo. Um nó recebe o estado e devolve só o que mudou.
"""
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from app.llm import fabrica
from app.llm.observabilidade import config_prompt
from app.prompts import catalogo
from app.utils.mensagens import conversa_limpa


# Nó do grafo: recebe o estado atual (mensagens e perfil) e devolve só o que mudou.
def no_chatbot(estado: dict) -> dict:
    # Busca o prompt de sistema (no Langfuse ou no .md) e preenche {{perfil}}.
    prompt = catalogo.obter("sistema")
    sistema = SystemMessage(prompt.compile(perfil=estado.get("perfil", "não informado")))
    # Envia regras + conversa (sem passos internos) ao LLM; config liga o trace ao prompt.
    resposta = fabrica.criar_modelo().invoke(
        [sistema] + conversa_limpa(estado["messages"]),
        config=config_prompt(prompt),
    )
    # A nova mensagem do assistente; name="conversa" marca qual agente respondeu.
    return {"messages": [AIMessage(content=resposta.content, name="conversa")]}
```

### Passo 8 — O grafo (`app/agents/grafo.py`)

> 🎯 **Para que serve no projeto:** É o novo **centro do FinBot**: o grafo do LangGraph, que organiza quem faz o quê. Nesta aula ele tem um nó só (o chatbot), mas já traz o essencial: estado, memória no MongoDB (checkpointer) e perfil. Nas próximas aulas, novos nós e caminhos entram aqui, sem mudar a API.

**Do desenho ao código.** Lembra do grafo da Parte 1, com pontos (nós) ligados por setas (arestas)? Neste arquivo, você monta o grafo do FinBot em três linhas, uma para cada parte do desenho:

```mermaid
flowchart LR
    S([START]) --> C[chatbot] --> E([END])
```

| No desenho | No código | O que faz |
|---|---|---|
| o nó `chatbot` | `g.add_node("chatbot", no_chatbot)` | cria a caixa e diz qual função ela executa (a `no_chatbot` do Passo 7) |
| a seta `START → chatbot` | `g.add_edge(START, "chatbot")` | diz por onde o grafo começa |
| a seta `chatbot → END` | `g.add_edge("chatbot", END)` | diz que, depois do chatbot, o grafo termina |
| o que viaja pelas setas | `class EstadoChat` | o **estado**: as mensagens e o perfil, que cada nó lê e atualiza |

Depois de declarar nós e setas, `g.compile(...)` transforma o desenho num grafo que pode ser executado com `.invoke()`. Procure essas linhas na função `montar_grafo()`, abaixo.

```python
# app/agents/grafo.py
"""O grafo principal do FinBot.

Grafo = NÓS (funções) + ARESTAS (quem vem depois) + ESTADO (o "bastão" que passa de nó em nó).

Aula 3:   START ─▶ chatbot ─▶ END        (+ checkpointer = memória de curto prazo)
"""
from functools import lru_cache  # guarda o grafo pronto para não montar de novo a cada pergunta
from typing import Annotated, TypedDict

from langchain_core.messages import AnyMessage, HumanMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from app.agents.chatbot import no_chatbot
from app.llm.observabilidade import callbacks, rastrear
from app.repository import checkpointer, conversas, perfis
from app.utils.mensagens import conversa_limpa


# O ESTADO do grafo: o que passa de nó em nó. total=False = nenhum campo é obrigatório.
class EstadoChat(TypedDict, total=False):
    # add_messages: em vez de substituir a lista, ACRESCENTA as mensagens novas ao histórico.
    messages: Annotated[list[AnyMessage], add_messages]  # histórico (o checkpointer salva)
    perfil: str                                           # memória de longo prazo, vinda do Mongo


# ---------- Montagem ----------
def montar_grafo(memoria=None):
    # Cria o grafo, registra o nó "chatbot" e liga START -> chatbot -> END.
    g = StateGraph(EstadoChat)
    g.add_node("chatbot", no_chatbot)
    g.add_edge(START, "chatbot")
    g.add_edge("chatbot", END)
    # compile() deixa o grafo pronto para rodar; o checkpointer salva o estado a cada passo.
    return g.compile(checkpointer=memoria)


@lru_cache
def grafo():
    """Compila uma única vez, com a memória no MongoDB."""
    return montar_grafo(checkpointer.criar_checkpointer())


def executar(pergunta: str, sessao: str, usuario: str = "anonimo") -> dict:
    # thread_id identifica a conversa: o checkpointer guarda um histórico para cada sessão.
    config = {"configurable": {"thread_id": sessao}, "callbacks": callbacks()}
    # Só a pergunta nova vai na entrada; o histórico anterior vem do checkpointer.
    entrada = {"messages": [HumanMessage(pergunta)], "perfil": perfis.texto_perfil(usuario)}
    with rastrear(sessao, usuario):
        # Roda o grafo do START ao END e devolve o estado final.
        estado = grafo().invoke(entrada, config)
    # Registra (ou atualiza) a conversa na lista da barra lateral.
    conversas.registrar(sessao, usuario, pergunta)

    # A última mensagem do estado é a resposta do FinBot.
    final = estado["messages"][-1]
    return {"resposta": final.content, "agente": "conversa", "fontes": []}


def historico(sessao: str) -> list[dict]:
    """Mensagens da sessão lidas do checkpointer (para mostrar na tela)."""
    # get_state lê o último estado salvo dessa sessão no checkpointer.
    estado = grafo().get_state({"configurable": {"thread_id": sessao}})
    mensagens = estado.values.get("messages", []) if estado else []
    # limite=1000: na tela queremos a conversa inteira, não só as 10 últimas.
    return [
        {"papel": "user" if m.type == "human" else "assistant", "conteudo": m.content, "agente": m.name}
        for m in conversa_limpa(mensagens, limite=1000)
    ]


if __name__ == "__main__":
    # python -m app.agents.grafo  -> desenho do grafo em Mermaid (cole em https://mermaid.live)
    print(montar_grafo().get_graph(xray=True).draw_mermaid())
```

**Leia com calma:**

- `montar_grafo()` declara nós e arestas; `compile(checkpointer=...)` liga a memória.
- `executar()` manda **só a mensagem nova**. O checkpointer recupera as anteriores pelo `thread_id` e o reducer `add_messages` junta tudo.
- `historico()` lê o estado salvo (`get_state`) para mostrar a conversa na tela.

Veja o desenho do grafo:

```bash
python -m app.agents.grafo
```

O terminal imprime um texto que começa com `graph TD;`. Copie **todo** esse texto, abra o [mermaid.live](https://mermaid.live) (gratuito, sem cadastro), apague o exemplo que aparece no painel **Code** e cole no lugar. O desenho deve ser este:

![Grafo da Aula 3 desenhado no Mermaid: __start__ ligado a chatbot, ligado a __end__](imagens/mermaid-grafo-aula3.png)

Três caixas em linha: `__start__` → `chatbot` → `__end__`. Os nomes com dois sublinhados são como o LangGraph chama o `START` e o `END` do código. Nas próximas aulas, rode o mesmo comando e veja o desenho crescer.

### Passo 9 — Serviço, API e front

O serviço passa a delegar para o grafo e ganha funções de perfil e conversas:

> 🎯 **Para que serve no projeto:** Este arquivo **substitui o da Aula 2**. O serviço continua sendo a porta única do chat, mas agora só repassa: as perguntas vão para o grafo, e perfil e conversas vão para o repository. O dicionário de memória provisória sai de cena.

```python
# app/servicos/chat.py
"""Camada de serviço: a ÚNICA porta de entrada do chat.

A API (e qualquer outro canal no futuro: WhatsApp, terminal...) chama estas funções.
Assim, quando o "miolo" muda de aula para aula, a API não precisa mudar.
"""
from app.agents import grafo
from app.repository import conversas, perfis


def perguntar(pergunta: str, sessao: str, usuario: str = "anonimo") -> dict:
    # A partir desta aula, quem responde é o grafo (com memória no MongoDB).
    return grafo.executar(pergunta, sessao, usuario)


def historico(sessao: str) -> list[dict]:
    return grafo.historico(sessao)


# As funções abaixo só repassam para o repository: a API não fala direto com o banco.
def listar_conversas(usuario: str) -> list[dict]:
    return conversas.listar(usuario)


def obter_perfil(usuario: str) -> dict:
    return perfis.obter_perfil(usuario)


def salvar_perfil(usuario: str, dados: dict) -> dict:
    perfis.salvar_perfil(usuario, dados)
    return perfis.obter_perfil(usuario)
```

> ✂️ **Como copiar:** o bloco mostra um trecho do arquivo. Acrescente no seu arquivo só o que está entre `↓↓↓ NOVO` e `↑↑↑ fim do novo ↑↑↑` (ou a linha logo abaixo de `↓ linha nova`). O próprio marcador diz **depois de qual linha** colar: procure essa linha no seu arquivo (`Ctrl+F`). As outras linhas já existem e servem para você achar o lugar. Ao colar, deixe o cursor **no começo da linha** (coluna 1, sem espaços antes), para o VS Code não mudar o recuo. A linha `# ...` indica um trecho do arquivo que foi pulado.

📄 Arquivo `app/api/schemas.py` (trecho alterado na Aula 3):

```python
class Resposta(BaseModel):
    resposta: str
    # ↓↓↓ NOVO: cole logo abaixo de "resposta: str", dentro de class Resposta ↓↓↓
    agente: str = "conversa"  # qual agente respondeu
    fontes: list[str] = []  # de onde vieram os dados da resposta (a partir da Aula 4)
    # ↑↑↑ fim do novo ↑↑↑


    # ... (parte do arquivo que não muda)
    papel: str
    conteudo: str
# ↓↓↓ NOVO: cole no FINAL do arquivo, logo abaixo de "conteudo: str" (class Mensagem) ↓↓↓
    agente: str | None = None  # qual agente escreveu a mensagem


# Dados do perfil (memória de longo prazo); todos opcionais.
class Perfil(BaseModel):
    nome: str = ""
    objetivo: str = ""        # ex.: "reserva de emergência", "aposentadoria"
    experiencia: str = ""     # ex.: "iniciante"
# ↑↑↑ fim do novo ↑↑↑
```

> ✂️ **Como copiar:** o bloco mostra um trecho do arquivo. Acrescente no seu arquivo só o que está entre `↓↓↓ NOVO` e `↑↑↑ fim do novo ↑↑↑` (ou a linha logo abaixo de `↓ linha nova`). O próprio marcador diz **depois de qual linha** colar: procure essa linha no seu arquivo (`Ctrl+F`). As outras linhas já existem e servem para você achar o lugar. Ao colar, deixe o cursor **no começo da linha** (coluna 1, sem espaços antes), para o VS Code não mudar o recuo. A linha `# ...` indica um trecho do arquivo que foi pulado.

📄 Arquivo `app/api/rotas.py` (trecho alterado na Aula 3):

```python

from app.api.schemas import Mensagem, Pergunta, Resposta
# ↓ linha nova: cole logo abaixo de "from app.api.schemas import Mensagem, Pergunta, Resposta"
from app.api.schemas import Perfil
from app.config.settings import settings
from app.servicos import chat
# ... (parte do arquivo que não muda)
def mensagens(sessao: str):
    return chat.historico(sessao)


# ↓↓↓ NOVO: cole logo abaixo de "return chat.historico(sessao)" ↓↓↓
# Lista as conversas do usuário (para a barra lateral).
@router.get("/usuarios/{usuario}/conversas")
def conversas(usuario: str):
    return chat.listar_conversas(usuario)


# Lê o perfil do usuário.
@router.get("/usuarios/{usuario}/perfil")
def ver_perfil(usuario: str):
    return chat.obter_perfil(usuario)


# PUT = substitui o perfil pelo que foi enviado (validado pelo schema Perfil).
@router.put("/usuarios/{usuario}/perfil")
def salvar_perfil(usuario: str, perfil: Perfil):
    # model_dump() transforma o objeto Pydantic em dicionário.
    return chat.salvar_perfil(usuario, perfil.model_dump())
# ↑↑↑ fim do novo ↑↑↑
```

No front, a barra lateral ganha usuário, perfil e lista de conversas:

> ✂️ **Como copiar:** o bloco mostra um trecho do arquivo. Acrescente no seu arquivo só o que está entre `↓↓↓ NOVO` e `↑↑↑ fim do novo ↑↑↑` (ou a linha logo abaixo de `↓ linha nova`). O próprio marcador diz **depois de qual linha** colar: procure essa linha no seu arquivo (`Ctrl+F`). As outras linhas já existem e servem para você achar o lugar. Ao colar, deixe o cursor **no começo da linha** (coluna 1, sem espaços antes), para o VS Code não mudar o recuo. As linhas depois de `APAGUE` aparecem comentadas: apague-as do seu arquivo.

📄 Arquivo `frontend/streamlit_app.py` (trecho alterado na Aula 3):

> ⚠️ **Atenção ao recuo.** O bloco novo começa com `with st.sidebar:` **na coluna 1, sem espaços antes**: no mesmo nível do `if "sessao" not in st.session_state:`, e **não dentro dele**. Ele entra exatamente no lugar da linha `usuario = "aluno1"`, que você apaga.
>
> **Por quê?** O Streamlit roda o script inteiro de novo a cada clique, e esse `if` só é verdadeiro na **primeira** vez (quando ainda não existe sessão). Se a barra lateral ficar dentro dele, ela aparece ao abrir a página e **some no primeiro clique**.

```python
    st.session_state.sessao = str(uuid.uuid4())[:8]
    st.session_state.mensagens = []
# APAGUE do seu arquivo a(s) linha(s) abaixo (aqui aparecem comentadas):
# usuario = "aluno1"

# ↓↓↓ NOVO: cole no lugar da linha usuario = "aluno1", FORA do if (sem recuo) ↓↓↓
# ---------- Barra lateral: usuário, perfil (memória de longo prazo) e conversas ----------
with st.sidebar:
    # Campo para escolher o usuário (cada um tem perfil e conversas próprios).
    usuario = st.text_input("Seu usuário", value="aluno1")

    with st.expander("Meu perfil"):
        # Busca o perfil salvo para preencher o formulário.
        perfil = api("GET", f"/usuarios/{usuario}/perfil")
        # st.form agrupa os campos: nada é enviado até clicar no botão.
        with st.form("perfil"):
            nome = st.text_input("Nome", perfil.get("nome", ""))
            objetivo = st.text_input("Objetivo", perfil.get("objetivo", ""))
            niveis = ["", "iniciante", "intermediário", "avançado"]
            # Se o nível salvo estiver na lista, ele já aparece selecionado.
            atual = perfil.get("experiencia", "")
            experiencia = st.selectbox("Experiência", niveis, index=niveis.index(atual) if atual in niveis else 0)
            # Ao clicar, envia o perfil para a API (PUT) e mostra a confirmação.
            if st.form_submit_button("Salvar perfil"):
                api("PUT", f"/usuarios/{usuario}/perfil",
                    json={"nome": nome, "objetivo": objetivo, "experiencia": experiencia})
                st.success("Perfil salvo!")

    # Nova conversa = novo id de sessão e tela limpa.
    if st.button("➕ Nova conversa", use_container_width=True):
        st.session_state.sessao = str(uuid.uuid4())[:8]
        st.session_state.mensagens = []

    st.subheader("Conversas")
    # Um botão por conversa; ao clicar, carrega o histórico dela pela API.
    # key=c["sessao"]: o Streamlit exige um identificador único para cada botão.
    for c in api("GET", f"/usuarios/{usuario}/conversas"):
        if st.button(c["titulo"], key=c["sessao"], use_container_width=True):
            st.session_state.sessao = c["sessao"]
            st.session_state.mensagens = api("GET", f"/sessoes/{c['sessao']}/mensagens")
# ↑↑↑ fim do novo ↑↑↑


```

Teste: converse, **reinicie a API** (Ctrl+C e `uvicorn` de novo) e clique na conversa na barra lateral. A memória sobreviveu.

#### O que fica guardado no MongoDB (e onde ver as conversas)

No Atlas, em **Project 0 Overview**, clique em **Browse collections** (na linha do `Cluster0`, entre **Connect** e **Metrics**), ou use o menu **DATABASE → Data Explorer**. Na lista à esquerda, abra o banco **`finbot_dev`** (o `sample_mflix` é o banco de exemplo do Atlas). Se ele não aparecer, clique em **Refresh**.

![Data Explorer do MongoDB Atlas com o banco finbot_dev aberto e a coleção conversas mostrando um documento com sessao, titulo e usuario](imagens/mongodb-colecao-conversas.png)

| Coleção | O que guarda | Dá para ler no Atlas? |
|---|---|---|
| `conversas` | **um documento por sessão**: `sessao`, `usuario`, `titulo` (só a **primeira** pergunta, para dar nome à conversa na barra lateral) e as datas | Sim |
| `perfis` | o perfil de cada usuário (nome, objetivo, experiência). Só aparece depois de salvar um perfil | Sim |
| `checkpoints` | o **histórico completo**: todas as perguntas **e** respostas, salvo pelo LangGraph a cada passo do grafo | **Não**: fica num formato compactado (`Binary`), feito para o programa ler |
| `checkpoint_writes` | passos intermediários do LangGraph (uso interno) | Não |

> **Por que não vejo as respostas em `conversas`?** Porque ela é só o **índice** das conversas, não o histórico: guarda o título e as datas, nada mais. Mesmo com 10 perguntas na mesma sessão, continua sendo **um** documento.
>
> **Por que há tantos documentos em `checkpoints`?** O LangGraph salva o estado a **cada passo** do grafo, não uma vez por pergunta. É normal crescer rápido.

Veja como um documento de `checkpoints` aparece no Atlas:

![Coleção checkpoints no Data Explorer do Atlas: documentos com thread_id sessao-123, o campo checkpoint em Binary, type msgpack e parent_checkpoint_id](imagens/mongodb-colecao-checkpoints.png)

- **`thread_id`**: a **sessão** (`sessao-123`). É assim que o LangGraph separa uma conversa da outra.
- **`checkpoint`**: o estado do grafo, **com as mensagens dentro**, mas compactado (`Binary.createFromBase64(...)`, no formato `msgpack`). Por isso não dá para ler a pergunta e a resposta aqui.
- **`parent_checkpoint_id`**: aponta para o checkpoint **anterior** da mesma sessão. Os documentos formam uma corrente, um retrato depois do outro; o primeiro tem `null`.

**Onde ver as perguntas e respostas, em texto:**

1. **Pela API:** no `/docs`, abra **`GET /sessoes/{sessao}/mensagens`** → **Try it out** → digite a sessão (ex.: `sessao-123`) → **Execute**. A API lê o checkpoint e devolve a conversa inteira, com `"papel": "user"` (pergunta) e `"papel": "assistant"` (resposta).
2. **Pelo front:** na barra lateral do Streamlit, clique na conversa: ela é carregada inteira.
3. **Pelo Langfuse:** em **Tracing**, cada pergunta é um trace, com o que foi enviado ao LLM (prompt de sistema, perfil e histórico) e a resposta. Em **Sessions**, as perguntas da mesma sessão aparecem agrupadas, em ordem. É o melhor lugar para entender **por que** o FinBot respondeu daquele jeito.

   ![Tela Sessions do Langfuse listando as sessões 4fc73108, 227afeae e sessao-123, com duração, ambiente local ou producao e o usuário de cada uma](imagens/langfuse-sessoes.png)

   Cada linha é uma **sessão** (uma conversa). A coluna **ID** é o mesmo valor de `sessao` que aparece na API e no MongoDB: as de 8 caracteres (ex.: `4fc73108`) foram criadas pelo Streamlit, e `sessao-123` é o exemplo do `/docs`. **Environment** mostra se a conversa foi no seu computador (`local`) ou no app publicado (`producao`), e **User IDs**, de qual usuário ela é. Clique no ID para ver todas as perguntas e respostas da sessão, em ordem.

### Passo 10 — Publicar os prompts no Langfuse

> 🎯 **Para que serve no projeto:** É um **script de linha de comando** (não faz parte da API) que envia os prompts da pasta `app/prompts/` para o Langfuse. Depois disso, você pode editar e versionar os prompts pelo site do Langfuse, e o FinBot passa a usar a versão nova sem precisar de deploy.

```python
# scripts/publicar_prompts.py
"""Aula 3 — Envia os prompts (app/prompts/*.md) para o Langfuse.

    python -m scripts.publicar_prompts            # cria só os que ainda não existem
    python -m scripts.publicar_prompts --forcar   # envia o .md como NOVA versão de todos

Depois de publicado, edite o prompt no site do Langfuse: salve uma versão nova e
mova o rótulo 'production' para ela. O app passa a usar a versão nova em até 60 s, sem deploy.
"""
import sys

from app.config.settings import settings
from app.llm.observabilidade import cliente_langfuse
from app.prompts import catalogo


def publicar(forcar: bool = False) -> None:
    # Sem as chaves não há para onde enviar.
    if not settings.langfuse_ativo:
        print("Configure LANGFUSE_PUBLIC_KEY e LANGFUSE_SECRET_KEY no .env primeiro.")
        return
    lf = cliente_langfuse()
    # Para cada arquivo .md da pasta app/prompts...
    for nome in catalogo.nomes_locais():
        # ...pega o texto local e o nome no Langfuse (ex.: finbot-sistema).
        texto, remoto = catalogo.carregar(nome), catalogo.nome_langfuse(nome)
        try:
            # Busca a versão atual (cache_ttl_seconds=0: sem cache, sempre a mais nova).
            atual = lf.get_prompt(remoto, label="production", cache_ttl_seconds=0)
            # Sem --forcar, ou se o texto não mudou, não cria versão nova.
            if not forcar or atual.prompt == texto:
                print(f"=  {remoto}: já existe (versão {atual.version})")
                continue
        except Exception:
            pass  # ainda não existe no Langfuse
        # Cria uma versão nova e já a marca como "production" (a que o app usa).
        novo = lf.create_prompt(name=remoto, prompt=texto, labels=["production"],
                                commit_message="enviado por scripts/publicar_prompts.py")
        print(f"+  {remoto}: versão {novo.version} (production)")
    # flush() garante que tudo foi enviado antes de o script terminar.
    lf.flush()


if __name__ == "__main__":
    # --forcar na linha de comando liga o modo forçar.
    publicar(forcar="--forcar" in sys.argv)
```

```bash
python -m scripts.publicar_prompts
```

O terminal mostra uma linha por prompt, por exemplo `+  finbot-sistema: versão 1 (production)`. Os prompts publicados são **todos os arquivos `.md` da pasta `app/prompts/`** (hoje, só o `sistema.md`), e cada um ganha o prefixo `finbot-` no Langfuse.

**Onde ver no Langfuse:**

1. No menu da esquerda, em **Prompt Management**, clique em **Prompts**. Aparece a lista dos prompts do projeto, com o `finbot-sistema` (coluna **Versions**: `1`; **Type**: `text`). A coluna **Number of Observations** começa em `0` e cresce conforme o FinBot usa o prompt.
2. Clique em `finbot-sistema` para abrir o prompt:

![Prompt finbot-sistema no Langfuse, versão 1 com os rótulos production e latest, o texto do prompt de sistema e a variável perfil](imagens/langfuse-prompt-publicado.png)

- À esquerda, a lista de **versões**: por enquanto, só a `# 1`, enviada pelo script.
- Os **rótulos** (*labels*) ao lado da versão. Eles são o que decide **qual versão o FinBot usa**:

  | Rótulo | Quem coloca | O que significa |
  |---|---|---|
  | **`latest`** | o **Langfuse, sozinho** | a versão **mais nova**. Muda sozinho a cada versão criada |
  | **`production`** | **você**, à mão | a versão que o **app usa**. O `catalogo.py` busca exatamente este rótulo (`label="production"`) |

  > ⚠️ **Criar uma versão nova não muda o app.** A versão nova ganha `latest`, mas o FinBot continua usando a que tem `production`. Ele só passa a usar a nova quando você **coloca o rótulo `production` nela**. Assim dá para escrever e testar um prompt com calma, sem afetar quem está usando o app, e "promover" a versão só quando estiver boa.

  > 🔜 **E para testar a versão nova no seu computador antes de promover?** Hoje o código busca `production` nos dois ambientes (computador e Render). Na **Aula 4**, o rótulo vira uma configuração, como o `MONGO_BANCO`: o computador pode usar `latest` (a versão mais nova, em teste) e o Render continua com `production` (a aprovada).
- Em **Prompt**, o texto, igual ao do `sistema.md`. O `{{perfil}}` aparece destacado, e o Langfuse lista `perfil` em **variables**: é a variável que o código preenche com o perfil do usuário.
- Na aba **Linked Generations**, aparecem as conversas que usaram esta versão (depois que você conversar com o FinBot).

> A partir de agora, aquela mensagem `Prompt not found: 'finbot-sistema'... 404`, que podia aparecer no terminal da API desde o Passo 6, deixa de aparecer: o código encontra o prompt no Langfuse.

**Experimento de versionamento:**

1. No Langfuse → **Prompts** → `finbot-sistema` → **New version**. Acrescente a regra: *"Termine toda resposta com uma pergunta para o usuário."*
2. Ao salvar, **marque o rótulo `production`** na versão nova (na tela de criação há a opção de aplicar o rótulo; se esquecer, abra a versão e use **Add label → production**). **Sem esse rótulo, o app continua usando a v1**: a versão nova fica só como `latest`.

   Depois de aplicar, a lista de versões fica assim: a **`# 2`** com **`production`** e **`latest`**, e a **`# 1` sem rótulo nenhum**. O rótulo `production` "mudou de casa": cada rótulo fica em **uma** versão por vez.
3. Em até 60 s (o cache), converse no app. O comportamento mudou **sem commit e sem deploy**.
4. Abra um trace: a geração mostra **qual versão** do prompt foi usada.
5. Para desfazer, mova o rótulo `production` de volta para a v1 (*rollback*).

### Passo 11 — Testes

> 🎯 **Para que serve no projeto:** São os **testes** desta aula: conferem a memória por sessão, o perfil entrando no prompt, as novas rotas da API e o uso do prompt local quando o Langfuse não está configurado. Usam um MongoDB falso, em memória, então rodam sem internet.

```python
# tests/test_aula3.py
"""Aula 3 — grafo com checkpointer (curto prazo), perfil (longo prazo) e prompts versionados."""
# A fixture falso (tests/conftest.py) troca o LLM e o MongoDB por versões falsas, em memória.
from app.agents import grafo
from app.prompts import catalogo
from app.repository import perfis


# Mesma sessão lembra a conversa; outra sessão começa do zero.
def test_memoria_de_curto_prazo_por_sessao(falso):
    grafo.executar("Meu nome é Ana", sessao="t1")
    grafo.executar("Qual é meu nome?", sessao="t1")
    assert "Meu nome é Ana" in [m.content for m in falso.vistas]
    grafo.executar("Oi", sessao="t2")
    assert "Meu nome é Ana" not in [m.content for m in falso.vistas]  # outra sessão, outra memória


# O histórico mostrado na tela é lido do checkpointer (pergunta + resposta).
def test_historico_vem_do_checkpointer(falso):
    grafo.executar("Pergunta 1", sessao="t3")
    historico = grafo.historico("t3")
    assert [m["papel"] for m in historico] == ["user", "assistant"]


# O perfil salvo no Mongo aparece no prompt de sistema (falso.vistas[0]).
def test_perfil_entra_no_prompt(falso):
    perfis.salvar_perfil("bia", {"nome": "Bia", "objetivo": "reserva de emergência"})
    grafo.executar("Oi", sessao="t4", usuario="bia")
    assert "reserva de emergência" in falso.vistas[0].content


# A API salva e lê o perfil, e a 1ª pergunta vira o título da conversa.
def test_api_perfil_e_conversas(api):
    api.put("/usuarios/caio/perfil", json={"nome": "Caio", "experiencia": "iniciante"})
    assert api.get("/usuarios/caio/perfil").json()["nome"] == "Caio"
    api.post("/chat", json={"mensagem": "O que é CDI?", "sessao": "c1", "usuario": "caio"})
    assert api.get("/usuarios/caio/conversas").json()[0]["titulo"] == "O que é CDI?"


# Sem chaves do Langfuse, o prompt vem do .md e {{perfil}} é preenchido.
def test_prompt_sem_langfuse_usa_arquivo_local():
    p = catalogo.obter("sistema")
    assert p.is_fallback
    assert p.compile(perfil="iniciante").endswith("iniciante")
```

```bash
pytest -v
```

### Passo 12 — Publicar: `render.yaml`, push e variáveis no Render

No seu computador, o endereço do MongoDB vem do `.env`. Mas o `.env` **não vai para o GitHub**, então a API publicada no Render ainda não sabe onde está o banco. Sem isso, toda rota que usa o MongoDB dá **erro 500**, e o app do Streamlit para com um `HTTPError` na barra lateral.

#### 12.1 — Declarar o `MONGO_URL` no `render.yaml`

> ✂️ **Como copiar:** o bloco mostra um trecho do arquivo. Acrescente no seu arquivo só o que está entre `↓↓↓ NOVO` e `↑↑↑ fim do novo ↑↑↑` (ou a linha logo abaixo de `↓ linha nova`). O próprio marcador diz **depois de qual linha** colar: procure essa linha no seu arquivo (`Ctrl+F`). As outras linhas já existem e servem para você achar o lugar. Ao colar, deixe o cursor **no começo da linha** (coluna 1, sem espaços antes), para o VS Code não mudar o recuo.

📄 Arquivo `render.yaml` (trecho alterado na Aula 3):

```yaml
      - key: LANGFUSE_HOST
        value: https://cloud.langfuse.com
      # ↓↓↓ NOVO: cole logo abaixo de "value: https://cloud.langfuse.com" ↓↓↓
      # Endereço do MongoDB Atlas (secreto: contém usuário e senha).
      - key: MONGO_URL
        sync: false
      # ↑↑↑ fim do novo ↑↑↑
```

`sync: false` diz ao Render que o valor é **secreto**: ele não fica no arquivo (que vai para o GitHub). Você digita o valor no painel, no passo 12.3.

#### 12.2 — Enviar para o GitHub

```bash
git add .
git commit -m "Aula 3: grafo com memória no MongoDB e prompts versionados"
git pull
git push
```

O Render percebe o push e publica o código novo sozinho. Mas, **até o passo 12.3**, a API publicada ainda não tem o `MONGO_URL`.

#### 12.3 — Cadastrar o `MONGO_URL` no Render

1. No [Render](https://dashboard.render.com), clique no serviço **`finbot-api`**.
2. No menu da esquerda, em **MANAGE**, clique em **Environment**. Aparecem as variáveis da Aula 2, com os valores escondidos (`••••••`). Clique em **Edit**, no canto superior direito:

   ![Página Environment do serviço finbot-api no Render, com o menu MANAGE, a lista de variáveis e o botão Edit destacado](imagens/render-environment.png)

> **Não acha "Logs" ou "Environment" no menu da esquerda do serviço?** O Render costuma mostrar um quadro de propaganda (ex.: **"Introducing Workflows"**) no meio desse menu, que **empurra os itens para baixo** e dá a impressão de que o menu só tem *Deploys* e *Settings*. Feche o quadro no **X** (ou role o menu da esquerda) e os outros itens aparecem: **Logs**, **Environment** e os demais. As variáveis de ambiente, como as chaves, ficam em **Environment**, e **não** em *Settings*; dá para editá-las no plano gratuito.

3. Se o `MONGO_URL` ainda não aparecer na lista, clique em **+ Add variable**, embaixo da lista, e preencha:
   - **Key:** `MONGO_URL`
   - **Value:** a **mesma URL do Atlas** que está no seu `.env`: copie só o que vem **depois** do `MONGO_URL=`.
4. Clique de novo em **+ Add variable** e crie:
   - **Key:** `MONGO_BANCO`
   - **Value:** `finbot` (**não** `finbot_dev`: esse é o banco do seu computador; o app publicado usa outro, para os seus testes não se misturarem com os dados do app no ar).

   ![Variáveis do Render em modo de edição, com MONGO_URL acrescentado e os botões Add variable e Save, rebuild, and deploy](imagens/render-environment-mongo.png)

5. Clique em **Save, rebuild, and deploy** (canto inferior direito). **Esse clique é o que republica a API** com as variáveis novas: só salvar não basta.

> 🔒 **Cuidado com prints desta tela:** depois de colar, o valor do `MONGO_URL` aparece **aberto**, com a senha do banco. Não compartilhe prints sem cobrir esse campo.

#### 12.4 — Conferir se funcionou

1. Volte para a página do serviço (**Events** ou **Deploys**) e espere o deploy terminar: o selo verde **Live** aparece de novo (de 1 a 3 minutos).
2. Abra o `/docs` da sua API publicada e teste `GET /usuarios/{usuario}/conversas` com qualquer nome: deve responder **200** (com `[]` se o usuário ainda não conversou), e não mais 500.
3. Abra o app no Streamlit e **recarregue a página** (F5). A barra lateral aparece com **Seu usuário**, **Meu perfil** e as conversas. Converse um pouco.
4. No Atlas, em **Browse collections**, aparece um banco novo, **`finbot`**, separado do `finbot_dev` do seu computador.

O Streamlit **não precisa de nenhuma mudança**: o `API_URL` dele já aponta para a API do Render, e ele se atualiza sozinho a cada push.

#### 12.5 — Marcar a aula

Com tudo funcionando no ar:

```bash
git tag aula-3
git push --tags
```

---

## ✅ Checklist da aula

- [ ] Cluster M0 no Atlas e `MONGO_URL` no `.env` e no Render
- [ ] Conversa sobrevive ao reinício da API
- [ ] Perfil salvo aparece no prompt (confira no trace do Langfuse)
- [ ] Prompts publicados; uma versão nova testada e um rollback feito
- [ ] App no ar atualizado; tag `aula-3` no GitHub

## 🚀 Para ir além

- Mostre na barra lateral a **versão do prompt** em uso (`prompt.version`).
- Use o `ttl` do `MongoDBSaver` para apagar conversas com mais de 30 dias.
- Memória de longo prazo **automática**: um nó extra que, ao fim da conversa, pede ao LLM um resumo dos fatos sobre o usuário e salva no perfil.

## 📁 Estrutura do projeto ao final da aula

Confira no painel **Explorer/Explorador** do VS Code se os arquivos de memória e do grafo estão nos caminhos abaixo. `settings.py`, `catalogo.py`, `chatbot.py`, `chat.py`, `.env.example` e `render.yaml` foram atualizados nesta aula; não crie cópias deles.

```text
finbot/
├── .env                         # local: credenciais; não publicar
├── .env.example
├── .gitignore
├── README.md
├── requirements.txt
├── requirements-dev.txt
├── render.yaml
├── aulas/
│   ├── aula-01.md
│   ├── aula-02.md
│   ├── aula-03.md
│   ├── aula-04.md
│   ├── aula-05.md
│   ├── aula-06.md
│   ├── aula-07.md
│   └── problemas-comuns.md
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── fabrica.py
│   │   └── observabilidade.py
│   ├── prompts/
│   │   ├── __init__.py
│   │   ├── catalogo.py
│   │   └── sistema.md
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── chatbot.py
│   │   └── grafo.py
│   ├── servicos/
│   │   ├── __init__.py
│   │   └── chat.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── schemas.py
│   │   └── rotas.py
│   ├── repository/
│   │   ├── __init__.py
│   │   ├── mongo.py
│   │   ├── checkpointer.py
│   │   ├── perfis.py
│   │   └── conversas.py
│   └── utils/
│       ├── __init__.py
│       └── mensagens.py
├── frontend/
│   ├── requirements.txt
│   └── streamlit_app.py
├── scripts/
│   ├── chat_terminal.py
│   └── publicar_prompts.py
└── tests/
    ├── conftest.py
    ├── test_aula1.py
    ├── test_aula2.py
    └── test_aula3.py
```

> A pasta `.venv/` existe no seu computador, mas é ignorada pelo Git. Não a envie ao GitHub.

## 🗺️ O papel de cada parte do FinBot

Em três aulas, o FinBot ganhou muitas pastas. Elas não são enfeite: cada uma tem **uma responsabilidade**, e é isso que permite mudar uma parte sem quebrar as outras. Vamos ver primeiro o **caminho de uma pergunta** e depois o papel de cada pasta.

### O caminho de uma pergunta

Quando alguém digita "O que é CDI?" no app, a pergunta passa por estas partes, nesta ordem:

```mermaid
flowchart TD
    U([Usuário no navegador]) --> F[frontend/streamlit_app.py<br/>a tela do chat]
    F -->|POST /chat| R[app/api/rotas.py<br/>recebe o pedido HTTP]
    R --> S[app/servicos/chat.py<br/>a porta única do chat]
    S --> G[app/agents/grafo.py<br/>o grafo do LangGraph]
    G --> C[app/agents/chatbot.py<br/>o nó que responde]
    C --> P[app/prompts/catalogo.py<br/>busca o prompt no Langfuse ou no .md]
    C --> L[app/llm/fabrica.py<br/>cria o modelo e chama o LLM]
    G <-->|lê e salva a conversa| M[(MongoDB Atlas<br/>app/repository/)]
    G -.->|registra tudo| O[Langfuse<br/>app/llm/observabilidade.py]
```

1. **`frontend/streamlit_app.py`** mostra a tela e envia a pergunta para a API (`POST /chat`), com a sessão e o usuário.
2. **`app/api/rotas.py`** recebe o pedido. O **`schemas.py`** confere se os dados vieram certos (senão, erro 422).
3. **`app/servicos/chat.py`** é a porta única do chat: repassa a pergunta para o grafo.
4. **`app/agents/grafo.py`** busca o perfil do usuário (**`repository/perfis.py`**) e roda o grafo. O **checkpointer** (**`repository/checkpointer.py`**) traz do MongoDB o histórico daquela sessão.
5. O nó **`app/agents/chatbot.py`** monta as mensagens: o prompt de sistema (via **`prompts/catalogo.py`**, já com o perfil), a conversa recente (limpa por **`utils/mensagens.py`**) e a pergunta nova.
6. **`app/llm/fabrica.py`** cria o modelo do provedor escolhido no `.env` (Groq, Gemini ou Mistral), que gera a resposta.
7. Na volta, o checkpointer **salva** a conversa no MongoDB, **`repository/conversas.py`** atualiza a lista de conversas, e a resposta sobe pelo mesmo caminho até a tela.
8. Durante tudo isso, **`app/llm/observabilidade.py`** registra cada passo no Langfuse (o trace).

### Como os arquivos se conectam

O diagrama acima mostra a **ordem** de uma pergunta. Este mostra **quem usa quem**: cada seta é um arquivo que **importa** outro e chama uma função dele. Repare nas camadas: as setas sempre **descem** (a tela usa a API, a API usa o serviço, o serviço usa o grafo...). Nenhum arquivo de baixo chama um de cima.

![Mapa de conexões entre os arquivos do FinBot: a tela chama a API por HTTP; rotas chama o serviço; o serviço chama o grafo; o grafo usa o chatbot, o repository e a observabilidade; o chatbot usa o catálogo de prompts, a fábrica de modelos e o utilitário de mensagens; mongo.py, fabrica.py e observabilidade.py acessam o MongoDB Atlas, a Groq e o Langfuse pela internet](imagens/mapa-conexoes-aula3.png)

**Quem chama quem, com a função usada:**

| Arquivo | Usa | Para quê |
|---|---|---|
| `frontend/streamlit_app.py` | a API, **por HTTP** (`requests`) | `POST /chat`, `GET`/`PUT` perfil, `GET` conversas e mensagens. A tela **não importa** nada de `app/`: só conversa com a API pela rede |
| `app/main.py` | `api/rotas.py` | `include_router(router)`: liga as rotas à aplicação |
| `api/rotas.py` | `api/schemas.py` | `Pergunta`, `Resposta`, `Perfil`...: validam o que entra e sai |
| | `servicos/chat.py` | `chat.perguntar()`, `chat.historico()`, `chat.obter_perfil()`... |
| `servicos/chat.py` | `agents/grafo.py` | `grafo.executar()` (perguntas) e `grafo.historico()` (mensagens) |
| | `repository/perfis.py` e `conversas.py` | perfil e lista de conversas, **sem passar pelo grafo** (não precisam do LLM) |
| `agents/grafo.py` | `agents/chatbot.py` | `no_chatbot`: o nó do grafo |
| | `repository/checkpointer.py` | a memória da conversa (o histórico da sessão) |
| | `repository/perfis.py` | `texto_perfil()`: o perfil que entra no prompt |
| | `repository/conversas.py` | `registrar()`: atualiza a lista de conversas |
| | `llm/observabilidade.py` | `callbacks()` e `rastrear()`: registram tudo no Langfuse |
| | `utils/mensagens.py` | `conversa_limpa()`: monta o histórico para a tela |
| `agents/chatbot.py` | `prompts/catalogo.py` | `catalogo.obter("sistema")`: o prompt de sistema |
| | `llm/fabrica.py` | `criar_modelo().invoke(...)`: chama o LLM |
| | `utils/mensagens.py` | `conversa_limpa()`: só as mensagens recentes vão para o LLM |
| | `llm/observabilidade.py` | `config_prompt()`: liga a resposta à versão do prompt |
| `prompts/catalogo.py` | `llm/observabilidade.py` | `cliente_langfuse()`: busca o prompt no Langfuse |
| `repository/perfis.py`, `conversas.py`, `checkpointer.py` | `repository/mongo.py` | `banco()` / `cliente()`: a conexão única com o MongoDB |
| quase todos | `config/settings.py` | `settings`: chaves, URLs e opções do `.env` (ou do Render) |
| `scripts/publicar_prompts.py` | `prompts/catalogo.py` e `llm/observabilidade.py` | lê os `.md` e envia para o Langfuse (roda à mão, fora da API) |

> **Por que a tela não importa o código da API?** Porque elas rodam em **computadores diferentes**: o Streamlit no Streamlit Cloud e a API no Render. A única ligação entre as duas é a **rede** (HTTP), pelo endereço do `API_URL`. É por isso que dá para trocar a tela (por um app de celular, por exemplo) sem mexer em nada de `app/`.

### As pastas e os arquivos

Continuando a analogia do restaurante da Aula 2:

#### `app/` — o FinBot (a API e o "cérebro")

| Pasta | No restaurante | Arquivo | Papel |
|---|---|---|---|
| raiz de `app/` | a porta de entrada | `main.py` | cria a aplicação FastAPI e liga as rotas. É o que o `uvicorn` executa |
| `config/` | o quadro de avisos da gerência | `settings.py` | lê todas as configurações (`.env` no computador, variáveis no Render) num lugar só |
| `api/` | o **garçom** e o **cardápio** | `rotas.py` | os endereços da API (`/chat`, `/saude`, perfil, conversas, mensagens). Só traduz HTTP |
| | | `schemas.py` | o formato do que entra e sai (o "cardápio"). Recusa pedidos errados com 422 |
| `servicos/` | o **balcão** entre o salão e a cozinha | `chat.py` | a porta única do chat. A API só fala com ele; ele fala com o grafo e com o banco |
| `agents/` | a **cozinha** | `grafo.py` | o grafo do LangGraph: estado, nós, setas e memória. Organiza quem faz o quê |
| | | `chatbot.py` | o nó que conversa: monta as mensagens e chama o LLM |
| `prompts/` | o **livro de receitas** | `sistema.md` | o prompt de sistema: as regras do FinBot. **É o único texto que vai para o LLM** |
| | | `catalogo.py` | busca o prompt no Langfuse (versão `production`); se não conseguir, usa o `.md` |
| `llm/` | o **fornecedor** e as **câmeras** | `fabrica.py` | cria o modelo do provedor escolhido (Groq, Gemini ou Mistral) |
| | | `observabilidade.py` | liga o Langfuse: traces, sessões, usuários e versão do prompt |
| `repository/` | a **despensa** e o **caderno do chefe** | `mongo.py` | a conexão com o MongoDB, uma só para o projeto |
| | | `checkpointer.py` | a memória de **curto prazo**: salva o estado do grafo (a conversa) a cada passo |
| | | `perfis.py` | a memória de **longo prazo**: o perfil de cada usuário |
| | | `conversas.py` | a lista de conversas de cada usuário (a barra lateral) |
| `utils/` | os **utensílios** | `mensagens.py` | ferramentas de apoio: escolhe quais mensagens do histórico vão para o LLM |

> **E o `__init__.py`?** Ele aparece em toda pasta de `app/` e normalmente fica vazio. Sua função é dizer ao Python "esta pasta é um **pacote**", o que permite escrever `from app.repository import mongo`. Sem ele, os `import` entre pastas não funcionam.

#### Fora de `app/`

| Pasta ou arquivo | Papel |
|---|---|
| `frontend/` | o **salão do restaurante**: a tela do chat (`streamlit_app.py`), publicada à parte no Streamlit Cloud. Não fala com o LLM nem com o banco: só com a API. Tem o próprio `requirements.txt`, porque é instalado separado |
| `scripts/` | programas para rodar **à mão**, fora da API: `chat_terminal.py` (o chat da Aula 1, no terminal) e `publicar_prompts.py` (envia os prompts para o Langfuse) |
| `tests/` | os testes automáticos de cada aula. `conftest.py` prepara as **peças falsas** (LLM, MongoDB e APIs de teste), para os testes rodarem sem internet e sem gastar tokens |
| `aulas/` | este material |
| `.env` | as **suas** chaves e senhas. Fica só no seu computador (está no `.gitignore`) |
| `.env.example` | o **modelo** do `.env`, sem valores secretos. Vai para o GitHub, para quem clonar saber o que preencher |
| `.gitignore` | a lista do que **não** vai para o GitHub (`.env`, `.venv/`, `__pycache__/`...) |
| `requirements.txt` | as bibliotecas da API (o Render instala este) |
| `requirements-dev.txt` | o anterior + as bibliotecas só de desenvolvimento e testes (`pytest`, `httpx`, `mongomock`) |
| `render.yaml` | a "receita" do deploy no Render: como instalar, como iniciar e quais variáveis existem |
| `README.md` | a apresentação do projeto no GitHub, com os links do app publicado |
| `.devcontainer/` | criada pelo Streamlit Cloud no deploy (Aula 2), para o GitHub Codespaces. Não afeta o FinBot |
| `.venv/` | o ambiente virtual com as bibliotecas instaladas. Só no seu computador |

### Por que separar tanto?

Porque **cada mudança fica num lugar só**:

| Se você quiser... | Mexe em... | O resto nem percebe |
|---|---|---|
| trocar o Groq pelo Gemini | `.env` (e, no máximo, `llm/fabrica.py`) | API, grafo, banco, tela |
| mudar o tom das respostas | o prompt no Langfuse (ou `prompts/sistema.md`) | todo o código |
| trocar o MongoDB por outro banco | `repository/` | grafo, API, tela |
| criar um app de celular | só o novo app, chamando a mesma API | todo o `app/` |
| ensinar o FinBot a consultar a bolsa (Aula 4) | `agents/` e uma pasta nova, `tools/` | API, banco, tela |

É exatamente isso que vai acontecer nas próximas aulas: o "miolo" (`agents/`, `prompts/` e as pastas novas `tools/` e `rag/`) cresce, enquanto a API, o banco e a tela quase não mudam.

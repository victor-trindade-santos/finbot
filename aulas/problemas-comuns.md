# 🛠️ Problemas comuns (e como resolver)

> Todos estes erros **aconteceram de verdade** ao montar este projeto. Antes de pedir ajuda, procure a mensagem de erro nesta página (Ctrl+F).
>
> **Como ler um erro do Python:** a mensagem importante é a **última linha** do `Traceback`. As linhas de cima mostram o caminho até ela.

## Ambiente e instalação (Aula 1)

| Mensagem / sintoma | Causa | Solução |
|---|---|---|
| `Could not find a version that satisfies the requirement numpy>=...` | Python antigo (3.11 ou menos) | `python --version`. Instale o 3.12 e recrie o venv: `py -3.12 -m venv .venv` |
| `No suitable Python runtime found` ao rodar `py -3.12` | O Python 3.12 não está instalado | `winget install Python.Python.3.12` ou pelo site python.org; depois **feche e abra o terminal** |
| `.venv\Scripts\Activate.ps1 não pode ser carregado` | PowerShell bloqueando scripts | Uma vez: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| `ModuleNotFoundError: No module named 'app'` | Rodou `python scripts/arquivo.py` ou fora da pasta do projeto | Use `python -m scripts.arquivo` **da pasta raiz** |
| `ModuleNotFoundError: No module named 'langchain_groq'` (ou outro) | venv não ativado ou `pip install` não terminou | Veja se aparece `(.venv)` no terminal; rode `pip install -r requirements-dev.txt` |

## Chaves e LLM (Aula 1)

| Mensagem / sintoma | Causa | Solução |
|---|---|---|
| `Defina a chave do provedor 'groq' no arquivo .env` | `.env` vazio, não salvo, ou com nome errado | Salve o `.env` (Ctrl+S); o arquivo se chama exatamente `.env`, na raiz |
| `401 - Invalid API Key` | Chave errada **ou** uma variável `GROQ_API_KEY` salva no Windows, que **tem prioridade sobre o `.env`** | `echo $env:GROQ_API_KEY`. Se aparecer algo, apague em *Editar as variáveis de ambiente do sistema* e reabra o VS Code |
| `404 - model_not_found` / `The model ... does not exist` | O provedor **desligou** o modelo (aconteceu com `llama-3.3-70b-versatile`) | Veja os modelos atuais em console.groq.com/docs/models e defina `LLM_MODELO=` no `.env` |
| `429 - rate limit` | Limite do plano grátis (por conta) | Espere 1 minuto; cada aluno deve usar a **própria** chave |
| A chave aparece num print ou foi para o GitHub | — | **Revogue** a chave no site do provedor e crie outra. Apagar o arquivo não adianta: ele continua no histórico do Git |

## API e front (Aula 2)

| Mensagem / sintoma | Causa | Solução |
|---|---|---|
| `{"detail":"Not Found"}` em `http://127.0.0.1:8000` | Normal: a API não tem página na raiz | Abra `http://127.0.0.1:8000/docs` |
| Mudei o `.env` e nada mudou | O `--reload` só observa arquivos `.py` | Pare a API (Ctrl+C) e suba de novo |
| `Erro ao falar com a API` no Streamlit | A API não está rodando | Suba a API num terminal e o Streamlit em **outro** |
| `500 Internal Server Error` no `/docs` | Erro dentro da API | Leia o **terminal do uvicorn**: o `Traceback` está lá |
| No Render, a 1ª pergunta demora ~1 min | O plano grátis "dorme" após 15 min sem uso | Normal; o front espera até 120 s |

## MongoDB (Aula 3)

| Mensagem / sintoma | Causa | Solução |
|---|---|---|
| "Preciso criar o banco/coleções no Atlas?" | — | **Não.** O banco do `MONGO_BANCO` e as coleções aparecem sozinhos na primeira gravação |
| `The DNS query name does not exist: _mongodb._tcp.cluster0...` | O endereço do cluster na URL não é o seu: a URL foi montada a partir de um exemplo da aula | Copie a URL **do Atlas** (Connect → Drivers) e troque só `<db_username>` e `<db_password>`. O trecho depois de `cluster0.` tem que ser igual ao do Atlas |
| `bad auth : authentication failed` | Usuário ou senha errados na URL, os `< >` ficaram, ou foi usado o login do site do Atlas em vez do usuário do banco | A senha fica entre `:` e `@`, sem `< >` |
| `InvalidURI` | Senha com `@ : / # %`, ou aspas/espaços na URL | Senha só com letras e números; `.env` sem aspas |
| `ServerSelectionTimeoutError` | IP não liberado ou rede bloqueando | Atlas → Network Access → `0.0.0.0/0`. Na rede da escola, teste no celular roteado |
| Muitos documentos em `checkpoints` | Normal: o LangGraph salva o estado a **cada passo** | Use `ttl` no checkpointer para limpar conversas antigas |

## Ferramentas e dados de mercado (Aula 4)

| Mensagem / sintoma | Causa | Solução |
|---|---|---|
| `400 tool_use_failed ... attempted to call tool 'taxa​s_bcb'` | O modelo escreveu o nome da ferramenta com um **caractere invisível** (problema de tokenização) | Nome de ferramenta simples (`indicadores_economicos`) + guardrail que tenta de novo |
| "Tive um problema ao consultar os dados agora" | O guardrail pegou um erro do modelo duas vezes | Veja as linhas `[mercado] ... falhou` no terminal do uvicorn |
| `Read timed out` no Banco Central | A API do BCB fica lenta em alguns horários | Tente de novo em alguns minutos; a ferramenta devolve `erro` sem derrubar o agente |
| Selic com **data futura** | O BCB publica a meta para cada dia em que ela vale | Pedir os dados até hoje (`dataFinal`), como no código da aula |
| Dividend yield `0.12` em vez de `12%` | A brapi devolve **fração** | Multiplicar por 100, como no código da aula |
| Ação "não encontrada" (ex.: BBAS3) | Sem token, a brapi só libera PETR4, VALE3, ITUB4, MGLU3, MXRF11, HGLG11 | Crie um token grátis na brapi e coloque em `BRAPI_TOKEN` |

## RAG (Aula 5)

| Mensagem / sintoma | Causa | Solução |
|---|---|---|
| "Não encontrei isso nos documentos" para tudo, com `fontes: []` | A coleção `chunks` está vazia (não rodou o indexador, ou rodou com outro `MONGO_BANCO`) | `python -m scripts.indexar` com o `.env` certo |
| O trecho certo vem em 2º ou 3º lugar | O TF-IDF compara palavras, não significado | Compare com `RAG_MODO=embeddings` |
| A resposta **copia** os parágrafos dos documentos | Prompt rígido demais ("responda SOMENTE com os trechos") | Fatos dos documentos, explicação do modelo (prompt da Aula 6) |
| Fonte citada como `【arquivo.md】` | Hábito do modelo | Peça "colchetes retos" no prompt |

## Multiagente e produção (Aulas 6 e 7)

| Mensagem / sintoma | Causa | Solução |
|---|---|---|
| O especialista ignora o perfil do usuário | O prompt dele não tem `{{perfil}}` | Acrescente a variável no `.md` do especialista |
| Pergunta composta respondida pela metade | O Router escolhe **um** especialista | Limite do padrão; veja o Supervisor (Aula 6) |
| Aviso "não é recomendação" duplicado | Especialista e revisor escreveram aviso | O revisor remove avisos antes de pôr o dele |
| Simulação com IR errado (17,5% em 2 anos) | Prazo calculado com `meses * 30` | `dias = round(meses * 365 / 12)`; o LLM só explica os números que recebe |

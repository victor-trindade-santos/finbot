# FinBot

O FinBot é um projeto educacional de um assistente conversacional sobre investimentos no Brasil. Seu objetivo técnico é explorar, passo a passo, como construir uma aplicação com modelos de linguagem (LLMs), ferramentas de consulta, memória de conversação e recuperação de informações em documentos.

## O chat que será desenvolvido

O usuário poderá conversar com o FinBot para tirar dúvidas sobre conceitos de investimentos. Ao longo do desenvolvimento, o chat será ampliado para consultar dados de mercado, manter o histórico das conversas e responder com base em documentos de referência.

O sistema será composto por:

- Uma interface de chat para enviar perguntas e exibir respostas.
- Uma API para receber as mensagens e coordenar o processamento.
- Um ou mais agentes para interpretar perguntas e decidir quando consultar ferramentas.
- Integrações com modelos de linguagem, com possibilidade de escolher entre diferentes provedores.
- Ferramentas para consultar indicadores econômicos e dados de ativos.
- Memória para preservar o contexto das conversas.
- Busca em documentos para fundamentar respostas.
- Testes automatizados e recursos de observabilidade.

## Tecnologias estudadas

Durante o projeto serão exploradas tecnologias como Python, LangChain, LangGraph, FastAPI, Streamlit, MongoDB, Langfuse e APIs de dados de mercado.

## Organização das aulas

As aulas apresentam a construção do projeto em etapas:

1. Ambiente de desenvolvimento, estrutura do projeto e primeiro chat.
2. API, interface, observabilidade e publicação.
3. Memória persistente, MongoDB e prompts versionados.
4. Ferramentas e consulta a dados de mercado.
5. RAG: busca e respostas baseadas em documentos.
6. Arquitetura multiagente.
7. Simulações, revisão de respostas, avaliações e entrega final.

Os materiais estão na pasta [`aulas/`](./aulas/).

## Uso responsável

O FinBot tem finalidade educacional. Suas respostas não constituem recomendação de compra ou venda de ativos, nem substituem a avaliação de um profissional qualificado. Dados e regras podem mudar; consulte fontes oficiais antes de tomar decisões financeiras.

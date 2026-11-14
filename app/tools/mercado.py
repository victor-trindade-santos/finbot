# app/tools/mercado.py
"""Aula 4 — Ferramentas (tools) de dados de mercado em tempo real.

O que o modelo vê de cada ferramenta: o NOME, a DESCRIÇÃO (docstring) e os ARGUMENTOS.
A descrição é a única instrução que ele tem para decidir quando chamar:
descrição vaga = chamada errada. Por isso as docstrings abaixo são detalhadas.

Fontes gratuitas:
- Banco Central (SGS): Selic, CDI, IPCA. Sem cadastro.
- brapi.dev: sem token funcionam PETR4, VALE3, ITUB4, MGLU3; FIIs MXRF11, HGLG11; 3 títulos do Tesouro.
"""
from datetime import date, timedelta
from functools import wraps  # preserva nome e docstring ao "embrulhar" uma função

from langchain_core.tools import tool

from app.utils.http import get_json

# Endereços das APIs; {codigo} é trocado pelo número da série do Banco Central.
BCB = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados"
BRAPI = "https://brapi.dev/api/v2"
# Códigos das séries do Banco Central: 432 = meta Selic, 4389 = CDI, 13522 = IPCA 12 meses.
SERIES_BCB = {"selic_meta_aa": 432, "cdi_aa": 4389, "ipca_12m": 13522}


# Decorador: "embrulha" a ferramenta num try/except.
def _seguro(funcao):
    """Ferramenta nunca deve quebrar o agente: erro vira uma resposta que o LLM entende."""
    @wraps(funcao)  # mantém nome, docstring e argumentos (o LLM precisa deles)
    def envolvida(*args, **kwargs):
        try:
            return funcao(*args, **kwargs)
        except Exception as erro:
            # Em vez de quebrar, devolve um dicionário de erro que o LLM consegue explicar ao usuário.
            return {"erro": f"dado indisponível no momento ({erro})"}
    return envolvida


def buscar_taxas() -> dict:
    """Função comum (sem @tool) para reaproveitar no simulador da Aula 7.

    Pedimos os dados ATÉ HOJE (dataFinal). Pedindo só "o último registro", a meta Selic
    vinha com data futura, porque o Banco Central publica a meta para cada dia em que ela vale.
    """
    hoje = date.today()
    periodo = {
        "formato": "json",
        "dataInicial": (hoje - timedelta(days=120)).strftime("%d/%m/%Y"),  # o IPCA é mensal e sai com atraso
        "dataFinal": hoje.strftime("%d/%m/%Y"),
    }
    taxas = {}
    # Para cada série, busca os dados do período e fica com o último valor publicado.
    for nome, codigo in SERIES_BCB.items():
        ultimo = get_json(BCB.format(codigo=codigo), periodo)[-1]  # {"data": "21/10/2026", "valor": "14.90"}
        taxas[nome] = {"valor": float(ultimo["valor"]), "data": ultimo["data"]}
    taxas["fonte"] = "Banco Central do Brasil (SGS)"
    return taxas


# @tool transforma a função em ferramenta que o LLM pode pedir; @_seguro protege contra erros.
@tool
@_seguro
def indicadores_economicos() -> dict:
    """Retorna as taxas de juros e inflação ATUAIS do Brasil: meta da Selic (% ao ano),
    CDI anualizado (% ao ano) e IPCA acumulado em 12 meses (%), com a data de referência.
    Use quando o usuário perguntar sobre Selic, CDI, juros, inflação ou rendimento de renda fixa hoje."""
    return buscar_taxas()


@tool
@_seguro
def cotacao_acao(ticker: str) -> dict:
    """Retorna a cotação atual de UMA ação da B3: preço em reais, variação do dia (%) e horário.
    ticker: código da ação em maiúsculas, ex.: "PETR4", "VALE3", "ITUB4", "MGLU3".
    Use apenas para ações (códigos terminados em 3 ou 4). Para fundos imobiliários use indicadores_fii."""
    # Pede a cotação à brapi.dev; upper() aceita "petr4" ou "PETR4".
    dados = get_json(f"{BRAPI}/stocks/quote", {"symbols": ticker.upper()})
    # Pega o 1º resultado com segurança: se "results" vier vazio, usa {} e .get devolve None.
    item = (dados.get("results") or [{}])[0].get("data")
    if not item:
        return {"erro": f"ação {ticker} não encontrada (sem token só PETR4, VALE3, ITUB4, MGLU3)"}
    # Devolve só os campos úteis, com nomes em português e a fonte do dado.
    return {
        "ticker": ticker.upper(),
        "nome": item.get("longName") or item.get("shortName"),
        "preco": item.get("regularMarketPrice"),
        "variacao_dia_pct": item.get("regularMarketChangePercent"),
        "data": item.get("regularMarketTime"),
        "fonte": "brapi.dev",
    }


@tool
@_seguro
def indicadores_fii(ticker: str) -> dict:
    """Retorna indicadores de UM fundo imobiliário (FII): preço da cota, P/VP,
    dividend yield dos últimos 12 meses (%) e segmento, com a data de referência.
    ticker: código do FII terminado em 11, ex.: "MXRF11", "HGLG11"."""
    # Pede os indicadores do FII à brapi.dev.
    dados = get_json(f"{BRAPI}/fii/indicators", {"symbols": ticker.upper()})
    fiis = dados.get("fiis") or []
    if not fiis:
        return {"erro": f"FII {ticker} não encontrado (sem token só MXRF11 e HGLG11)"}
    f = fiis[0]
    dy = f.get("dividendYield12m")
    if dy is not None and dy < 1.5:  # a API devolve FRAÇÃO (0.1266 = 12,66%): convertemos para %
        dy = round(dy * 100, 2)
    return {
        "ticker": ticker.upper(),
        "preco": f.get("price"),
        "p_vp": f.get("priceToNav"),
        "dividend_yield_12m_pct": dy,
        "segmento": f.get("segmentType"),
        "data": f.get("asOfDate"),
        "fonte": "brapi.dev",
    }


@tool
@_seguro
def tesouro_direto(simbolo: str) -> dict:
    """Retorna taxa e preço de compra atuais de UM título do Tesouro Direto.
    simbolo: identificador em minúsculas, um destes:
      "tesouro-selic-01032031" (Tesouro Selic),
      "tesouro-prefixado-com-juros-semestrais-01012037" (Prefixado),
      "tesouro-ipca-com-juros-semestrais-15082060" (IPCA+).
    O campo como_ler_a_taxa explica o que a taxa significa para aquele título."""
    # Pede os dados do título à brapi.dev (os símbolos do Tesouro são em minúsculas).
    dados = get_json(f"{BRAPI}/treasury/indicators", {"symbols": simbolo.lower()})
    resultados = dados.get("results") or []
    if not resultados:
        return {"erro": f"título {simbolo} não encontrado"}
    t = resultados[0]
    return {
        "titulo": t.get("bondType"),
        "simbolo": t.get("symbol"),
        "vencimento": t.get("maturityDate"),
        "taxa_compra_aa": t.get("buyRate"),
        "preco_compra": t.get("buyPrice"),
        # rateInfo pode não vir: "or {}" evita erro ao fazer .get().
        "como_ler_a_taxa": (t.get("rateInfo") or {}).get("description"),
        "data": t.get("baseDate"),
        "fonte": "brapi.dev (dados do Tesouro Nacional)",
    }


# Lista com todas as ferramentas de mercado; é ela que entregamos ao agente.
FERRAMENTAS_MERCADO = [indicadores_economicos, cotacao_acao, indicadores_fii, tesouro_direto]


if __name__ == "__main__":
    # python -m app.tools.mercado  -> testa as APIs sem LLM
    from pprint import pprint
    pprint(indicadores_economicos.invoke({}))
    pprint(cotacao_acao.invoke({"ticker": "PETR4"}))
    pprint(indicadores_fii.invoke({"ticker": "MXRF11"}))
    pprint(tesouro_direto.invoke({"simbolo": "tesouro-selic-01032031"}))

import requests
from bs4 import BeautifulSoup
import json
import re
import os
from datetime import datetime

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/120.0 Safari/537.36"
    )
}

SERIES = {
    "sintrenseA": (
        "https://www.zerozero.pt/edicao/"
        "af-lisboa-fut7-juniores-d-s12-1-fase-serie-8-"
        "2026-2027/226443"
    ),
    "sintrenseB": (
        "https://www.zerozero.pt/edicao/"
        "af-lisboa-fut7-juniores-d-s12-1-fase-serie-9-"
        "2026-2027/226134"
    )
}


def limpar(texto):
    return re.sub(r"\s+", " ", texto).strip()


def obter_pagina(url):
    resposta = requests.get(
        url,
        headers=HEADERS,
        timeout=40
    )

    resposta.raise_for_status()

    if not resposta.text:
        raise ValueError("Página vazia")

    soup = BeautifulSoup(
        resposta.text,
        "html.parser"
    )

    if not soup.find("table"):
        raise ValueError(
            "Não foram encontradas tabelas. "
            "O Zerozero pode ter bloqueado a consulta."
        )

    return soup


def encontrar_colunas(tabela):
    primeira = tabela.find("tr")

    if not primeira:
        return {}

    celulas = primeira.find_all(["th", "td"])

    nomes = [
        limpar(c.get_text()).lower()
        for c in celulas
    ]

    colunas = {}

    sinonimos = {
        "posicao": ["pos", "posição", "pos."],
        "equipa": ["equipa", "equipe"],
        "pontos": ["pts", "pontos"],
        "jogos": ["j", "pj", "jogos"],
        "vitorias": ["v", "vitórias", "vit"],
        "empates": ["e", "empates"],
        "derrotas": ["d", "derrotas"],
        "golosMarcados": ["gm", "golos marcados"],
        "golosSofridos": ["gs", "golos sofridos"],
        "diferenca": ["dg", "dif", "diferença"]
    }

    for chave, alternativas in sinonimos.items():
        for i, nome in enumerate(nomes):
            if nome in alternativas:
                colunas[chave] = i
                break

    return colunas


def processar_serie(url, nome_equipa):

    soup = obter_pagina(url)

    tabelas = soup.find_all("table")

    classificacao = None
    linhas_jogos = []

    for tabela in tabelas:

        linhas = tabela.find_all("tr")

        colunas = encontrar_colunas(tabela)

        for linha in linhas:

            celulas = linha.find_all("td")

            if not celulas:
                continue

            texto = limpar(
                linha.get_text(" ", strip=True)
            )

            if "Sintrense" not in texto:
                continue

            # Procurar tabela de classificação

            if (
                "equipa" in colunas
                and "pontos" in colunas
                and len(celulas) >= 4
            ):
                classificacao = tabela

            # Guardar possíveis linhas de jogos

            if len(celulas) >= 3:
                linhas_jogos.append(celulas)

    if classificacao is None:
        raise ValueError(
            f"Classificação de {nome_equipa} não encontrada"
        )

    # ==================================
    # CLASSIFICAÇÃO
    # ==================================

    colunas = encontrar_colunas(classificacao)

    def valor(celulas, chave, fallback):
        indice = colunas.get(chave, fallback)

        if indice >= len(celulas):
            return ""

        return limpar(celulas[indice].get_text())

    resultado = {
        "posicao": "",
        "equipa": nome_equipa,
        "pontos": "",
        "jogos": "",
        "vitorias": "",
        "empates": "",
        "derrotas": "",
        "golosMarcados": "",
        "golosSofridos": "",
        "diferenca": "",
        "ultimoResultado": {},
        "proximoJogo": {},
        "top5": [],
        "proximosJogos": []
    }

    for linha in classificacao.find_all("tr"):

        celulas = linha.find_all("td")

        if len(celulas) < 4:
            continue

        equipa_original = valor(
            celulas, "equipa", 2
        )

        if not equipa_original:
            continue

        equipa = limpar(equipa_original)

        dados_equipa = {
            "posicao": valor(celulas, "posicao", 0),
            "equipa": equipa,
            "pontos": valor(celulas, "pontos", 3)
        }

        if len(resultado["top5"]) < 5:
            resultado["top5"].append(
                dados_equipa.copy()
            )

        if "sintrense" in equipa.lower():

            resultado.update({
                "posicao": dados_equipa["posicao"],
                "equipa": nome_equipa,
                "pontos": dados_equipa["pontos"],
                "jogos": valor(celulas, "jogos", 4),
                "vitorias": valor(celulas, "vitorias", 5),
                "empates": valor(celulas, "empates", 6),
                "derrotas": valor(celulas, "derrotas", 7),
                "golosMarcados": valor(celulas, "golosMarcados", 8),
                "golosSofridos": valor(celulas, "golosSofridos", 9),
                "diferenca": valor(celulas, "diferenca", 10)
            })

    if not resultado["posicao"]:
        raise ValueError(
            f"{nome_equipa} não encontrada na classificação"
        )

    # ==================================
    # RESULTADOS E PRÓXIMOS JOGOS
    # ==================================

    jogos_com_resultado = []
    jogos_sem_resultado = []

    for celulas in linhas_jogos:

        textos = [
            limpar(c.get_text())
            for c in celulas
        ]

        texto_linha = " ".join(textos)

        if "Sintrense" not in texto_linha:
            continue

        if len(textos) >= 6:
            data = textos[0]
            casa = textos[1]
            hora_ou_resultado = textos[3]
            fora = textos[5]
        else:
            data = textos[0]
            casa = textos[1]
            hora_ou_resultado = ""
            fora = textos[-1]

        if not casa or not fora:
            continue

        jogo = {
            "data": data,
            "casa": casa,
            "resultado": "",
            "hora": "",
            "fora": fora
        }

        # Identificar resultado

        if re.fullmatch(
            r"\d+\s*[-–:]\s*\d+",
            hora_ou_resultado
        ):
            jogo["resultado"] = hora_ou_resultado
            jogos_com_resultado.append(jogo)

        else:
            jogo["hora"] = hora_ou_resultado

            if not re.fullmatch(
                r"\d{1,2}[-/]\d{1,2}[-/]\d{2,4}",
                data
            ):
                continue

            jogos_sem_resultado.append(jogo)

    # Último resultado

    if jogos_com_resultado:
        jogo = jogos_com_resultado[0]

        resultado["ultimoResultado"] = {
            "data": jogo["data"],
            "casa": jogo["casa"],
            "resultado": jogo["resultado"],
            "fora": jogo["fora"]
        }

    # Próximos jogos

    resultado["proximosJogos"] = jogos_sem_resultado[:5]

    for jogo in jogos_sem_resultado:

        if (
            "sintrense" in jogo["casa"].lower()
            or "sintrense" in jogo["fora"].lower()
        ):
            adversario = (
                jogo["fora"]
                if "sintrense" in jogo["casa"].lower()
                else jogo["casa"]
            )

            resultado["proximoJogo"] = {
                **jogo,
                "adversario": adversario
            }

            break

    return resultado


# ======================================
# ATUALIZAR DADOS
# ======================================

def atualizar_dados():

    ficheiro = "dados.json"

    # Ler dados anteriores

    if os.path.exists(ficheiro):
        try:
            with open(
                ficheiro,
                "r",
                encoding="utf-8"
            ) as f:
                dados = json.load(f)
        except Exception:
            dados = {}
    else:
        dados = {}

    sucessos = 0

    for chave, url in SERIES.items():

        nome = (
            "Sintrense A"
            if chave == "sintrenseA"
            else "Sintrense B"
        )

        print(f"\nA processar {nome}...")

        try:
            novo = processar_serie(
                url,
                nome
            )

            dados[chave] = novo

            sucessos += 1

            print(
                f"OK: {nome} - "
                f"Posição {novo['posicao']} - "
                f"{novo['pontos']} pontos"
            )

        except Exception as erro:

            print(f"ERRO em {nome}: {erro}")

            print(
                "Os dados anteriores serão preservados."
            )

    if sucessos == 0:
        raise RuntimeError(
            "Nenhuma série foi atualizada. "
            "O dados.json não será substituído."
        )

    dados["ultimaAtualizacao"] = (
        datetime.now().strftime("%d/%m/%Y %H:%M")
    )

    temporario = ficheiro + ".tmp"

    with open(
        temporario,
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(
            dados,
            f,
            indent=2,
            ensure_ascii=False
        )

    os.replace(temporario, ficheiro)

    print("\nAtualização concluída!")
    print(f"Séries atualizadas: {sucessos}/2")


if __name__ == "__main__":
    atualizar_dados()

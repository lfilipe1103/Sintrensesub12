import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

SERIES = {
    "sintrenseA": "https://www.zerozero.pt/edicao/af-lisboa-fut7-juniores-d-s12-1-fase-serie-8-2026-2027/226443",
    "sintrenseB": "https://www.zerozero.pt/edicao/af-lisboa-fut7-juniores-d-s12-1-fase-serie-9-2026-2027/226134"
}


def limpar(texto):
    return texto.replace("\n", "").strip()


def processar_serie(url):

    html = requests.get(
        url,
        headers=HEADERS,
        timeout=30
    ).text

    soup = BeautifulSoup(html, "html.parser")

    tabelas = soup.find_all("table")

    tabela_classificacao = None
    tabela_resultados = None
    tabela_proximos = None

    # =====================================
    # IDENTIFICAR TABELAS
    # =====================================

    for tabela in tabelas:

        for linha in tabela.find_all("tr"):

            texto = linha.get_text(
                " ",
                strip=True
            )

            cols = linha.find_all("td")

            if "Sintrense" not in texto:
                continue

            # Classificação

            if len(cols) >= 12:

                tabela_classificacao = tabela

            # Próximos Jogos

            elif "h2h" in texto:

                tabela_proximos = tabela

            # Resultados

            elif "-" in texto:

                tabela_resultados = tabela

    resultado = {

        "posicao": "",
        "equipa": "",
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

    # =====================================
    # CLASSIFICAÇÃO
    # =====================================

    if tabela_classificacao:

        linhas = tabela_classificacao.find_all("tr")

        for linha in linhas:

            cols = linha.find_all("td")

            if len(cols) < 12:
                continue

            try:

                equipa = limpar(
                    cols[2].get_text()
                )

                # TOP 5

                if (
                    len(resultado["top5"])
                    < 5
                ):

                    resultado["top5"].append({

                        "posicao":
                        limpar(
                            cols[0].get_text()
                        ),

                        "equipa":
                        equipa,

                        "pontos":
                        limpar(
                            cols[3].get_text()
                        )

                    })

                # SINSTRENSE

                if "Sintrense" in equipa:

                    resultado["posicao"] = limpar(
                        cols[0].get_text()
                    )

                    resultado["equipa"] = equipa

                    resultado["pontos"] = limpar(
                        cols[3].get_text()
                    )

                    resultado["jogos"] = limpar(
                        cols[4].get_text()
                    )

                    resultado["vitorias"] = limpar(
                        cols[5].get_text()
                    )

                    resultado["empates"] = limpar(
                        cols[6].get_text()
                    )

                    resultado["derrotas"] = limpar(
                        cols[7].get_text()
                    )

                    resultado["golosMarcados"] = limpar(
                        cols[8].get_text()
                    )

                    resultado["golosSofridos"] = limpar(
                        cols[9].get_text()
                    )

                    resultado["diferenca"] = limpar(
                        cols[10].get_text()
                    )

            except:
                pass

    # =====================================
    # ÚLTIMO RESULTADO
    # =====================================

    if tabela_resultados:

        for linha in tabela_resultados.find_all(
            "tr"
        ):

            texto = linha.get_text(
                " ",
                strip=True
            )

            if "Sintrense" not in texto:
                continue

            cols = linha.find_all("td")

            if len(cols) < 6:
                continue

            resultado["ultimoResultado"] = {

                "data":
                limpar(
                    cols[0].get_text()
                ),

                "casa":
                limpar(
                    cols[1].get_text()
                ),

                "resultado":
                limpar(
                    cols[3].get_text()
                ),

                "fora":
                limpar(
                    cols[5].get_text()
                )
            }

            break

            # =====================================
    # PRÓXIMOS JOGOS
    # =====================================

    if tabela_proximos:

        for linha in tabela_proximos.find_all(
            "tr"
        ):

            cols = linha.find_all("td")

            if len(cols) < 6:
                continue

            try:

                jogo = {

                    "data":
                    limpar(
                        cols[0].get_text()
                    ),

                    "casa":
                    limpar(
                        cols[1].get_text()
                    ),

                    "hora":
                    limpar(
                        cols[3].get_text()
                    ),

                    "fora":
                    limpar(
                        cols[5].get_text()
                    )

                }

                resultado[
                    "proximosJogos"
                ].append(
                    jogo
                )

                if (
                    (
                        "Sintrense"
                        in jogo["casa"]
                    )
                    or
                    (
                        "Sintrense"
                        in jogo["fora"]
                    )
                ) and (
                    not resultado[
                        "proximoJogo"
                    ]
                ):

                    if (
                        "Sintrense"
                        in jogo["casa"]
                    ):
                        adversario = jogo[
                            "fora"
                        ]
                    else:
                        adversario = jogo[
                            "casa"
                        ]

                    resultado[
                        "proximoJogo"
                    ] = {

                        **jogo,

                        "adversario":
                        adversario

                    }

            except:
                pass

            if len(
                resultado[
                    "proximosJogos"
                ]
            ) >= 5:
                break

    return resultado


def atualizar_dados():

    dados = {

        "ultimaAtualizacao":
        datetime.now().strftime(
            "%d/%m/%Y %H:%M"
        )

    }

    for chave, url in SERIES.items():

        print(
            f"A processar {chave}..."
        )

        try:

            dados[chave] = processar_serie(
                url
            )

        except Exception as erro:

            print(
                f"Erro em {chave}: {erro}"
            )

            dados[chave] = {}

    with open(
        "dados.json",
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            dados,
            f,
            indent=2,
            ensure_ascii=False
        )

    print("\n✅ dados.json atualizado")

    print(
        json.dumps(
            dados,
            indent=2,
            ensure_ascii=False
        )
    )


if __name__ == "__main__":

    atualizar_dados()

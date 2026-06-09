import csv
import heapq
import math
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Estruturas de dados usadas

from estruturas_dados import Pilha
from estruturas_dados import Fila
from estruturas_dados import ListaLigada

from buscas import busca_linear_satelite
from buscas import bubble_sort_alertas

PASTA_CACHE = Path("data/cache")
PASTA_CACHE.mkdir(parents=True, exist_ok=True)

URL_CELESTRAK = "https://celestrak.org/NORAD/elements/gp.php?GROUP={grupo}&FORMAT=csv"

MU_TERRA = 398600.4418
RAIO_TERRA_KM = 6378.137

GRUPOS = {
    "1": ("stations", "Estacoes espaciais"),
    "2": ("starlink", "Starlink"),
    "3": ("gps-ops", "GPS operacional"),
    "4": ("iridium-NEXT", "Iridium NEXT"),
    "5": ("active", "Satelites ativos"),
}


def baixar_csv_celestrak(grupo):
    """Baixa o CSV publico do CelesTrak. Se a internet falhar, usa o cache."""
    caminho_cache = PASTA_CACHE / f"gp_{grupo}.csv"

    if caminho_cache.exists() and time.time() - caminho_cache.stat().st_mtime < 3600:
        return caminho_cache

    try:
        url = URL_CELESTRAK.format(grupo=grupo)
        request = urllib.request.Request(url, headers={"User-Agent": "ProjetoFaculdade/1.0"})
        with urllib.request.urlopen(request, timeout=20) as resposta:
            texto = resposta.read().decode("utf-8")
            caminho_cache.write_text(texto, encoding="utf-8")
    except Exception:
        if not caminho_cache.exists():
            raise RuntimeError("Nao foi possivel baixar dados e nao existe cache local.")

    return caminho_cache


def converter_float(valor, padrao=0.0):
    try:
        return float(valor)
    except Exception:
        return padrao


def converter_data(texto):
    texto = texto.strip().replace("Z", "+00:00")
    if "+" not in texto:
        texto += "+00:00"
    data = datetime.fromisoformat(texto)
    return data.astimezone(timezone.utc)


def calcular_apogeu_perigeu(mean_motion, excentricidade):
    n_rad_s = mean_motion * 2 * math.pi / 86400.0
    semi_eixo_maior = (MU_TERRA / (n_rad_s * n_rad_s)) ** (1 / 3)
    perigeu = semi_eixo_maior * (1 - excentricidade) - RAIO_TERRA_KM
    apogeu = semi_eixo_maior * (1 + excentricidade) - RAIO_TERRA_KM
    return apogeu, perigeu

def carregar_satelites(grupo, limite):
    """Le o CSV e transforma cada linha em um dicionario de satelite."""
    caminho_csv = baixar_csv_celestrak(grupo)
    satelites = []

    with caminho_csv.open(encoding="utf-8") as arquivo:
        leitor = csv.DictReader(arquivo)

        for linha in leitor:
            mean_motion = converter_float(linha.get("MEAN_MOTION"))
            if mean_motion <= 0:
                continue

            excentricidade = converter_float(linha.get("ECCENTRICITY"))
            apogeu, perigeu = calcular_apogeu_perigeu(mean_motion, excentricidade)

            satelite = {
                "norad": linha.get("NORAD_CAT_ID", "").strip(),
                "nome": linha.get("OBJECT_NAME", "SEM NOME").strip(),
                "epoch": converter_data(linha.get("EPOCH", "")),
                "mean_motion": mean_motion,
                "excentricidade": excentricidade,
                "inclinacao": converter_float(linha.get("INCLINATION")),
                "raan": converter_float(linha.get("RA_OF_ASC_NODE")),
                "arg_perigeu": converter_float(linha.get("ARG_OF_PERICENTER")),
                "anomalia_media": converter_float(linha.get("MEAN_ANOMALY")),
                "periodo_min": 1440 / mean_motion,
                "apogeu_km": apogeu,
                "perigeu_km": perigeu,
            }

            satelites.append(satelite)

            if len(satelites) >= limite:
                break

    return satelites


def resolver_kepler(anomalia_media, excentricidade):
    """Resolve uma aproximacao simples da orbita eliptica."""
    anomalia = anomalia_media

    for _ in range(10):
        erro = anomalia - excentricidade * math.sin(anomalia) - anomalia_media
        derivada = 1 - excentricidade * math.cos(anomalia)
        anomalia -= erro / derivada

    return anomalia


def calcular_posicao(satelite, momento):
    """Retorna uma tupla (x, y, z) aproximada da posicao do satelite."""
    segundos = (momento - satelite["epoch"]).total_seconds()
    n_rad_s = satelite["mean_motion"] * 2 * math.pi / 86400.0
    semi_eixo_maior = (MU_TERRA / (n_rad_s * n_rad_s)) ** (1 / 3)

    excentricidade = satelite["excentricidade"]
    anomalia_media = math.radians(satelite["anomalia_media"]) + n_rad_s * segundos
    anomalia_media = anomalia_media % (2 * math.pi)
    anomalia_excentrica = resolver_kepler(anomalia_media, excentricidade)

    x_orbital = semi_eixo_maior * (math.cos(anomalia_excentrica) - excentricidade)
    y_orbital = semi_eixo_maior * math.sqrt(1 - excentricidade**2) * math.sin(anomalia_excentrica)

    raan = math.radians(satelite["raan"])
    inclinacao = math.radians(satelite["inclinacao"])
    arg_perigeu = math.radians(satelite["arg_perigeu"])

    cos_o = math.cos(raan)
    sin_o = math.sin(raan)
    cos_i = math.cos(inclinacao)
    sin_i = math.sin(inclinacao)
    cos_w = math.cos(arg_perigeu)
    sin_w = math.sin(arg_perigeu)

    x = (cos_o * cos_w - sin_o * sin_w * cos_i) * x_orbital
    x += (-cos_o * sin_w - sin_o * cos_w * cos_i) * y_orbital

    y = (sin_o * cos_w + cos_o * sin_w * cos_i) * x_orbital
    y += (-sin_o * sin_w + cos_o * cos_w * cos_i) * y_orbital

    z = (sin_w * sin_i) * x_orbital + (cos_w * sin_i) * y_orbital

    return (x, y, z)


def calcular_distancia(posicao_a, posicao_b):
    return math.sqrt(
        (posicao_a[0] - posicao_b[0]) ** 2
        + (posicao_a[1] - posicao_b[1]) ** 2
        + (posicao_a[2] - posicao_b[2]) ** 2
    )


def classificar_risco(distancia):
    if distancia < 1:
        return "CRITICO"
    if distancia < 5:
        return "ALTO"
    if distancia < 10:
        return "MODERADO"
    if distancia < 20:
        return "ATENCAO"
    return "BAIXO"


def familia_orbital(nome):
    """Evita falso alerta entre modulos acoplados da mesma estacao."""
    nome = nome.upper()

    if "ISS" in nome or "ZARYA" in nome or "POISK" in nome or "NAUKA" in nome:
        return "COMPLEXO_ISS"

    if "CSS" in nome or "TIANHE" in nome or "MENGTIAN" in nome or "SHENZHOU" in nome:
        return "COMPLEXO_CHINES"

    return nome


def deve_ignorar_par(sat_a, sat_b, distancia):
    mesma_familia = familia_orbital(sat_a["nome"]) == familia_orbital(sat_b["nome"])
    orbita_igual = (
        abs(sat_a["periodo_min"] - sat_b["periodo_min"]) < 0.01
        and abs(sat_a["inclinacao"] - sat_b["inclinacao"]) < 0.01
        and abs(sat_a["raan"] - sat_b["raan"]) < 0.01
    )
    return distancia < 0.1 and (mesma_familia or orbita_igual)


def criar_matriz_posicoes(satelites, horas, passo_minutos):
    """Cria uma matriz: cada linha representa um horario analisado."""
    agora = datetime.now(timezone.utc)
    total_passos = int((horas * 60) / passo_minutos)
    matriz = []

    for passo in range(total_passos + 1):
        momento = agora + timedelta(minutes=passo * passo_minutos)
        linha = []

        for satelite in satelites:
            posicao = calcular_posicao(satelite, momento)
            linha.append((momento, satelite, posicao))

        matriz.append(linha)

    return matriz


def encontrar_alertas(satelites, horas, passo_minutos, limite_km):

    print("[LOG] Criando matriz de posições")

    matriz_posicoes = criar_matriz_posicoes(
        satelites,
        horas,
        passo_minutos
    )

    fila_processamento = Fila()

    pares_ja_vistos = set()

    print("[LOG] Inserindo alertas na fila FIFO")

    for linha in matriz_posicoes:

        for i in range(len(linha)):

            momento_a, sat_a, pos_a = linha[i]

            for j in range(i + 1, len(linha)):

                _, sat_b, pos_b = linha[j]

                if abs(
                    sat_a["periodo_min"]
                    - sat_b["periodo_min"]
                ) > 35:
                    continue

                distancia = calcular_distancia(
                    pos_a,
                    pos_b
                )

                if deve_ignorar_par(
                    sat_a,
                    sat_b,
                    distancia
                ):
                    continue

                if distancia <= limite_km:

                    chave = tuple(
                        sorted(
                            [sat_a["norad"], sat_b["norad"]]
                        )
                    )

                    if chave in pares_ja_vistos:
                        continue

                    pares_ja_vistos.add(chave)

                    alerta = {
                        "risco": classificar_risco(distancia),
                        "distancia": distancia,
                        "momento": momento_a,
                        "sat_a": sat_a,
                        "sat_b": sat_b,
                    }

                    fila_processamento.enqueue(alerta)

    alertas = []

    print("[LOG] Processando fila FIFO")

    while not fila_processamento.is_empty():

        alerta = fila_processamento.dequeue()

        alertas.append(alerta)

    print("[LOG] Ordenando alertas com Bubble Sort")

    alertas = bubble_sort_alertas(alertas)

    historico_alertas = Pilha()

    for alerta in alertas:
        historico_alertas.push(alerta)

    print(
        f"[LOG] Pilha criada com {len(historico_alertas.itens)} alertas"
    )

    return alertas

def mostrar_satelites(satelites, indice_por_norad):
    print("\nPrimeiros satelites carregados:")
    for satelite in satelites[:10]:
        print(
            f"- {satelite['norad']} | {satelite['nome']} | "
            f"perigeu {satelite['perigeu_km']:.1f} km | "
            f"apogeu {satelite['apogeu_km']:.1f} km"
        )

    print(f"\nTotal na lista: {len(satelites)}")
    print(f"Total no dicionario por NORAD: {len(indice_por_norad)}")


def mostrar_alertas(alertas):
    if not alertas:
        print("\nNenhum alerta encontrado para os parametros escolhidos.")
        return

    print("\nAlertas encontrados:")

    for alerta in alertas[:20]:
        sat_a = alerta["sat_a"]
        sat_b = alerta["sat_b"]

        print("-" * 70)
        print(f"Risco: {alerta['risco']}")
        print(f"Distancia minima: {alerta['distancia']:.3f} km")
        print(f"Horario UTC: {alerta['momento'].strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Satelite A: {sat_a['nome']} (NORAD {sat_a['norad']})")
        print(f"Satelite B: {sat_b['nome']} (NORAD {sat_b['norad']})")


def escolher_grupo():
    print("\nEscolha a base publica do CelesTrak:")
    for numero, (_, nome) in GRUPOS.items():
        print(f"{numero} - {nome}")

    opcao = input("Opcao: ").strip()
    return GRUPOS.get(opcao, GRUPOS["2"])


def main():
    print("=" * 70)
    print("ORBITAL GUARDIAN SIMPLES")
    print("Sistema academico de alerta de aproximacao entre satelites")
    print("=" * 70)

    grupo, nome_grupo = escolher_grupo()

    limite = input("Quantidade de satelites para analisar [120]: ").strip()
    limite = int(limite) if limite else 120

    horas = input("Horizonte de analise em horas [6]: ").strip()
    horas = int(horas) if horas else 6

    passo = input("Passo da simulacao em minutos [15]: ").strip()
    passo = int(passo) if passo else 15

    limite_km = input("Gerar alerta abaixo de quantos km? [20]: ").strip()
    limite_km = float(limite_km) if limite_km else 20.0

    print(f"\nCarregando grupo: {nome_grupo}")
    satelites = carregar_satelites(grupo, limite)
    print("[LOG] Criando Lista Ligada")

    lista_ligada_satelites = ListaLigada()

    for satelite in satelites:
        lista_ligada_satelites.adicionar(satelite)

    print(
        f"[LOG] Lista Ligada criada com "
        f"{len(lista_ligada_satelites.para_lista())} satélites"
    )

    # Dicionario para busca rapida por NORAD ID.
    indice_por_norad = {satelite["norad"]: satelite for satelite in satelites}

    if satelites:

        primeiro_norad = satelites[0]["norad"]

        resultado_busca = busca_linear_satelite(
            satelites,
            primeiro_norad
        )

        if resultado_busca:
            print(
                f"[LOG] Busca Linear executada "
                f"para NORAD {primeiro_norad}"
            )

    mostrar_satelites(satelites, indice_por_norad)

    print("\nAnalisando aproximacoes orbitais...")
    alertas = encontrar_alertas(satelites, horas, passo, limite_km)
    mostrar_alertas(alertas)

    print("\nFonte dos dados:")
    print(URL_CELESTRAK.format(grupo=grupo))
    print("\nObservacao: simulacao educacional, nao substitui analise orbital real.")


if __name__ == "__main__":
    main()

import json
import urllib.parse
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import projeto_faculdade as projeto

PASTA_FRONT = Path("front_faculdade")


def resposta_json(handler, dados, status=200):
    corpo = json.dumps(dados, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(corpo)))
    handler.end_headers()
    handler.wfile.write(corpo)


class ServidorFaculdade(SimpleHTTPRequestHandler):
    def translate_path(self, path):
        rota = urllib.parse.urlparse(path).path
        if rota == "/":
            return str(PASTA_FRONT / "index.html")
        return str(PASTA_FRONT / rota.lstrip("/"))

    def do_GET(self):
        rota = urllib.parse.urlparse(self.path)

        if rota.path == "/api/analisar":
            parametros = urllib.parse.parse_qs(rota.query)

            grupo = parametros.get("grupo", ["starlink"])[0]
            limite = int(parametros.get("limite", ["80"])[0])
            horas = int(parametros.get("horas", ["3"])[0])
            passo = int(parametros.get("passo", ["20"])[0])
            limite_km = float(parametros.get("limite_km", ["20"])[0])

            try:
                satelites = projeto.carregar_satelites(grupo, limite)
                indice_por_norad = {satelite["norad"]: satelite for satelite in satelites}
                from buscas import busca_linear_satelite
                if satelites:
                    busca_linear_satelite(
                        satelites,
                        satelites[0]["norad"]
                    )

                alertas = projeto.encontrar_alertas(satelites, horas, passo, limite_km)

                resposta_json(
                    self,
                    {
                        "grupo": grupo,
                        "quantidade_satelites": len(satelites),
                        "quantidade_no_dicionario": len(indice_por_norad),
                        "parametros": {
                            "horas": horas,
                            "passo": passo,
                            "limite_km": limite_km,
                        },
                        "satelites": [
                            {
                                "norad": satelite["norad"],
                                "nome": satelite["nome"],
                                "perigeu_km": round(satelite["perigeu_km"], 1),
                                "apogeu_km": round(satelite["apogeu_km"], 1),
                                "inclinacao": round(satelite["inclinacao"], 2),
                                "periodo_min": round(satelite["periodo_min"], 2),
                            }
                            for satelite in satelites[:30]
                        ],
                        "alertas": [
                            {
                                "risco": alerta["risco"],
                                "distancia": round(alerta["distancia"], 3),
                                "momento": alerta["momento"].strftime("%Y-%m-%d %H:%M:%S UTC"),
                                "satelite_a": alerta["sat_a"]["nome"],
                                "norad_a": alerta["sat_a"]["norad"],
                                "satelite_b": alerta["sat_b"]["nome"],
                                "norad_b": alerta["sat_b"]["norad"],
                            }
                            for alerta in alertas[:20]
                        ],
                    },
                )
            except Exception as erro:
                resposta_json(self, {"erro": str(erro)}, 500)

            return

        super().do_GET()


def main():
    host = "127.0.0.1"
    porta = 8080
    servidor = ThreadingHTTPServer((host, porta), ServidorFaculdade)
    print(f"Front faculdade rodando em http://{host}:{porta}")
    servidor.serve_forever()


if __name__ == "__main__":
    main()

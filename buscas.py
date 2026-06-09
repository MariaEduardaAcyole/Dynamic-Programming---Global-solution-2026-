# BUSCA LINEAR

def busca_linear_satelite(lista_satelites, norad):

    for satelite in lista_satelites:

        if satelite["norad"] == norad:
            return satelite

    return None


# BUBBLE SORT

def bubble_sort_alertas(alertas):

    tamanho = len(alertas)

    for i in range(tamanho):

        for j in range(0, tamanho - i - 1):

            if alertas[j]["distancia"] > alertas[j + 1]["distancia"]:

                alertas[j], alertas[j + 1] = (
                    alertas[j + 1],
                    alertas[j]
                )

    return alertas
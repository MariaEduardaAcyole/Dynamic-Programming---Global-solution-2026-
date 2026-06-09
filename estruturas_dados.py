from collections import deque

# PILHA

class Pilha:
    def __init__(self):
        self.itens = []

    def push(self, item):
        self.itens.append(item)

    def pop(self):
        if self.itens:
            return self.itens.pop()
        return None

    def is_empty(self):
        return len(self.itens) == 0

# FILA FIFO

class Fila:
    def __init__(self):
        self.itens = deque()

    def enqueue(self, item):
        self.itens.append(item)

    def dequeue(self):
        if self.itens:
            return self.itens.popleft()
        return None

    def is_empty(self):
        return len(self.itens) == 0


# LISTA LIGADA

class No:
    def __init__(self, dado):
        self.dado = dado
        self.proximo = None


class ListaLigada:
    def __init__(self):
        self.inicio = None

    def adicionar(self, dado):
        novo = No(dado)

        if self.inicio is None:
            self.inicio = novo
            return

        atual = self.inicio

        while atual.proximo:
            atual = atual.proximo

        atual.proximo = novo

    def para_lista(self):
        resultado = []

        atual = self.inicio

        while atual:
            resultado.append(atual.dado)
            atual = atual.proximo

        return resultado
# Exercicios
# Crie funções que duplicam, triplicam e quadriplicam
# o número recebido como paramêtro.

# numero = 5

# def duplicar(numero):
#     return numero * 2
# def triplicar(numero):
#     return numero * 3
# def quadruplicar(numero):
#     return numero * 4

def criar_multiplicador(multiplicador):
    def multiplicar(numero):
        return numero * multiplicador
    return multiplicar

triplicar = criar_multiplicador(3)
duplicar = criar_multiplicador(2)
print(duplicar(2))
print(triplicar(2))





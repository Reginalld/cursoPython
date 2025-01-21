# Problema dos parâmetros mutáveis em funções Python
def adiciona_clientes(nome,lista=None):
    if lista is None:
        lista = []
    lista.append(nome)
    return lista

cliente1 = adiciona_clientes('luiz')
adiciona_clientes('Joana',cliente1)
adiciona_clientes('Fernanda',cliente1)
cliente1.append('Edu')

cliente2 = adiciona_clientes('helena')
adiciona_clientes('maria',cliente2)

cliente3 = adiciona_clientes('Rafael')
adiciona_clientes('douglas',cliente3)

print(cliente1)
print(cliente2)
print(cliente3)
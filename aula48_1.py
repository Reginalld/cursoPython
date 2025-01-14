"""
Listas em Python
Tipo list - Mutável
Suporta vários valores de qualquer tipo
Conhecimentos reutilizáveis - índices e fatiamento
Métodos úteis: append, insert, pop, del, clear, extend,
"""

#         01234
#        -54321

# string = "ABCDE" # 5 caracteres (len)
# #print(bool(lista)) #falsy
# #print (lista, type(lista))

# #         0     1         2         3    4
# lista = [123, True, "Luiz Otávio", 1.2, []]
# lista[2] = "Maria"
# print(lista)
# print(lista[2], type(lista[2]))

lista = [10, 20, 30, 40]
# lista[2] = 300
# del lista[2]
# print(lista)
# print(lista[2])
lista.append(50)
lista.pop()
lista.append(60)
lista.append(70)
ultimo_valor = lista.pop(3)
print(lista, "Removido", ultimo_valor)

# Exercício - Unir listas
# Crie uma função zipper (como o zipper de roupas)
# O trabalho dessa função será unir duas
# listas na ordem.
# Use todos os valores da menor lista.
# Ex.:
# ['Salvador', 'Ubatuba', 'Belo Horizonte']
# ['BA','SP','MG','RJ']
# Resultado
# [('Salvador','BA'),('Ubatuba,'SP'),('Belo Horizonte','MG')]

from itertools import zip_longest

lista1 = ['Salvador', 'Ubatuba', 'Belo Horizonte']
lista2 = ['BA','SP','MG','RJ']

print(list(zip(lista1,lista2)))
print(list(zip_longest(lista1,lista2,fillvalue='Sem cidade')))





# def zipper(l1,l2):
#     intervalo_maximo = min(len(l1),len(l2))
#     return [
#         (l1[i],l2[i]) for i in range(intervalo_maximo)
#     ]

# print(zipper(lista1,lista2))


# def zipper(lista1,lista2):
#     global listas_zipadas, listas_zipadas_tuple
#     listas_zipadas = []
#     if len(lista1) > len(lista2):
#         for i in range(len(lista2)):
#            print(lista1)
#            listas_zipadas.append(lista1[i] + ' ' + lista2[i])
#     else:
#         for j in range(len(lista1)):
#             listas_zipadas.append(lista1[j] + ' ' + lista2[j])
#     return listas_zipadas
        
# lista_juntas = zipper(lista1,lista2)

# print(lista_juntas)


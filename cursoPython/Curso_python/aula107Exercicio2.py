"""
Soma duas listas ae
"""
lista_a = [1,2,3,4,5,6,7]
lista_b = [1,2,3,4]

lista_somado = []

def soma(l1,l2):
    range_lists = min(len(l1),len(l2))
    
    for i in range(range_lists):
        lista_somado.append(l1[i] + l2[i])
    return lista_somado

print(soma(lista_a,lista_b))


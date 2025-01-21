"""
splot e join com list e str
split - divide uma string
join - une uma string
"""

frase = "Olha só    que,   coisa interessante"
lista_palavras = frase.split(",")

lista_palavras_corrigidas = []
for i, frase in enumerate(lista_palavras):
    lista_palavras_corrigidas.append(lista_palavras[i].strip())

# print(lista_palavras)
# print(lista_palavras_corrigidas)
frases_unidas = "-".join(lista_palavras_corrigidas)
print(frases_unidas)
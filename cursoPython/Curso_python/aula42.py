frase = "O Python é uma linguagem de programação " \
    "multiparadigma " \
    "Python foi criado por Guida van Rossum."

i = 0

qtd_apareceu_mais_vezes = 0
letra_apareceu_mais_vezes = ""

while i < len(frase):
    letra_atual = frase[i]
    qtd_apareceu_mais_atual = frase.count(letra_atual)

    i += 1

    if letra_atual == " ":
        continue

    if qtd_apareceu_mais_atual > qtd_apareceu_mais_vezes:
        qtd_apareceu_mais_vezes = qtd_apareceu_mais_atual
        letra_apareceu_mais_vezes = letra_atual

print(f"Letra que apareceu mais vezes: {letra_apareceu_mais_vezes} Quantidade de aparições: {qtd_apareceu_mais_vezes}")

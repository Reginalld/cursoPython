"""
Argumentos nomeados e não nomeados em funções Python
Argumento nomeado tem nome com sinal de igual
Argumento não nomeado recebe apenas o argumento (valor)
"""

def soma(x,y,z):
    #Definição
    print(f"{x=} y= {y} {z=}", "|", "x+y = ", x + y + z)

soma(1,2,3)
soma(2, y=1, z=3)

print(1,2,3, sep="-")
lista = []
for x in range(3):
    for y in range(3):
        lista.append((x,y))

lista = [
    (x,y)
    for x in range(3)
    for y in range(3)

]

lista = [
    [(0,letra) for letra in 'Luiz']
    for x in range(3)
]

print(lista)
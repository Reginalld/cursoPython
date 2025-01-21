# Dictionary Comprehension e Set Comprehension
produto = {
    'nome':'Caneta Azul',
    'preco': 2.5,
    'categoria': 'Escritório'
}

print(produto.items())

dc = {
    chave: valor
    if isinstance(valor, (int,float)) else valor.upper()
    for chave, valor 
    in produto.items()
    if chave != 'categoria'
}

lista = [
    ('a','valor a'),
    ('a','valor a'),
    ('a','valor a'),
]

dc = {
    chave: valor 
    for chave, valor in lista 
}

# s1 = {i for i in range(10)}
print(set(range(10)))
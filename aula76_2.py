"""
Métodos úteis dos dicionários em Python
len - quantas chaves
keys - iterável com as chaves
values - iterável com os valores
items - iterável com chaves e valores
setdefault - adiciona valor se a chave não existe
copy - retorna uma cópia rasa (shallow copy)
get - obtém uma chave
pop - Apagar um item com a chave especificada (del)
popitem - Apaga o último item adicionado
update - Atualiza um dicionário com outro
"""
pessoa = {
    'nome': 'Luiz Otávio',
    'sobrenome': 'Miranda',
    # 'idade': 900,

}

pessoa.setdefault('idade', None)
print(pessoa['idade'])

# print(pessoa.__len__())
# print(len(pessoa))

# print(tuple(pessoa.items()))

# for chaves in pessoa.values():
#     print(chaves)

# for chave, valor in pessoa.items():
#     print(chave,valor)
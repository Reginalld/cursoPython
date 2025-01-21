"""
Exercício - Salve sua classe em JSON
Salve os dados da sua classe em JSON
e depois crie novamente as instâncias
da classe com os dados salvos
Faça em arquivos separados.
"""
import os
import json

CAMINHO_ARQUIVO = 'aula127.json'

class Pessoa:
    def __init__(self,nome,idade):
        self.nome = nome
        self.idade = idade
        


p1 = Pessoa('João',30)
p2 = Pessoa('Maria',35)
p3 = Pessoa('Carlos',19)
bd = [p1.__dict__,p2.__dict__,p3.__dict__]

def fazer_dump():
    with open(CAMINHO_ARQUIVO, 'w', encoding='utf-8') as arquivo:
        json.dump(bd,arquivo, indent=2,ensure_ascii=False)

if __name__ == '__main__':
    fazer_dump()

from aula127_1Exercicio import CAMINHO_ARQUIVO, Pessoa
import json



with open(CAMINHO_ARQUIVO, 'r',encoding='utf8' ) as arquivo:
    pessoas = json.load(arquivo)
    p1 = Pessoa(**pessoas[0])
    p2 = Pessoa(**pessoas[1])
    p3 = Pessoa(**pessoas[2])


    print(p1.nome, p1.idade)
    print(p2.nome, p2.idade)
    print(p3.nome, p3.idade)



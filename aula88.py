# Valores Truthy e Falsy, Tipos Mutáveis e Imutáveis
# Mutáveis [] {} set()
# Imutáveis () "" 0 0.0 None False Range(0,10)
lista = []
dicionario = {}
conjunto = set()
tupla = ()
string = ''
inteiro = 0
float = 0.0
nada = None
falso = False
intervalo = range(0)

def falsy(valor):
    return 'falsy' if not valor else 'truthy'

print(f'TESTE', falsy('TESTE'))
print('Lista=',lista,falsy(lista))
print(f'Dicionario=',dicionario,falsy(dicionario))
print(conjunto,falsy(conjunto))
print(tupla,falsy(tupla))
print(string,falsy(string))
print(inteiro,falsy(inteiro))
print(float,falsy(float))
print(nada,falsy(nada))
print(falso,falsy(falso))
print(intervalo,falsy(intervalo))
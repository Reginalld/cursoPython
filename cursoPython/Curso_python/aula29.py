"""
Introdução ao try/except
try -> tentar executar o código
except -> ocorreu algum erro ao tentar executar
"""
numero_str = input("Vou dobrar o número que voce digitar")

try:
    numero_float = float(numero_str)
    print(f"O dobro de {numero_str} é {numero_float * 2:.2f}")
except:
    print("Você não digitou um número")


    
# if numero_str.isdigit():
#     numero_float = float(numero_str)
#     print(f"O dobro de {numero_str} é {numero_float * 2:.2f}")
# else:
#     print("Você não digitou um número")
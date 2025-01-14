# Exercicio com função

# Crie uma função que multiplica todos os argumentos
# não nomeados recebidos
# Retorne o total para uma variável e mostre o valor 
# da variável

def multiplicao(*args):
    conta_multiplicacao = 1
    for numero in args:
        conta_multiplicacao *= numero
    return conta_multiplicacao

conta = multiplicao(1,2,3,4,5)
print(conta)

# Crie uma função que fala se um número é par ou ímpar.
# Retorne se o número é par ou ímpar.

def par_ou_impar(x):
    if x % 2 == 0:
        return ("É par")
    else:
        return ("É ímpar")
    
variavel_par_ou_impar = par_ou_impar(4)
print(variavel_par_ou_impar)
    
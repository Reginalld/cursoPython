primeiro_valor = input("Digite um valor: ")
segundo_valor = input("Digite um segundo valor: ")

if primeiro_valor > segundo_valor:
    print("primeiro_valor =",primeiro_valor,"é maior que o segundo_valor =",segundo_valor)

if segundo_valor > primeiro_valor:
    print("segundo_valor =",segundo_valor,"é maior que o primeiro_valor =", primeiro_valor)

if primeiro_valor == segundo_valor:
    print("Os dois valores são iguais")


"""
Outra resolução

if primeiro_valor >= segundo_valor:
    print(
        f'{primeiro_valor=}é maior ou igual'
        f'ao que {segundo_valor=}'
    )
else:
    print(
        f'{segundo_valor=} é maior'
        f'do que {primeiro_valor=}'
    )
    
"""
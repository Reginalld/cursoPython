nome = input("Digite seu nome: ")
idade = input("Digite sua idade: ")
if not nome or not idade:
    print("Desculpe, você digitou campos vazios")

else:
    print(f"Seu nome é: {nome}")
    print("Seu nome invertido é:",nome[::-1])

    if (" " in nome):
        print("Seu nome contem espaço")

    else:
        print("Seu nome não tem espaço")

    print("A primeira letra do seu nome é:", nome[0])

    print("A ultima letra do seu nome é:", nome[len(nome)-1])

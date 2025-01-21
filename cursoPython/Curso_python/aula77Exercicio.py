# Exercício - sistema de perguntas e respostas

perguntas = [
    {
        'Pergunta': 'Quanto é 2+2?',
        'Opções': ['1','2','3','4','5'],
        'Resposta': '4',
    },
    {
        'Pergunta': 'Quanto é 5*5?',
        'Opções': ['25','55','10','51'],
        'Resposta': '25',
    },
    {
        'Pergunta': 'Quanto é 10/2?',
        'Opções': ['4','5','2','1'],
        'Resposta': '5',
    },
]

qtd_acertos = 0

for pergunta in perguntas:
    print(pergunta['Pergunta'])
    opcoes = pergunta['Opções']

    for i,opcao in enumerate(opcoes):
        print(f'{i})',opcoes[i])

    entrada = input("")
    entrada_int = None
    opcoes_qtd = len(opcoes)
    acertou = False
    
    if entrada.isdigit():
        entrada_int = int(entrada)


    if entrada_int is not None:    
        if entrada_int >= 0 and entrada_int < opcoes_qtd:
            if opcoes[entrada_int] == pergunta['Resposta']:
                acertou = True

    if acertou:
        qtd_acertos += 1
        print("Acertou")
    else:
        print("Errou")

print(f'Você acertou {qtd_acertos} de {len(perguntas)} perguntas')









# qtd_acertos = 0
# for pergunta in perguntas:
#     print('Pergunta:',pergunta['Pergunta'], '\n')

#     opcoes = pergunta['Opções']

#     for i,opcao in enumerate(opcoes):
#         print(f'{i})',opcao)

#     entrada = input('Escolha uma opção: ')

#     acertou = False
#     entrada_int = None
#     qtd_opcoes = len(opcoes)

#     if entrada.isdigit():
#         entrada_int = int(entrada)

#     if entrada_int is not None:
#         if entrada_int >= 0 and entrada_int < qtd_opcoes:
#             if opcoes[entrada_int] == pergunta['Resposta']:
#                 acertou = True

#     print()

#     if acertou:
#         qtd_acertos += 1
#         print('Acertou')
#     else:
#         print('Errou')

# print('Você acertou', qtd_acertos)
# print('de', len(perguntas), 'perguntas.')

            
        

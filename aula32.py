"""
Faça um programa que peça ao usuário para digitar um número inteiro,
informe se este número é par ou ímpar. Caso o usuário não digite um número
inteiro, informe que não é um número inteiro.
"""

# numero = input("Digite um número inteiro: ")

# if numero.isdigit():
#       numero_int = int(numero)
#       conta = numero_int % 2 == 0
#       par_impar_texto = "impar"

#       if conta:
#             par_impar_texto = "par"

#       print(f"O número {numero_int} é {par_impar_texto}")
# else:
#       print("Você não digitou um número")

"""
Faça um programa que pergunte a hora ao usuário e, baseando-se no horário 
descrito, exiba a saudação apropriada. Ex. 
Bom dia 0-11, Boa tarde 12-17 e Boa noite 18-23.
"""

# horario = input("Digite o horário: ")

# if horario.isdigit():

#       horario_int = int(horario)

#       dia = horario_int >= 0 and horario_int <= 11
#       tarde = horario_int >= 12 and horario_int <= 17
#       noite = horario_int >= 18 and horario_int <= 23
#       invalido = horario_int >  24 or horario_int < 0

#       if dia:
#             print("Bom dia")
#       if tarde:
#             print("Boa tarde")
#       if noite:
#             print("Boa noite")
#       if invalido:
#             print("Horas inexistentes")
# else:
#       print("Entrada inválida")
"""
Faça um programa que peça o primeiro nome do usuário. Se o nome tiver 4 letras ou 
menos escreva "Seu nome é curto"; se tiver entre 5 e 6 letras, escreva 
"Seu nome é normal"; maior que 6 escreva "Seu nome é muito grande". 
"""

primeiro_nome = input("Digite seu primeiro nome")

nome_curto = primeiro_nome <= 4
nome_normal = primeiro_nome >= 5 and primeiro_nome <= 6
nome_grande = primeiro_nome > 6

if nome_curto:
      print("Seu nome é curto")
if nome_normal:
      print("Seu nome é normal")
if nome_grande:
      print("Seu nome é muito Grande")
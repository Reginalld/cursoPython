"""
Faça uma lista de comprar com listas
O usuário deve ter a possibilidade de
inserir, apagar e listar valores da sua lista
Não permita que o programa quebre com
erros de índices inexistentes na lista
"""
lista = []

while True:
    entrada = input("Selecione uma opção \n" 
                    "[i]nserir [a]pagar [l]istar: ")
    
    if entrada == "i":
        inserir = input("Escolha um item para adicionar: ")
        lista.append(inserir)
        

    elif entrada == "a":
        apagar = input("Selecione um índice para apagar: ")
        if len(lista) == 0:
            print("Não tem nada para apagar")
        for indice, nome_lista in enumerate(lista):
            if apagar.isdigit:
                print("Você digitou uma letra")
                break
            apagar_int = int(apagar)
            if apagar_int == indice:
                lista.pop(apagar_int)
            if apagar_int + 1 > len(lista) or apagar_int < 0:
                print("Esse indice não existe")
                break
    
    elif entrada == "l":
        for indice, nome_lista in enumerate(lista):
            print(indice,nome_lista)

    else:
        print("Entrada inválida")
            
    
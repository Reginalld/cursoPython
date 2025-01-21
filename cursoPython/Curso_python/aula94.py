#try, except, else e finally
try:
    print('Abrir o arquivo')
    # open
except ZeroDivisionError as e:
    print(e.__class__.__name__)
    print(e)
    print('Dividiu zero')
else:
    print('Não deu erro')
finally:
    print('Fechar arquivo')

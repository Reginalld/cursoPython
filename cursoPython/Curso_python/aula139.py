"""
super() é a super classe na sub classe
Classe principal (Pessoa)
    -> super class, base class, parent class
Classes filhas (Cliente)
    -> sub class, child class, derived class
"""
# class MinhaString(str):
#     def upper(self):
#         print('Chamou Upper')
#         retorno = super().upper()
#         print('Depois do upper')
#         return retorno

# string = MinhaString('Luiz')
# print(string.upper())

class A(object):
    atributo_a = 'valor a'

    def __init__(self, atributo):
        self.atributo = atributo
        
        
    def metodo(self):
        print('A')

class B(A):

    atributo_b = 'valor b'

    def __init__(self, atributo, outra_coisa):
        super().__init__(atributo)
        self.outra_coisa = outra_coisa

    def metodo(self):
        print('B')

class C(B):

    atributo_c = 'valor c'

    def __init__(self, atributo, outra_coisa):
        super().__init__(atributo, outra_coisa)

    def metodo(self):
        #super().metodo() # B
        #super(B, self).metodo() # A
        #super(A, self).metodo() # object
        A.metodo(self)
        B.metodo(self)
        #print('C')

class D(C):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

# c = C()
# print(c.atributo_a)
# print(c.atributo_b)
# print(c.atributo_c)
# c.metodo()
c = C('Atributo', 'Qualquer')
c.metodo()
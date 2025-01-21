"""
Composição - É dono de, Herença - É um

Herença vs Composição

Classe principal (Pessoa)
    -> super class, base class, parent class
Classes filhas (Cliente)
    -> sub class, child class, derived class
"""
#object
class Pessoa:
    cpf = '12314'
    def __init__(self,nome,sobrenome):
        self.nome = nome
        self.sobrenome = sobrenome
    
    def falar_nome_classe(self):
        print(self.nome,self.sobrenome,self.__class__.__name__)

class Cliente(Pessoa):
    
    def falar_nome_classe(self):
        print('Nem sai do cliente')
        print(self.nome,self.sobrenome,self.__class__.__name__)

class Aluno(Pessoa):
    cpf = 'cpf aluno'
    ...

c1 = Cliente('Luiz','Otávio')
c1.falar_nome_classe()
a1 = Aluno('Maria','Helena')
a1.falar_nome_classe()
print(a1.cpf)
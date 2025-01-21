# @property + @setter - getter e setter no modo Pythônico
# - como getter
# - p/ evitar quebrar código cliente
# - p/ habilitar setter
# - p/ executar ações ao obter um atributo
# Atributos que começar com um ou dois underlines
# não devem ser usados fora da classe.
#  🐍🤓🤯🤯🤯🤯

class Caneta:
    def __init__(self,cor):
        self._cor = cor
        self._cor_tampa = None

    @property
    def cor(self):
        return self._cor
    
    @cor.setter
    def cor(self,valor):
        if valor == 'Verde':
            raise ValueError('Não aceito essa cor')
        self._cor = valor

    @property
    def cor_tampa(self):
        return self.cor_tampa
    
    @cor_tampa.setter
    def cor_tampa(self,valor):
        self.cor_tampa = valor
        

    
caneta = Caneta('Azul')
caneta.cor = 'Rosa'
print(caneta.cor)
#getter > obter valor

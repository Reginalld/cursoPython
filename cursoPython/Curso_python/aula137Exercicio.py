"""
Exercício com classes
1 - Crie uma classe Carro (Nome)
2 - Crie uma classe Motor (Nome)
3 - Crie uma classe Fabricante (Nome)
4 - Faça a ligação entre Carro tem Motor
Obs.: Um motor pode ter vários carros
5 - Faça a ligação entra Carro e Fabricante
Obs.: Um fabricante pode fabricar vários carros
Exiba o nome do carro, motor e fabricante na tela
"""

class Carro:
    def __init__(self, nome_carro):
        self.nome_carro = nome_carro
        self._motor = None
        self._fabricante = None

    @property
    def motor(self):
        return self._motor
    
    @motor.setter
    def motor(self,valor):
        self._motor = valor

    @property
    def fabricante(self):
        return self._fabricante
    
    @fabricante.setter
    def fabricante(self, valor):
         self._fabricante = valor


class Fabricante:
    def __init__(self, fabricante):
        self.fabricante = fabricante

class Motor:
    def __init__(self,motor):
        self.motor = motor

   


fusca = Carro('Fusca')
volkswagen = Fabricante('Volkswagen')
motor_1_0 = Motor('1.0')
fusca.fabricante = volkswagen
fusca.motor = motor_1_0
print(fusca.nome_carro, fusca.fabricante.fabricante,fusca.motor.motor)

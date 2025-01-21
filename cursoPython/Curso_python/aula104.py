"""
Funções decoradoras e decoradores
Decorar = Adicionar / Removar / Restringir / Alterar
Funções decoradoras são funções que decoram outras funções
Decoradores são usados para fazer o Python
usar as funções decoradoras em outras funções
Decoradores no Python são "Syntax Sugar" (Açucar sintático)
"""
def criar_funcao(funcao):
    def interna(*args,**kwargs):
        print('Vou te decorar')
        for arg in args:
            eh_string(arg)

        resultado = funcao(*args,*kwargs)
        print(f'O seu resultado foi:{resultado}.')
        print('Ok, agora você foi decorado')
        return resultado
    return interna

@criar_funcao
def inverte_string(string):
    return string[::-1]

def eh_string(param):
    if not isinstance(param,str):
        raise TypeError('param deve ser uma string')



invertida = inverte_string('213')
print(invertida)
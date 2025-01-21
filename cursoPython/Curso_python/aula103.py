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
        for arg in args:
            eh_string(arg)

        resultado = funcao(*args,*kwargs)

        return resultado
    return interna

def inverte_string(string):
    return string[::-1]

def eh_string(param):
    if not isinstance(param,str):
        raise TypeError('param deve ser uma string')



inverte_string_checando_parametro = criar_funcao(inverte_string)

invertida = inverte_string_checando_parametro(23)
print(invertida)
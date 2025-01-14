try:
    import sys
    print(*sys.path, sep='\n')
except ModuleNotFoundError:
    ...

print(213)
import aula97_m

print('Este módulo se chama', __name__)

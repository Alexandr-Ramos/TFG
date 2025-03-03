"""	
Biblioteca con definiciones importantes para la división de números.
Se incluyen las funciones divideSiDivisible() y cocienteModulo().
"""

def divideSiDivisible(nume, deno):
	"""
	Si nume es divisible por deno, devuelve la división
	entera. Si no lo es, devuelve None.
	"""

	if not nume % deno:
	return nume // deno


def cocienteModulo(nume, deno):
	"""
	Devuelve el conciente entero y el resto de
	la divisi
	ón entera (mod) de dos números.
	"""

	return nume // deno, nume % deno


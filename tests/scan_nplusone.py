# -*- coding: utf-8 -*-
"""scan_nplusone.py : boucles for/while executant des reponses SQL ligne par
ligne (pattern N+1) avec contexte de fonction et nb de lignes de boucle."""
import ast

SRC = r"C:\FM2027V2\app.py"
src = open(SRC, encoding="utf-8").read()
tree = ast.parse(src)

def func_of(node):
    cur = getattr(node, "parent", None)
    stack = []
    n = node
    while n is not None:
        stack.append(type(n).__name__)
        n = getattr(n, "_parent", None)
    return None

# ast has no parent links; build manually
parents = {}
for p in ast.walk(tree):
    for child in ast.iter_child_nodes(p):
        parents[child] = p

def enclosing_function(node):
    while node in parents:
        node = parents[node]
        if isinstance(node, ast.FunctionDef):
            return node
    return None

found = []
for fn in ast.walk(tree):
    if isinstance(fn, ast.FunctionDef):
        for loopnode in ast.walk(fn):
            if isinstance(loopnode, (ast.For, ast.While)):
                # n'accepter que si la requete n'est pas dans une fonction imbriquee
                exes = [n for n in ast.walk(loopnode)
                        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                        and n.func.attr == "execute"]
                if exes:
                    # exclure les boucles contenant un def/local fonction
                    nested = any(isinstance(x, ast.FunctionDef) for x in ast.walk(loopnode))
                    if nested:
                        continue
                    # taille estimee du corps de boucle
                    size = loopnode.end_lineno - loopnode.lineno + 1
                    in_try = any(isinstance(p, ast.Try) for p in ast.iter_child_nodes(fn))
                    for e in exes:
                        try:
                            argsrc = ast.get_source_segment(src, e.args[0])[:90] if e.args else "?"
                        except Exception:
                            argsrc = "?"
                        found.append((fn.name, fn.lineno, type(loopnode).__name__, size, argsrc))

# dedupe
seen = set()
out = []
for f in sorted(found, key=lambda x: x[0]):
    key = (f[0], f[3])
    if key in seen:
        continue
    seen.add(key)
    out.append(f)
for f in out:
    print(f"{f[1]:6d} {f[0]:40s} {f[2]:5s} lignes={f[3]:3d}  {f[4]!r}")
print("---", len(out), "boucles SQL suspectees")

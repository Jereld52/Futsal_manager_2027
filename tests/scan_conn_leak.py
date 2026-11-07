# -*- coding: utf-8 -*-
"""scan_conn_leak.py : fonctions de app.py qui ouvrent conn=db() mais ne
ferment pas toujours la connexion (fuites -> verrous 'database is locked')."""
import ast, sys

SRC = r"C:\FM2027V2\app.py"
src = open(SRC, encoding="utf-8").read()
tree = ast.parse(src)

rows = []
for fn in set([n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]):
    calls = [n for n in ast.walk(fn) if isinstance(n, ast.Call)
             and isinstance(n.func, ast.Name) and n.func.id == "db"]
    if not calls:
        continue
    names = set()
    for c in calls:
        # pattern classique : conn=db() / c=db() ...
        node = c
        # remonter a l'assignation si possible : parcours des Assign parents trop cher -> fallback : detecter variables
    # on cherche toutes les assignations X=db()
    opens = []
    for n in ast.walk(fn):
        if isinstance(n, ast.Assign) and isinstance(n.value, ast.Call) \
           and isinstance(n.value.func, ast.Name) and n.value.func.id == "db":
            for t in n.targets:
                if isinstance(t, ast.Name):
                    opens.append(t.id)
    if not opens:
        continue
    body_first = None
    # detection simple : la fonction contient-elle 'finally' avec close, ou un except qui close ?
    text = ast.get_source_segment(src, fn) or ""
    has_finally_close = "finally:" in text and "close()" in text.split("finally:", 1)[1]
    leaks = []
    for var in opens:
        # compter les ouvrages
        n_open = text.count(f"{var}=db()")
        n_close = text.count(f"{var}.close()")
        if n_close < n_open:
            leaks.append((var, n_open, n_close))
    if leaks and not has_finally_close:
        rows.append((fn.name, fn.lineno, leaks))

for name, line, leaks in sorted(rows):
    detail = "; ".join(f"{v}: open={o} close={c}" for v, o, c in leaks)
    print(f"L{line:6d} {name:45s} {detail}")
print("---", len(rows), "fonctions a revoir")

# -*- coding: utf-8 -*-
"""Rapport de bug : ZIP autonome, logs et copie de sauvegarde."""
import os
import sqlite3
import sys
import tempfile
import zipfile

sys.path.insert(0, r"C:\FM2027V2")
from support import create_bug_report

TMP = tempfile.mkdtemp(prefix="fm_bugreport_")
DATA = os.path.join(TMP, "data")
os.makedirs(DATA, exist_ok=True)
with open(os.path.join(DATA, "error.log"), "w", encoding="utf-8") as handle:
    handle.write("Traceback test\n")
with open(os.path.join(DATA, "fault.log"), "w", encoding="utf-8") as handle:
    handle.write("fault test\n")
with open(os.path.join(DATA, "game_options.json"), "w", encoding="utf-8") as handle:
    handle.write('{"theme":"Nuit violette"}')

SAVE = os.path.join(TMP, "sauvegarde.db")
conn = sqlite3.connect(SAVE)
conn.execute("CREATE TABLE club(id INTEGER PRIMARY KEY,name TEXT,division INTEGER,season INTEGER)")
conn.execute("CREATE TABLE career(id INTEGER PRIMARY KEY,current_date TEXT,matchday INTEGER)")
conn.execute("CREATE TABLE player(id INTEGER PRIMARY KEY)")
conn.execute("INSERT INTO club VALUES(1,'Test FC',2,3)")
conn.execute("INSERT INTO career VALUES(1,'2026-09-10',4)")
conn.execute("INSERT INTO player VALUES(1)")
conn.commit(); conn.close()
before = os.path.getmtime(SAVE)

path = create_bug_report(os.path.join(DATA, "reports"), "Le commentaire saute.",
                         data_dir=DATA, save_path=SAVE, include_save=True)
assert os.path.isfile(path) and os.path.getsize(path) > 0
with zipfile.ZipFile(path) as zf:
    names = set(zf.namelist())
    assert {"rapport.txt", "error.log", "fault.log", "sauvegarde_active.db"} <= names, names
    report = zf.read("rapport.txt").decode("utf-8")
    assert "Le commentaire saute." in report and "Test FC" in report
    assert "Traceback test" in zf.read("error.log").decode("utf-8")
    copy = os.path.join(TMP, "copie.db")
    with open(copy, "wb") as handle:
        handle.write(zf.read("sauvegarde_active.db"))
copy_conn = sqlite3.connect(copy)
assert copy_conn.execute("SELECT name FROM club WHERE id=1").fetchone()[0] == "Test FC"
copy_conn.close()
assert os.path.getmtime(SAVE) == before
print("1) ZIP : logs + rapport + copie de sauvegarde, sauvegarde intacte")

path2 = create_bug_report(os.path.join(DATA, "reports"), "Sans copie",
                          data_dir=DATA, save_path=SAVE, include_save=False)
with zipfile.ZipFile(path2) as zf:
    assert "sauvegarde_active.db" not in zf.namelist()
    assert "Sans copie" in zf.read("rapport.txt").decode("utf-8")
print("2) option sans copie : aucun fichier de sauvegarde inclus")
print("RESULT: ALL OK")

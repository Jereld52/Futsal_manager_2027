# -*- coding: utf-8 -*-
"""Integrite du monde : effectifs pleins, marche libre sain, paie mensuelle, maillots."""
import os, sys, tempfile
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app

TMP = tempfile.mkdtemp(prefix="fm_world_")
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = os.path.join(TMP, "x.db")
app.DB_PATH = os.path.join(TMP, "saves", "p.db")
app.DATA_DIR = TMP; app.BASE_DIR = TMP
app.active_save_path = lambda: app.DB_PATH
app.set_active_save_path = lambda p: None
app.init_db(fresh_universe=True, selected_division=3,
            identity={"name": "World FC", "arena_name": "A", "color1": "#c47220",
                      "color2": "#14171f", "division": 3})

from PySide6.QtWidgets import QApplication
q = QApplication.instance() or QApplication([])
q.setStyleSheet(app.style_for_theme("Nuit violette"))
w = app.MainWindow(); w.show(); w.app_stack.setCurrentWidget(w.game_shell); q.processEvents()
w.show_game_message = lambda *a, **k: True

# 1) Chaque club demarre avec un effectif complet et le marche libre est genere.
c = app.db()
clubs = c.execute("SELECT COUNT(*) n FROM club").fetchone()["n"]
squads = c.execute("""SELECT c.id,c.name,COUNT(p.id) n FROM club c
                      LEFT JOIN player p ON p.club_id=c.id AND COALESCE(p.is_free_agent,0)=0
                      GROUP BY c.id""").fetchall()
frees = c.execute("SELECT COUNT(*) n FROM player WHERE is_free_agent=1").fetchone()["n"]
free_club1 = c.execute("SELECT COUNT(*) n FROM player WHERE is_free_agent=1 AND club_id=1").fetchone()["n"]
free_bad = c.execute("""SELECT COUNT(*) n FROM player p WHERE p.is_free_agent=1
                        AND NOT EXISTS(SELECT 1 FROM club c WHERE c.id=p.club_id)""").fetchone()["n"]
c.close()
print(f"clubs={clubs} libres={frees} min_effectif={min(int(r['n']) for r in squads)}")
assert clubs == 60
assert min(int(r["n"]) for r in squads) == 12, [(r["name"], r["n"]) for r in squads if int(r["n"]) != 12]
assert frees >= 140, frees
assert free_club1 == 0 and free_bad == 0, (free_club1, free_bad)

# 2) La paie est chargee CHAQUE mois dans une nouvelle carriere.
c = app.db()
total = sum(int(r["salary"] or 0) for r in c.execute(
    "SELECT salary FROM player WHERE club_id=1 AND COALESCE(is_free_agent,0)=0").fetchall())
b0 = int(c.execute("SELECT budget FROM club WHERE id=1").fetchone()["budget"])
w.process_player_payroll(c, "2026-08-01"); c.commit()
b1 = int(c.execute("SELECT budget FROM club WHERE id=1").fetchone()["budget"])
w.process_player_payroll(c, "2026-09-01"); c.commit()
b2 = int(c.execute("SELECT budget FROM club WHERE id=1").fetchone()["budget"])
c.close()
print(f"paie: {b0 - b1} puis {b1 - b2} (masse {total})")
assert b0 - b1 == total, (b0 - b1, total)
assert b1 - b2 == total, (b1 - b2, total)

# 3) Aucun doublon de numero, et le reparateur corrige un doublon injecte.
c = app.db()
ids = [int(r["id"]) for r in c.execute(
    "SELECT id FROM player WHERE club_id=1 AND is_free_agent=0 ORDER BY id LIMIT 2").fetchall()]
c.execute("UPDATE player SET shirt_number=7 WHERE id=?", (ids[0],))
c.execute("UPDATE player SET shirt_number=7 WHERE id=?", (ids[1],))
c.commit()
fixed = app.repair_shirt_numbers(c); c.commit()
dups = c.execute("""SELECT shirt_number,COUNT(*) n FROM player WHERE club_id=1
                    AND is_free_agent=0 AND shirt_number BETWEEN 1 AND 99
                    GROUP BY shirt_number HAVING n>1""").fetchall()
free_after = c.execute("SELECT COUNT(*) n FROM player WHERE is_free_agent=1 AND club_id=1").fetchone()["n"]
c.close()
print(f"maillots repares={fixed} doublons={len(dups)}")
assert fixed >= 1 and not dups
assert free_after == 0

# 4) Cloture de saison : les clubs IA sont recompletes immediatement.
c = app.db()
c.execute("UPDATE fixture SET played=1,home_goals=2,away_goals=1 WHERE played=0")
stressed = [int(r["id"]) for r in c.execute("SELECT id FROM club WHERE id<>1 ORDER BY id LIMIT 3").fetchall()]
for cid in stressed:
    for row in c.execute("SELECT id FROM player WHERE club_id=? ORDER BY id LIMIT 3", (cid,)).fetchall():
        c.execute("UPDATE player SET is_free_agent=1,contract_years=0 WHERE id=?", (int(row["id"]),))
c.commit(); c.close()
assert w.start_new_season() is True
c = app.db()
after = [int(c.execute("SELECT COUNT(*) n FROM player WHERE club_id=? AND COALESCE(is_free_agent,0)=0",
                       (cid,)).fetchone()["n"]) for cid in stressed]
min_after = c.execute("""SELECT MIN(n) FROM (SELECT COUNT(*) n FROM player
                         WHERE COALESCE(is_free_agent,0)=0 GROUP BY club_id)""").fetchone()[0]
free1_after = c.execute("SELECT COUNT(*) n FROM player WHERE is_free_agent=1 AND club_id=1").fetchone()["n"]
c.close()
print(f"cloture: {after} | min={min_after} | libres club1={free1_after}")
assert all(n >= 11 for n in after), after
assert min_after >= 11
assert free1_after == 0

# 5) Le reapprovisionnement du marche ne vide jamais un club (plafond 13).
c = app.db()
club_id = int(c.execute("SELECT id FROM club WHERE id<>1 ORDER BY id LIMIT 1").fetchone()["id"])
for row in c.execute("SELECT id FROM player WHERE is_free_agent=1 ORDER BY id LIMIT 3").fetchall():
    c.execute("UPDATE player SET club_id=?,is_free_agent=0,free_agent_since='' WHERE id=?",
              (club_id, int(row["id"])))
free_now = int(c.execute("SELECT COUNT(*) n FROM player WHERE is_free_agent=1").fetchone()["n"])
c.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('free_agent_target',?)", (str(free_now + 4),))
c.commit()
before_size = int(c.execute("SELECT COUNT(*) n FROM player WHERE club_id=? AND is_free_agent=0",
                            (club_id,)).fetchone()["n"])
app.ensure_free_agents(c); c.commit()
after_size = int(c.execute("SELECT COUNT(*) n FROM player WHERE club_id=? AND is_free_agent=0",
                           (club_id,)).fetchone()["n"])
c.close()
print(f"reapprovisionnement: club {before_size} -> {after_size}")
assert before_size >= 13 and after_size >= 13

print("RESULT: ALL OK")

# -*- coding: utf-8 -*-
"""Audit profond : 3 changements de club successifs + faillite forcée."""
import os, sys, tempfile
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app
from PySide6.QtWidgets import QApplication

issues = []


def note(msg):
    issues.append(msg)
    print("  !!", msg)


def fresh(prefix, division=3):
    tmp = tempfile.mkdtemp(prefix=prefix)
    os.makedirs(os.path.join(tmp, "saves"), exist_ok=True)
    app.SAVE_DIR = os.path.join(tmp, "saves")
    app.DEFAULT_DB_PATH = os.path.join(tmp, "x.db")
    app.DB_PATH = os.path.join(tmp, "saves", "p.db")
    app.DATA_DIR = tmp
    app.BASE_DIR = tmp
    app.active_save_path = lambda: app.DB_PATH
    app.set_active_save_path = lambda p: None
    app.init_db(fresh_universe=True, selected_division=division,
                identity={"name": f"{prefix} FC", "arena_name": "A", "color1": "#2f6fed",
                          "color2": "#101a2e", "division": division})
    w = app.MainWindow()
    w.setAttribute(app.Qt.WA_DontShowOnScreen, True)
    w.show_game_message = lambda *a, **k: True
    app.QDialog.exec = lambda self, *a, **k: 1
    w.resize(1300, 850)
    w.show()
    w.app_stack.setCurrentWidget(w.game_shell)
    q.processEvents()
    return w


def world_ok(w, tag):
    c = app.db()
    dup = c.execute("SELECT COUNT(*) n, COUNT(DISTINCT id) d FROM club").fetchone()
    if int(dup["n"]) != int(dup["d"]):
        note(f"{tag}: ids de club dupliqués")
    if int(c.execute("SELECT COUNT(*) n FROM club WHERE id=1").fetchone()["n"]) != 1:
        note(f"{tag}: pas exactement un club id=1")
    div = c.execute("SELECT division FROM club WHERE id=1").fetchone()["division"]
    if not (1 <= int(div) <= 6):
        note(f"{tag}: division du club 1 invalide ({div})")
    squad = int(c.execute("SELECT COUNT(*) n FROM player WHERE club_id=1 AND COALESCE(is_free_agent,0)=0").fetchone()["n"])
    if not (5 <= squad <= 30):
        note(f"{tag}: effectif {squad}")
    fx = int(c.execute("SELECT COUNT(*) n FROM fixture WHERE (home_club_id=1 OR away_club_id=1)").fetchone()["n"])
    if fx == 0:
        note(f"{tag}: aucun calendrier pour le club 1")
    dups = c.execute("SELECT club_id, COUNT(*) n FROM league_standing GROUP BY club_id HAVING n>1").fetchall()
    if dups:
        note(f"{tag}: classements dupliqués {[dict(r) for r in dups][:3]}")
    orphan = int(c.execute("""SELECT COUNT(*) n FROM player p LEFT JOIN club cl ON cl.id=p.club_id
                              WHERE COALESCE(p.retired,0)=0 AND p.is_free_agent=0 AND cl.id IS NULL""").fetchone()["n"])
    if orphan:
        note(f"{tag}: {orphan} joueur(s) sans club")
    c.close()
    return div, squad


def play_next_match(w, tag, max_days=90):
    fx = None
    for _ in range(max_days):
        c = app.db()
        fx = w._today_fixture_for_user(c)
        c.close()
        if fx is not None:
            break
        w.advance_calendar_days(1)
        q.processEvents()
    if fx is None:
        note(f"{tag}: aucun match jouable en {max_days} jours")
        return False
    w.start_match(); w.finish_match_now(); q.processEvents()
    c = app.db()
    row = c.execute("SELECT played FROM fixture WHERE id=?", (int(fx["id"]),)).fetchone()
    c.close()
    if int(row["played"]) != 1:
        note(f"{tag}: match non validé")
        return False
    return True


q = QApplication.instance() or QApplication([])
q.setStyleSheet(app.style_for_theme("Nuit violette"))

# ---------------------------------------------------------------- 1) 3 clubs
print("== 3 changements de club successifs ==")
w = fresh("Multi", 3)
for step, wanted_div in enumerate((1, 5, 2), start=1):
    c = app.db()
    target = c.execute("""SELECT id,name,division FROM club WHERE id<>1 AND division=?
                          ORDER BY id LIMIT 1""", (wanted_div,)).fetchone()
    if target is None:
        target = c.execute("SELECT id,name,division FROM club WHERE id<>1 ORDER BY id LIMIT 1").fetchone()
    c.close()
    ok = w.change_manager_club(int(target["id"]))
    if not ok:
        note(f"changement {step} refusé ({target['name']})")
        break
    div, squad = world_ok(w, f"changement {step}")
    played = play_next_match(w, f"changement {step}")
    print(f"  changement {step}: {target['name']} L{div}, effectif {squad}, match joué {played}")

world_ok(w, "apres 3 changements")
w.close(); q.processEvents()

# ---------------------------------------------------------------- 2) faillite
print("== faillite forcée ==")
w = fresh("Bank", 3)
c = app.db()
c.execute("UPDATE club SET budget=-4000000 WHERE id=1")
c.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('board_confidence','15')")
c.commit()
c.close()
w.refresh_all(); q.processEvents()

days = 0
crashes = []
while days < 160:
    try:
        c = app.db()
        fx = w._today_fixture_for_user(c)
        ready = c.execute("SELECT value FROM meta WHERE key='season_ready'").fetchone()
        c.close()
        if ready and str(ready["value"]) == "1":
            w.start_new_season()
        elif fx:
            w.start_match(); w.finish_match_now()
        else:
            w.advance_calendar_days(1)
        q.processEvents()
    except Exception as exc:
        crashes.append(repr(exc))
        if len(crashes) <= 3:
            print("  ERREUR:", repr(exc))
    days += 1

if crashes:
    note(f"faillite: {len(crashes)} exception(s)")
c = app.db()
budget = int(c.execute("SELECT budget FROM club WHERE id=1").fetchone()["budget"] or 0)
squad = int(c.execute("SELECT COUNT(*) n FROM player WHERE club_id=1 AND COALESCE(is_free_agent,0)=0").fetchone()["n"])
embargo = c.execute("SELECT value FROM meta WHERE key='board_transfer_freeze'").fetchone()
red_days = c.execute("SELECT value FROM meta WHERE key='club1_red_days'").fetchone()
news = [r["title"] for r in c.execute("SELECT title FROM news ORDER BY id DESC LIMIT 400").fetchall()]
fin_news = [t for t in news if any(k in str(t).lower() for k in ("trésorerie", "embargo", "redressement", "déficit"))]
all_news = [r["title"] for r in c.execute("SELECT title FROM news").fetchall()]
market_share = 100.0 * sum(1 for t in all_news if t == "Marché des transferts") / max(1, len(all_news))
msgs = int(c.execute("SELECT COUNT(*) n FROM manager_message").fetchone()["n"])
c.close()
print(f"  budget final {budget:,} | effectif {squad} | freeze {embargo['value'] if embargo else '-'}"
      f" | jours rouges {red_days['value'] if red_days else '-'} | news financières {len(fin_news)}"
      f" | messages {msgs} | part marché {market_share:.0f}% ({len(all_news)} news)")
if market_share > 60.0:
    note(f"faillite: fil d'actualité saturé par le marché ({market_share:.0f}%)")
if not fin_news:
    note("faillite: aucune news financière (embargo/redressement) générée")
if squad < 8:
    note(f"faillite: effectif cassé ({squad})")
if budget < -50_000_000:
    note(f"faillite: budget extrême ({budget})")
w.close(); q.processEvents()

size = os.path.getsize(os.path.join(r"C:\FM2027V2\data", "error.log"))
if size:
    note(f"error.log non vide ({size} octets)")
print("error.log :", size, "octet(s)")
print("RESULTAT :", "ALL OK" if not issues else f"{len(issues)} ANOMALIE(S)")
for it in issues:
    print(" -", it)
sys.exit(0 if not issues else 1)

# -*- coding: utf-8 -*-
"""Audit du calendrier : invariants, coupe, amicaux, filtres et clôture.

Vérifie la génération (aller-retour, 9/9 domicile-extérieur, journées
complètes, trêves), la coupe (tours du mercredi, sans doublon), les amicaux
(quota, repos, dates occupées), l'affichage (ordre chronologique, filtres,
étiquette COUPE) et la régénération à la nouvelle saison.
"""
import os
import sys
import tempfile
from collections import Counter, defaultdict

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app
from PySide6.QtWidgets import QApplication, QLabel
from PySide6.QtCore import QDate, Qt

TMP = tempfile.mkdtemp(prefix="fm_calaudit_")
os.makedirs(os.path.join(TMP, "saves"), exist_ok=True)
app.SAVE_DIR = os.path.join(TMP, "saves")
app.DEFAULT_DB_PATH = os.path.join(TMP, "x.db")
app.DB_PATH = os.path.join(TMP, "saves", "p.db")
app.DATA_DIR = TMP
app.BASE_DIR = TMP
app.active_save_path = lambda: app.DB_PATH
app.set_active_save_path = lambda p: None
app.init_db(fresh_universe=True, selected_division=2,
            identity={"name": "Cal FC", "arena_name": "A", "color1": "#2f6fed",
                      "color2": "#101a2e", "division": 2})

q = QApplication.instance() or QApplication([])
q.setStyleSheet(app.style_for_theme("Nuit violette"))
app.QDialog.exec = lambda self, *a, **k: 1
w = app.MainWindow()
w.setAttribute(app.Qt.WA_DontShowOnScreen, True)
messages = []
w.show_game_message = lambda title, body="", kind="info", **k: messages.append((title, body))
w.resize(1600, 1000)
w.show(); q.processEvents()
w.app_stack.setCurrentWidget(w.game_shell)

c = app.db()
clubs = {int(r["id"]): int(r["division"]) for r in c.execute("SELECT id,division FROM club").fetchall()}
rows = c.execute("SELECT * FROM fixture WHERE season=1").fetchall()
c.close()

# ---------- 1) Invariants du championnat ----------
champ = [r for r in rows if (r["fixture_type"] or "championship") == "championship"]
assert len(clubs) == 60, len(clubs)
assert len(champ) == 540, len(champ)
for div in range(1, 7):
    rs = [r for r in champ if clubs[int(r["home_club_id"])] == div]
    assert len(rs) == 90, (div, len(rs))
    by_md = defaultdict(list)
    for r in rs:
        by_md[int(r["matchday"])].append(r)
    assert len(by_md) == 18, (div, len(by_md))
    for md, games in by_md.items():
        assert len(games) == 5, (div, md, len(games))
        teams = {int(g["home_club_id"]) for g in games} | {int(g["away_club_id"]) for g in games}
        assert len(teams) == 10, (div, md, len(teams))
        assert len({g["fixture_date"] for g in games}) == 1, (div, md)
    pairs = Counter(tuple(sorted((int(r["home_club_id"]), int(r["away_club_id"])))) for r in rs)
    assert set(pairs.values()) == {2}, (div, Counter(pairs.values()))
    home = Counter(int(r["home_club_id"]) for r in rs)
    away = Counter(int(r["away_club_id"]) for r in rs)
    for cid in set(home) | set(away):
        assert home.get(cid, 0) == 9 and away.get(cid, 0) == 9, (div, cid, home.get(cid), away.get(cid))
    dates = sorted({r["fixture_date"] for r in rs})
    assert dates == sorted(set(r["fixture_date"] for r in rs))
    assert all("2026-09-01" <= d <= "2027-04-30" for d in dates), (div, dates[0], dates[-1])
    assert not any("2026-12-21" <= d <= "2027-01-04" for d in dates), div
    # chaque club joue une seule fois par journée, une seule fois par date
    per_date = Counter()
    for r in rs:
        for cid in (int(r["home_club_id"]), int(r["away_club_id"])):
            per_date[(cid, r["fixture_date"])] += 1
    assert max(per_date.values()) == 1, div
print("1) championnat: 6 divisions × 90 matchs, 18 journées, 9/9 domicile-extérieur")

# ---------- 2) Coupe ----------
cup = [r for r in rows if (r["fixture_type"] or "") == "cup"]
assert len(cup) == 28, len(cup)  # 60 clubs, 4 exemptés
assert {int(r["matchday"]) for r in cup} == {app.CUP_MATCHDAY_OFFSET + 1}
teams = [int(r["home_club_id"]) for r in cup] + [int(r["away_club_id"]) for r in cup]
assert len(teams) == len(set(teams)) == 56, (len(teams), len(set(teams)))
for r in cup:
    from datetime import date as _date
    assert app.parse_iso(r["fixture_date"]).weekday() == 2, r["fixture_date"]
for r in cup:
    if 1 in (int(r["home_club_id"]), int(r["away_club_id"])):
        for o in champ:
            if 1 in (int(o["home_club_id"]), int(o["away_club_id"])):
                gap = abs((app.parse_iso(r["fixture_date"]) - app.parse_iso(o["fixture_date"])).days)
                assert gap >= 3, (r["fixture_date"], o["fixture_date"], gap)
print("2) coupe: 28 matchs, 56 clubs distincts, mercredis, repos club1 ≥ 3 j")

# ---------- 3) Affichage et ordre chronologique ----------
w.show_page(8); q.processEvents()
user_cup = next((r for r in cup if 1 in (int(r["home_club_id"]), int(r["away_club_id"]))), None)
expected_rows = 18 + (1 if user_cup else 0)
assert w.calendar_fixture_list.count() == expected_rows, (w.calendar_fixture_list.count(), expected_rows)
assert "JOURNÉES" in (w.calendar_league_title.text() if hasattr(w, "calendar_league_title") else ""), \
    getattr(w, "calendar_league_title", None)
dates = []
for i in range(w.calendar_fixture_list.count()):
    data = w.calendar_fixture_list.item(i).data(Qt.UserRole)
    fid = int(data["fixture_id"])
    cc = app.db(); row = cc.execute("SELECT fixture_date FROM fixture WHERE id=?", (fid,)).fetchone(); cc.close()
    dates.append(row["fixture_date"])
assert dates == sorted(dates), dates
# Étiquette COUPE, jamais « J101 »
if user_cup is not None:
    cup_id = int(user_cup["id"])
    cup_row = None
    for i in range(w.calendar_fixture_list.count()):
        if int(w.calendar_fixture_list.item(i).data(Qt.UserRole)["fixture_id"]) == cup_id:
            cup_row = i; break
    assert cup_row is not None
    card = w.calendar_fixture_list.itemWidget(w.calendar_fixture_list.item(cup_row))
    texts = [lbl.text() for lbl in card.findChildren(QLabel)]
    assert "COUPE" in " ".join(texts), texts
    assert not any(t.strip() == "J101" for t in texts), texts
    print("3) affichage: lignes chronologiques, carte coupe étiquetée COUPE")
else:
    print("3) affichage: club exempté de coupe au 1er tour")

# Filtres
w.calendar_filter_combo.setCurrentText("RÉSULTATS"); q.processEvents()
assert w.calendar_fixture_list.count() == 0, w.calendar_fixture_list.count()
w.calendar_filter_combo.setCurrentText("PROCHAINS MATCHS"); q.processEvents()
assert w.calendar_fixture_list.count() == expected_rows
w.calendar_filter_combo.setCurrentText("TOUT"); q.processEvents()
assert w.calendar_fixture_list.count() == expected_rows
print("4) filtres: résultats 0, prochains", expected_rows, ", tout", expected_rows)

# Vue d'une autre division : le filtre prochains/résultats doit aussi s'appliquer.
def n_fx():
    n = 0
    for i in range(w.calendar_fixture_list.count()):
        d = w.calendar_fixture_list.item(i).data(Qt.UserRole)
        if isinstance(d, dict) and d.get("type") == "fx":
            n += 1
    return n

w.apply_calendar_division(1); q.processEvents()
w.calendar_filter_combo.setCurrentText("RÉSULTATS"); q.processEvents()
assert n_fx() == 0, n_fx()
w.calendar_filter_combo.setCurrentText("PROCHAINS MATCHS"); q.processEvents()
assert n_fx() == 90, n_fx()
# Aucune étiquette « TON CLUB » sur les matchs des autres divisions.
checked = 0
for i in range(w.calendar_fixture_list.count()):
    data = w.calendar_fixture_list.item(i).data(Qt.UserRole)
    if not (isinstance(data, dict) and data.get("type") == "fx"):
        continue
    card = w.calendar_fixture_list.itemWidget(w.calendar_fixture_list.item(i))
    texts = [lbl.text() for lbl in card.findChildren(QLabel)]
    assert "TON CLUB" not in texts, (i, texts)
    checked += 1
assert checked == 90, checked
w.calendar_filter_combo.setCurrentText("TOUT"); q.processEvents()
w.apply_calendar_division(0); q.processEvents()
# La carte de division garde l'étiquette uniquement pour le club du joueur
# (utile si l'éditeur change sa division), jamais pour les autres clubs.
own_card = w.build_division_fixture_card({
    "played": 0, "home_goals": None, "away_goals": None,
    "home_club_id": 1, "away_club_id": 2, "home_name": "Cal FC",
    "away_name": "Adversaire", "matchday": 1, "fixture_date": "2026-09-05"})
own_texts = [lbl.text() for lbl in own_card.findChildren(QLabel)]
assert "TON CLUB" in own_texts, own_texts
other_card = w.build_division_fixture_card({
    "played": 0, "home_goals": None, "away_goals": None,
    "home_club_id": 2, "away_club_id": 3, "home_name": "Club A",
    "away_name": "Club B", "matchday": 1, "fixture_date": "2026-09-05"})
other_texts = [lbl.text() for lbl in other_card.findChildren(QLabel)]
assert "TON CLUB" not in other_texts, other_texts
print("5) autre division: filtre appliqué (0 résultat, 90 à venir), sans étiquette TON CLUB")

# ---------- 4) Amicaux : quota, date occupée, repos ----------
def schedule(date_iso):
    w.friendly_date_edit.setDate(QDate.fromString(date_iso, "yyyy-MM-dd"))
    w.schedule_friendly_match(); q.processEvents()

messages.clear()
w.friendly_opponent_combo.setCurrentIndex(0)
schedule("2026-09-05")  # jour de J1
c = app.db(); n = c.execute("SELECT COUNT(*) n FROM fixture WHERE fixture_type='friendly'").fetchone()["n"]; c.close()
assert n == 0 and any("joue déjà" in (m[1] or "") for m in messages), (n, messages[-1:])
schedule("2026-09-04")  # veille de J1 : repos insuffisant
c = app.db(); n = c.execute("SELECT COUNT(*) n FROM fixture WHERE fixture_type='friendly'").fetchone()["n"]; c.close()
assert n == 0 and any("Repos" in (m[1] or "") for m in messages), (n, messages[-1:])
free = ("2026-08-01", "2026-08-08", "2026-08-15", "2026-08-22", "2026-08-29")
for d in free:
    schedule(d)
c = app.db(); n = c.execute("SELECT COUNT(*) n FROM fixture WHERE fixture_type='friendly'").fetchone()["n"]; c.close()
assert n == 5, n
schedule("2026-08-26")
c = app.db(); n = c.execute("SELECT COUNT(*) n FROM fixture WHERE fixture_type='friendly'").fetchone()["n"]; c.close()
assert n == 5 and any("Limite de 5" in (m[1] or "") for m in messages), (n, messages[-1:])
w.refresh_all(); q.processEvents()
assert "5 / 5" in w.calendar_kpi_friendly.text(), w.calendar_kpi_friendly.text()
print("5) amicaux: date occupée/veille refusées, 5 programmés, quota bloqué")

# ---------- 5) Résultat joué et filtre RÉSULTATS ----------
c = app.db()
first = c.execute("""SELECT id,home_club_id,away_club_id FROM fixture WHERE fixture_type='championship'
                     AND (home_club_id=1 OR away_club_id=1) ORDER BY fixture_date LIMIT 1""").fetchone()
c.execute("UPDATE fixture SET played=1, home_goals=3, away_goals=1 WHERE id=?", (int(first["id"]),))
c.commit(); c.close()
w.refresh_all(); q.processEvents()
w.calendar_filter_combo.setCurrentText("RÉSULTATS"); q.processEvents()
assert w.calendar_fixture_list.count() == 1, w.calendar_fixture_list.count()
card = w.calendar_fixture_list.itemWidget(w.calendar_fixture_list.item(0))
texts = [lbl.text() for lbl in card.findChildren(QLabel)]
assert any("3 : 1" in t or "1 : 3" in t for t in texts), texts
w.calendar_filter_combo.setCurrentText("TOUT"); q.processEvents()
assert "AMICAL" in w.calendar_kpi_next.text(), w.calendar_kpi_next.text()
c = app.db()
c.execute("UPDATE fixture SET played=1, home_goals=2, away_goals=2 WHERE fixture_type='friendly'")
c.execute("UPDATE career SET current_date='2026-09-06' WHERE id=1")
c.commit(); c.close()
w.refresh_all(); q.processEvents()
c = app.db(); _nxt = w._next_fixture_for_user(c); c.close()
assert _nxt is not None and int(_nxt["matchday"]) == 2, (_nxt["matchday"] if _nxt else None)
_opp = _nxt["away_name"] if int(_nxt["home_club_id"]) == 1 else _nxt["home_name"]
assert _opp[:15] in w.calendar_kpi_next.text(), (_opp, w.calendar_kpi_next.text())
print("6) résultat: score affiché, filtre RÉSULTATS = 1, prochain =", w.calendar_kpi_next.text())

# ---------- 6) Nouvelle saison : calendrier régénéré ----------
c = app.db()
c.execute("DELETE FROM fixture WHERE played=0")
c.execute("UPDATE career SET current_date='2027-06-30' WHERE id=1")
c.commit(); c.close()
assert w.start_new_season(), "clôture refusée"
c = app.db()
new_rows = c.execute("SELECT * FROM fixture WHERE season=2").fetchall()
old_rows = c.execute("SELECT COUNT(*) n FROM fixture WHERE season=1").fetchone()["n"]
c.close()
assert old_rows == 0, old_rows
assert len([r for r in new_rows if (r["fixture_type"] or "championship") == "championship"]) == 540
assert len([r for r in new_rows if (r["fixture_type"] or "") == "cup"]) == 28
u = [r for r in new_rows if 1 in (int(r["home_club_id"]), int(r["away_club_id"]))
     and (r["fixture_type"] or "championship") == "championship"]
assert len(u) == 18 and sum(1 for r in u if int(r["home_club_id"]) == 1) == 9
print("7) nouvelle saison: 540 matchs + 28 coupe, ancienne saison purgée, club1 9/9")

w.close(); q.processEvents()
size = os.path.getsize(r"C:\FM2027V2\data\error.log")
assert size == 0, size
print("RESULT: ALL OK")

# -*- coding: utf-8 -*-
"""AUDIT DE JEU : 6 divisions, plusieurs semaines, invariants de monde.

Lance un vrai univers par division, joue les journées (matchs du manager + IA),
vérifie les classements, effectifs, maillots, calendrier, coupe, finances et
messages. Sort en erreur si une anomalie est détectée.
"""
import os, sys, tempfile, traceback
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app
from PySide6.QtWidgets import QApplication, QDialog

app.QDialog.exec = lambda self, *a, **k: 1
q = QApplication.instance() or QApplication([])
q.setStyleSheet(app.style_for_theme("Nuit violette"))

# Le journal d'erreurs est global au dossier du jeu : on le tronque et on
# surveille sa croissance apres chaque division.
try:
    open(app.ERROR_LOG, "r+b").truncate(0)
except FileNotFoundError:
    open(app.ERROR_LOG, "wb").close()


def error_log_size():
    try:
        return os.path.getsize(app.ERROR_LOG)
    except OSError:
        return 0

DAYS = int(os.environ.get("AUDIT_DAYS", "120"))
TARGET = int(os.environ.get("AUDIT_MATCHES", "6"))
DIVISIONS = [int(x) for x in os.environ.get("AUDIT_DIVS", "1,2,3,4,5,6").split(",")]
issues = []


def note(div, msg):
    issues.append(f"L{div}: {msg}")
    print("  !!", msg)


def check_world(div, c):
    # 1) matchs joués complets
    n = c.execute("SELECT COUNT(*) n FROM fixture WHERE played=1 AND (home_goals IS NULL OR away_goals IS NULL)").fetchone()["n"]
    if n:
        note(div, f"{n} match(s) joué(s) sans score")
    neg = c.execute("SELECT COUNT(*) n FROM fixture WHERE home_goals<0 OR away_goals<0").fetchone()["n"]
    if neg:
        note(div, f"{neg} score(s) négatif(s)")
    # 2) classements cohérents (par division)
    rows = c.execute("""SELECT s.*, cl.division FROM league_standing s
                        JOIN club cl ON cl.id=s.club_id""").fetchall()
    by_div = {}
    for r in rows:
        by_div.setdefault(int(r["division"]), []).append(r)
        if int(r["played"]) != int(r["wins"]) + int(r["draws"]) + int(r["losses"]):
            note(div, f"played incohérent club {r['club_id']}")
        if int(r["pts"]) != 3 * int(r["wins"]) + int(r["draws"]):
            note(div, f"points incohérents club {r['club_id']}: {r['pts']}")
    for d, rr in by_div.items():
        gf, ga = sum(int(x["gf"]) for x in rr), sum(int(x["ga"]) for x in rr)
        if gf != ga:
            note(div, f"division {d}: GF {gf} != GA {ga}")
    # 3) calendrier : pas de doublon
    dup = c.execute("""SELECT season,home_club_id,away_club_id,matchday,fixture_type,COUNT(*) n
                       FROM fixture GROUP BY season,home_club_id,away_club_id,matchday,fixture_type
                       HAVING n>1""").fetchall()
    if dup:
        note(div, f"{len(dup)} doublon(s) de calendrier")
    # 4) coupe : aucun match nul SANS séance de 10 m enregistrée
    draw = c.execute("""SELECT COUNT(*) n FROM fixture WHERE fixture_type='cup' AND played=1
                        AND home_goals=away_goals
                        AND (pen_home IS NULL OR pen_away IS NULL)""").fetchone()["n"]
    if draw:
        note(div, f"{draw} match(s) de coupe nul(s)")
    # 5) effectifs et maillots
    small = c.execute("""SELECT club_id, COUNT(*) n FROM player
                         WHERE is_free_agent=0 AND COALESCE(retired,0)=0
                         GROUP BY club_id HAVING n<5 OR n>30""").fetchall()
    if small:
        note(div, f"effectif hors bornes: {[(r['club_id'], r['n']) for r in small][:5]}")
    shirts = c.execute("""SELECT club_id, shirt_number, COUNT(*) n FROM player
                          WHERE is_free_agent=0 AND shirt_number IS NOT NULL AND shirt_number>0
                          GROUP BY club_id, shirt_number HAVING n>1""").fetchall()
    if shirts:
        note(div, f"{len(shirts)} numéro(s) de maillot en double")
    # 6) finances
    broke = c.execute("SELECT COUNT(*) n FROM club WHERE budget < -50000000").fetchone()["n"]
    if broke:
        note(div, f"{broke} club(s) sous -50 M€")
    # 7) messagerie
    msgs = c.execute("SELECT COUNT(*) n FROM manager_message").fetchone()["n"]
    if msgs > 900:
        note(div, f"{msgs} messages en boîte")
    # 8) joueurs orphelins
    orphan = c.execute("""SELECT COUNT(*) n FROM player p LEFT JOIN club cl ON cl.id=p.club_id
                          WHERE COALESCE(p.retired,0)=0 AND p.is_free_agent=0 AND cl.id IS NULL""").fetchone()["n"]
    if orphan:
        note(div, f"{orphan} joueur(s) sans club")
    # 9) divisions et classements uniques
    bad_div = c.execute("SELECT COUNT(*) n FROM club WHERE division<1 OR division>6").fetchone()["n"]
    if bad_div:
        note(div, f"{bad_div} club(s) hors division 1-6")
    dup_standing = c.execute("""SELECT club_id, COUNT(*) n FROM league_standing
                                GROUP BY club_id HAVING n>1""").fetchall()
    if dup_standing:
        note(div, f"{len(dup_standing)} club(s) avec plusieurs lignes de classement")
    # 10) archives : rangs uniques par saison/division
    dup_rank = c.execute("""SELECT season, division, rank, COUNT(*) n FROM season_archive
                            GROUP BY season, division, rank HAVING n>1""").fetchall()
    if dup_rank:
        note(div, f"{len(dup_rank)} rang(s) dupliqué(s) dans les archives")
    # 11) prêts expirés
    cur_season = int(c.execute("SELECT season FROM club WHERE id=1").fetchone()["season"])
    stale = c.execute("""SELECT COUNT(*) n FROM player WHERE COALESCE(loan_from_club,0)>0
                         AND COALESCE(loan_until_season,0)>0 AND loan_until_season < ?""",
                      (cur_season,)).fetchone()["n"]
    if stale:
        note(div, f"{stale} prêt(s) expiré(s) non rentré(s)")
    # 12) distributions de scores par division (moteur v2)
    rows = c.execute("""SELECT cl.division d, COUNT(*) n, SUM(f.home_goals+f.away_goals) g,
                               SUM(CASE WHEN f.home_goals=0 AND f.away_goals=0 THEN 1 ELSE 0 END) z
                        FROM fixture f JOIN club cl ON cl.id=f.home_club_id
                        WHERE f.played=1 AND COALESCE(f.fixture_type,'championship')='championship'
                        GROUP BY cl.division""").fetchall()
    for r in rows:
        n = int(r["n"] or 0)
        if n < 30:
            continue
        per = float(r["g"] or 0) / n
        if not (1.8 <= per <= 8.0):
            note(div, f"L{r['d']}: {per:.2f} buts/match hors plage")
        zero = 100.0 * float(r["z"] or 0) / n
        if zero > 35.0:
            note(div, f"L{r['d']}: {zero:.0f}% de 0-0")
    maxgf = c.execute("SELECT MAX(gf) m FROM league_standing").fetchone()["m"]
    if maxgf is not None and int(maxgf) > 99:
        note(div, f"une équipe a {int(maxgf)} buts marqués")


def check_transition(div, c):
    """Après une clôture : archives complètes et montées/descentes appliquées."""
    row = c.execute("SELECT MAX(season) s FROM season_archive").fetchone()
    if not row or row["s"] is None:
        return
    season = int(row["s"])
    now_div = {int(r["id"]): int(r["division"]) for r in c.execute("SELECT id,division FROM club").fetchall()}
    for d in range(1, 7):
        rows = c.execute("SELECT * FROM season_archive WHERE season=? AND division=? ORDER BY rank",
                         (season, d)).fetchall()
        if len(rows) != 10:
            note(div, f"archives saison {season} L{d}: {len(rows)} club(s) au lieu de 10")
        ranks = [int(r["rank"]) for r in rows]
        if ranks != list(range(1, len(rows) + 1)):
            note(div, f"archives L{d}: rangs incohérents {ranks}")
        if len(rows) >= 2:
            if d > 1:
                for r in rows[:2]:
                    if now_div.get(int(r["club_id"])) != d - 1:
                        note(div, f"montée L{d} → L{d-1} non appliquée : {r['club_name']}")
            if d < 6:
                for r in rows[-2:]:
                    if now_div.get(int(r["club_id"])) != d + 1:
                        note(div, f"descente L{d} → L{d+1} non appliquée : {r['club_name']}")
    # Coupe : plus aucun match en attente sur la saison close, une seule finale.
    pending = c.execute("""SELECT COUNT(*) n FROM fixture WHERE fixture_type='cup'
                           AND season=? AND played=0""", (season,)).fetchone()["n"]
    if pending:
        note(div, f"coupe saison {season}: {pending} match(s) non joué(s)")
    last_round = c.execute("""SELECT MAX(matchday) m FROM fixture WHERE fixture_type='cup' AND season=?""",
                           (season,)).fetchone()["m"]
    if last_round is not None:
        finals = c.execute("""SELECT home_goals,away_goals FROM fixture WHERE fixture_type='cup'
                              AND season=? AND matchday=?""", (season, int(last_round))).fetchall()
        if len(finals) != 1:
            note(div, f"coupe saison {season}: {len(finals)} finale(s)")
        elif finals[0]["home_goals"] == finals[0]["away_goals"]:
            note(div, f"coupe saison {season}: finale nulle")


def run_division(div):
    tmp = tempfile.mkdtemp(prefix=f"fm_audit_d{div}_")
    os.makedirs(os.path.join(tmp, "saves"), exist_ok=True)
    app.SAVE_DIR = os.path.join(tmp, "saves")
    app.DEFAULT_DB_PATH = os.path.join(tmp, "x.db")
    app.DB_PATH = os.path.join(tmp, "saves", "p.db")
    app.DATA_DIR = tmp
    app.BASE_DIR = tmp
    app.active_save_path = lambda: app.DB_PATH
    app.set_active_save_path = lambda p: None
    app.init_db(fresh_universe=True, selected_division=div,
                identity={"name": f"Audit D{div}", "arena_name": "A", "color1": "#2f6fed",
                          "color2": "#101a2e", "division": div})

    w = app.MainWindow()
    w.setAttribute(app.Qt.WA_DontShowOnScreen, True)
    w.show_game_message = lambda *a, **k: True
    w.resize(1400, 900)
    w.show()
    w.app_stack.setCurrentWidget(w.game_shell)
    q.processEvents()

    days = matches = 0
    seasons = 0
    errors = []
    while days < DAYS and matches < TARGET:
        try:
            c = app.db()
            fx = w._today_fixture_for_user(c)
            ready = c.execute("SELECT value FROM meta WHERE key='season_ready'").fetchone()
            c.close()
            if ready and str(ready["value"]) == "1":
                w.start_new_season(); seasons += 1
                c2 = app.db()
                if int(c2.execute("SELECT COUNT(*) n FROM league_standing WHERE played>0").fetchone()["n"]):
                    note(div, "classements non remis à zéro après la clôture")
                if not int(c2.execute("SELECT COUNT(*) n FROM fixture WHERE played=0").fetchone()["n"]):
                    note(div, "aucun calendrier généré après la clôture")
                c2.close()
            elif fx:
                w.start_match(); w.finish_match_now(); matches += 1
            else:
                w.advance_calendar_days(1)
            q.processEvents()
        except Exception as exc:
            errors.append(f"jour {days}: {exc!r}")
            if len(errors) <= 3:
                print("  ERREUR:", repr(exc))
                traceback.print_exc()
        days += 1
        if days % 6 == 0:
            c = app.db(); check_world(div, c); c.close()

    c = app.db()
    check_world(div, c)
    check_transition(div, c)
    season = c.execute("SELECT season FROM club WHERE id=1").fetchone()["season"]
    row = c.execute("SELECT COUNT(*) n FROM league_standing WHERE played>0").fetchone()["n"]
    arch = c.execute("SELECT COUNT(*) n FROM season_archive WHERE club_id=1").fetchone()["n"]
    style = c.execute("SELECT profile FROM club WHERE id=1").fetchone()["profile"]
    profiles = c.execute("SELECT profile, COUNT(*) n FROM club WHERE id<>1 GROUP BY profile").fetchall()
    c.close()
    w.close()
    q.processEvents()
    if errors:
        note(div, f"{len(errors)} exception(s) pendant la simulation")
    errlog = error_log_size()
    if errlog:
        note(div, f"error.log a grossi ({errlog} octets)")
    print(f"  Ligue {div}: saison {season}, {matches} match(s) manager, {days} jours, "
          f"profils IA {[(p['profile'], p['n']) for p in profiles]}, archives {arch}, error.log {errlog}")
    return errlog


print("AUDIT DE JEU — divisions:", DIVISIONS, "| jours:", DAYS)
bad_logs = 0
for div in DIVISIONS:
    try:
        bad_logs += run_division(div)
    except Exception as exc:
        note(div, f"crash du harnais: {exc!r}")
        traceback.print_exc()

print("\nRESULTAT:", "ALL OK" if not issues else f"{len(issues)} ANOMALIE(S)")
for it in issues[:40]:
    print(" -", it)
sys.exit(0 if not issues else 1)

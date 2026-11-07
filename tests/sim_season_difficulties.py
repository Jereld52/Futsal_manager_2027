# -*- coding: utf-8 -*-
"""sim_season_difficulties.py - une saison complete par niveau de difficulte.

Usage :
    python tests\\sim_season_difficulties.py

Cree trois univers neufs (Facile / Normal / Difficile), joue la saison du club
du manager match par match, laisse l'IA jouer les autres rencontres, puis
declenche la transition de saison pour mesurer :
  - classement final, points, buts ;
  - budget de fin de saison et confiance du board ;
  - offres de clubs proposees au manager a la nouvelle saison ;
  - erreurs eventuelles.

Aucune sauvegarde utilisateur n'est touchee : tout se passe dans TEMP.
"""
import os, sys, tempfile, time, json
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, r"C:\FM2027V2")
import app
from PySide6.QtWidgets import QApplication

DIFFICULTIES = [
    ("Facile", "Facile", "Normale", 1.25, +10, +6, +1),
    ("Normal", "Normal", "Normale", 1.00, 0, 0, 0),
    ("Difficile", "Difficile", "Difficile", 0.72, -8, -6, -1),
]
DIVISION = 3
DAYS = 340


def one_season(label, creation_key, mode, budget_factor):
    tmp = tempfile.mkdtemp(prefix="fm_season_%s_" % label.lower())
    os.makedirs(os.path.join(tmp, "saves"), exist_ok=True)
    db_path = os.path.join(tmp, "saves", "season.db")
    app.SAVE_DIR = os.path.join(tmp, "saves")
    app.DEFAULT_DB_PATH = os.path.join(tmp, "default.db")
    app.DB_PATH = db_path
    app.DATA_DIR = tmp
    app.BASE_DIR = tmp
    app.OPTIONS_FILE = os.path.join(tmp, "options.json")
    app.active_save_path = lambda: db_path
    app.set_active_save_path = lambda p: None
    app.init_db(
        fresh_universe=True, selected_division=DIVISION,
        identity={"name": "AS Test %s" % label, "arena_name": "Arena Test",
                  "color1": "#2f6fed", "color2": "#101a2e",
                  "division": DIVISION, "difficulty": creation_key,
                  "database_size": "classic"})
    c = app.db()
    c.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('difficulty_mode',?)", (mode,))
    c.commit()
    start = c.execute("SELECT budget,reputation,division FROM club WHERE id=1").fetchone()
    squad = c.execute("SELECT COUNT(*) n, AVG(technique+passing+finishing+dribble+defense+goalkeeper) lvl "
                      "FROM player WHERE club_id=1 AND COALESCE(is_free_agent,0)=0").fetchone()
    c.close()

    q = QApplication.instance() or QApplication([])
    w = app.MainWindow()
    w.show_game_message = lambda *a, **k: True
    w.resize(1400, 900)
    w.show()
    w.refresh_job_offers = lambda *a, **k: None
    app.QDialog.exec = lambda self, *a, **k: 1
    errors = []
    seasons = 0
    matches = 0
    t0 = time.perf_counter()
    stop_reason = "limite de jours"
    for step in range(DAYS):
        try:
            c = app.db()
            fx = w._today_fixture_for_user(c)
            ready = c.execute("SELECT value FROM meta WHERE key='season_ready'").fetchone()
            c.close()
            if ready and str(ready["value"]) == "1":
                w.start_new_season()
                q.processEvents()
                stop_reason = "nouvelle saison"
                break
            if fx:
                w.start_match()
                q.processEvents()
                w.finish_match_now()
                q.processEvents()
                matches += 1
            else:
                w.advance_calendar_days(1)
                q.processEvents()
        except Exception as exc:
            errors.append("%d:%r" % (step, exc))
            if len(errors) <= 3:
                print("  ERREUR", repr(exc))
    duration = time.perf_counter() - t0

    c = app.db()
    archive = c.execute("SELECT * FROM season_archive WHERE club_id=1 ORDER BY season DESC LIMIT 1").fetchone()
    club = c.execute("SELECT season,budget,reputation,division FROM club WHERE id=1").fetchone()
    board = c.execute("SELECT value FROM meta WHERE key='board_confidence'").fetchone()
    offers_row = c.execute("SELECT value FROM meta WHERE key='job_offers'").fetchone()
    post = c.execute("SELECT COUNT(*) n FROM fixture WHERE played=1").fetchone()["n"]
    c.close()
    offers = json.loads(offers_row["value"] or "[]") if offers_row else []
    rank = int(archive["rank"]) if archive else None
    points = int(archive["pts"]) if archive and "pts" in archive.keys() else None
    gf = int(archive["gf"]) if archive and "gf" in archive.keys() else None
    ga = int(archive["ga"]) if archive and "ga" in archive.keys() else None
    kind = (archive["kind"] if archive and "kind" in archive.keys() else "") or ""
    try:
        w.close()
        QApplication.processEvents()
    except Exception:
        pass
    return {
        "label": label, "mode": mode, "division": DIVISION,
        "start_budget": int(start["budget"] or 0), "start_rep": int(start["reputation"] or 0),
        "start_level": round(float(squad["lvl"] or 0), 1), "start_squad": int(squad["n"] or 0),
        "matches": matches, "duration": duration, "stop": stop_reason,
        "rank": rank, "points": points, "gf": gf, "ga": ga, "kind": kind,
        "end_budget": int(club["budget"] or 0), "season": int(club["season"] or 0),
        "board": int(board["value"] or 0) if board else None,
        "offers": offers, "errors": errors, "played_total": int(post or 0),
    }


def main():
    rows = []
    for label, creation, mode, factor, _rep, _lvl, _fac in DIFFICULTIES:
        print("=== Saison %s (%s / en jeu : %s) ===" % (label, creation, mode), flush=True)
        row = one_season(label, creation, mode, factor)
        rows.append(row)
        print("  duree %.1fs | matchs joues %d | fin : %s" % (row["duration"], row["matches"], row["stop"]))
        print("  classement %s | pts %s | %s-%s | %s" % (row["rank"], row["points"], row["gf"], row["ga"], row["kind"]))
        print("  budget %s -> %s | board %s | offres %d | erreurs %d" % (
            row["start_budget"], row["end_budget"], row["board"], len(row["offers"]), len(row["errors"])))
        if row["offers"]:
            print("  offres :", ", ".join("%s (L%s)" % (o.get("name"), o.get("division")) for o in row["offers"]))
        if row["errors"]:
            print("  details :", row["errors"][:3])
        print()

    print("SYNTHESE")
    print("%-10s %-9s %5s %5s %6s %12s %8s %6s" % ("Niveau", "Mode", "Rang", "Pts", "Buts", "Budget fin", "Board", "Offres"))
    for r in rows:
        buts = "%s-%s" % (r["gf"], r["ga"]) if r["gf"] is not None else "-"
        print("%-10s %-9s %5s %5s %6s %12s %8s %6d" % (
            r["label"], r["mode"], r["rank"], r["points"], buts,
            "{:,}".format(r["end_budget"]).replace(",", " "), r["board"], len(r["offers"])))
    assert all(not r["errors"] for r in rows), "erreurs pendant la simulation"
    print("RESULT: ALL OK")


if __name__ == "__main__":
    main()

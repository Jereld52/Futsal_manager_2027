# -*- coding: utf-8 -*-
"""Point d'entree unique des tests courts FM2027V2.

Usage :
    python tests\\run_tests.py            # tous les tests | suites en argument
    python tests\\run_tests.py banqueroute # une seule suite (nom partiel)

Garanties : DBs de test sur TEMP, aucune ecriture dans data/active_save.txt ni
dans les sauvegardes utilisateur ; data/error.log tronque (jamais supprime)
et verifie 0 octet en fin de course.
"""
import os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = r"C:\FM2027V2"
LOG = os.path.join(ROOT, "data", "error.log")

SUITES = ["test_banqueroute.py", "test_prepaid_discard.py", "test_daily_loop.py", "test_messagerie.py", "test_message_badges.py", "test_new_features.py", "test_transfer_history.py", "test_transfer_scouting_ui.py", "test_match_pitch2d.py", "test_match_report_view.py", "test_motion_step.py", "test_coaching_options.py", "test_live_team_signal.py", "test_infra_save_ui.py", "test_campus_view.py", "test_ui_start_render.py", "test_splash_sequence.py", "test_club_swap.py", "test_job_offers.py", "test_club_change_elements.py", "test_balance_soak.py", "test_loans.py", "test_loan_tracking.py", "test_loan_profiles.py", "test_sold_player_offers.py", "test_world_integrity.py", "test_phantom_cup_repair.py", "test_ai_scouting.py", "test_ai_profiles.py", "test_ai_clubs.py", "test_wage_budget.py", "test_bench_drag.py", "test_academy_facility.py", "test_academy_options.py", "test_start_screen.py", "test_images_audit.py", "test_club_sheet_ai.py", "test_club_sheet_ui.py", "test_help_panel.py", "test_messaging_ui.py", "test_messaging_audit.py", "test_visual_glitches.py", "test_training_ui.py", "test_offers_cards.py", "test_market_columns.py", "test_market_sort.py", "test_match_engine_v2.py", "test_engine_balance.py", "test_pitch_flow.py", "test_transfer_contracts.py", "test_contract_renewal.py", "test_precontract_season.py", "test_precontract_negotiation.py", "test_transfer_competition.py", "audit_scenarios.py", "test_dashboard_fit.py", "test_dashboard_audit.py", "test_tactics_layout.py", "test_tactics_render_audit.py", "test_tactical_instructions_ui.py", "test_pitch_render.py", "test_facility_gestion_fit.py", "test_academy_development.py", "test_academy_pipeline.py", "test_academy_project.py", "test_history_match_types.py", "test_competitions_ui.py", "test_competitions_audit.py", "test_calendar_audit.py", "test_cup_report_links.py", "test_cup_shootout.py", "test_cup_reperes.py", "test_finance_exploitation.py", "test_finances_audit.py", "test_finance_sponsors_ui.py", "test_staff_ui.py", "test_staff_audit.py", "test_staff_delegations.py", "test_staff_delegations_extended.py", "test_shortlist_cleanup.py", "test_ui_labels_clean.py", "test_squad_audit.py", "test_date_formats.py", "test_facility_project_repair.py", "test_facility_arena_repair.py", "test_facility_new_buildings.py", "test_facility_gestion_actions.py", "test_dashboard_honours.py", "test_scouting_digest.py", "test_old_save_boot.py", "test_beta_clean.py", "test_icon_consistency.py", "test_save_editor.py", "test_immersion.py", "test_immersion_flow.py", "test_bug_report.py", "test_onboarding.py", "global_smoke.py"]


def reset_error_log():
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    f = open(LOG, "r+b") if os.path.exists(LOG) else open(LOG, "wb")
    f.truncate(0)
    f.close()


def main():
    wanted = [s.lower() for s in sys.argv[1:]]
    suites = [s for s in SUITES if not wanted or any(w in s.lower() for w in wanted)]
    if not suites:
        print("Aucune suite ne correspond :", wanted)
        return 2
    reset_error_log()
    fails = []
    for suite in suites:
        t0 = time.time()
        r = subprocess.run([sys.executable, os.path.join(HERE, suite)],
                           capture_output=True, text=True,
                           encoding="utf-8", errors="replace",
                           cwd=ROOT,
                           env={**os.environ, "QT_QPA_PLATFORM": "offscreen",
                                "PYTHONIOENCODING": "utf-8"})
        dt = time.time() - t0
        tail = [l for l in (r.stdout or "").strip().splitlines() if l.strip()]
        last = tail[-1] if tail else ""
        print(f"[{'PASS' if r.returncode == 0 else 'FAIL'}] {suite:24s} {dt:5.1f}s  {last}")
        if r.returncode != 0:
            fails.append(suite)
            print("  --- sortie (fin) ---")
            for l in (r.stdout or "").splitlines()[-8:]:
                print("  |", l)
            for l in (r.stderr or "").splitlines()[-8:]:
                print("  !", l)
    size = os.path.getsize(LOG)
    print(f"error.log : {size} octet(s) -> {'OK' if size == 0 else 'ERREUR'}")
    ok = not fails and size == 0
    print("RESULT :", "ALL OK" if ok else "ECHEC : " + ", ".join(fails))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

"""Schéma SQLite autonome et migrations idempotentes (utilisable headless)."""
import sqlite3

def column_exists(conn, table, column):
    return any(row[1] == column for row in conn.execute(f'PRAGMA table_info({table})'))

SCHEMA = '''
CREATE TABLE IF NOT EXISTS club(id INTEGER PRIMARY KEY,name TEXT NOT NULL,reputation INTEGER NOT NULL DEFAULT 1,budget INTEGER NOT NULL DEFAULT 250000,season INTEGER NOT NULL DEFAULT 1,division INTEGER NOT NULL DEFAULT 1,legacy_id INTEGER,color1 TEXT NOT NULL DEFAULT '#1f8a4d',color2 TEXT NOT NULL DEFAULT '#0f3d27',kit_pattern TEXT NOT NULL DEFAULT 'vertical',logo_pattern TEXT NOT NULL DEFAULT 'shield',arena_name TEXT NOT NULL DEFAULT 'Arena Horizon');
CREATE TABLE IF NOT EXISTS player(id INTEGER PRIMARY KEY AUTOINCREMENT,club_id INTEGER NOT NULL,first_name TEXT NOT NULL,last_name TEXT NOT NULL,age INTEGER NOT NULL,position TEXT NOT NULL,technique INTEGER NOT NULL,passing INTEGER NOT NULL,finishing INTEGER NOT NULL,defense INTEGER NOT NULL,goalkeeper INTEGER NOT NULL,stamina INTEGER NOT NULL,condition INTEGER NOT NULL DEFAULT 100,morale INTEGER NOT NULL DEFAULT 70,nationality TEXT NOT NULL DEFAULT 'Inconnue',injury_matches INTEGER NOT NULL DEFAULT 0,legacy_id INTEGER,salary INTEGER NOT NULL DEFAULT 2500,contract_years INTEGER NOT NULL DEFAULT 2,market_value INTEGER NOT NULL DEFAULT 45000,transfer_listed INTEGER NOT NULL DEFAULT 0,is_free_agent INTEGER NOT NULL DEFAULT 0,shirt_number INTEGER NOT NULL DEFAULT 0,yellow_cards INTEGER NOT NULL DEFAULT 0,suspension_matches INTEGER NOT NULL DEFAULT 0,injury_days INTEGER NOT NULL DEFAULT 0,suspension_days INTEGER NOT NULL DEFAULT 0,birth_date TEXT,season_goals INTEGER NOT NULL DEFAULT 0,season_passes INTEGER NOT NULL DEFAULT 0,season_assists INTEGER NOT NULL DEFAULT 0,season_saves INTEGER NOT NULL DEFAULT 0,season_conceded INTEGER NOT NULL DEFAULT 0,season_yellow INTEGER NOT NULL DEFAULT 0,season_red INTEGER NOT NULL DEFAULT 0,season_matches INTEGER NOT NULL DEFAULT 0,season_rating_sum REAL NOT NULL DEFAULT 0,season_rating_count INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS match_record(id INTEGER PRIMARY KEY AUTOINCREMENT,season INTEGER,matchday INTEGER,home TEXT,away TEXT,home_goals INTEGER,away_goals INTEGER,report TEXT,created_at TEXT,simulation_seed INTEGER);
CREATE TABLE IF NOT EXISTS career(id INTEGER PRIMARY KEY CHECK(id=1),club_id INTEGER,matchday INTEGER DEFAULT 1,wins INTEGER DEFAULT 0,draws INTEGER DEFAULT 0,losses INTEGER DEFAULT 0,goals_for INTEGER DEFAULT 0,goals_against INTEGER DEFAULT 0,points INTEGER DEFAULT 0,current_date TEXT NOT NULL DEFAULT '2026-08-01');
CREATE TABLE IF NOT EXISTS league(id INTEGER PRIMARY KEY,name TEXT NOT NULL,strength INTEGER NOT NULL,base_budget INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS league_standing(club_id INTEGER PRIMARY KEY,played INTEGER NOT NULL DEFAULT 0,wins INTEGER NOT NULL DEFAULT 0,draws INTEGER NOT NULL DEFAULT 0,losses INTEGER NOT NULL DEFAULT 0,gf INTEGER NOT NULL DEFAULT 0,ga INTEGER NOT NULL DEFAULT 0,pts INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS finance_tx(id INTEGER PRIMARY KEY AUTOINCREMENT,club_id INTEGER NOT NULL,label TEXT NOT NULL,amount INTEGER NOT NULL,created_at TEXT NOT NULL,category TEXT NOT NULL DEFAULT 'Divers');
CREATE TABLE IF NOT EXISTS training_session(id INTEGER PRIMARY KEY AUTOINCREMENT,focus TEXT NOT NULL,intensity TEXT NOT NULL,quality INTEGER NOT NULL,created_at TEXT NOT NULL,planned_date TEXT,activity_key TEXT NOT NULL DEFAULT 'Technique',completed INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS facility(id INTEGER PRIMARY KEY CHECK(id=1),arena_level INTEGER NOT NULL DEFAULT 1,medical_level INTEGER NOT NULL DEFAULT 1,youth_level INTEGER NOT NULL DEFAULT 1,marketing_level INTEGER NOT NULL DEFAULT 1,lighting_level INTEGER NOT NULL DEFAULT 1,parking_level INTEGER NOT NULL DEFAULT 1,has_bar INTEGER NOT NULL DEFAULT 0,has_vip INTEGER NOT NULL DEFAULT 0,has_shop INTEGER NOT NULL DEFAULT 0,has_rental_courts INTEGER NOT NULL DEFAULT 0,has_events_hall INTEGER NOT NULL DEFAULT 0,has_fan_zone INTEGER NOT NULL DEFAULT 0,ticket_price INTEGER NOT NULL DEFAULT 12);
CREATE TABLE IF NOT EXISTS loan(id INTEGER PRIMARY KEY AUTOINCREMENT,principal INTEGER NOT NULL,rate_bps INTEGER NOT NULL,weekly_due INTEGER NOT NULL,term_weeks INTEGER NOT NULL,weeks_paid INTEGER NOT NULL DEFAULT 0,start_date TEXT NOT NULL,next_due_date TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'active',label TEXT NOT NULL DEFAULT 'Prêt bancaire');
CREATE TABLE IF NOT EXISTS facility_project(id INTEGER PRIMARY KEY AUTOINCREMENT,facility_key TEXT NOT NULL,label TEXT NOT NULL,target_level INTEGER NOT NULL,cost INTEGER NOT NULL,duration_days INTEGER NOT NULL,start_date TEXT NOT NULL,due_date TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'in_progress',completed_date TEXT);
CREATE TABLE IF NOT EXISTS news(id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT NOT NULL,body TEXT NOT NULL,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS manager_message(id INTEGER PRIMARY KEY AUTOINCREMENT,kind TEXT NOT NULL,title TEXT NOT NULL,body TEXT NOT NULL,created_date TEXT NOT NULL,due_date TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'waiting',action_data TEXT NOT NULL DEFAULT '{}',is_read INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS scout_report(player_id INTEGER PRIMARY KEY,knowledge INTEGER NOT NULL DEFAULT 0,reports INTEGER NOT NULL DEFAULT 0,updated_date TEXT);
CREATE TABLE IF NOT EXISTS ai_match_report(fixture_id INTEGER PRIMARY KEY,scorers TEXT NOT NULL DEFAULT '[]',created_at TEXT);
CREATE TABLE IF NOT EXISTS squad_action_log(action_key TEXT NOT NULL,player_id INTEGER NOT NULL DEFAULT 0,action_date TEXT NOT NULL,PRIMARY KEY(action_key,player_id,action_date));
CREATE TABLE IF NOT EXISTS fixture(id INTEGER PRIMARY KEY AUTOINCREMENT,season INTEGER NOT NULL DEFAULT 1,matchday INTEGER NOT NULL,fixture_date TEXT NOT NULL,home_club_id INTEGER NOT NULL,away_club_id INTEGER NOT NULL,played INTEGER NOT NULL DEFAULT 0,home_goals INTEGER,away_goals INTEGER,fixture_type TEXT NOT NULL DEFAULT 'championship');
CREATE TABLE IF NOT EXISTS player_match_log(id INTEGER PRIMARY KEY AUTOINCREMENT,player_id INTEGER NOT NULL,season INTEGER NOT NULL,fixture_id INTEGER,fixture_type TEXT NOT NULL DEFAULT 'championship',matchday INTEGER NOT NULL DEFAULT 0,match_date TEXT,goals INTEGER NOT NULL DEFAULT 0,assists INTEGER NOT NULL DEFAULT 0,saves INTEGER NOT NULL DEFAULT 0,yellow INTEGER NOT NULL DEFAULT 0,red INTEGER NOT NULL DEFAULT 0,played INTEGER NOT NULL DEFAULT 0,rating REAL);
CREATE INDEX IF NOT EXISTS idx_player_match_log ON player_match_log(player_id,season);
CREATE TABLE IF NOT EXISTS player_attr_archive(id INTEGER PRIMARY KEY AUTOINCREMENT,player_id INTEGER NOT NULL,season INTEGER NOT NULL,level REAL,potential REAL,UNIQUE(player_id,season));
CREATE TABLE IF NOT EXISTS shortlist(player_id INTEGER NOT NULL PRIMARY KEY,added_date TEXT,added_value INTEGER DEFAULT 0,added_knowledge INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS player_training_log(id INTEGER PRIMARY KEY AUTOINCREMENT,player_id INTEGER NOT NULL,attribute_key TEXT NOT NULL,delta INTEGER NOT NULL,activity_key TEXT,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT);
CREATE TABLE IF NOT EXISTS staff_member(id INTEGER PRIMARY KEY AUTOINCREMENT,role TEXT NOT NULL,name TEXT NOT NULL,level INTEGER NOT NULL DEFAULT 1,active INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS club_honours(id INTEGER PRIMARY KEY AUTOINCREMENT,club_id INTEGER NOT NULL,season INTEGER NOT NULL,division INTEGER NOT NULL,kind TEXT NOT NULL,detail TEXT NOT NULL,created_at TEXT);
CREATE TABLE IF NOT EXISTS player_season_archive(id INTEGER PRIMARY KEY AUTOINCREMENT,player_id INTEGER NOT NULL,season INTEGER NOT NULL,club_id INTEGER,matches INTEGER DEFAULT 0,goals INTEGER DEFAULT 0,passes INTEGER DEFAULT 0,assists INTEGER DEFAULT 0,saves INTEGER DEFAULT 0,yellow INTEGER DEFAULT 0,red INTEGER DEFAULT 0,rating REAL,UNIQUE(player_id,season));
CREATE TABLE IF NOT EXISTS player_history(id INTEGER PRIMARY KEY AUTOINCREMENT,player_id INTEGER NOT NULL,season INTEGER NOT NULL,club_id INTEGER,kind TEXT NOT NULL,detail TEXT,created_at TEXT);
'''

def ensure_schema(conn):
    conn.executescript(SCHEMA)
    # Migrations only run after all base tables exist. Le backfill ne tourne QUE quand la colonne vient d'être ajoutée.
    migrations=[
        ('fixture','fixture_type',"ALTER TABLE fixture ADD COLUMN fixture_type TEXT NOT NULL DEFAULT 'championship'",None),
        # Notes propres au futsal : dribble serré, explosivité, placement/rotations.
        ('player','dribble',"ALTER TABLE player ADD COLUMN dribble INTEGER NOT NULL DEFAULT 50",
         "UPDATE player SET dribble=MAX(20,MIN(98,technique+2))"),
        ('player','speed',"ALTER TABLE player ADD COLUMN speed INTEGER NOT NULL DEFAULT 50",
         "UPDATE player SET speed=MAX(20,MIN(98,stamina+1))"),
        ('player','positioning',"ALTER TABLE player ADD COLUMN positioning INTEGER NOT NULL DEFAULT 50",
         "UPDATE player SET positioning=MAX(20,MIN(98,(defense+passing+4)/2))"),
        ('scout_report','accuracy',"ALTER TABLE scout_report ADD COLUMN accuracy REAL NOT NULL DEFAULT 0.60",
         "UPDATE scout_report SET accuracy=0.75 WHERE knowledge>=100"),
    ]
    for table,col,sql,backfill in migrations:
        if not column_exists(conn,table,col):
            conn.execute(sql)
            if backfill: conn.execute(backfill)
    conn.commit()

def init_db(path=None, fresh_universe=False, selected_division=3, identity=None):
    conn=sqlite3.connect(path or ':memory:')
    ensure_schema(conn)
    conn.commit(); conn.close()

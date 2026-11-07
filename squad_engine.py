# -*- coding: utf-8 -*-
"""Gestion d'effectif : garde-fou du club et reconstruction des clubs IA."""
import random


def maintain_minimum_squad(host, conn, minimum=12):
    """Sous 12 joueurs, recrute des libres puis promeut des jeunes."""
    from app import (next_shirt_number, record_player_history, player_level_from_row,
                     player_potential_from_row, random_player_name, set_birth_date,
                     career_year_of, compute_fair_salary, compute_market_value,
                     add_news, queue_manager_message)
    try:
        count=int(conn.execute("SELECT COUNT(*) n FROM player WHERE club_id=1 AND COALESCE(is_free_agent,0)=0").fetchone()["n"] or 0)
        if count>=minimum: return 0
        need=minimum-count; added=[]
        frees=conn.execute("SELECT * FROM player WHERE is_free_agent=1 AND COALESCE(retired,0)=0 ORDER BY market_value DESC LIMIT ?",(need,)).fetchall()
        for p in frees:
            number=next_shirt_number(conn,1)
            conn.execute("UPDATE player SET club_id=1,is_free_agent=0,transfer_listed=0,shirt_number=?,contract_years=MAX(1,contract_years),salary=MAX(1200,salary) WHERE id=?",(number,int(p["id"])))
            record_player_history(conn,int(p["id"]),1,"free","Recrutement d'appoint (effectif minimum)")
            added.append(f"{p['first_name']} {p['last_name']}")
        mods={"Gardien":{"technique":-6,"passing":-3,"finishing":-20,"defense":3,"goalkeeper":22,"stamina":0,"dribble":-12,"speed":-3,"positioning":13},
              "Défenseur":{"technique":-2,"passing":1,"finishing":-9,"defense":13,"goalkeeper":-35,"stamina":5,"dribble":2,"speed":4,"positioning":9},
              "Ailier":{"technique":9,"passing":5,"finishing":4,"defense":-5,"goalkeeper":-40,"stamina":8,"dribble":13,"speed":13,"positioning":4},
              "Pivot":{"technique":3,"passing":-2,"finishing":13,"defense":-4,"goalkeeper":-40,"stamina":2,"dribble":10,"speed":-2,"positioning":8},
              "Universel":{"technique":3,"passing":5,"finishing":2,"defense":2,"goalkeeper":-40,"stamina":5,"dribble":6,"speed":6,"positioning":6}}
        while len(added)<need:
            division=int(conn.execute("SELECT division FROM club WHERE id=1").fetchone()["division"] or 6)
            pos=random.choice(("Défenseur","Ailier","Pivot","Universel","Gardien"))
            age=random.randint(17,20)
            base={1:72,2:66,3:60,4:54,5:48,6:42}.get(division,45)*0.82
            attrs={k:max(15,min(95,int(round(random.gauss(base+off,6))))) for k,off in mods[pos].items()}
            probe=dict(attrs); probe["position"]=pos
            level=player_level_from_row(probe); potential=player_potential_from_row({**probe,"age":age})
            salary=compute_fair_salary(level,division,age,potential)
            club=conn.execute("SELECT reputation FROM club WHERE id=1").fetchone()
            value=compute_market_value(level,age,potential,pos,division,int(club["reputation"] or 20),contract_years=2)
            first,last,nat=random_player_name()
            number=next_shirt_number(conn,1)
            conn.execute("""INSERT INTO player(club_id,first_name,last_name,age,position,technique,passing,finishing,defense,goalkeeper,stamina,dribble,speed,positioning,condition,morale,nationality,salary,contract_years,market_value,is_free_agent,shirt_number)
                            VALUES(1,?,?,?,?,?,?,?,?,?,?,?,?,?,90,65,?,?,2,?,0,?)""",
                         (first,last,age,pos,attrs["technique"],attrs["passing"],attrs["finishing"],attrs["defense"],attrs["goalkeeper"],attrs["stamina"],attrs["dribble"],attrs["speed"],attrs["positioning"],nat,salary,value,number))
            pid=int(conn.execute("SELECT last_insert_rowid() id").fetchone()["id"])
            set_birth_date(conn,pid,age,career_year_of(conn))
            record_player_history(conn,pid,1,"free","Formation : jeune promu pour compléter l'effectif")
            added.append(f"{first} {last}")
        if added:
            body=f"Effectif complété automatiquement ({len(added)} arrivée(s)) : {', '.join(added)}. Le club ne peut pas rester sous {minimum} joueurs."
            add_news(conn,"Effectif",body)
            try: queue_manager_message(conn,"club_news","Effectif complété",body,host._current_date(conn),host._current_date(conn),{},is_read=True,ready=True)
            except Exception: pass
        return len(added)
    except Exception as exc:
        host.log_error("maintain_minimum_squad",exc); return 0


def ensure_ai_squads(host, conn, minimum=11):
    """Complete IMMEDIATEMENT les clubs IA sous le minimum (cloture de saison).

    Les fins de contrat videm les effectifs par vagues : attendre le lundi
    suivant laissait des clubs a 9 joueurs au coup d'envoi. Cette passe signe
    des libres, deux par club et par tour, sans limite hebdomadaire.
    """
    from app import next_shirt_number, record_player_history
    from ai_scouting import rank_free_agents
    from ai_finance import can_afford
    try:
        signed=0
        for _round in range(10):
            moved=0
            clubs=conn.execute("SELECT id,name,budget,reputation,division,profile FROM club WHERE id<>1").fetchall()
            for cl in clubs:
                cid=int(cl["id"])
                count=int(conn.execute(
                    "SELECT COUNT(*) n FROM player WHERE club_id=? AND COALESCE(is_free_agent,0)=0",
                    (cid,)).fetchone()["n"] or 0)
                if count>=minimum: continue
                need=min(2,minimum-count)
                ranked=rank_free_agents(conn,cl,"",pool=12,known=4)
                added=0
                for item in ranked:
                    if added>=need: break
                    p=item["player"]
                    # Effectif minimum : un club ne peut pas rester a 9 joueurs.
                    # Le board accepte un effort (tresorerie et ratio salarial)
                    # plutot que de laisser le club incapable d'aligner cinq.
                    number=next_shirt_number(conn,cid)
                    conn.execute(
                        """UPDATE player SET club_id=?,is_free_agent=0,free_agent_since='',transfer_listed=0,shirt_number=?,
                                             contract_years=MAX(2,contract_years),loan_from_club=0,
                                             loan_until_season=0,loan_promise='' WHERE id=?""",
                        (cid,number,int(p["id"])))
                    record_player_history(conn,int(p["id"]),cid,"free",f"Recrutement de fin de saison ({cl['name']})")
                    signed+=1; moved+=1; added+=1
            if not moved: break
        return signed
    except Exception as exc:
        host.log_error("ensure_ai_squads",exc)
        return 0


def rebuild_ai_squads(host, conn, current_iso_date):
    """Le lundi, les clubs IA sous 11 joueurs signent des libres (budget vérifié)."""
    from app import (parse_iso, next_shirt_number, record_player_history, ensure_free_agents)
    from ai_scouting import rank_free_agents
    from ai_finance import can_afford
    try:
        if parse_iso(current_iso_date).weekday()!=0: return 0
        signed=0
        clubs=conn.execute("SELECT id,name,budget,reputation,division,profile FROM club WHERE id<>1 AND budget>0 ORDER BY RANDOM()").fetchall()
        for cl in clubs:
            if signed>=4: break
            count=int(conn.execute("SELECT COUNT(*) n FROM player WHERE club_id=? AND COALESCE(is_free_agent,0)=0",(int(cl["id"]),)).fetchone()["n"] or 0)
            if count>=11: continue
            need=min(2,11-count)
            ranked=rank_free_agents(conn,cl,current_iso_date,pool=12,known=4)
            added=0
            for item in ranked:
                if added>=need: break
                p=item["player"]
                _salary=int(p["salary"] or 0)
                # Un club sous 11 doit se renforcer : le ratio salarial ne doit
                # pas le condamner à jouer à court d'effectif.
                if int(cl["budget"] or 0) < 0: continue
                number=next_shirt_number(conn,int(cl["id"]))
                conn.execute("UPDATE player SET club_id=?,is_free_agent=0,free_agent_since='',transfer_listed=0,shirt_number=?,contract_years=MAX(1,contract_years) WHERE id=?",(int(cl["id"]),number,int(p["id"])))
                record_player_history(conn,int(p["id"]),int(cl["id"]),"free",f"Recrutement d'appoint ({cl['name']})")
                signed+=1; added+=1
        try: ensure_free_agents(conn)
        except Exception: pass
        return signed
    except Exception as exc:
        host.log_error("ai_squad_rebuild",exc); return 0

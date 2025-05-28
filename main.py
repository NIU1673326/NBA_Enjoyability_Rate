import os
import json
from nba_api.stats.endpoints import ScoreboardV2, BoxScoreTraditionalV2, PlayByPlayV2
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import time
from flask import Flask
from threading import Thread

partits_dir = "nba_json_partits"
jugadors_dir = "nba_json_jugadors"
pbp_dir = "nba_json_playbyplay"
db_dir = "Enjoyability_Index_Database.txt"
output_path = "partits_del_dia.json"

os.makedirs(partits_dir, exist_ok=True)
os.makedirs(jugadors_dir, exist_ok=True)
os.makedirs(pbp_dir, exist_ok=True)



def detectar_local_visitant(game_id):
    try:
        # Carrega play-by-play
        with open(os.path.join(pbp_dir, f"{game_id}_pbp.json"), encoding="utf-8") as f:
            accions = json.load(f)

        # Carrega info d'equips
        with open(os.path.join(partits_dir, f"{game_id}.json"), encoding="utf-8") as f:
            equips = json.load(f)

        equips_ids = [equip["TEAM_ID"] for equip in equips]
        equip_home_id = None
        equip_away_id = None

        for accio in accions:
            marcador = accio.get("SCORE")
            if marcador and (accio.get("HOMEDESCRIPTION") or accio.get("VISITORDESCRIPTION")):
                anotador_id = accio.get("PLAYER1_TEAM_ID")
                if anotador_id:
                    if accio.get("HOMEDESCRIPTION"):
                        equip_home_id = anotador_id
                        equip_away_id = [eid for eid in equips_ids if eid != equip_home_id][0]
                    elif accio.get("VISITORDESCRIPTION"):
                        equip_away_id = anotador_id
                        equip_home_id = [eid for eid in equips_ids if eid != equip_away_id][0]
                    break

        if equip_home_id is None or equip_away_id is None:
            raise ValueError("No s'ha pogut detectar equip local i visitant.")

        local = next(e for e in equips if e["TEAM_ID"] == equip_home_id)
        visitant = next(e for e in equips if e["TEAM_ID"] == equip_away_id)
        return local, visitant
    except Exception as e:
        print(f"[ERROR detecció local/visitant {game_id}]: {e}")
        return None, None

def carregar_game_date(game_id):
    try:
        with open(os.path.join(partits_dir, f"{game_id}.json"), encoding="utf-8") as f:
            data = json.load(f)
            for equip in data:
                if "GAME_DATE" in equip:
                    return equip["GAME_DATE"]  # format 'YYYY-MM-DD'
    except Exception as e:
        print(f"[ERROR] No s'ha pogut obtenir la data per {game_id}: {e}")
    return None

def generar_json_ultims_partits(db_path, output_json_path, n=4):
    try:
        with open(db_path, "r", encoding="utf-8") as f:
            linies = [l.strip() for l in f if "|" in l]

        # Extreure valors
        valors = []
        for l in linies:
            try:
                parts = l.split("|")
                game_id = parts[0].strip()
                index = float(parts[2].strip())
                valors.append((game_id, index))
            except:
                continue

        ultims = valors[-n:]
        tots_scores = [v[1] for v in valors]

        partits = []
        for game_id, index in ultims:
            try:
                with open(os.path.join(partits_dir, f"{game_id}.json"), encoding="utf-8") as f_json:
                    equips = json.load(f_json)

                # Detectar local i visitant
                local, visitant = detectar_local_visitant(game_id)
                nom_local = local.get("TEAM_NAME", "") if local else ""
                nom_visitant = visitant.get("TEAM_NAME", "") if visitant else ""
                data_partit = local.get("GAME_DATE", "") if local else ""
                try:
                    data_partit = datetime.strptime(data_partit, "%Y-%m-%d").strftime("%d/%m/%Y")
                except:
                    pass


                nom_local = local.get("TEAM_NAME", "")
                nom_visitant = visitant.get("TEAM_NAME", "")
                data_bruta = local.get("GAME_DATE", "")
                try:
                    data_partit = datetime.strptime(data_bruta, "%Y-%m-%d").strftime("%d/%m/%Y")
                except:
                    data_partit = data_bruta
            except Exception as e:
                print(f"[ERROR llegint dades del partit {game_id}]: {e}")
                nom_local = ""
                nom_visitant = ""
                data_partit = ""

            percentil = round((sum(1 for v in tots_scores if v < index) / len(tots_scores)) * 10, 1)

            partits.append({
                "game_id": game_id,
                "nota": percentil,
                "data": data_partit,
                "equip_local": nom_local,
                "equip_visitant": nom_visitant
            })

        with open(output_json_path, "w", encoding="utf-8") as f_out:
            json.dump(partits, f_out, indent=2)

        return partits

    except Exception as e:
        print(f"[ERROR general]: {e}")
        return None 

def ordenar_base_per_data():
    temp_output_path = db_dir + ".temp"
    dades = []

    with open(db_dir, "r", encoding="utf-8") as f:
        for linia in f:
            linia = linia.strip()
            if "|" in linia:
                game_id, game_date_str, score = [x.strip() for x in linia.split("|")]
                try:
                    game_date = datetime.strptime(game_date_str, "%Y-%m-%d")
                    dades.append((game_date, game_id, game_date_str, score))
                except:
                    continue
            elif ":" in linia:
                # Format antic: GAME_ID: SCORE
                game_id, score = linia.split(":")
                game_date_str = carregar_game_date(game_id.strip())
                if game_date_str:
                    game_date = datetime.strptime(game_date_str, "%Y-%m-%d")
                    dades.append((game_date, game_id.strip(), game_date_str, score.strip()))

    dades.sort()  # Ordena per data

    with open(temp_output_path, "w", encoding="utf-8") as f:
        for _, game_id, game_date_str, score in dades:
            f.write(f"{game_id} | {game_date_str} | {score}\n")

    os.replace(temp_output_path, db_dir)

def _save_game_data(game_id, dest_dir = partits_dir):
    try:
        box = BoxScoreTraditionalV2(game_id=game_id)
        raw = box.team_stats.get_dict()
        headers = raw["headers"]
        rows = raw["data"]
        if not rows:
            print(f"[INFO] Sense dades d’equip per {game_id}")
            return
        parsed = [dict(zip(headers, row)) for row in rows]
        file_path = os.path.join(dest_dir, f"{game_id}.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(parsed, f, indent=2)
        print(f"[OK] Dades d’equip guardades: {game_id}")
    except Exception as e:
        print(f"[ERROR _save_game_data] {game_id}: {e}")
    time.sleep(0.5)

def _save_player_data(game_id, dest_dir = jugadors_dir):
    try:
        box = BoxScoreTraditionalV2(game_id=game_id)
        raw = box.player_stats.get_dict()
        headers = raw["headers"]
        rows = raw["data"]
        if not rows:
            print(f"[INFO] Sense dades de jugadors per {game_id}")
            return
        parsed = [dict(zip(headers, row)) for row in rows]
        file_path = os.path.join(dest_dir, f"{game_id}_players.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(parsed, f, indent=2)
        print(f"[OK] Dades de jugadors guardades: {game_id}")
    except Exception as e:
        print(f"[ERROR _save_player_data] {game_id}: {e}")
    time.sleep(0.5)

def _save_pbp_data(game_id, dest_dir = pbp_dir):
    try:
        df = PlayByPlayV2(game_id=game_id).get_data_frames()[0]
        data = df.to_dict(orient="records")
        if not data:
            print(f"[INFO] Sense dades de play-by-play per {game_id}")
            return
        file_path = os.path.join(dest_dir, f"{game_id}_pbp.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"[OK] Play-by-play guardat: {game_id}\n")
    except Exception as e:
        print(f"[ERROR _save_pbp_data] {game_id}: {e}")
    time.sleep(0.5)

def analitza_partit(game_id, partits_dir, jugadors_dir, pbp_dir):
    def temps_a_segons(t):
        try:
            minuts, segons = map(int, t.split(":"))
            return minuts * 60 + segons
        except:
            return 9999

    resultat = {
        "game_id": game_id,
        "punts_tot": None,
        "score_diff": None,
        "canvis_avantatge": 0,
        "clutch_game": False,
        "overtimes": 0,
        "remuntada_max": 0,
        "triples_dobles": 0,
        "punts_20": 0, "punts_30": 0, "punts_40": 0, "punts_50": 0, "punts_60": 0, "punts_70+": 0,
        "rebots_10": 0, "rebots_15": 0, "rebots_20": 0, "rebots_25+": 0,
        "assist_10": 0, "assist_15": 0, "assist_20": 0, "assist_25+": 0,
        "rob_3": 0, "rob_5": 0, "rob_8": 0, "rob_10+": 0,
        "tap_3": 0, "tap_5": 0, "tap_8": 0, "tap_10+": 0,
    }

    # PART 1: Diferència de punts
    try:
        with open(os.path.join(partits_dir, f"{game_id}.json"), encoding="utf-8") as f:
            equips = json.load(f)
            pts = [equip["PTS"] for equip in equips]
            resultat["score_diff"] = abs(pts[0] - pts[1])
            resultat["punts_tot"] = abs(pts[0] + pts[1])
    except Exception as e:
        print(f"[ERROR _partits] {game_id}: {e}")
        return resultat

    # PART 2: Jugadors destacats
    try:
        with open(os.path.join(jugadors_dir, f"{game_id}_players.json"), encoding="utf-8") as f:
            jugadors = json.load(f)
            for j in jugadors:
                pts = j.get("PTS") or 0
                reb = j.get("REB") or 0
                ast = j.get("AST") or 0
                stl = j.get("STL") or 0
                blk = j.get("BLK") or 0


                categories_amb_10 = sum(1 for val in [pts, reb, ast, stl, blk] if val >= 10)
                if categories_amb_10 >= 3:
                    resultat["triples_dobles"] += 1

                if pts >= 70: resultat["punts_70+"] += 1
                elif pts >= 60: resultat["punts_60"] += 1
                elif pts >= 50: resultat["punts_50"] += 1
                elif pts >= 40: resultat["punts_40"] += 1
                elif pts >= 30: resultat["punts_30"] += 1
                elif pts >= 20: resultat["punts_20"] += 1

                if reb >= 25: resultat["rebots_25+"] += 1
                elif reb >= 20: resultat["rebots_20"] += 1
                elif reb >= 15: resultat["rebots_15"] += 1
                elif reb >= 10: resultat["rebots_10"] += 1

                if ast >= 25: resultat["assist_25+"] += 1
                elif ast >= 20: resultat["assist_20"] += 1
                elif ast >= 15: resultat["assist_15"] += 1
                elif ast >= 10: resultat["assist_10"] += 1

                if stl >= 10: resultat["rob_10+"] += 1
                elif stl >= 8: resultat["rob_8"] += 1
                elif stl >= 5: resultat["rob_5"] += 1
                elif stl >= 3: resultat["rob_3"] += 1

                if blk >= 10: resultat["tap_10+"] += 1
                elif blk >= 8: resultat["tap_8"] += 1
                elif blk >= 5: resultat["tap_5"] += 1
                elif blk >= 3: resultat["tap_3"] += 1
                
    except Exception as e:
        print(f"[ERROR _players] {game_id}: {e}")

    # PART 3: Play-by-play
    try:
        with open(os.path.join(pbp_dir, f"{game_id}_pbp.json"), encoding="utf-8") as f:
            accions = json.load(f)
        
        lead_history = []
        last_leader = None
        lead_changes = 0
        periods = set()
        max_deficit = 0
        last_score = None

        for accio in accions:
            marcador = accio.get("SCORE")
            periode = accio.get("PERIOD")
            temps = accio.get("PCTIMESTRING")

            if marcador:
                try:
                    home_score, away_score = map(int, marcador.split(" - "))
                    periode = int(periode) if periode else 0
                    periods.add(periode)

                    if home_score > away_score:
                        current_leader = "HOME"
                    elif away_score > home_score:
                        current_leader = "AWAY"
                    else:
                        current_leader = "TIE"

                    if current_leader != "TIE":
                        if last_leader is not None and last_leader != current_leader:
                            lead_changes += 1
                        last_leader = current_leader

                    
                    lead_history.append({
                        "home": home_score,
                        "away": away_score,
                        "periode": periode,
                        "temps": temps
                    })

                    last_score = (home_score, away_score)
                except:
                    continue
            else:
                # Clutch detection fallback
                if last_score and periode and temps and int(periode) >= 4 and temps_a_segons(temps) <= 300:
                    if abs(last_score[0] - last_score[1]) <= 5:
                        resultat["clutch_game"] = True

        resultat["canvis_avantatge"] = lead_changes
        resultat["overtimes"] = max(0, len(periods) - 4)

        # Remuntada real
                # Remuntada real (amb detecció robusta de l'equip local)
        try:
            # Detectar qui és local i visitant a partir de la primera acció amb SCORE vàlid
            equip_home_id = None
            equip_away_id = None
            for accio in accions:
                marcador = accio.get("SCORE")
                if marcador and (accio.get("HOMEDESCRIPTION") or accio.get("VISITORDESCRIPTION")):
                    home_pts, away_pts = map(int, marcador.split(" - "))
                    anotador_id = accio.get("PLAYER1_TEAM_ID")
                    if anotador_id:
                        equips_ids = [equip.get("TEAM_ID") for equip in equips]
                        if accio.get("HOMEDESCRIPTION"):
                            # L'equip que ha anotat és el local → el seu marcador està en primera posició
                            equip_home_id = anotador_id
                            equip_away_id = [eid for eid in equips_ids if eid != equip_home_id][0]
                        elif accio.get("VISITORDESCRIPTION"):
                            # L'equip que ha anotat és el visitant → el seu marcador està en segona posició
                            equip_away_id = anotador_id
                            equip_home_id = [eid for eid in equips_ids if eid != equip_away_id][0]
                        break  # ja tenim la info necessària

            if equip_home_id is None or equip_away_id is None:
                raise ValueError("No s'ha pogut determinar quin equip és local")

            home_team = next(e for e in equips if e["TEAM_ID"] == equip_home_id)
            away_team = next(e for e in equips if e["TEAM_ID"] == equip_away_id)

            home_score = home_team.get("PTS", 0)
            away_score = away_team.get("PTS", 0)
            guanya_home = home_score < away_score  # volem saber si el local va perdre
        except Exception as e:
            print(f"[ERROR _play_by_play detecció equip local] {game_id}: {e}")
            return resultat



        for accio in accions:
            marcador = accio.get("SCORE")
            if not marcador:
                continue
            try:
                home, away = map(int, marcador.split(" - "))
                if guanya_home and home < away:
                    deficit = away - home
                    max_deficit = max(max_deficit, deficit)
                elif not guanya_home and away < home:
                    deficit = home - away
                    max_deficit = max(max_deficit, deficit)
            except:
                continue

        resultat["remuntada_max"] = max_deficit

    except Exception as e:
        print(f"[ERROR _play_by_play] {game_id}: {e}")

    return resultat

def Enjoyability_Index(resultat):
    score = 0

    # Punts totals
    score += resultat["punts_tot"]*2

    # Diferència ajustada
    diff = resultat["score_diff"]
    score -= diff*8

    # Clutch i pròrroga
    if resultat["clutch_game"]:
        score += 50
    score += resultat["overtimes"] * 75

    # Remuntada
    score += resultat["remuntada_max"] * 5

    # Canvis d'avantatge
    score += resultat["canvis_avantatge"]*3

    # Triples dobles
    score += resultat["triples_dobles"] * 25

    # Grans anotacions
    score += resultat["punts_20"] * 5
    score += resultat["punts_30"] * 10
    score += resultat["punts_40"] * 25
    score += resultat["punts_50"] * 75
    score += resultat["punts_60"] * 150
    score += resultat["punts_70+"] * 300

    # Grans rebots
    score += resultat["rebots_10"] * 5
    score += resultat["rebots_15"] * 15
    score += resultat["rebots_20"] * 25
    score += resultat["rebots_25+"] * 50

    # Grans assistències
    score += resultat["assist_10"] * 5
    score += resultat["assist_15"] * 15
    score += resultat["assist_20"] * 25
    score += resultat["assist_25+"] * 50

    # Grans robatoris
    score += resultat["rob_3"] * 5
    score += resultat["rob_5"] * 15
    score += resultat["rob_8"] * 25
    score += resultat["rob_10+"] * 50

    # Grans taps
    score += resultat["tap_3"] * 5
    score += resultat["tap_5"] * 15
    score += resultat["tap_8"] * 25
    score += resultat["tap_10+"] * 50

    return score

def afegeix_i_valora(game_id, score, base_txt_path = db_dir):
    # Comprovar si ja existeix
    if os.path.exists(base_txt_path):
        with open(base_txt_path, "r", encoding="utf-8") as f:
            for linia in f:
                if game_id in linia:
                    print(f"[INFO] El partit {game_id} ja existeix a la base de dades.")
                    return None

    # Obtenir la data
    game_date = carregar_game_date(game_id)
    if not game_date:
        game_date = "1900-01-01"  # valor per defecte si no es troba

    # Escriure
    with open(base_txt_path, "a", encoding="utf-8") as f:
        f.write(f"{game_id} | {game_date} | {score}\n")

    print(f"✔ El partit {game_id} s’ha afegit a la base de dades.")
    return score

def completa_game_date_si_cal(game_id, partits_dir, game_date_obj):
    path_equips = os.path.join(partits_dir, f"{game_id}.json")

    try:
        # Carregar dades equips
        with open(path_equips, encoding="utf-8") as f:
            equips = json.load(f)

        # Si ja tenen GAME_DATE, no cal fer res
        if "GAME_DATE" in equips[0]:
            return

        # Injectar la data passada (objecte datetime → string)
        game_date_str = game_date_obj.strftime("%Y-%m-%d")
        for equip in equips:
            equip["GAME_DATE"] = game_date_str

        # Desa el fitxer modificat
        with open(path_equips, "w", encoding="utf-8") as f:
            json.dump(equips, f, indent=2)


    except Exception as e:
        print(f"[ERROR afegint GAME_DATE] {game_id}: {e}")

# Obtenir la data d'ahir
dia_now = datetime.now(ZoneInfo("US/Eastern"))

# Data d’ahir en Eastern Time
dia_et = dia_now - timedelta(days=4)
dia_str = dia_et.strftime("%m/%d/%Y")


# Demanar partits de la data
scoreboard = ScoreboardV2(game_date=dia_str)
games = scoreboard.game_header.get_dict()["data"]

# Obtenir els GAME_IDs
game_ids_dia = [game[2] for game in games]  # index 2 = GAME_ID

for game_id in game_ids_dia:
    print(game_id)
    _save_game_data(game_id)
    _save_player_data(game_id)
    _save_pbp_data(game_id)
    completa_game_date_si_cal(game_id, partits_dir, dia_et)
    resum = analitza_partit(game_id, partits_dir, jugadors_dir, pbp_dir)
    score = Enjoyability_Index(resum)
    print(f"{game_id}: {score}")
    afegeix_i_valora(game_id, score)

ordenar_base_per_data()
generar_json_ultims_partits(db_dir, output_path)

from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "Enjoyability script is running!"

def run():
    app.run(host='0.0.0.0', port=8080)

# Llançar Flask en segon pla
t = Thread(target=run)
t.start()

import push_to_github

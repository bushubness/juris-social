#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, json, requests

API_KEY  = os.environ["JUDILIBRE_API_KEY"]
API_BASE = "https://sandbox-api.piste.gouv.fr/cassation/judilibre/v1.0"
DATA_FILE = "data.json"
MAX_TOTAL = 200

def fetch_arrets(batch=30):
    headers = {"accept": "application/json", "KeyId": API_KEY}
    params  = {"chamber": "soc", "publication": "b", "order": "desc", "batch": batch}
    r = requests.get(f"{API_BASE}/search", headers=headers, params=params, timeout=20)
    r.raise_for_status()
    return r.json().get("results", [])

def to_fiche(a):
    zones = a.get("zones", {}) or {}
    def zone(key):
        val = zones.get(key)
        if isinstance(val, list): return " ".join(val).strip()
        if isinstance(val, str):  return val.strip()
        return ""
    texte    = a.get("text", "") or ""
    faits    = zone("expose_litige") or zone("faits") or texte[:400].strip()
    proc     = zone("procedure") or ""
    moyens   = zone("moyens") or ""
    disp     = zone("dispositif") or zone("decision") or ""
    solution = (a.get("solution") or "").lower()
    if "cassation" in solution: label = "Cassation"
    elif "rejet"   in solution: label = "Rejet"
    else:                       label = solution.capitalize() or "Décision"
    decision = f"{label}. {disp}" if disp else label
    numero   = a.get("number") or a.get("id", "")
    date     = (a.get("decision_date") or "")[:10]
    titre    = a.get("summary") or a.get("title") or numero
    url      = f"https://www.courdecassation.fr/decision/{a.get('id','')}"
    return {
        "id": numero, "date": date, "chambre": "Chambre sociale",
        "formation": a.get("formation") or "Chambre sociale",
        "numero_pourvoi": numero, "titre": titre,
        "faits": faits or "—", "procedure": proc or "—",
        "moyens": moyens or "—", "decision": decision or "—", "url": url,
    }

def load_data():
    try:
        with open(DATA_FILE, encoding="utf-8") as f: return json.load(f)
    except: return []

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def main():
    print("[info] Récupération des arrêts Judilibre…")
    raw = fetch_arrets(30)
    print(f"[info] {len(raw)} arrêts récupérés")
    existing     = load_data()
    existing_ids = {a["id"] for a in existing}
    new_fiches   = []
    for a in raw:
        fiche = to_fiche(a)
        if fiche["id"] and fiche["id"] not in existing_ids:
            new_fiches.append(fiche)
            print(f"  + {fiche['date']} — {fiche['titre'][:70]}")
    if not new_fiches:
        print("[info] Aucun nouvel arrêt."); return
    combined = sorted(new_fiches + existing, key=lambda x: x["date"], reverse=True)[:MAX_TOTAL]
    save_data(combined)
    print(f"[ok] {len(new_fiches)} nouveaux ajoutés, {len(combined)} au total.")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Robot de mise à jour automatique — Juris Social
Récupère les nouveaux arrêts publiés au Bulletin (chambre sociale)
via l'API Judilibre (PISTE sandbox), les ajoute à data.json,
et le site se met à jour tout seul via GitHub Pages.
"""

import os
import json
import datetime
import requests

CLIENT_ID     = os.environ["PISTE_CLIENT_ID"]
CLIENT_SECRET = os.environ["PISTE_CLIENT_SECRET"]

OAUTH_URL = "https://sandbox-oauth.piste.gouv.fr/api/oauth/token"
API_BASE  = "https://sandbox-api.piste.gouv.fr/cassation/judilibre/v1.0"

DATA_FILE = "data.json"
MAX_TOTAL = 200

def get_token():
    r = requests.post(OAUTH_URL, data={
        "grant_type":    "client_credentials",
        "client_id":     CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope":         "openid",
    }, timeout=15)
    r.raise_for_status()
    return r.json()["access_token"]

def fetch_arrets(token, batch=30):
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "chamber":     "soc",
        "publication": "b",
        "order":       "desc",
        "batch":       batch,
        "resolve_references": "true",
    }
    r = requests.get(f"{API_BASE}/search", headers=headers,
                     params=params, timeout=20)
    r.raise_for_status()
    return r.json().get("results", [])

def to_fiche(a):
    zones = a.get("zones", {}) or {}

    def zone(key, fallback=""):
        val = zones.get(key)
        if isinstance(val, list):
            return " ".join(val).strip()
        if isinstance(val, str):
            return val.strip()
        return fallback

    texte = a.get("text", "") or ""
    apercu = texte[:400].strip() if texte else ""

    decision_txt = zone("dispositif") or zone("decision") or ""
    faits_txt    = zone("expose_litige") or zone("faits") or apercu
    proc_txt     = zone("procedure") or ""
    moyens_txt   = zone("moyens") or ""

    solution = (a.get("solution") or "").lower()
    if "cassation" in solution:
        dec_label = "Cassation"
    elif "rejet" in solution:
        dec_label = "Rejet"
    else:
        dec_label = solution.capitalize() or "Décision"

    decision_full = f"{dec_label}. {decision_txt}" if decision_txt else dec_label

    numero = a.get("number") or a.get("id", "")
    date   = (a.get("decision_date") or "")[:10]
    titre  = a.get("summary") or a.get("title") or numero
    url    = f"https://www.courdecassation.fr/decision/{a.get('id','')}"

    return {
        "id":             numero,
        "date":           date,
        "chambre":        "Chambre sociale",
        "formation":      a.get("formation") or "Chambre sociale",
        "numero_pourvoi": numero,
        "titre":          titre,
        "faits":          faits_txt or "—",
        "procedure":      proc_txt  or "—",
        "moyens":         moyens_txt or "—",
        "decision":       decision_full or "—",
        "url":            url,
    }

def load_data():
    try:
        with open(DATA_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def main():
    print("[info] Authentification PISTE…")
    token = get_token()
    print("[info] Token OK — récupération des arrêts…")

    raw = fetch_arrets(token, batch=30)
    print(f"[info] {len(raw)} arrêts récupérés depuis Judilibre")

    existing = load_data()
    existing_ids = {a["id"] for a in existing}

    new_fiches = []
    for a in raw:
        fiche = to_fiche(a)
        if fiche["id"] and fiche["id"] not in existing_ids:
            new_fiches.append(fiche)
            print(f"  + {fiche['date']} — {fiche['titre'][:70]}")

    if not new_fiches:
        print("[info] Aucun nouvel arrêt, data.json inchangé.")
        return

    combined = new_fiches + existing
    combined.sort(key=lambda x: x["date"], reverse=True)
    combined = combined[:MAX_TOTAL]

    save_data(combined)
    print(f"[ok] data.json mis à jour : {len(new_fiches)} nouveaux, "
          f"{len(combined)} au total.")

if __name__ == "__main__":
    main()

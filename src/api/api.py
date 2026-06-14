"""
SteelSight — FastAPI Backend
Serves all data endpoints for the dashboard.

HOW TO RUN:
    uvicorn src.api.api:app --reload --port 8000
"""

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import numpy as np
import os
from typing import Optional

app = FastAPI(title="SteelSight API", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])

# ── Data loaders ───────────────────────────────────────────────────────────────
def load(path):
    if os.path.exists(path):
        return pd.read_csv(path)
    return pd.DataFrame()

def get_mills():     return load("data/mills.csv")
def get_scores():    return load("data/activity_scores.csv")
def get_signal():    return load("data/monthly_signal.csv")
def get_wsa():       return load("data/wsa_steel_output.csv")
def get_iron_ore():  return load("data/financial/iron_ore_prices.csv")
def get_hrc():       return load("data/financial/hrc_steel_prices.csv")
def get_fin_corr():  return load("data/financial/financial_correlation.csv")

# ── Routes ─────────────────────────────────────────────────────────────────────
@app.get("/")
def root(): return {"service": "SteelSight API", "version": "2.0.0", "docs": "/docs"}

@app.get("/api/stats")
def stats():
    scores  = get_scores()
    signal  = get_signal()
    iron    = get_iron_ore()
    hrc     = get_hrc()

    if scores.empty:
        return {"total_mills":45,"active_mills":0,"pct_active":0,"mom_change":0,
                "latest_iron_ore":0,"iron_ore_change":0,"latest_hrc":0,"hrc_change":0,
                "latest_year":2024,"latest_month":12}

    latest = scores.sort_values(["year","month"]).iloc[-1]
    latest_data = scores[(scores.year==latest.year)&(scores.month==latest.month)]
    active = int((latest_data.prediction=="ACTIVE").sum())
    total  = int(len(latest_data))
    pct    = round(active/total*100,1) if total else 0

    mom_change = 0
    if not signal.empty and len(signal) >= 2:
        mom_change = round(float(signal.iloc[-1]["pct_active"]) -
                           float(signal.iloc[-2]["pct_active"]), 1)

    latest_io, io_chg = 0, 0
    if not iron.empty and len(iron) >= 2:
        latest_io = round(float(iron.iloc[-1]["iron_ore_usd"]), 1)
        io_chg    = round((float(iron.iloc[-1]["iron_ore_usd"]) -
                           float(iron.iloc[-2]["iron_ore_usd"])) /
                           float(iron.iloc[-2]["iron_ore_usd"]) * 100, 1)

    latest_hrc, hrc_chg = 0, 0
    if not hrc.empty and len(hrc) >= 2:
        latest_hrc = round(float(hrc.iloc[-1]["hrc_steel_usd"]), 0)
        hrc_chg    = round((float(hrc.iloc[-1]["hrc_steel_usd"]) -
                            float(hrc.iloc[-2]["hrc_steel_usd"])) /
                            float(hrc.iloc[-2]["hrc_steel_usd"]) * 100, 1)

    return {
        "total_mills":    total,
        "active_mills":   active,
        "pct_active":     pct,
        "mom_change":     mom_change,
        "latest_iron_ore":latest_io,
        "iron_ore_change":io_chg,
        "latest_hrc":     latest_hrc,
        "hrc_change":     hrc_chg,
        "latest_year":    int(latest.year),
        "latest_month":   int(latest.month),
    }


@app.get("/api/mills")
def mills():
    mills_df  = get_mills()
    scores_df = get_scores()
    if scores_df.empty: return mills_df.to_dict(orient="records")

    latest = (scores_df.sort_values(["year","month"],ascending=False)
                        .groupby("mill_id").first().reset_index()
                        .rename(columns={"heat_score":"latest_score",
                                          "prediction":"latest_status"}))
    result = pd.merge(mills_df,
                       latest[["mill_id","latest_score","latest_status","year","month"]],
                       on="mill_id", how="left")
    return result.fillna(0).to_dict(orient="records")


@app.get("/api/mills/{mill_id}")
def mill_detail(mill_id: int):
    mills_df  = get_mills()
    scores_df = get_scores()
    row = mills_df[mills_df.mill_id==mill_id]
    if row.empty: raise HTTPException(404, "Mill not found")
    hist = scores_df[scores_df.mill_id==mill_id].sort_values(["year","month"])
    return {"mill": row.iloc[0].to_dict(),
            "history": hist.to_dict(orient="records")}


@app.get("/api/signal")
def signal(start_year: Optional[int]=2019, end_year: Optional[int]=2024):
    df = get_signal()
    if df.empty: return []
    df = df[(df.year>=start_year)&(df.year<=end_year)]
    wsa = get_wsa()
    if not wsa.empty:
        df = pd.merge(df, wsa[["year","month","china_output_mt"]],
                       on=["year","month"], how="left")
    return df.fillna("").to_dict(orient="records")


@app.get("/api/financial")
def financial():
    signal = get_signal()
    iron   = get_iron_ore()
    hrc    = get_hrc()
    if signal.empty: return []
    merged = signal[["year","month","pct_active","mean_heat"]].copy()
    if not iron.empty:
        merged = pd.merge(merged, iron[["year","month","iron_ore_usd"]],
                           on=["year","month"], how="left")
    if not hrc.empty:
        merged = pd.merge(merged, hrc[["year","month","hrc_steel_usd"]],
                           on=["year","month"], how="left")
    return merged.fillna(0).to_dict(orient="records")


@app.get("/api/financial/correlation")
def financial_correlation():
    df = get_fin_corr()
    if df.empty: return []
    return df.to_dict(orient="records")

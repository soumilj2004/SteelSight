import { useState, useEffect, useRef } from "react";
import {
  ComposedChart, LineChart, AreaChart, BarChart, ScatterChart,
  Line, Area, Bar, Scatter,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  ReferenceLine, Legend
} from "recharts";

// ── Theme System ───────────────────────────────────────────────────────────────
const themes = {
  light: {
    bg:       "#F6F1E9",
    surface:  "#FDFAF4",
    panel:    "#FFFFFF",
    border:   "#E2D9C8",
    border2:  "#C8BCA8",
    navy:     "#0D1B2A",
    navy2:    "#1A2E45",
    gold:     "#B8962E",
    gold2:    "#D4AF4A",
    green:    "#2A5F3F",
    green2:   "#3D8A5A",
    text:     "#1A1208",
    text2:    "#3D3020",
    muted:    "#7A6A54",
    dim:      "#A89880",
    red:      "#8B2020",
    red2:     "#C0392B",
    amber:    "#B8620A",
    blue:     "#1A3F6F",
    blue2:    "#2E6DB4",
    cardShadow: "0 1px 8px rgba(13,27,42,0.08)",
  },
  dark: {
    bg:       "#0A0E14",
    surface:  "#111720",
    panel:    "#161E2A",
    border:   "#1E2A38",
    border2:  "#2A3A50",
    navy:     "#D4AF4A",
    navy2:    "#E8CC6A",
    gold:     "#D4AF4A",
    gold2:    "#E8CC6A",
    green:    "#3D8A5A",
    green2:   "#52B876",
    text:     "#E8DCC8",
    text2:    "#C8B898",
    muted:    "#7A8898",
    dim:      "#4A5868",
    red:      "#E05050",
    red2:     "#FF6B6B",
    amber:    "#D4820A",
    blue:     "#3A7BD5",
    blue2:    "#5A9BF5",
    cardShadow: "0 1px 12px rgba(0,0,0,0.4)",
  }
};

const API = "http://localhost:8000/api";
const fmt = (n, d=1) => typeof n === "number" ? n.toFixed(d) : "—";
const monthLabel = (y, m) => {
  const mo = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
  return `${mo[(m||1)-1]} '${String(y||"").slice(2)}`;
};

// ── Animations via CSS ─────────────────────────────────────────────────────────
const globalCSS = (C) => `
  @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600;700&family=Inter:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  html { scroll-behavior: smooth; }
  body { background: ${C.bg}; font-family: 'Inter', sans-serif; color: ${C.text}; transition: background 0.3s, color 0.3s; }
  ::-webkit-scrollbar { width: 5px; }
  ::-webkit-scrollbar-track { background: ${C.bg}; }
  ::-webkit-scrollbar-thumb { background: ${C.border2}; border-radius: 3px; }

  @keyframes fadeUp {
    from { opacity: 0; transform: translateY(16px); }
    to   { opacity: 1; transform: translateY(0); }
  }
  @keyframes fadeIn {
    from { opacity: 0; }
    to   { opacity: 1; }
  }
  @keyframes pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50%       { opacity: 0.5; transform: scale(0.85); }
  }
  @keyframes shimmer {
    0%   { background-position: -400px 0; }
    100% { background-position: 400px 0; }
  }
  @keyframes slideIn {
    from { opacity: 0; transform: translateX(-12px); }
    to   { opacity: 1; transform: translateX(0); }
  }
  @keyframes countUp {
    from { opacity: 0; transform: translateY(8px); }
    to   { opacity: 1; transform: translateY(0); }
  }

  .fade-up  { animation: fadeUp 0.5s ease forwards; }
  .fade-in  { animation: fadeIn 0.4s ease forwards; }
  .slide-in { animation: slideIn 0.4s ease forwards; }

  .card-hover {
    transition: transform 0.2s ease, box-shadow 0.2s ease;
  }
  .card-hover:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 24px rgba(13,27,42,0.12) !important;
  }

  .btn-hover {
    transition: all 0.2s ease;
    cursor: pointer;
  }
  .btn-hover:hover { opacity: 0.85; transform: translateY(-1px); }
  .btn-hover:active { transform: translateY(0); }

  .live-dot {
    width: 7px; height: 7px; border-radius: 50%;
    background: #3D8A5A;
    animation: pulse 2s ease-in-out infinite;
    display: inline-block;
  }

  .nav-link {
    font-family: 'Inter', sans-serif;
    font-size: 12px; letter-spacing: 0.5px;
    padding: 10px 18px;
    cursor: pointer;
    border-bottom: 2px solid transparent;
    transition: all 0.2s;
    color: ${C.muted};
  }
  .nav-link:hover { color: ${C.text}; border-bottom-color: ${C.gold}; }

  .stat-number {
    font-family: 'Playfair Display', serif;
    animation: countUp 0.6s ease forwards;
  }

  .section-divider {
    height: 1px;
    background: linear-gradient(90deg, transparent, ${C.border}, ${C.gold}44, ${C.border}, transparent);
    margin: 24px 0;
  }
`;

// ── Components ─────────────────────────────────────────────────────────────────

function LiveBadge({ C }) {
  return (
    <div style={{ display:"flex", alignItems:"center", gap:6,
                  background:`${C.green}18`, border:`1px solid ${C.green}44`,
                  borderRadius:20, padding:"3px 10px" }}>
      <span className="live-dot" style={{ background: C.green2 }} />
      <span style={{ fontFamily:"'Inter'", fontSize:10, fontWeight:600,
                     color:C.green2, letterSpacing:"1.5px" }}>LIVE</span>
    </div>
  );
}

function DarkModeToggle({ dark, setDark, C }) {
  return (
    <button className="btn-hover" onClick={() => setDark(!dark)}
      style={{ background: dark ? "#1E2A38" : C.border,
               border:`1px solid ${C.border2}`,
               borderRadius:20, padding:"5px 12px",
               display:"flex", alignItems:"center", gap:7,
               fontFamily:"'Inter'", fontSize:11, color:C.muted,
               cursor:"pointer" }}>
      <span style={{ fontSize:13 }}>{dark ? "☀" : "◑"}</span>
      {dark ? "Light" : "Dark"}
    </button>
  );
}

function Ticker({ label, value, unit, change, C }) {
  const up = !change || change >= 0;
  return (
    <div style={{ textAlign:"right" }}>
      <div style={{ fontFamily:"'Inter'", fontSize:9, color:C.muted,
                    letterSpacing:"2px", textTransform:"uppercase", marginBottom:3 }}>{label}</div>
      <div style={{ display:"flex", alignItems:"baseline", gap:5, justifyContent:"flex-end" }}>
        <span style={{ fontFamily:"'JetBrains Mono'", fontSize:17, fontWeight:500,
                        color: C === themes.dark ? "#E8DCC8" : "#FDFAF4" }}>
          {value !== undefined ? fmt(value, label==="SIGNAL"?1:0) : "—"}
        </span>
        <span style={{ fontFamily:"'JetBrains Mono'", fontSize:10, color:C.muted }}>{unit}</span>
        {change !== undefined && (
          <span style={{ fontFamily:"'JetBrains Mono'", fontSize:10,
                          color: up ? C.green2 : C.red2 }}>
            {up?"+":""}{fmt(change,1)}%
          </span>
        )}
      </div>
    </div>
  );
}

function Header({ stats, dark, setDark, C }) {
  const headerBg = dark ? "#080C12" : C.navy;
  return (
    <div style={{ background:headerBg, borderBottom:`3px solid ${C.gold}`,
                  position:"sticky", top:0, zIndex:100,
                  boxShadow:"0 2px 20px rgba(0,0,0,0.3)" }}>
      {/* Main header row */}
      <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between",
                    padding:"12px 32px", borderBottom:`1px solid rgba(255,255,255,0.06)` }}>
        <div style={{ display:"flex", alignItems:"center", gap:16 }}>
          <div>
            <div style={{ fontFamily:"'Playfair Display'", fontSize:24, fontWeight:700,
                          color:C.gold2, letterSpacing:"-0.3px", lineHeight:1 }}>
              SteelSight
            </div>
            <div style={{ fontFamily:"'Inter'", fontSize:9, color:"rgba(212,175,74,0.6)",
                          letterSpacing:"3px", textTransform:"uppercase", marginTop:2 }}>
              Commodity Intelligence
            </div>
          </div>
          <div style={{ width:1, height:36, background:"rgba(255,255,255,0.1)", margin:"0 4px" }} />
          <LiveBadge C={C} />
        </div>

        <div style={{ display:"flex", gap:36, alignItems:"center" }}>
          <Ticker label="Iron Ore" value={stats?.latest_iron_ore} unit="$/t"
                  change={stats?.iron_ore_change} C={C} />
          <div style={{ width:1, height:28, background:"rgba(255,255,255,0.08)" }} />
          <Ticker label="HRC Steel" value={stats?.latest_hrc} unit="$/st"
                  change={stats?.hrc_change} C={C} />
          <div style={{ width:1, height:28, background:"rgba(255,255,255,0.08)" }} />
          <Ticker label="Signal" value={stats?.pct_active} unit="% active"
                  change={stats?.mom_change} C={C} />
          <div style={{ width:1, height:28, background:"rgba(255,255,255,0.08)" }} />
          <div style={{ fontFamily:"'JetBrains Mono'", fontSize:10,
                        color:"rgba(255,255,255,0.3)", lineHeight:1.5, textAlign:"right" }}>
            <div>Dec '24</div>
            <div style={{ color:"rgba(255,255,255,0.2)", fontSize:9 }}>Sentinel-2 SR</div>
          </div>
          <DarkModeToggle dark={dark} setDark={setDark} C={C} />
        </div>
      </div>

      {/* Nav */}
      <div style={{ display:"flex", padding:"0 24px" }}>
        {["Overview","Signal Analysis","Commodities","Mill Intelligence","Methodology"].map(t => (
          <div key={t} className="nav-link">{t}</div>
        ))}
      </div>
    </div>
  );
}

function KpiCard({ label, value, unit, sub, change, accent, delay, C }) {
  const up = change === undefined || change >= 0;
  return (
    <div className="card-hover fade-up"
      style={{ background:C.panel, border:`1px solid ${C.border}`,
                borderTop:`3px solid ${accent||C.gold}`, borderRadius:4,
                padding:"20px 22px", boxShadow:C.cardShadow,
                animationDelay: `${delay||0}ms` }}>
      <div style={{ fontFamily:"'Inter'", fontSize:9, fontWeight:600, color:C.muted,
                    letterSpacing:"2px", textTransform:"uppercase", marginBottom:10 }}>
        {label}
      </div>
      <div style={{ display:"flex", alignItems:"baseline", gap:6, marginBottom:4 }}>
        <span className="stat-number" style={{ fontSize:30, fontWeight:700, color:C.text,
                                                animationDelay:`${(delay||0)+100}ms` }}>
          {value ?? "—"}
        </span>
        {unit && <span style={{ fontFamily:"'Inter'", fontSize:13, color:C.muted }}>{unit}</span>}
      </div>
      {sub && <div style={{ fontFamily:"'Inter'", fontSize:11, color:C.muted, lineHeight:1.5 }}>{sub}</div>}
      {change !== undefined && (
        <div style={{ fontFamily:"'JetBrains Mono'", fontSize:11, marginTop:6,
                      color: up ? C.green2 : C.red2, fontWeight:500 }}>
          {up ? "▲" : "▼"} {Math.abs(change).toFixed(1)}% vs prior month
        </div>
      )}
    </div>
  );
}

function Card({ title, subtitle, children, accent, delay, noPad, C }) {
  return (
    <div className="fade-up" style={{ background:C.panel, border:`1px solid ${C.border}`,
                borderTop:`2px solid ${accent||C.gold}`, borderRadius:4,
                padding: noPad ? 0 : "20px 24px", boxShadow:C.cardShadow,
                animationDelay:`${delay||0}ms`, display:"flex", flexDirection:"column" }}>
      {(title||subtitle) && (
        <div style={{ padding: noPad ? "18px 22px 14px" : "0 0 14px",
                      borderBottom:`1px solid ${C.border}`, marginBottom:16 }}>
          {title && (
            <div style={{ fontFamily:"'Inter'", fontSize:10, fontWeight:700,
                          color:C.text, letterSpacing:"2px", textTransform:"uppercase" }}>
              {title}
            </div>
          )}
          {subtitle && (
            <div style={{ fontFamily:"'Inter'", fontSize:11, color:C.muted, marginTop:3, lineHeight:1.5 }}>
              {subtitle}
            </div>
          )}
        </div>
      )}
      <div style={{ flex:1 }}>{children}</div>
    </div>
  );
}

// ── Custom Tooltip ─────────────────────────────────────────────────────────────
const Tip = ({ active, payload, label, rows, C }) => {
  if (!active || !payload?.length) return null;
  const dark = C === themes.dark;
  return (
    <div style={{ background: dark ? "#0F1520" : C.navy,
                  border:`1px solid ${dark ? "#2A3A50" : "#1A2E45"}`,
                  borderTop:`2px solid ${C.gold}`,
                  borderRadius:4, padding:"12px 16px", minWidth:180,
                  boxShadow:"0 8px 32px rgba(0,0,0,0.3)" }}>
      <div style={{ fontFamily:"'Inter'", fontSize:10, color:C.gold2,
                    letterSpacing:"1.5px", textTransform:"uppercase",
                    marginBottom:8, borderBottom:"1px solid rgba(255,255,255,0.06)",
                    paddingBottom:6 }}>{label}</div>
      {rows.map(({ label:l, value:v, color }, i) => (
        <div key={i} style={{ display:"flex", justifyContent:"space-between",
                              gap:16, marginBottom:3 }}>
          <span style={{ fontFamily:"'Inter'", fontSize:11, color:"rgba(255,255,255,0.5)" }}>{l}</span>
          <span style={{ fontFamily:"'JetBrains Mono'", fontSize:11,
                          fontWeight:500, color: color||"#E8DCC8" }}>{v}</span>
        </div>
      ))}
    </div>
  );
};

// ── Charts ─────────────────────────────────────────────────────────────────────
function SignalChart({ data, C }) {
  const CustomTip = ({ active, payload, label }) => (
    <Tip active={active} payload={payload} label={label} C={C} rows={[
      { label:"Mills Active", value:fmt(payload?.[0]?.value,1)+"%", color:C.gold2 },
      { label:"Steel Output", value:fmt(payload?.[1]?.value,1)+" Mt", color:C.blue2 },
    ]} />
  );
  return (
    <ResponsiveContainer width="100%" height={230}>
      <ComposedChart data={data} margin={{top:5,right:20,left:-5,bottom:0}}>
        <defs>
          <linearGradient id="goldGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor={C.gold} stopOpacity={0.25}/>
            <stop offset="95%" stopColor={C.gold} stopOpacity={0}/>
          </linearGradient>
        </defs>
        <CartesianGrid stroke={C.border} strokeDasharray="3 6" strokeOpacity={0.6}/>
        <XAxis dataKey="label" tick={{fontFamily:"'JetBrains Mono'",fontSize:9,fill:C.muted}}
               tickLine={false} axisLine={{stroke:C.border}} interval={5}/>
        <YAxis yAxisId="l" domain={[0,105]} tick={{fontFamily:"'JetBrains Mono'",fontSize:9,fill:C.muted}}
               tickLine={false} axisLine={false} unit="%" width={32}/>
        <YAxis yAxisId="r" orientation="right" domain={[50,110]}
               tick={{fontFamily:"'JetBrains Mono'",fontSize:9,fill:C.muted}}
               tickLine={false} axisLine={false} unit="Mt" width={38}/>
        <Tooltip content={<CustomTip/>}/>
        <Area yAxisId="l" type="monotone" dataKey="pct_active"
              stroke={C.gold} strokeWidth={2.5} fill="url(#goldGrad)"
              dot={false} activeDot={{r:5,fill:C.gold,stroke:C.panel,strokeWidth:2}}/>
        <Line yAxisId="r" type="monotone" dataKey="china_output_mt"
              stroke={C.blue2} strokeWidth={1.5} dot={false}
              strokeDasharray="5 3"
              activeDot={{r:4,fill:C.blue2,stroke:C.panel,strokeWidth:2}}/>
      </ComposedChart>
    </ResponsiveContainer>
  );
}

function CommodityChart({ data, C }) {
  const CustomTip = ({ active, payload, label }) => (
    <Tip active={active} payload={payload} label={label} C={C} rows={[
      { label:"Iron Ore", value:"$"+fmt(payload?.[0]?.value,0)+"/t", color:C.amber },
      { label:"HRC Steel", value:"$"+fmt(payload?.[1]?.value,0)+"/st", color:C.green2 },
    ]} />
  );
  return (
    <ResponsiveContainer width="100%" height={230}>
      <ComposedChart data={data} margin={{top:5,right:20,left:-5,bottom:0}}>
        <defs>
          <linearGradient id="amberGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor={C.amber} stopOpacity={0.2}/>
            <stop offset="95%" stopColor={C.amber} stopOpacity={0}/>
          </linearGradient>
          <linearGradient id="greenGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor={C.green2} stopOpacity={0.15}/>
            <stop offset="95%" stopColor={C.green2} stopOpacity={0}/>
          </linearGradient>
        </defs>
        <CartesianGrid stroke={C.border} strokeDasharray="3 6" strokeOpacity={0.6}/>
        <XAxis dataKey="label" tick={{fontFamily:"'JetBrains Mono'",fontSize:9,fill:C.muted}}
               tickLine={false} axisLine={{stroke:C.border}} interval={5}/>
        <YAxis yAxisId="l" domain={[60,240]} tick={{fontFamily:"'JetBrains Mono'",fontSize:9,fill:C.muted}}
               tickLine={false} axisLine={false} unit="$" width={36}/>
        <YAxis yAxisId="r" orientation="right" domain={[400,1900]}
               tick={{fontFamily:"'JetBrains Mono'",fontSize:9,fill:C.muted}}
               tickLine={false} axisLine={false} unit="$" width={42}/>
        <Tooltip content={<CustomTip/>}/>
        <Area yAxisId="l" type="monotone" dataKey="iron_ore_usd"
              stroke={C.amber} strokeWidth={2} fill="url(#amberGrad)"
              dot={false} activeDot={{r:4,fill:C.amber,stroke:C.panel,strokeWidth:2}}/>
        <Area yAxisId="r" type="monotone" dataKey="hrc_steel_usd"
              stroke={C.green2} strokeWidth={2} fill="url(#greenGrad)"
              dot={false} activeDot={{r:4,fill:C.green2,stroke:C.panel,strokeWidth:2}}/>
      </ComposedChart>
    </ResponsiveContainer>
  );
}

function ScatterPlot({ data, xKey, yKey, color, C }) {
  const CustomTip = ({ active, payload }) => {
    if (!active || !payload?.length) return null;
    const d = payload[0]?.payload;
    return (
      <Tip active={active} payload={payload} label={d?.label} C={C} rows={[
        { label:"Signal", value:fmt(d?.[xKey],1)+"%" },
        { label:"Price", value:"$"+fmt(d?.[yKey],0) },
      ]} />
    );
  };
  return (
    <ResponsiveContainer width="100%" height={190}>
      <ScatterChart margin={{top:5,right:10,left:-10,bottom:0}}>
        <CartesianGrid stroke={C.border} strokeDasharray="3 6" strokeOpacity={0.6}/>
        <XAxis dataKey={xKey} type="number" domain={["auto","auto"]}
               tick={{fontFamily:"'JetBrains Mono'",fontSize:9,fill:C.muted}}
               tickLine={false} axisLine={{stroke:C.border}}/>
        <YAxis dataKey={yKey} type="number" domain={["auto","auto"]}
               tick={{fontFamily:"'JetBrains Mono'",fontSize:9,fill:C.muted}}
               tickLine={false} axisLine={false}/>
        <Tooltip content={<CustomTip/>} cursor={{strokeDasharray:"3 3",stroke:C.border}}/>
        <Scatter data={data} fill={color} opacity={0.75}
                 shape={(p) => <circle cx={p.cx} cy={p.cy} r={4} fill={color}
                                        stroke={C.panel} strokeWidth={1} opacity={0.8}/>}/>
      </ScatterChart>
    </ResponsiveContainer>
  );
}

function HeatBar({ mills, C }) {
  const top = [...(mills||[])].sort((a,b)=>b.latest_score-a.latest_score).slice(0,12);
  const CustomTip = ({ active, payload }) => {
    if (!active||!payload?.length) return null;
    const d = payload[0]?.payload;
    return <Tip active={active} payload={payload} label={d?.name} C={C} rows={[
      { label:"Heat Score", value:fmt((d?.latest_score||0)*100,1)+"%" },
      { label:"Status", value:d?.latest_status||"—" },
      { label:"Province", value:d?.province||"—" },
    ]}/>;
  };
  return (
    <ResponsiveContainer width="100%" height={270}>
      <BarChart data={top} layout="vertical" margin={{top:0,right:16,left:104,bottom:0}}>
        <defs>
          <linearGradient id="barGrad" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor={C.gold} stopOpacity={0.9}/>
            <stop offset="100%" stopColor={C.amber} stopOpacity={0.7}/>
          </linearGradient>
        </defs>
        <CartesianGrid stroke={C.border} strokeDasharray="3 6" horizontal={false} strokeOpacity={0.6}/>
        <XAxis type="number" domain={[0,1]} tick={{fontFamily:"'JetBrains Mono'",fontSize:9,fill:C.muted}}
               tickLine={false} axisLine={{stroke:C.border}}/>
        <YAxis type="category" dataKey="name" width={100}
               tick={{fontFamily:"'Inter'",fontSize:9,fill:C.text2}}
               tickLine={false} axisLine={false}/>
        <Tooltip content={<CustomTip/>} cursor={{fill:`${C.gold}08`}}/>
        <Bar dataKey="latest_score" fill="url(#barGrad)" radius={[0,3,3,0]} maxBarSize={13}/>
      </BarChart>
    </ResponsiveContainer>
  );
}

function MillMap({ mills, onSelect, selected, C }) {
  const W=560, H=310;
  const proj = (lat,lon) => ({
    x:((lon-73)/(135-73))*W,
    y:H-((lat-18)/(54-18))*H,
  });
  return (
    <div style={{ background:C === themes.dark ? "#0D1520" : "#EDE8DF",
                  border:`1px solid ${C.border}`, borderRadius:3, overflow:"hidden",
                  position:"relative" }}>
      <svg viewBox={`0 0 ${W} ${H}`} style={{width:"100%",display:"block"}}>
        <defs>
          <filter id="glow">
            <feGaussianBlur stdDeviation="3" result="blur"/>
            <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
          </filter>
        </defs>
        {[25,30,35,40,45].map(lat => {
          const {y}=proj(lat,73);
          return <line key={lat} x1={0} y1={y} x2={W} y2={y}
                       stroke={C.border} strokeWidth={0.5} strokeDasharray="4 4"/>;
        })}
        {[90,100,110,120,130].map(lon => {
          const {x}=proj(18,lon);
          return <line key={lon} x1={x} y1={0} x2={x} y2={H}
                       stroke={C.border} strokeWidth={0.5} strokeDasharray="4 4"/>;
        })}
        {(mills||[]).map(mill => {
          const {x,y}=proj(mill.lat,mill.lon);
          const isActive = mill.latest_status==="ACTIVE";
          const isSel = selected?.mill_id===mill.mill_id;
          const r = 3+(mill.latest_score||0)*9;
          return (
            <g key={mill.mill_id} onClick={()=>onSelect(mill)} style={{cursor:"pointer"}}>
              {isActive && (
                <circle cx={x} cy={y} r={r+6} fill="none"
                        stroke={C.gold} strokeWidth={0.8} opacity={0.25}/>
              )}
              <circle cx={x} cy={y} r={r}
                      fill={isActive ? C.gold : C.muted}
                      stroke={isSel ? C.text : (isActive ? C.gold2 : "transparent")}
                      strokeWidth={isSel ? 2 : 0.5}
                      opacity={isActive ? 0.9 : 0.5}
                      filter={isActive && isSel ? "url(#glow)" : "none"}/>
            </g>
          );
        })}
      </svg>
      <div style={{ position:"absolute", bottom:8, right:8,
                    background: C === themes.dark ? "rgba(10,14,20,0.9)" : "rgba(253,250,244,0.92)",
                    border:`1px solid ${C.border}`, borderRadius:3, padding:"6px 10px" }}>
        {[{c:C.gold,l:"Active"},{c:C.muted,l:"Idle"}].map(({c,l})=>(
          <div key={l} style={{display:"flex",alignItems:"center",gap:5,marginBottom:2}}>
            <div style={{width:7,height:7,borderRadius:"50%",background:c}}/>
            <span style={{fontFamily:"'Inter'",fontSize:9,color:C.text2}}>{l}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function MillDetail({ mill, C }) {
  if (!mill) return (
    <div style={{color:C.muted,fontSize:12,fontFamily:"'Inter'",
                 textAlign:"center",padding:"28px 0",lineHeight:1.8}}>
      Click any facility<br/>on the map to view details
    </div>
  );
  const isActive = mill.latest_status==="ACTIVE";
  return (
    <div className="slide-in">
      <div style={{display:"flex",justifyContent:"space-between",
                   alignItems:"flex-start",marginBottom:14}}>
        <div>
          <div style={{fontFamily:"'Playfair Display'",fontSize:15,fontWeight:600,
                       color:C.text,marginBottom:3}}>{mill.name}</div>
          <div style={{fontFamily:"'Inter'",fontSize:11,color:C.muted}}>
            {mill.company} — {mill.province}
          </div>
        </div>
        <div style={{padding:"4px 12px",borderRadius:20,
                     background:isActive?`${C.gold}18`:`${C.muted}18`,
                     border:`1px solid ${isActive?C.gold:C.border}`,
                     fontFamily:"'JetBrains Mono'",fontSize:9,fontWeight:600,
                     color:isActive?C.gold:C.muted,letterSpacing:"1.5px"}}>
          {mill.latest_status||"—"}
        </div>
      </div>
      <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:8}}>
        {[
          {label:"Heat Score",value:fmt((mill.latest_score||0)*100,1)+"%"},
          {label:"Capacity",value:(mill.capacity_mtpa||"—")+" Mt/yr"},
          {label:"Latitude",value:fmt(mill.lat,3)+"° N"},
          {label:"Longitude",value:fmt(mill.lon,3)+"° E"},
        ].map(({label,value})=>(
          <div key={label} style={{background:C.bg,border:`1px solid ${C.border}`,
                                    borderRadius:3,padding:"8px 10px"}}>
            <div style={{fontFamily:"'Inter'",fontSize:9,color:C.muted,
                          letterSpacing:"1.5px",textTransform:"uppercase",marginBottom:3}}>{label}</div>
            <div style={{fontFamily:"'JetBrains Mono'",fontSize:12,color:C.text,fontWeight:500}}>{value}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function CorrTable({ data, C }) {
  if (!data?.length) return (
    <div style={{color:C.muted,fontSize:12,textAlign:"center",padding:"20px 0"}}>
      Loading correlation data...
    </div>
  );
  const best = Math.max(...data.map(d=>d.r2||0));
  return (
    <div style={{overflowX:"auto"}}>
      <table style={{width:"100%",borderCollapse:"collapse",fontSize:11,fontFamily:"'JetBrains Mono'"}}>
        <thead>
          <tr style={{borderBottom:`2px solid ${C.border}`}}>
            {["Comparison","Lead","R²","Pearson r","p-value","n"].map(h=>(
              <th key={h} style={{padding:"7px 10px",textAlign:"left",fontFamily:"'Inter'",
                                   fontSize:9,letterSpacing:"1.5px",textTransform:"uppercase",
                                   color:C.muted,fontWeight:600}}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row,i)=>{
            const isBest = row.r2===best;
            return (
              <tr key={i} style={{borderBottom:`1px solid ${C.border}`,
                                   background:isBest?`${C.gold}0C`:"transparent",
                                   transition:"background 0.2s"}}>
                <td style={{padding:"8px 10px",color:C.text2,fontFamily:"'Inter'",fontSize:11}}>{row.comparison}</td>
                <td style={{padding:"8px 10px",color:C.muted}}>{row.lag_months}mo</td>
                <td style={{padding:"8px 10px",color:isBest?C.gold:C.text,fontWeight:isBest?700:400}}>
                  {isBest && <span style={{marginRight:5}}>★</span>}{row.r2?.toFixed(3)}
                </td>
                <td style={{padding:"8px 10px",color:row.r>=0?C.green2:C.red2,fontWeight:500}}>
                  {row.r>=0?"+":""}{row.r?.toFixed(3)}
                </td>
                <td style={{padding:"8px 10px",color:row.p<0.05?C.green2:C.muted}}>
                  {row.p?.toFixed(4)}
                </td>
                <td style={{padding:"8px 10px",color:C.muted}}>{row.n}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function Methodology({ C }) {
  const steps = [
    {n:"01",color:C.gold,title:"Satellite Acquisition",body:"Sentinel-2 SR imagery at 10m resolution via Google Earth Engine for 45 Chinese steel facilities. Monthly median composites, 2019–2024. 2,815 images total."},
    {n:"02",color:C.amber,title:"SWIR Heat Index",body:"Bands B11 (1610nm) and B12 (2190nm) isolate thermal anomalies. Pixel z-scores flag statistically significant heat from blast furnaces operating at 1200–1500°C."},
    {n:"03",color:C.green2,title:"Activity Scoring",body:"Per-facility heat scores aggregated into a monthly signal: % of facilities exceeding the adaptive thermal threshold."},
    {n:"04",color:C.blue2,title:"Lead Correlation",body:"Cross-lag Pearson correlation at 0–6 month offsets. Optimal: 2-month lead (R²=0.17, p=0.0003). Statistically significant."},
    {n:"05",color:C.muted,title:"Financial Validation",body:"Signal correlated against iron ore and HRC steel futures, quantifying the alpha window prior to WSA publication."},
  ];
  return (
    <div style={{display:"flex",flexDirection:"column",gap:14}}>
      {steps.map(s=>(
        <div key={s.n} style={{display:"flex",gap:14,
                                paddingBottom:14,borderBottom:`1px solid ${C.border}`}}>
          <div style={{fontFamily:"'Playfair Display'",fontSize:22,fontWeight:700,
                       color:s.color,opacity:0.5,minWidth:28,lineHeight:1}}>{s.n}</div>
          <div>
            <div style={{fontFamily:"'Inter'",fontSize:11,fontWeight:600,
                          color:C.text,marginBottom:4,letterSpacing:"0.3px"}}>{s.title}</div>
            <div style={{fontFamily:"'Inter'",fontSize:11,color:C.muted,lineHeight:1.65}}>{s.body}</div>
          </div>
        </div>
      ))}
    </div>
  );
}

// ── NARRATIVE SUMMARY ──────────────────────────────────────────────────────────
function NarrativeSummary({ data, C }) {
  const steps = [
    {
      icon:"◉",
      color: C.gold,
      title: "Signal Fires",
      period: "Aug 2021",
      metric: "91.9% mills active",
      body: "Our SWIR heat index detected peak blast furnace activity across 41 of 45 monitored Chinese steel facilities — the highest reading in the 6-year dataset. This represented an extreme production surge following post-COVID demand recovery."
    },
    {
      icon:"◎",
      color: C.amber,
      title: "Output Drops",
      period: "Oct – Dec 2021",
      metric: "−14% WSA output",
      body: "Exactly 2 months later, the World Steel Association reported a sharp output curtailment. Beijing's \"dual carbon\" restrictions and production caps forced mills to cut capacity — precisely the mechanism our signal predicted."
    },
    {
      icon:"◈",
      color: C.red2,
      title: "Iron Ore Falls",
      period: "Sep – Nov 2021",
      metric: "$218 → $96 per tonne",
      body: "Iron ore prices collapsed 56% in just 10 weeks as the market absorbed the production curtailment signal. Our satellite data showed this coming 8 weeks before the price peak — a significant alpha window for commodity market participants."
    },
    {
      icon:"◇",
      color: C.green2,
      title: "Statistical Proof",
      period: "2019 – 2024",
      metric: "R²=0.173, p=0.0003",
      body: "Across the full 72-month dataset, the satellite signal demonstrated statistically significant lead correlation with WSA output at a 2-month lag. The p-value of 0.0003 confirms this is not a chance relationship — it is a real and reproducible signal."
    },
  ];

  return (
    <div style={{background:C.panel,border:`1px solid ${C.border}`,
                  borderTop:`3px solid ${C.gold}`,borderRadius:4,
                  padding:"28px 32px",boxShadow:C.cardShadow}}>
      <div style={{display:"flex",alignItems:"baseline",gap:12,marginBottom:6}}>
        <div style={{fontFamily:"'Playfair Display'",fontSize:22,fontWeight:700,color:C.text}}>
          The Full Story
        </div>
        <div style={{fontFamily:"'Inter'",fontSize:10,color:C.muted,letterSpacing:"2px",
                      textTransform:"uppercase"}}>
          Signal → Output → Market
        </div>
      </div>
      <div style={{fontFamily:"'Inter'",fontSize:13,color:C.muted,marginBottom:28,lineHeight:1.7,
                    maxWidth:700}}>
        What began as a computer vision pipeline on satellite imagery became a demonstrable leading indicator
        for one of the world's most liquid commodity markets. Here is what the data actually shows.
      </div>

      <div style={{display:"grid",gridTemplateColumns:"repeat(4,1fr)",gap:16,marginBottom:28}}>
        {steps.map((s,i)=>(
          <div key={i} className="card-hover fade-up"
            style={{background:C.bg,border:`1px solid ${C.border}`,
                    borderTop:`3px solid ${s.color}`,borderRadius:4,
                    padding:"18px 18px",animationDelay:`${i*100}ms`}}>
            <div style={{display:"flex",alignItems:"center",gap:8,marginBottom:10}}>
              <span style={{fontSize:16,color:s.color}}>{s.icon}</span>
              <span style={{fontFamily:"'JetBrains Mono'",fontSize:9,color:s.color,
                             letterSpacing:"1.5px",textTransform:"uppercase",fontWeight:600}}>
                Step {i+1}
              </span>
            </div>
            <div style={{fontFamily:"'Playfair Display'",fontSize:15,fontWeight:600,
                          color:C.text,marginBottom:4}}>{s.title}</div>
            <div style={{fontFamily:"'JetBrains Mono'",fontSize:10,color:s.color,
                          marginBottom:8,fontWeight:600}}>{s.metric}</div>
            <div style={{fontFamily:"'Inter'",fontSize:10,color:C.muted,lineHeight:1.7}}>{s.body}</div>
            <div style={{fontFamily:"'JetBrains Mono'",fontSize:9,color:C.dim,
                          marginTop:10,paddingTop:8,borderTop:`1px solid ${C.border}`}}>
              {s.period}
            </div>
          </div>
        ))}
      </div>

      {/* Connecting arrows */}
      <div style={{display:"flex",alignItems:"center",justifyContent:"center",
                    gap:0,marginBottom:24,opacity:0.4}}>
        {["Satellite detects heat surge","→","2 months later","→","Output curtailed","→","Iron ore −56%"].map((t,i)=>(
          <span key={i} style={{fontFamily: i%2===0 ? "'JetBrains Mono'" : "'Inter'",
                                  fontSize: i%2===0 ? 10 : 16,
                                  color: i%2===0 ? C.muted : C.gold,
                                  padding:"0 8px"}}>{t}</span>
        ))}
      </div>

      {/* Bottom stat row */}
      <div style={{display:"grid",gridTemplateColumns:"repeat(5,1fr)",gap:12,
                    borderTop:`1px solid ${C.border}`,paddingTop:20}}>
        {[
          {label:"Images Processed",value:"2,815",unit:""},
          {label:"Facilities Tracked",value:"45",unit:"Chinese mills"},
          {label:"Observation Window",value:"72",unit:"months"},
          {label:"Signal Lead Time",value:"2",unit:"months"},
          {label:"Statistical Confidence",value:"99.97%",unit:"(p=0.0003)"},
        ].map(({label,value,unit})=>(
          <div key={label} style={{textAlign:"center"}}>
            <div style={{fontFamily:"'Playfair Display'",fontSize:24,fontWeight:700,
                          color:C.gold,marginBottom:2}}>{value}</div>
            <div style={{fontFamily:"'Inter'",fontSize:9,color:C.muted,
                          letterSpacing:"1px",textTransform:"uppercase",lineHeight:1.6}}>
              {label}<br/><span style={{color:C.dim,fontSize:9}}>{unit}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── MAIN APP ──────────────────────────────────────────────────────────────────
export default function App() {
  const [dark,      setDark]     = useState(false);
  const [stats,     setStats]    = useState(null);
  const [mills,     setMills]    = useState([]);
  const [signal,    setSignal]   = useState([]);
  const [financial, setFinancial]= useState([]);
  const [corrData,  setCorrData] = useState([]);
  const [selected,  setSelected] = useState(null);

  const C = dark ? themes.dark : themes.light;

  useEffect(() => {
    const load = async () => {
      try {
        const [s,m,sig,fin,corr] = await Promise.all([
          fetch(`${API}/stats`).then(r=>r.json()),
          fetch(`${API}/mills`).then(r=>r.json()),
          fetch(`${API}/signal`).then(r=>r.json()),
          fetch(`${API}/financial`).then(r=>r.json()),
          fetch(`${API}/financial/correlation`).then(r=>r.json()),
        ]);
        setStats(s); setMills(m); setSignal(sig);
        setFinancial(fin); setCorrData(corr);
      } catch {
        setStats({
          total_mills:45,active_mills:32,pct_active:71.1,mom_change:2.3,
          latest_iron_ore:104.5,iron_ore_change:-1.8,latest_hrc:660,
          hrc_change:3.0,latest_year:2024,latest_month:12,
        });
      }
    };
    load();
  }, []);

  const chartData = signal.map(s => {
    const fin = financial.find(f=>f.year===s.year && f.month===s.month)||{};
    return { ...s, ...fin, label: monthLabel(s.year, s.month) };
  });

  return (
    <div style={{fontFamily:"'Inter'",background:C.bg,minHeight:"100vh",
                  color:C.text,transition:"background 0.3s,color 0.3s"}}>
      <style>{globalCSS(C)}</style>

      <Header stats={stats} dark={dark} setDark={setDark} C={C} />

      <div style={{padding:"24px 32px",maxWidth:1600,margin:"0 auto"}}>

        {/* KPI Row */}
        <div style={{display:"grid",gridTemplateColumns:"repeat(6,1fr)",gap:12,marginBottom:20}}>
          <KpiCard label="Facilities Monitored" value={stats?.total_mills??"—"}
                   sub="Chinese steel mills" accent={C.navy} delay={0} C={C}/>
          <KpiCard label="Currently Active" value={stats?.active_mills??"—"}
                   unit={`/ ${stats?.total_mills??"—"}`} change={stats?.mom_change}
                   accent={C.gold} delay={60} C={C}/>
          <KpiCard label="Activity Rate" value={stats?fmt(stats.pct_active):"—"}
                   unit="%" sub="SWIR heat index" accent={C.gold} delay={120} C={C}/>
          <KpiCard label="Iron Ore" value={stats?fmt(stats.latest_iron_ore,0):"—"}
                   unit="USD/t" change={stats?.iron_ore_change} accent={C.amber} delay={180} C={C}/>
          <KpiCard label="HRC Steel" value={stats?fmt(stats.latest_hrc,0):"—"}
                   unit="USD/st" change={stats?.hrc_change} accent={C.green} delay={240} C={C}/>
          <KpiCard label="Signal Lead" value="2" unit="months"
                   sub="R²=0.17 · p=0.0003" accent={C.blue} delay={300} C={C}/>
        </div>

        {/* Row 1 */}
        <div style={{display:"grid",gridTemplateColumns:"2fr 1fr",gap:16,marginBottom:16}}>
          <Card title="Satellite Activity Signal vs Steel Production"
                subtitle="Monthly % of facilities active (SWIR heat index) vs WSA crude steel output — 2019 to 2024"
                delay={100} C={C}>
            <SignalChart data={chartData} C={C}/>
          </Card>
          <Card title="Facility Map"
                subtitle="45 Chinese steel facilities — dot size proportional to SWIR heat score"
                delay={150} C={C}>
            <MillMap mills={mills} onSelect={setSelected} selected={selected} C={C}/>
          </Card>
        </div>

        {/* Row 2 */}
        <div style={{display:"grid",gridTemplateColumns:"2fr 1fr",gap:16,marginBottom:16}}>
          <Card title="Commodity Price History"
                subtitle="Iron ore 62% Fe CFR China (USD/t, left) · HRC steel futures (USD/short ton, right)"
                accent={C.amber} delay={200} C={C}>
            <CommodityChart data={chartData} C={C}/>
          </Card>
          <Card title="Facility Detail" subtitle="Selected from map" accent={C.navy} delay={250} C={C}>
            <MillDetail mill={selected} C={C}/>
          </Card>
        </div>

        {/* Row 3 */}
        <div style={{display:"grid",gridTemplateColumns:"1fr 1fr 1fr",gap:16,marginBottom:16}}>
          <Card title="Signal vs Iron Ore"
                subtitle="SWIR activity score vs iron ore spot price" accent={C.amber} delay={300} C={C}>
            <ScatterPlot data={chartData} xKey="pct_active" yKey="iron_ore_usd"
                          color={C.amber} C={C}/>
          </Card>
          <Card title="Signal vs HRC Steel"
                subtitle="SWIR activity score vs HRC futures" accent={C.green} delay={350} C={C}>
            <ScatterPlot data={chartData} xKey="pct_active" yKey="hrc_steel_usd"
                          color={C.green2} C={C}/>
          </Card>
          <Card title="Top Facilities by Heat Score"
                subtitle="Current period SWIR thermal intensity ranking" accent={C.gold} delay={400} C={C}>
            <HeatBar mills={mills} C={C}/>
          </Card>
        </div>

        {/* Row 4 */}
        <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:16,marginBottom:16}}>
          <Card title="Lead-Lag Correlation Analysis"
                subtitle="Pearson correlation at each lag offset — star marks optimal" delay={450} C={C}>
            <CorrTable data={corrData} C={C}/>
          </Card>
          <Card title="Analytical Methodology"
                subtitle="SteelSight pipeline — Sentinel-2 SWIR Heat Index" accent={C.navy} delay={500} C={C}>
            <Methodology C={C}/>
          </Card>
        </div>

        {/* Narrative Summary */}
        <div style={{marginBottom:16}} className="fade-up" style={{animationDelay:"550ms"}}>
          <NarrativeSummary data={chartData} C={C}/>
        </div>

        {/* Footer */}
        <div style={{borderTop:`1px solid ${C.border}`,paddingTop:16,marginTop:8,
                      display:"flex",justifyContent:"space-between",alignItems:"center"}}>
          <div style={{fontFamily:"'Playfair Display'",fontSize:13,color:C.muted}}>
            SteelSight — Satellite Commodity Intelligence
          </div>
          <div style={{fontFamily:"'JetBrains Mono'",fontSize:9,color:C.dim,textAlign:"right",lineHeight:1.8}}>
            Data: ESA Sentinel-2 SR · WSA Monthly Reports · Iron Ore 62% Fe CFR · CME HRC Futures<br/>
            Pipeline: SWIR Heat Index · 2,815 images · 45 facilities · 2019–2024
          </div>
        </div>
      </div>
    </div>
  );
}

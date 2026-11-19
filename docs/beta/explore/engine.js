// The record's drawing code, from the full-record page; started by explore.js once data.json has loaded.
const esc=v=>String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
window.PBEngine = function(DATA, BASEMAP){
  const css = v => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
  const D = DATA.daily, N = D.length;
  const t0 = new Date(D[0].d);
  const idxOf = new Map(D.map((r,i)=>[r.d,i]));
  const dayIdx = d => Math.round((new Date(d) - t0)/864e5);
  const FMAX = Math.max(...D.map(r=>r.f)), SMAX = Math.max(...D.map(r=>r.s));
  const SHADOW = new Array(N); { let s=0; for(let i=0;i<N;i++){ s=0.73*s+(D[i].mm||0); SHADOW[i]=s; } }
  const DSR = new Array(N); { let last=-999;
    for(let i=0;i<N;i++){ if((D[i].mm||0)>=1) last=i; DSR[i]= last<0?999:(i-last); } }
  const SPD = new Array(N).fill(false);
  DATA.spills.forEach(sp=>{ const j=idxOf.get(sp.d); if(j==null) return;
    for(let k=j;k<Math.min(j+8,N);k++) SPD[k]=true; });
  let DOTPOS=[]; let exNote=null;
  const TREND=(()=>{ const a=DATA.creek.filter(pp=>pp.v!=null).map(pp=>({i:idxOf.get(pp.d),l:Math.log10(Math.max(pp.v,1))})).filter(pp=>pp.i!=null);
    return a.map((pp,j)=>{ const w=a.slice(Math.max(0,j-4),j+5);
      return {i:pp.i, v:10**(w.reduce((s2,q)=>s2+q.l,0)/w.length)}; }); })();
  let _TRENDA=null;
  const getTRENDA=()=>{ if(_TRENDA) return _TRENDA;
    const rowsA=[...siteBy.entries()].map(([d,row])=>{
      const vals=SITES.map(s2=>row[s2]&&row[s2].ec).filter(v=>v!=null);
      if(vals.length<2) return null; const i=idxOf.get(d); if(i==null) return null;
      return {i, l: vals.reduce((a,v)=>a+Math.log10(Math.max(v,1)),0)/vals.length}; })
      .filter(Boolean).sort((a,b)=>a.i-b.i);
    _TRENDA=rowsA.map((pp,j)=>{ const w=rowsA.slice(Math.max(0,j-4),j+5);
      return {i:pp.i, v:10**(w.reduce((s2,q)=>s2+q.l,0)/w.length)}; });
    return _TRENDA; };
  let _TRENDB=null;
  const getTRENDB=()=>{ if(_TRENDB) return _TRENDB;
    const a=DATA.beach.map(pp=>({i:idxOf.get(pp.d),l:Math.log10(Math.max(pp.v,1))})).filter(pp=>pp.i!=null);
    _TRENDB=a.map((pp,j)=>{ const w=a.slice(Math.max(0,j-4),j+5);
      return {i:pp.i, v:10**(w.reduce((s2,q)=>s2+q.l,0)/w.length)}; });
    return _TRENDB; };
  let _TRENDW=null;
  const getTRENDW=()=>{ if(_TRENDW) return _TRENDW;
    const a=DATA.bwtf.filter(pp=>pp.v!=null).map(pp=>({i:idxOf.get(pp.d),l:Math.log10(Math.max(pp.v,1))})).filter(pp=>pp.i!=null);
    _TRENDW=a.map((pp,j)=>{ const w=a.slice(Math.max(0,j-4),j+5);
      return {i:pp.i, v:10**(w.reduce((s2,q)=>s2+q.l,0)/w.length)}; });
    return _TRENDW; };

  const SITES = ["LMMS","ADMS","PRLT","SPCM"];
  const SCOL = {LMMS:"--s2",ADMS:"--s3",PRLT:"--prlt",SPCM:"--wtemp",AVG:"--purp"};
  const SERCOL = {creek:"--creek",beach:"--beach",bwtf:"--bwtf",...SCOL};
  let colorBySite=false;
  const serCol = code => css(code==="AVG" ? "--purp" : (colorBySite ? SERCOL[code] : "--samp"));
  const siteBy = new Map(); DATA.sites.forEach(r=>{ if(!siteBy.has(r.d)) siteBy.set(r.d,{}); siteBy.get(r.d)[r.s]=r; });
  { const fmtD=d=>{ const M=["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"][+d.slice(5,7)-1]; return `${M} ${+d.slice(8,10)}, ${d.slice(0,4)}`; };
    const lasts=[["coalition sites",DATA.sites],["county creek",DATA.creek],["county beach",DATA.beach],["Surfrider",DATA.bwtf]]
      .filter(([k,arr])=>arr&&arr.length).map(([k,arr])=>[k,arr[arr.length-1].d]);
    const latest=lasts.map(x=>x[1]).sort().pop();
    const dl=document.getElementById("dateline");
    if(dl&&latest) dl.textContent=`Data through ${fmtD(latest)}`+(DATA.built?` · page updated ${fmtD(DATA.built)}`:"");
    const fl=document.getElementById("freshline");
    if(fl) fl.textContent="Data through: "+lasts.map(([k,v])=>`${k} ${v}`).join(" · ")+(DATA.built?` · page updated ${DATA.built}`:"")+"."; }
  let analyte = "ent";
  const stdFor = (code, an) => an==="ec" ? 320 : (code==="LM5"||code==="LM7" ? 104 : 110);
  const STDTIP={
    ec:"The single-sample standard for E. coli in fresh water where people play — set by the State Water Board (statewide Bacteria Provisions, 2018) from EPA's 2012 recreational criteria, which swimmer-illness studies calibrated to hold sickness under about 32 per 1,000 swimmers. One result over the line is one bad sample; a water body meeting the standard sees results this high less than about 1 sample in 10, and holds its six-week average under 100. Sources are linked in Methods.",
    ent:"Two enterococcus standards drawn as one line, less than a pixel apart on this scale: 104 is California's ocean single-sample standard (AB 411, 1997) — the line the county posts the beach on; 110 is the freshwater value applied at the creek sites (EPA 2012). Same illness-study basis as the E. coli standard. Sources are linked in Methods.",
    gm:"The primary test: a rolling six-week geometric mean of E. coli results must stay under 100 — the single-sample line is its companion, not the main event. Since 2015 the creek's running average has been over this line in about 9 of every 10 six-week stretches; the main exception was 2021, after a dry winter. The trend lines are what this standard judges. Sources are linked in Methods."};

  const TRACKS = [
    {id:"bact", name:"BACTERIA", sub:"MPN per 100 mL", h:150, log:true},
    {id:"rain",  name:"RAIN",   sub:"mm / day", h:64, max:80, ticks:[0,40,80]},
    {id:"wy",    name:"RAIN VS NORMAL", sub:"% of typical year", h:52, max:260, ticks:[100,200]},
    {id:"flow",  name:"FLOW (EST.)", sub:"index, from rain", h:64, sqrt:true, max:FMAX, ticks:[10,50,150]},
    {id:"grnd",  name:"GROUND (EST.)", sub:"index, from rain", h:64, max:SMAX, ticks:[100,300]},
    {id:"air",   name:"AIR TEMP", sub:"daily °C", h:52, min2:6, max:24, ticks:[10,15,20]},
    {id:"wtemp", name:"WATER TEMP (EST.)", sub:"°C, from air", h:52, min2:6, max:24, ticks:[10,15,20]},
    {id:"sp",    name:"SPILLS", sub:"reported", h:26},
  ];
  const on = new Set(["rain","flow","wtemp"]); // conditions
  const sampleOn = new Set(["creek","LMMS","ADMS","PRLT","SPCM","beach"]); // samples: creek|beach|AVG|LMMS|ADMS|PRLT|SPCM|bwtf
  const anOn = new Set(["ent","ec"]);         // bacteria for coalition series
  const ann = new Set(["shadow","warm"]);
  const PHONE={on:false, lane:"rain"};
  const laneVisible = id => id==="bact" ? sampleOn.size>0 : (PHONE.on ? id===PHONE.lane : on.has(id));
  let LAY = {}, H = 0;
  function layout(){
    LAY={}; let y=PHONE.on?28:18;
    for(const t of TRACKS){ if(!laneVisible(t.id)) continue; LAY[t.id]={...t,y0:y};
      if(PHONE.on) LAY[t.id].h=t.id==="bact"?160:(t.id==="sp"?44:84);
      y+=LAY[t.id].h+(PHONE.on?28:18); }
    H = y+44;
  }
  const Y=(t,v)=>{ const tr=LAY[t];
    if(tr.log){ const l0=1,l1=Math.log10(30000);
      return tr.y0+tr.h - tr.h*(Math.log10(Math.max(v,10))-l0)/(l1-l0); }
    if(tr.sqrt) return tr.y0+tr.h - tr.h*Math.sqrt(Math.min(v,tr.max))/Math.sqrt(tr.max);
    if(tr.min2!=null) return tr.y0+tr.h - tr.h*(Math.min(Math.max(v,tr.min2),tr.max)-tr.min2)/(tr.max-tr.min2);
    return tr.y0+tr.h - tr.h*Math.min(v,tr.max)/tr.max; };

  function gutter(){
    const g=document.getElementById("gutter"); g.style.height=H+"px"; g.innerHTML="";
    for(const [id,tr] of Object.entries(LAY)){
      g.insertAdjacentHTML("beforeend",`<div class="name" style="top:${tr.y0-2}px">${tr.name}</div>
        <div class="sub" style="top:${tr.y0+11}px">${id==="air"?(degF?"daily \u00b0F":"daily \u00b0C"):id==="wtemp"?(degF?"\u00b0F, from air":"\u00b0C, from air"):(tr.sub||"")}</div>`);
      if(tr.log){ [10,100,1000,10000].forEach(v=>g.insertAdjacentHTML("beforeend",
          `<div class="tick" style="top:${Y(id,v)-7}px">${v>=1000?(v/1000)+"k":v}</div>`));
        const ecOn=anOn.has("ec") && (sampleOn.has("creek")||sampleOn.has("beach")||["AVG",...SITES].some(s=>sampleOn.has(s)));
        const entOn=anOn.has("ent") && (sampleOn.has("beach")||sampleOn.has("creek")||sampleOn.has("bwtf")||["AVG",...SITES].some(s=>sampleOn.has(s)));
        const mkstd=(top,txt,tip)=>{ const el=document.createElement("div"); el.className="stdlab"; el.style.top=top+"px";
          el.textContent=txt; el.tabIndex=0; attachTip(el,txt,tip,null); g.appendChild(el); };
        if(ecOn) mkstd(Y(id,320)-11,"320 E.coli",STDTIP.ec);
        if(entOn) mkstd(Y(id,104)+1,"104 entero",STDTIP.ent);
        if(ann.has("trend")&&(sampleOn.has("creek")||sampleOn.has("AVG"))) mkstd(Y(id,100)+1+(entOn?11:0),"100 geo-mean",STDTIP.gm); }
      else if(tr.ticks) tr.ticks.forEach(v=>g.insertAdjacentHTML("beforeend",
          `<div class="tick" style="top:${Y(id,v)-7}px">${(id==="air"||id==="wtemp")&&degF?Math.round(v*9/5+32):v}</div>`));
    }
  }

  const sc=document.getElementById("scroller");
  const WORKS=[
    ["2001-06-01","2003-09-30","Mouth & flood control (2001–03)","The creek mouth and tidal wetlands were rebuilt and two oceanfront homes removed — a managed-retreat and flood-control project, about 2001–2003."],
    ["2003-11-01","2004-04-30","Capistrano fish passage (2004)","A failed fish ladder at Capistrano Avenue was removed and the mid-reach channel regraded, winter 2003–2004."],
    ["2014-06-20","2015-10-31","Hwy 1 bridge rebuilt (2014–15)","Caltrans replaced the Highway 1 bridge and widened the creek channel above the mouth, June 2014 – October 2015. County creek testing began just after, in September 2015."],
    ["2017-07-01","2020-06-30","Sewer basin (2017–20)","A 2.1-million-gallon sewer equalization basin at 540 Crespi Dr — a sewer-system project beside the lower creek, built ~2017–2020 under a Water Board order to stop wet-weather overflows. Not in-channel creek work, but a ~$19M attempt to cut beach pollution, shown here in a different shade. Storm-weather bacteria did not fall after it opened, and the beach did not improve.","sewer"],
    ["2026-04-01","2026-08-14","Adobe Dr culvert (2026)","The undersized Adobe Drive culvert is being replaced with a free-span bridge in the mid-valley reach, during the 2026 dry season."]];
  let PPD=1.3, pinned=false, curI=null, theory=null, targetPPD=PPD;

  const ANN = {
    shadow:{label:"Rain shadow", col:"--rain",
      draw:(X)=>{ if(!LAY.bact) return "";
        const yT=LAY.bact.y0, yB=LAY.bact.y0+LAY.bact.h;
        let s2="";
        for(let i=0;i<N;i++){ const v=SHADOW[i]; if(v<2) continue;
          s2+=`<rect x="${X(i)-PPD/2}" y="${yT}" width="${PPD}" height="${yB-yT}" fill="${css('--rain')}" opacity="${Math.min(Math.sqrt(v/80)*0.55,0.5).toFixed(3)}"></rect>`; }
        return s2; }},
    warm:{label:"Warm-water tint", col:"--temp",
      draw:(X)=>{ if(!LAY.bact) return ""; let s2=""; let run=null;
        const lab=(a,b)=>{ if(a!=null&&(b-a)*PPD>90) s2+=`<text x="${X(a)+6}" y="${LAY.bact.y0+13}" font-size="9.5" fill="${css('--temp')}" letter-spacing="1" opacity=".9">WARM + RAIN-FREE</text>`; };
        for(let i=0;i<N;i++){ const w=D[i].wt, hot=(w!=null&&w>=14.5&&D[i].f<=5);
          if(hot){ if(run==null) run=i;
            s2+=`<rect x="${X(i)-PPD/2}" y="${LAY.bact.y0}" width="${PPD}" height="${LAY.bact.h}" fill="${css('--temp')}" opacity="${Math.min((w-14.5)/6*0.4+0.1,0.45).toFixed(3)}"></rect>`; }
          else if(run!=null){ lab(run,i); run=null; } }
        lab(run,N); return s2; }},
    dryrings:{label:"Dry-spell rings", col:"--ink",
      draw:(X)=>{ if(!LAY.bact) return ""; let s2="";
        DOTPOS.forEach(dp=>{ if(DSR[dp.i]>30)
          s2+=`<circle cx="${X(dp.i)}" cy="${dp.y}" r="${PPD>=3?7:5.5}" fill="none" stroke="${css('--ink')}" stroke-width="1.3" opacity=".8"></circle>`; });
        return s2; }},
    spillrings:{label:"Spill windows", col:"--ink",
      draw:(X)=>{ if(!LAY.bact) return ""; let s2="";
        DOTPOS.forEach(dp=>{ if(SPD[dp.i]){ const rr=PPD>=3?9.5:7.5;
          s2+=`<circle cx="${X(dp.i)}" cy="${dp.y}" r="${rr}" fill="none" stroke="#ffffff" stroke-width="3.4" opacity=".9"></circle>
            <circle cx="${X(dp.i)}" cy="${dp.y}" r="${rr}" fill="none" stroke="${css('--ink')}" stroke-width="1.8" stroke-dasharray="3 2.5"></circle>`; } });
        return s2; }},
    works:{label:"Construction", col:"--muted",
      draw:(X)=>{ if(!LAY.bact) return ""; let s2=""; const yb=LAY.bact.y0+LAY.bact.h+4;
        WORKS.forEach(([d0,d1,lab,desc,kind],wi)=>{ const i0=idxOf.has(d0)?idxOf.get(d0):dayIdx(d0), i1=idxOf.has(d1)?idxOf.get(d1):dayIdx(d1);
          const x0=X(i0), w=Math.max(X(i1)-x0,3);
          const sew=kind==="sewer", wf=sew?css('--wsewer'):css('--muted'), wo=sew?".4":".3";
          s2+=`<rect data-wk="${wi}" x="${x0}" y="${yb}" width="${w}" height="11" rx="2" fill="${wf}" opacity="${wo}"${sew?` stroke="${css('--wsewer')}" stroke-width="0.9" stroke-opacity=".55"`:""} style="cursor:help"></rect>
            <text x="${x0+4}" y="${yb+8.5}" font-size="8.5" font-weight="600" fill="${css('--page')}" stroke="${css('--page')}" stroke-width="2.4" stroke-linejoin="round" pointer-events="none">${lab}</text>
            <text x="${x0+4}" y="${yb+8.5}" font-size="8.5" font-weight="600" fill="${css('--ink2')}" pointer-events="none">${lab}</text>`; });
        return s2; }},
    trend:{label:"Trend lines", col:"--creek",
      draw:(X)=>{ if(!LAY.bact) return ""; let s2="";
        if(sampleOn.has("creek")||sampleOn.has("AVG")){ const gmY=Y('bact',100);
          s2+=`<line x1="0" x2="${X(N-1)+20}" y1="${gmY}" y2="${gmY}" stroke="${css('--std')}" stroke-width="1.5" stroke-dasharray="1 3" opacity=".85"></line>`; }
        const line2=(pts,col)=>{ let d2=""; pts.forEach((pp,j)=>{ d2+=(j?"L":"M")+X(pp.i).toFixed(1)+","+Y('bact',pp.v).toFixed(1); });
          return `<path d="${d2}" fill="none" stroke="#ffffff" stroke-width="4.5" opacity=".85"></path>
            <path d="${d2}" fill="none" stroke="${col}" stroke-width="2.4"></path>`; };
        if(sampleOn.has("creek")) s2+=line2(TREND,"#1c5cab");
        if(sampleOn.has("AVG")){ const TA=getTRENDA(); if(TA.length>3) s2+=line2(TA,"#5b3fb0"); }
        if(sampleOn.has("beach")){ const TB=getTRENDB(); if(TB.length>3) s2+=line2(TB,"#a34a12"); }
        if(sampleOn.has("bwtf")){ const TW=getTRENDW(); if(TW.length>3) s2+=line2(TW,"#3d5271"); }
        return s2; }},
    verdicts:{label:"Winter carryover", col:"--ground",
      draw:(X)=>{ if(!LAY.bact) return ""; let s2="";
        for(const sm of summerRows()){ const yy=sm.y, cls=sm.cls;
          const j0=idxOf.get(`${yy}-06-01`), j1=idxOf.get(`${yy}-09-30`);
          if(j0==null) continue;
          const gmv=sm.n>=5?Math.round(sm.gm):null;
          const x0=X(j0), w2=((j1??j0+120)-j0)*PPD;
          if(cls!=="norm") s2+=`<rect x="${x0}" y="${LAY.bact.y0}" width="${w2}" height="${LAY.bact.h}" fill="${cls==="wet"?css('--ground'):css('--flow')}" opacity="${cls==="wet"?0.13:0.09}"></rect>`;
          if(w2>120){ const col=cls==="wet"?css('--ground'):(cls==="dry"?css('--flow'):css('--muted'));
            s2+=`<text x="${x0+4}" y="${LAY.bact.y0+13}" font-size="9.5" fill="${col}" letter-spacing="1">AFTER ${cls==="norm"?"NORMAL":cls.toUpperCase()} WINTER</text>`;
            if(gmv!=null) s2+=`<text x="${x0+4}" y="${LAY.bact.y0+26}" font-size="9.5" fill="${css('--ink2')}">rain-free typical ${gmv}</text>`; } }
        return s2; }},
  };
  const VIEWS = {
    storm:{label:"Rainstorms", samples:["creek","beach"], show:["rain","flow","sp"], ann:["shadow"],
      bar:`<b>Claim:</b> rain sends bacteria up for a few days, scaled by storm size — the <b>rain shadow</b> fades at the measured rate (risk halves every ~2 days). <b>Measured:</b> creek 75% over 0–1 days after rain → 44% by day 2–3; beach 77% → 28% by day 4–7. The water stays up ~3× longer than the risk — the first flush carries the load.`},
    carry:{label:"Wet winters", samples:["creek"], show:["wy","grnd"], ann:["verdicts","trend"],
      bar:`<b>Claim:</b> a wet winter raises the creek's level through the following summer. Each summer is labeled with the winter that preceded it and the creek's typical rain-free level. <b>Measured:</b> ~165 after dry winters vs ~496 after wet ones (28% → 68% over the standard) — on eleven summers, the dry-winter figure mostly on 2020–21, so a lead rather than a settled finding. <b>Dated test:</b> if this El Niño winter tops 130% of normal, summer 2027 should run near 68%.`},
    warm:{label:"Warm water", samples:["creek"], show:["air","wtemp"], ann:["warm"],
      bar:`<b>Claim:</b> warm water lets bacteria persist and regrow — warm rain-free stretches tinted amber, with inferred water temperature drawn (air-to-water transfer fitted on Pescadero Creek 1965–79, r=0.85). <b>Measured:</b> cool rain-free summer weeks 241 → warm weeks 452.`},
    chronic:{label:"Contamination without rain", samples:["creek","LMMS","ADMS","PRLT","SPCM"], show:["rain"], ann:["dryrings"], bySite:true,
      bar:`<b>Claim:</b> something feeds the creek with no rain at all — ringed samples are &gt;30 days after any rain (172 of them; 53% still over the standard). The four sites show where: the dry-weather load roughly doubles between Adobe Sanchez and Peralta Bridge. This is what DNA source-tracking targets.`},
    spills:{label:"Reported spills", samples:["creek"], show:["rain","sp"], ann:["spillrings","works"],
      bar:`<b>Claim (checked, found wanting):</b> reported spills explain it. Ringed samples fall within 7 days after a surface-reaching spill — just 18 of 523. Reported spills collapsed after 2011 while the creek worsened after 2014 — pointing at what is <em>not</em> reported: continuous exfiltration.`},
    cleanera:{label:"The beach used to be cleaner", samples:["beach"], show:["rain"], ann:["trend","works"],
      bar:`<b>Claim:</b> clean water at this beach is recent, documented fact — 43% of county tests before 2014 found no bacteria at all; 2% since 2022. In 2014 water quality found a new normal, much worse than before. Same station, same lab method throughout.`},
  };

  function render(keepDate){
    layout(); gutter(); DOTPOS=[];
    const W = 24 + N*PPD, X = i => 20 + i*PPD;
    let s=`<svg width="${W}" height="${H}" role="img">`;
    for(let yy=2000; yy<=2026; yy++){
      const x=X(dayIdx(`${yy}-01-01`));
      s+=`<line x1="${x}" x2="${x}" y1="8" y2="${H-44}" stroke="${css('--line')}"></line>
          ${(PPD*365>=40||yy%5===0)?`<text x="${x+4}" y="${H-26}" font-size="11" fill="${css('--muted')}">${yy}</text>`:""}`;
      if(PPD>3) for(let m=2;m<=12;m++){ const xm=X(dayIdx(`${yy}-${String(m).padStart(2,"0")}-01`));
        s+=`<line x1="${xm}" x2="${xm}" y1="${H-52}" y2="${H-44}" stroke="${css('--line')}"></line>`; }
    }
    for(const [id,tr] of Object.entries(LAY)){
      if(tr.log) [10,100,1000,10000].forEach(v=> s+=`<line x1="0" x2="${W}" y1="${Y(id,v)}" y2="${Y(id,v)}" stroke="${css('--line')}" opacity=".6"></line>`);
      else if(tr.ticks) tr.ticks.forEach(v=> s+=`<line x1="0" x2="${W}" y1="${Y(id,v)}" y2="${Y(id,v)}" stroke="${css('--line')}" opacity=".6"></line>`);
      s+=`<line x1="0" x2="${W}" y1="${tr.y0+tr.h}" y2="${tr.y0+tr.h}" stroke="${css('--line')}"></line>`;
      if(id==="bact"){
        const ecOn=anOn.has("ec") && (sampleOn.has("creek")||sampleOn.has("beach")||["AVG",...SITES].some(x2=>sampleOn.has(x2)));
        const entOn=anOn.has("ent") && (sampleOn.has("beach")||sampleOn.has("creek")||sampleOn.has("bwtf")||["AVG",...SITES].some(x2=>sampleOn.has(x2)));
        if(ecOn) s+=`<line x1="0" x2="${W}" y1="${Y(id,320)}" y2="${Y(id,320)}" stroke="${css('--std')}" stroke-dasharray="4 4" opacity=".7"></line>`;
        if(entOn) s+=`<line x1="0" x2="${W}" y1="${Y(id,104)}" y2="${Y(id,104)}" stroke="${css('--std')}" stroke-dasharray="2 5" opacity=".6"></line>`;
      }
    }
    s+=`<g id="ov"></g>`;
    if(LAY.rain){ let rain="";
      if(PPD>=3){ D.forEach((r,i)=>{ if(r.mm<=0.2) return;
        rain+=`<rect x="${X(i)-PPD/2+0.6}" y="${Y('rain',r.mm)}" width="${PPD-1.2}" height="${LAY.rain.y0+LAY.rain.h-Y('rain',r.mm)}" fill="${css('--rain')}"></rect>`; });
      } else { for(let i=0;i<N;i+=7){ const mm=D.slice(i,i+7).reduce((a,r)=>a+r.mm,0);
        if(mm<=0.5) continue; const v=Math.min(mm/2,LAY.rain.max);
        rain+=`<rect x="${X(i)}" y="${Y('rain',v)}" width="${Math.max(7*PPD-1.5,0.4)}" height="${LAY.rain.y0+LAY.rain.h-Y('rain',v)}" fill="${css('--rain')}" opacity=".9"></rect>`; } }
      s+=`<g id="g-rain">${rain}</g>`; }
    const area=(key,t,color,op)=>{ let d="M"+X(0)+","+(LAY[t].y0+LAY[t].h);
      const step=PPD<2?2:1;
      for(let i=0;i<N;i+=step) d+="L"+X(i).toFixed(1)+","+Y(t,D[i][key]).toFixed(1);
      return `<path d="${d}L${X(N-1)},${LAY[t].y0+LAY[t].h}Z" fill="${css(color)}" opacity="${op}" stroke="${css(color)}" stroke-width="1"></path>`; };
    if(LAY.flow) s+=`<g id="g-flow">${area("f","flow","--flow",0.55)}</g>`;
    if(LAY.grnd) s+=`<g id="g-grnd">${area("s","grnd","--ground",0.35)}</g>`;
    const lineOf=(key,t)=>{ let d="",st=false; const step=PPD<2?2:1;
      for(let i=0;i<N;i+=step){ const v=D[i][key]; if(v==null){st=false;continue;}
        d+=(st?"L":"M")+X(i).toFixed(1)+","+Y(t,v).toFixed(1); st=true; } return d; };
    if(LAY.wy) s+=`<g id="g-wy"><path d="${lineOf('wy','wy')}" fill="none" stroke="${css('--wy')}" stroke-width="1.4" opacity=".85"></path>
      <line x1="0" x2="${W}" y1="${Y('wy',100)}" y2="${Y('wy',100)}" stroke="${css('--muted')}" stroke-dasharray="2 4" opacity=".6"></line></g>`;
    if(LAY.air) s+=`<g id="g-air"><path d="${lineOf('t','air')}" fill="none" stroke="${css('--temp')}" stroke-width="1.4" opacity=".85"></path></g>`;
    if(LAY.wtemp) s+=`<g id="g-wtemp"><path d="${lineOf('wt','wtemp')}" fill="none" stroke="${css('--wtemp')}" stroke-width="1.8" opacity=".95"></path></g>`;
    const dots=(arr,t,std,code,an)=>arr.map(p=>{ const i=idxOf.get(p.d); if(i==null) return "";
      const over=p.v>std, yy=Y(t,p.v); DOTPOS.push({i,y:yy});
      const r=PPD>=3?(over?4.2:3.4):(over?3.3:2.5), col=(over&&!colorBySite)?css('--std'):serCol(code);
      return an==="ent"
        ? `<circle data-site="${code}" cx="${X(i)}" cy="${yy}" r="${r}" fill="${col}" opacity="${over?0.95:0.6}"></circle>`
        : `<circle data-site="${code}" cx="${X(i)}" cy="${yy}" r="${r}" fill="none" stroke="${col}" stroke-width="1.7" opacity="${over?0.95:0.65}"></circle>`; }).join("");
    if(LAY.bact&&sampleOn.has("creek")&&anOn.has("ec")) s+=`<g id="g-creekd">${dots(DATA.creek.filter(p=>p.v!=null),"bact",320,"creek","ec")}</g>`;
    if(LAY.bact&&sampleOn.has("creek")&&anOn.has("ent")) s+=`<g id="g-creeke">${dots(DATA.creek.filter(p=>p.ent!=null).map(p=>({d:p.d,v:p.ent})),"bact",110,"creek","ent")}</g>`;
    if(LAY.bact&&sampleOn.has("beach")&&anOn.has("ent")) s+=`<g id="g-beachd">${dots(DATA.beach,"bact",104,"beach","ent")}</g>`;
    if(LAY.bact&&sampleOn.has("beach")&&anOn.has("ec")) s+=`<g id="g-beache">${dots(DATA.beach.filter(p=>p.ec!=null).map(p=>({d:p.d,v:p.ec})),"bact",320,"beach","ec")}</g>`;
    if(LAY.bact&&sampleOn.has("bwtf")&&anOn.has("ent")) s+=`<g id="g-bwtf">${dots(DATA.bwtf,"bact",110,"bwtf","ent")}</g>`;
    if(LAY.bact){ const mk=(d0,lab,on2,anch)=>{ if(!on2) return; const ci=idxOf.get(d0); if(ci==null) return;
        const xx=X(ci)-6;
        s+=`<line x1="${xx}" x2="${xx}" y1="${LAY.bact.y0+4}" y2="${LAY.bact.y0+LAY.bact.h-4}" stroke="${css('--muted')}" opacity=".35" stroke-dasharray="2 3"></line>
          <text x="${xx+(anch==="end"?-4:4)}" y="${LAY.bact.y0+14}" font-size="9.5" fill="${css('--muted')}" text-anchor="${anch}">${lab}</text>`; };
      mk("2015-09-21","county creek testing begins", sampleOn.has("creek"),"end");
      mk("2000-05-16","county beach testing begins", sampleOn.has("beach"),"start"); }
    if(LAY.bact){ let sd="";
      const mark=(i,v,code,an)=>{ const over=v>stdFor(code,an);
        const col=(over&&!colorBySite)?css('--std'):serCol(code);
        const r=PPD>=3?(over?4.2:3.4):(over?3.3:2.5);
        const yy=Y('bact',v); DOTPOS.push({i,y:yy});
        return an==="ent"
          ? `<circle data-site="${code}" cx="${X(i)}" cy="${yy}" r="${r}" fill="${col}" opacity="${over?0.95:0.7}"></circle>`
          : `<circle data-site="${code}" cx="${X(i)}" cy="${yy}" r="${r}" fill="none" stroke="${col}" stroke-width="1.8" opacity="${over?0.95:0.75}"></circle>`; };
      DATA.sites.forEach(p=>{ if(!sampleOn.has(p.s)) return;
        const i=idxOf.get(p.d); if(i==null) return;
        for(const an of anOn){ const v=p[an]; if(v!=null) sd+=mark(i,v,p.s,an); } });
      if(sampleOn.has("AVG")){
        const pts={ent:[],ec:[]};
        for(const [d,row] of siteBy){
          const i=idxOf.get(d); if(i==null) continue;
          for(const an of anOn){
            const vals=SITES.map(s2=>row[s2]&&row[s2][an]).filter(v=>v!=null);
            if(vals.length>=2){
              const gmv=10**(vals.reduce((a,v)=>a+Math.log10(Math.max(v,1)),0)/vals.length);
              pts[an].push({i,v:gmv}); } } }
        for(const an of ["ent","ec"]){ const arr=pts[an]; if(!arr.length) continue;
          arr.sort((a,b)=>a.i-b.i);
          arr.forEach(pp=>{ const yy=Y('bact',pp.v); DOTPOS.push({i:pp.i,y:yy});
            const over=pp.v>stdFor("AVG",an), col=(over&&!colorBySite)?css('--std'):css('--purp');
            sd+= an==="ent"
              ? `<circle data-site="AVG" cx="${X(pp.i)}" cy="${yy}" r="${PPD>=3?3.2:2.6}" fill="${col}" opacity=".95"></circle>`
              : `<circle data-site="AVG" cx="${X(pp.i)}" cy="${yy}" r="${PPD>=3?3:2.4}" fill="${css('--card')}" stroke="${col}" stroke-width="1.6" opacity=".95"></circle>`; }); } }
      s+=`<g id="g-sites">${sd}</g>`; }
    if(LAY.sp){ let sp="";
      DATA.spills.forEach(x=>{ const i=idxOf.get(x.d); if(i==null) return;
        const r=Math.min(4+Math.log10(Math.max(x.gal,10))*1.6,12);
        sp+=`<path d="M${X(i)} ${LAY.sp.y0+2} l${r} ${r*1.4} h${-2*r} z" fill="${css('--ink')}" opacity=".7"></path>`; });
      s+=`<g id="g-sp">${sp}</g>`; }
    s+=`<g id="ov2"></g>`;
    s+=`<line id="xh" x1="-9" x2="-9" y1="8" y2="${H-44}" stroke="${css('--ink')}" opacity=".35"></line></svg>`;
    sc.innerHTML=s;
    applyAnn();
    if(keepDate) sc.scrollLeft=Math.max(20+dayIdx(keepDate)*PPD - sc.clientWidth/2,0);
    else sc.scrollLeft=sc.scrollWidth;
  }

  function applyTheory(skipRender){
    const ov=document.getElementById("ov"); if(!ov) return;
    const bar=document.getElementById("theorybar");
    if(!theory){ ov.innerHTML=""; bar.innerHTML="Select a theory for a tuned view — or build your own with the layer panel."; return; }
    const T=THEORIES[theory]; const X=i=>20+i*PPD;
    ov.innerHTML=T.overlay(X); bar.innerHTML=T.bar;
  }
  function applyAnn(){
    const ov=document.getElementById("ov"); if(!ov) return;
    const X=i=>20+i*PPD;
    let out=[...ann].filter(k=>k!=="trend").map(k=>ANN[k]?ANN[k].draw(X):"").join("");
    if(exNote&&exNote.text&&LAY.bact){ const x=20+exNote.i0*PPD;
      out+=`<line x1="${x}" x2="${x}" y1="${LAY.bact.y0}" y2="${LAY.bact.y0+LAY.bact.h}" stroke="${css('--creek')}" opacity=".75" stroke-width="1.6" stroke-dasharray="4 3"></line>`;
    }
    ov.innerHTML=out;
    const o2=document.getElementById("ov2");
    if(o2) o2.innerHTML=(ann.has("trend")&&ANN.trend)?ANN.trend.draw(X):"";
    const tb=document.getElementById("tourbox");
    if(tb){ if(exNote&&exNote.text){ const tr2=exNote.tour;
        tb.innerHTML=(tr2?`<div class="tstep">STEP ${tr2.i+1} OF ${tr2.n}</div>`:"")
          +`<div>${exNote.text}</div><div class="tnav">`
          +(tr2&&tr2.i>0?`<button data-tnav="back">← Back</button>`:"")
          +(tr2&&tr2.i<tr2.n-1?`<button data-tnav="next">Next →</button>`:"")
          +`<button data-tnav="end">${tr2?"End tour":"Close"}</button></div>`;
        tb.hidden=false;
        tb.querySelectorAll("button").forEach(b2=>b2.onclick=()=>{ const t2=b2.dataset.tnav;
          if(t2==="next"&&TOUR){ TOUR.idx++; tourStep(); }
          else if(t2==="back"&&TOUR){ TOUR.idx--; tourStep(); }
          else { TOUR=null; exNote=null; applyAnn(); } });
      } else tb.hidden=true; }
  }
  const thc=document.getElementById("theories");
  const vbar=document.getElementById("theorybar");
  function clearViewHighlight(){ theory=null;
    thc.querySelectorAll("button").forEach(x=>{ if(x.dataset.v) x.setAttribute("aria-pressed","false"); });
    vbar.innerHTML="Choose a view above to set the graph and read an explanation of what it shows."; }
  const LONG={
    storm:`<b>Rainstorms.</b> When it rains, the creek rises and runoff carries contamination into the water. The shaded blue bands mark the days after each storm while that influence fades; on this record the added risk drops by about half every two days. Creek samples taken within a day of rain exceed the standard 75% of the time, falling to 44% by day two or three. At the beach it falls from 77% to 28% by day four to seven. Note the red dots outside any shaded band — rain does not explain those. The water level itself stays high about three times longer than the added risk does, which suggests the first flush of a storm carries most of the contamination.`,
    carry:`<b>Wet winters.</b> The idea: a wet winter stores water in the ground, and that stored water keeps feeding the creek through the following summer. Each summer on the graph is labeled with the winter that came before it and the typical creek level during weeks with no rain: about 165 after dry winters and about 496 after wet ones — 28% versus 68% of samples over the standard. Read this as a lead, not a settled finding. It rests on eleven summers; the low dry-winter figure comes mostly from two of them, 2020 and 2021; and summer 2018 followed a dry winter yet tested as high as the wet-winter summers. Past well readings across Pacifica (2002–2018; no well in the valley is read today) tell the same loose story: the summer water table usually, but not always, stood higher after a wet winter. The next test is dated: if this El Niño winter ends above 130% of normal rainfall, summer 2027 would be expected to look like the wet-winter summers. <a data-ask="wy" style="cursor:pointer">See every summer plotted</a>.`,
    warm:`<b>Warm water.</b> Bacteria survive and regrow better in warm water. The amber bands mark periods that were warm with no recent rain, using water temperature estimated from air temperature (the method was checked against a neighboring creek's 1965–1979 measurements, r = 0.85). In rain-free summer weeks, cool periods typically measure 241 and warm periods 452.`,
    chronic:`<b>Contamination without rain.</b> The circled samples were taken more than 30 days after any rain. There are 172 of them, and 53% still exceed the standard; the typical level in rain-free weeks sits at about the health limit. Turn on the four creek sites and the pattern shows where: in dry weather the level roughly doubles between Adobe Sanchez and Peralta Bridge. Something is feeding the creek year-round. DNA source-tracking is designed to find it.`,
    spills:`<b>Reported sewer spills — and the fix that proved a point.</b> Ringed samples fall within a week of a spill reported to the State — just 18 of 523. Before 2017, ordinary wet winters overflowed the sewer lines beside the creek mouth by hundreds of thousands of gallons. A $19 million storage basin, finished in 2020 under a Water Board order, stopped those overflows almost entirely — the slate-blue block on the Construction strip. Yet the creek’s storm results stayed where they were, and the beach’s worst years followed. Eliminating the biggest known discrete source barely moved the water: the evidence points at what never gets reported — continuous leakage from aging pipes.`,
    cleanera:`<b>The beach used to be cleaner.</b> Before 2014, 43% of the county's weekly tests at the creek mouth found no detectable bacteria — the result reads "under 10," the lowest the test can see, drawn here as dots on the chart floor. The beach once passed that way fourteen weeks in a row. Since 2014 the clean share has fallen to 15%, and since 2022 to about 2% — one clean test in each of 2022, 2023 and 2024, none so far in 2026. Same station, same lab method, the entire record. This was not a bad stretch that passed: in 2014 the water quality found a new normal, far worse than the decade before it, and it has never returned. The dark running-average line drawn with this view shows the shift, and the weather record does not explain it. What was lost is concrete and recent — and finding what changed around 2014 is what the source hunt upstream is for.`};
  const EPXG={storm:[["February 2019 storm","2019-02-10",7,"A typical storm: rain falls, results run high for three or four days, then recover."],
      ["2022–23 storm parade","2023-01-05",7,"Nine storms back to back. The creek never got a break between them."],
      ["First storms of fall 2024","2024-11-20",7,"The first real storms after the dry season wash in the most."]],
    carry:[["Summer 2021 vs summer 2023","2022-07-01",1.3,"Left: summer 2021 after a dry winter, mostly under the standard. Right: summer 2023 after a record winter, over it for months."]],
    chronic:[["Aug–Sep 2024, no rain","2024-08-20",7,"No rain for weeks, creek near zero flow — and still at or over the standard."],
      ["Site-by-site, summer 2025","2025-08-15",7,"Compare the four sites: in dry weather the level rises between Adobe Sanchez and Peralta Bridge."]],
    spills:[["The overflow winters","2014-12-11",7,"December 11, 2014: about 335,000 gallons overflowed the sewer lines beside the creek mouth in one day — the dark triangles. Winters like this were routine before the fix."],
      ["The $19 million fix","2018-09-01",1.3,"The slate-blue block on the Construction strip: a 2.1-million-gallon storage basin, built 2017–2020 under a Water Board order. It ended the routine overflows."],
      ["Oct 2021 lift station spill","2021-10-25",7,"The 2.9-million-gallon lift station spill — a pump-station failure, not the lines the basin relieves. The weekly Monday sample missed it entirely."],
      ["Storms after the fix","2024-01-05",3,"Storms without overflows — and the creek as red as ever. The biggest known discrete source was gone; the contamination was not."]],
    cleanera:[["The 2008 clean spring","2008-05-12",7,"Fourteen weekly tests in a row \u2014 late March into June 2008 \u2014 found no detectable bacteria. Dots on the chart floor read \u201cunder 10,\u201d the lowest the lab can see."],
      ["2009, the cleanest year","2009-06-15",1.3,"31 of 48 tests in 2009 found nothing at all. Results this low were the beach\u2019s usual state."],
      ["The change after 2014","2017-01-01",0.8,"Clean tests thin out from 2014 on: 21 in 2014, 11 in 2016, 2 by 2019. The standards and the lab method did not change. The grey strip just below the samples marks something that did: the Highway 1 bridge over the creek was rebuilt and the channel widened in 2014–15. Whether that altered how the creek's contamination reaches the beach is an open question — hover the block for details."],
      ["The recent record","2024-03-01",1.3,"2022\u20132024: one clean test each year. None so far in 2026. The running average sits several times the standard."]]};
  let TOUR=null;
  function tourStep(){ if(!TOUR) return; const st=EPXG[TOUR.k][TOUR.idx];
    exNote={i0:dayIdx(st[1]), text:st[3], tour:{i:TOUR.idx, n:EPXG[TOUR.k].length}};
    PPD=targetPPD=st[2]; syncViewButtons(); render(st[1]);
    const smooth=matchMedia("(prefers-reduced-motion: reduce)").matches?"auto":"smooth";
    window.scrollTo({top:document.querySelector(".tl").offsetTop-80, behavior:smooth}); }
  function applyView(k){
    const T=VIEWS[k]; if(!T) return;
    theory=k; exNote=null; TOUR=null;
    thc.querySelectorAll("button").forEach(x=>{ if(x.dataset.v) x.setAttribute("aria-pressed",String(x.dataset.v===k)); });
    sampleOn.clear(); T.samples.forEach(x=>sampleOn.add(x));
    on.clear(); T.show.forEach(x=>on.add(x));
    ann.clear(); T.ann.forEach(x=>ann.add(x));
    anOn.clear(); anOn.add("ent"); anOn.add("ec");
    colorBySite=!!T.bySite; syncBySite();
    const tourLink=(EPXG[k]&&EPXG[k].length)?`<a data-tour="${k}" style="cursor:pointer;font-weight:600">▶ Take the tour</a>`:"";
    const ex=[tourLink].concat((EPXG[k]||[]).map(([t,d2,z,note])=>`<a data-d="${d2}" data-z="${z}" data-n="${note}" style="cursor:pointer">${t}</a>`)).filter(Boolean).join(" · ");
    vbar.innerHTML=(LONG[k]||T.bar)+(ex?`<div style="margin-top:8px"><b>See it:</b> ${ex}</div>`:"");
    syncPanel(); render(centerDate());
    const gs=document.getElementById("geoslider"); if(gs&&gs.max) geoFrame(+gs.value);
  }
  const VTIP={storm:"Shows rainfall, estimated creek flow, reported spills, and the days after each storm.",
    carry:"Compares summers by how wet the preceding winter was.",
    warm:"Shows estimated water temperature alongside creek results in rain-free periods.",
    chronic:"Shows samples taken more than 30 days after any rain, at all creek sites.",
    spills:"Shows samples taken within a week of a sewer spill reported to the State.",
    cleanera:"Shows the county beach record back to 2000 with its running average \u2014 clean until 2014, failing since."};
  Object.entries(VIEWS).forEach(([k,T])=>{ const b=document.createElement("button");
    b.textContent=T.label; b.dataset.v=k; b.setAttribute("aria-pressed","false"); attachTip(b, T.label, VTIP[k]||"", null);
    b.onclick=()=>{ theory===k ? (clearViewHighlight(), render(centerDate())) : applyView(k); };
    thc.appendChild(b); });
  clearViewHighlight();
  vbar.addEventListener("click",e=>{
    const tb=e.target.closest("a[data-tour]");
    if(tb){ TOUR={k:tb.dataset.tour, idx:0}; tourStep(); return; }
    const ask=e.target.closest("a[data-ask]");
    if(ask){ const q=FACT.find(f=>f[0]===ask.dataset.ask), xf=document.getElementById("xf");
      const qb=q&&[...xf.querySelectorAll("button")].find(x=>x.textContent===q[1]);
      if(qb){ qb.click(); document.getElementById("ask").scrollIntoView({block:"start"}); } return; }
    const a=e.target.closest("a[data-d]"); if(!a) return;
    TOUR=null; exNote={i0:dayIdx(a.dataset.d), text:a.dataset.n||""};
    PPD=targetPPD=parseFloat(a.dataset.z); syncViewButtons(); render(a.dataset.d);
    const smooth=matchMedia("(prefers-reduced-motion: reduce)").matches?"auto":"smooth";
    window.scrollTo({top:document.querySelector(".tl").offsetTop-80, behavior:smooth}); });

  const panel=document.getElementById("panel"), spanel=document.getElementById("spanel"), apanel=document.getElementById("apanel"), npanel=document.getElementById("npanel");
  const tipcard=document.createElement("div"); tipcard.id="tipcard"; document.body.appendChild(tipcard);
  const wkPos=e=>{ tipcard.style.left=Math.max(6,Math.min(e.clientX+12,innerWidth-268))+"px"; tipcard.style.top=Math.min(e.clientY+16,innerHeight-130)+"px"; };
  sc.addEventListener("mouseover",e=>{ const t=e.target; if(t&&t.dataset&&t.dataset.wk!=null){ const w=WORKS[+t.dataset.wk]; if(!w) return;
    tipcard.innerHTML=`<div class="tt">${w[2]}</div><div>${w[3]}</div>`; tipcard.dataset.wk="1"; tipcard.style.display="block"; wkPos(e); } });
  sc.addEventListener("mousemove",e=>{ if(tipcard.dataset.wk==="1") wkPos(e); });
  sc.addEventListener("mouseout",e=>{ if(e.target&&e.target.dataset&&e.target.dataset.wk!=null){ tipcard.dataset.wk=""; tipcard.style.display="none"; } });
  const glyph=g=>{ const i=g.indexOf(":"), k=g.slice(0,i), v=g.slice(i+1);
    if(k==="dot") return `<span class="gd" style="background:${v}"></span>`;
    if(k==="ring") return `<span class="gd ring" style="border-color:${v}"></span>`;
    if(k==="block") return `<span class="gb" style="background:${v}"></span>`;
    return `<span class="gt">${v}</span>`; };
  function attachTip(b,label,text,legend){
    b.removeAttribute("title");
    const html=`<div class="tt">${label}</div><div>${text}</div>`+
      ((legend&&legend.length)?`<div class="tleg">${legend.map(([g,c])=>`<span>${glyph(g)}<i style="font-style:normal">${c}</i></span>`).join("")}</div>`:"");
    const show=()=>{ tipcard.innerHTML=html;
      const r=b.getBoundingClientRect();
      tipcard.style.left=Math.max(6,Math.min(r.left,innerWidth-272))+"px";
      tipcard.style.top=Math.min(r.bottom+8,innerHeight-160)+"px";
      tipcard.style.display="block"; };
    b.addEventListener("mouseenter",show); b.addEventListener("focus",show);
    b.addEventListener("mouseleave",()=>tipcard.style.display="none");
    b.addEventListener("blur",()=>tipcard.style.display="none");
  }
  const swatch={rain:"--rain",flow:"--flow",grnd:"--ground",wy:"--wy",air:"--temp",wtemp:"--wtemp",sp:"--std"};
  const SAMPLES=[["AVG","Creek — coalition (average)","--purp"],["creek","Creek — county","--creek"],
    ["LMMS","LMMS","--s2"],["ADMS","ADMS","--s3"],["PRLT","PRLT","--prlt"],["SPCM","SPCM","--wtemp"],
    ["beach","Beach — county","--beach"],["bwtf","Creek mouth — Surfrider (2013→)","--bwtf"]];
  function syncPanel(){
    panel.querySelectorAll("button").forEach(b=>{ if(b.dataset.t) b.setAttribute("aria-pressed",String(on.has(b.dataset.t))); });
    spanel.querySelectorAll("button").forEach(b=>{ if(b.dataset.s) b.setAttribute("aria-pressed",String(sampleOn.has(b.dataset.s))); });
    apanel.querySelectorAll("button").forEach(b=>{ if(b.dataset.a) b.setAttribute("aria-pressed",String(anOn.has(b.dataset.a))); });
    { const tOk=sampleOn.has("creek")||sampleOn.has("AVG")||sampleOn.has("beach")||sampleOn.has("bwtf");
      if(!tOk) ann.delete("trend");
      npanel.querySelectorAll("button").forEach(b=>{ if(b.dataset.n){
        if(b.dataset.n==="trend") b.disabled=!tOk;
        b.setAttribute("aria-pressed",String(ann.has(b.dataset.n))); } }); }
  }
  SAMPLES.forEach(([id,label,col])=>{ const b=document.createElement("button"); b.dataset.s=id;
    if(id==="AVG") attachTip(b,"Creek — coalition (average)",
      "The average of the four coalition creek sites each week, July 2024 onward (needs at least 2 sampled). Creek only — the county station and the ocean stations are not included. A calculation, not a place; a dot's height is the level, on the same log scale as everything else.",
      [["dot:var(--purp)","small filled purple dot = that week's enterococcus average"],
       ["ring:var(--purp)","small open purple dot = that week's E. coli average"],
       ["dot:var(--std)","red = that week's average is over its standard"]]);
    b.innerHTML=`<span class="swd" style="background:var(${col})"></span>${label}`;
    b.onclick=()=>{ sampleOn.has(id)?sampleOn.delete(id):sampleOn.add(id);
      clearViewHighlight();
      syncPanel(); render(centerDate()); geoRebuild(); };
    spanel.appendChild(b); });
  { const b=document.createElement("button"); b.id="bysite"; b.setAttribute("aria-pressed","false");
    b.innerHTML=`<span class="swd" style="background:linear-gradient(90deg,var(--s2),var(--s3),var(--prlt),var(--wtemp))"></span>Color by source`;
    attachTip(b,"Color by source",
      "Off, color answers how bad: every sample shares one color and red alone marks results over the standard. On, color answers where from: each sampling program keeps its own color even when a result is over the standard — judge pass/fail by height against the dashed lines. Hovering a name in this row spotlights one program\u2019s dots either way.",null);
    b.onclick=()=>{ colorBySite=!colorBySite; clearViewHighlight(); syncBySite(); render(centerDate()); geoLegend(); if(gdates.length) geoFrame(+document.getElementById("geoslider").value); };
    spanel.appendChild(b); }
  function syncBySite(){
    const bs=document.getElementById("bysite"); if(bs) bs.setAttribute("aria-pressed",String(colorBySite));
    spanel.querySelectorAll("button").forEach(b=>{ const id=b.dataset.s; if(!id) return;
      const sw=b.querySelector(".swd"); if(!sw) return;
      sw.style.background = id==="AVG" ? "var(--purp)" : (colorBySite ? `var(${SERCOL[id]})` : "var(--samp)"); }); }
  syncBySite();
  spanel.querySelectorAll("button").forEach(b=>{ const id=b.dataset.s; if(!id) return;
    const spot=o=>{ const sv=sc.querySelector("svg"); if(!sv) return;
      if(o&&sampleOn.has(id)) sv.setAttribute("data-hl",id); else sv.removeAttribute("data-hl"); };
    b.addEventListener("mouseenter",()=>spot(true)); b.addEventListener("focus",()=>spot(true));
    b.addEventListener("mouseleave",()=>spot(false)); b.addEventListener("blur",()=>spot(false)); });
  [["ent","● Enterococcus","Enterococcus — one of the two indicator bacteria, drawn as filled dots. Measured in the lab from water samples. Hides or shows every mark that measures it — the coalition sites, the county beach (the organism its advisories key on), and the tests the county began at its creek station in spring 2026."],
   ["ec","○ E. coli","E. coli — the other indicator bacteria, drawn as rings. Measured in the lab from water samples. Hides or shows every mark that measures it — the coalition sites, the county creek station (since 2015), and the county beach's E. coli record (since 2001)."]].forEach(([id,label,tip])=>{ const b=document.createElement("button"); b.dataset.a=id;
    b.textContent=label;
    attachTip(b, id==="ent"?"Enterococcus":"E. coli", tip,
      id==="ent"?[["dot:var(--samp)","filled dot = enterococcus, passed"],["dot:var(--std)","red filled dot = over its standard"]]
                :[["ring:var(--samp)","ring = E. coli, passed"],["ring:var(--std)","red ring = over its standard"]]);
    b.onclick=()=>{ anOn.has(id)?anOn.delete(id):anOn.add(id);
      clearViewHighlight();
      syncPanel(); render(centerDate());
      const gs=document.getElementById("geoslider"); if(gs&&gs.max) geoFrame(+gs.value); };
    apanel.appendChild(b); });
  const CTIP={rain:"Daily rainfall, estimated by a weather model. No rain gauge in the valley has a complete daily record.",
    wy:"This season's rain so far, as a % of a normal year to the same date. Computed from the rainfall record.",
    flow:"How much water we estimate is moving in the creek. Inferred from rain; checked against 5 gauged creeks nearby. Not a measurement — this creek has never had a flow gauge. Like ground wetness, the scale is an index — compare levels, not absolute numbers.",
    grnd:"How wet we estimate the ground is. Inferred from rain — fills in winter, dries over months; checked against nearby creeks' summer flows. The scale is an index, not a unit: each day keeps 97% of yesterday's value and adds a share of yesterday's estimated flow, so 0 means fully drained and the wettest winters on record reach about 300. Compare levels, not absolute numbers — twice the number means twice the stored-water signal. The method is a standard hydrology technique — an antecedent wetness index — with the constants fitted and checked for this creek.",
    air:"Daily air temperature, from weather records.",
    wtemp:"Estimated creek water temperature. Inferred from air temperature with a formula fitted on a nearby creek's 1965–79 measurements. No one measures it today.",
    sp:"Sewer spills the city reported to the state, drawn as dark triangles sized by volume. Real official records."};
  TRACKS.forEach(t=>{ if(t.id==="bact") return;
    const b=document.createElement("button"); b.dataset.t=t.id;
    attachTip(b, t.name.charAt(0)+t.name.slice(1).toLowerCase(), CTIP[t.id]||"", null);
    b.innerHTML=`<span class="swd" style="background:var(${swatch[t.id]})"></span>${t.name.charAt(0)+t.name.slice(1).toLowerCase()}`;
    b.onclick=()=>{ on.has(t.id)?on.delete(t.id):on.add(t.id);
      clearViewHighlight();
      syncPanel(); render(centerDate()); };
    panel.appendChild(b); });
  { const bc=document.getElementById("degc"), bf=document.getElementById("degf");
    const setU=f=>{ degF=f; bc.setAttribute("aria-pressed",String(!f)); bf.setAttribute("aria-pressed",String(f)); gutter(); if(curI!=null) show(curI); };
    if(bc&&bf){ attachTip(bf,"\u00b0F","Show temperatures in Fahrenheit. Display only \u2014 the water-temperature estimate is computed in Celsius either way.",null);
      bc.onclick=()=>setU(false); bf.onclick=()=>setU(true); } }
  const NTIP={shadow:"Shades the days after each storm when risk stays raised. Fades at the measured rate — risk halves about every 2 days.",
    warm:"Tints stretches that are warm AND rain-free — the conditions where bacteria persist. Darker = warmer estimated water.",
    dryrings:"Circles whichever displayed samples were taken 30+ days after any rain. If these still fail, weather isn't the cause.",
    spillrings:"Circles whichever displayed samples fall within a week after a reported sewer spill.",
    verdicts:"Labels each summer with the winter that came before it, plus the creek's typical level in rain-free weeks — so you can judge whether wet winters echo into the following summer.",
    works:"Grey blocks in the strip just below the samples mark dated creek construction. Hover any block for what was done and when. Facts, plotted so the record can be read against them — not stated causes.",
    trend:"Running averages, about two months of samples each: county creek results in dark blue, the coalition sites average (E. coli, 2024 onward) in purple, the county beach in dark sienna, and Surfrider\u2019s creek mouth in dark slate \u2014 each when displayed. The Surfrider line is enterococcus rather than E. coli, so it rides lower than the county creek line; its own geometric-mean standard is 30, stated here rather than drawn. The fine dotted line at 100 is the geometric-mean standard — the primary test, which judges the average rather than single samples. Where a trend line rides above it, the creek is failing the standard on average, not just on bad days."};
  const NLEG={shadow:[["block:var(--rain)","shaded days = raised risk after a storm (darker = stronger)"]],
    warm:[["block:var(--temp)","amber tint = warm AND rain-free stretch"]],
    dryrings:[["ring:var(--ink)","solid dark ring = sampled 30+ dry days after any rain"]],
    spillrings:[["ring:var(--ink)","larger dashed dark ring = within 7 days after a reported spill"]],
    verdicts:[["text:AFTER WET WINTER","label written over each summer"],["text:typical 496","that summer's typical rain-free level"]]};
  Object.entries(ANN).forEach(([k,A])=>{ const b=document.createElement("button"); b.dataset.n=k;
    attachTip(b, A.label, NTIP[k]||"", NLEG[k]);
    b.innerHTML=`<span class="swd" style="background:var(${A.col})"></span>${A.label}`;
    b.onclick=()=>{ ann.has(k)?ann.delete(k):ann.add(k); clearViewHighlight(); syncPanel(); render(centerDate()); };
    npanel.appendChild(b); });
  syncPanel();
  { const mb=document.getElementById("mapbtn");
    if(mb) attachTip(mb,"Map view","Docks the site map beside the graph. It steps to whichever week you hover on the timeline.",null); }
  // hover mini-map: where is this sampling site?
  { const cm=document.createElement("div"); cm.id="chipmap";
    const dot=document.createElement("div"); dot.className="dot";
    const cap=document.createElement("div"); cap.className="cap";
    const osm=document.createElement("div"); osm.className="osm"; osm.textContent="© OpenStreetMap";
    cm.append(dot,osm,cap); document.body.appendChild(cm);
    const M2=BASEMAP.meta, mY2=lat=>Math.asinh(Math.tan(lat*Math.PI/180));
    const px=lon=>(lon-M2.lonW)/(M2.lonE-M2.lonW)*M2.w;
    const py=lat=>(mY2(M2.latN)-mY2(lat))/(mY2(M2.latN)-mY2(M2.latS))*M2.h;
    cm.style.backgroundImage=`url(${BASEMAP.url})`;
    cm.style.backgroundSize=`${M2.w}px ${M2.h}px`;
    const GLY_D='<span class="gd" style="background:var(--samp);width:8px;height:8px;vertical-align:-1px"></span>',
          GLY_R='<span class="gd ring" style="border-color:var(--samp);width:7px;height:7px;vertical-align:-1px"></span>',
          OVR='<b style="color:var(--std)">red</b> = over';
    const SSHOW=GLY_D+' filled = enterococcus (standard 110) · '+GLY_R+' ring = E. coli (standard 320) · '+OVR+'.';
    const LOC={
      creek:{lat:37.5960,lon:-122.5053,name:"County creek station",
        info:"San Mateo County Environmental Health · weekly since 2015 · E. coli (Colilert lab; enterococcus added spring 2026). Same reach as SPCM — an independent program and lab on the same water.",
        shows:GLY_R+' ring = E. coli (standard 320) · '+GLY_D+' filled = enterococcus, spring 2026 on (standard 110) · '+OVR+'.'},
      beach:{lat:37.59658,lon:-122.50578,name:"County beach station (LM5)",
        info:"San Mateo County Environmental Health · weekly since 1998 · enterococcus + E. coli. Surf zone at the creek mouth — the longest record on this page.",
        shows:GLY_D+' filled = enterococcus (standard 104) · '+GLY_R+' ring = E. coli (standard 320) · '+OVR+'. Tide at the sampling time appears in the data display below the graph.'},
      bwtf:{lat:37.596172,lon:-122.505586,name:"Creek mouth — Surfrider BWTF",
        info:"Surfrider SMC Blue Water Task Force · enterococcus · since Dec 2013 — the only creek record reaching before the county station (Sep 2015) and the Highway 1 bridge work. Same reach as SPCM, an independent program.",
        shows:GLY_D+' filled = enterococcus (standard 110) · '+OVR+'. Off by default — turn on to extend the creek record back through 2014.'}};
    const SINFO={
      LMMS:"Coalition volunteers · weekly since Jul 2024 · E. coli + enterococcus. Most upstream site — top of the urban reach; water arriving from the parkland forks.",
      ADMS:"Coalition volunteers · weekly since Jul 2024 · E. coli + enterococcus. Mid-valley, at the historic Sanchez Adobe — upstream of the reach where the dry-weather load enters.",
      PRLT:"Coalition volunteers · weekly since Jul 2024 · E. coli + enterococcus. In dry weather the level roughly doubles between Adobe Sanchez and here — the reach the source hunt points at.",
      SPCM:"Coalition volunteers · weekly since Jul 2024 · E. coli + enterococcus. Where the creek crosses the beach — same reach as the county station, different lab."};
    ["LMMS","ADMS","PRLT","SPCM"].forEach(s2=>{ const g=DATA.geo[s2]; LOC[s2]={lat:g.lat,lon:g.lon,name:g.name,info:SINFO[s2],shows:SSHOW}; });
    spanel.querySelectorAll("button").forEach(b=>{
      const id=b.dataset.s; if(!id||!LOC[id]) return;
      const show=()=>{ const L=LOC[id], x=px(L.lon), y=py(L.lat);
        cm.style.backgroundPosition=`${-(x-150).toFixed(0)}px ${-(y-72).toFixed(0)}px`;
        dot.style.left="150px"; dot.style.top="72px";
        const sw=b.querySelector(".swd"); dot.style.background=sw?getComputedStyle(sw).backgroundColor:"#2a78d6";
        let sh=L.shows||"";
        if(sh&&colorBySite){ sh=sh.split("var(--samp)").join("var("+(SERCOL[id]||"--samp")+")")
            .split('<b style="color:var(--std)">red</b> = over').join("✕ = over"); }
        if(sh) sh=sh.split(" · ").join("<br>");
        cap.innerHTML="<b>"+esc(L.name)+"</b> — "+L.info+(sh?'<div class="shows">'+sh+"</div>":"");
        const r=b.getBoundingClientRect();
        cm.style.left=Math.max(6,Math.min(r.left,innerWidth-312))+"px";
        cm.style.top=Math.min(r.bottom+8,innerHeight-278)+"px";
        cm.style.display="block"; };
      b.addEventListener("mouseenter",show);
      b.addEventListener("focus",show);
      b.addEventListener("mouseleave",()=>cm.style.display="none");
      b.addEventListener("blur",()=>cm.style.display="none");
    });
  }
  const centerDate=()=>D[Math.min(Math.max(Math.round((sc.scrollLeft+sc.clientWidth/2-20)/PPD),0),N-1)].d;

  const detail=document.getElementById("detail");
  const ckBy=new Map(DATA.creek.map(p=>[p.d,p])), bcBy=new Map(DATA.beach.map(p=>[p.d,p])), bwBy=new Map((DATA.bwtf||[]).map(p=>[p.d,p]));
  const spBy=new Map(DATA.spills.map(p=>[p.d,p]));
  let degF=false;
  const fT=v=>v==null?"\u2013":(degF?Math.round(v*9/5+32)+"\u00b0F":v+"\u00b0C");
  function show(i){
    const r=D[i]; if(!r) return;
    const c=ckBy.get(r.d), b=bcBy.get(r.d), sp=spBy.get(r.d), st=siteBy.get(r.d);
    let h=`<b>${r.d}</b>`;
    const conds=`<span>rain <b>${r.mm}mm</b></span><span>flow <b>${r.f}</b></span><span>ground <b>${r.s}</b></span><span>winter <b>${r.wy??"–"}%</b></span><span>air temp <b>${fT(r.t)}</b></span><span>water temp <b>${fT(r.wt)}</b> est.</span>`;
    const idm=colorBySite, lab=(t,cv)=>idm?`<i style="font-style:normal;font-weight:600;color:${css(cv)}">${t}</i>`:t;
    if(c){ const cv=c.v!=null?`E.coli <b class="${(!idm&&c.v>320)?'over':''}">${c.v}</b>${c.v>320?' ✕':''}`:"";
      const ce=c.ent!=null?`${c.v!=null?" · ":""}ent <b class="${(!idm&&c.ent>110)?'over':''}">${c.ent}</b>${c.ent>110?' ✕':''}`:"";
      h+=`<span>${lab("creek (county)","--creek")} ${cv}${ce} <i style="font-style:normal;color:var(--muted)">(rain ${c.dsr}d ago; ${c.hr??"–"}h)</i></span>`; }
    if(b){ const bt=b.hr!=null?`${Math.floor(b.hr)}:${String(Math.round((b.hr%1)*60)).padStart(2,"0")}`:null;
      const tide=(sampleOn.has("beach")&&b.th!=null)?` <i style="font-style:normal;color:var(--muted)">(${bt?bt+" · ":""}tide ${b.th} ft ${b.ti?"↑ in":"↓ out"})</i>`:"";
      const be=b.ec!=null?` · E.coli <b class="${(!idm&&b.ec>320)?'over':''}">${b.ec}</b>${b.ec>320?' ✕':''}`:"";
      h+=`<span>${lab("beach (county)","--beach")} entero <b class="${(!idm&&b.v>104)?'over':''}">${b.nd?"&lt;10":b.v}</b>${b.v>104?' ✕':''}${b.nd?' <i style="font-style:normal;color:var(--muted)">none detected</i>':''}${be}${tide}</span>`; }
    if(st){ const parts=SITES.filter(x=>st[x]&&[...anOn].some(a2=>st[x][a2]!=null)).map(x=>{
        return lab(x,SERCOL[x])+" "+[...anOn].filter(a2=>st[x][a2]!=null).map(a2=>{
          const v=st[x][a2], ov=v>stdFor(x,a2); return `${a2==="ent"?"ent":"E.coli"} <b class="${(!idm&&ov)?'over':''}">${v}</b>${ov?'✕':''}`; }).join(" / "); });
      if(parts.length) h+=`<span>sites (coalition): ${parts.join(" · ")}</span>`; }
    if(sampleOn.has("bwtf")){ const w=bwBy.get(r.d); if(w) h+=`<span>${lab("creek mouth (Surfrider)","--bwtf")} <b class="${(!idm&&w.v>110)?'over':''}">${w.v}</b>${w.v>110?' ✕':''} <i style="font-style:normal;color:var(--muted)">(entero)</i></span>`; }
    if(sp) h+=`<span class="over">▲ spill ${sp.gal.toLocaleString()} gal — ${esc(sp.loc)}</span>`;
    h+=conds;
    const dtx=document.getElementById("dtext"); if(dtx) dtx.innerHTML=h+(/county|Surfrider|coalition|sites/i.test(h)?' <i style="font-style:normal;color:var(--muted)">· bacteria in MPN per 100 mL · \u2715 = over the health standard</i>':""); curI=i;
    if(geoFollow && !geoSync && typeof gdates!=="undefined"){
      const t=+new Date(r.d); let best=-1, bd=6*864e5;
      for(let k=0;k<gdates.length;k++){ const dd=Math.abs(+new Date(gdates[k])-t); if(dd<bd){ bd=dd; best=k; } }
      if(best>=0){ document.getElementById("geoslider").value=best; geoFrame(best); }
    }
  }
  const stepSample=dir=>{
    const list=[...new Set(DOTPOS.map(p=>p.i))].sort((a2,b2)=>a2-b2);
    if(!list.length) return;
    let t=null;
    if(curI==null) t=dir>0?list[0]:list[list.length-1];
    else if(dir>0) t=list.find(x=>x>curI);
    else { for(let k=list.length-1;k>=0;k--) if(list[k]<curI){ t=list[k]; break; } }
    if(t==null) return;
    pinned=true; show(t);
    const l=document.getElementById("xh"); if(l){ l.setAttribute("x1",20+t*PPD); l.setAttribute("x2",20+t*PPD); }
    const x=20+t*PPD;
    if(x<sc.scrollLeft+40||x>sc.scrollLeft+sc.clientWidth-40) sc.scrollLeft=Math.max(x-sc.clientWidth/2,0);
  };
  document.getElementById("dprev").onclick=()=>stepSample(-1);
  document.getElementById("dnext").onclick=()=>stepSample(1);
  let geoFollow=false, geoSync=false;
  sc.addEventListener("mousemove",e=>{ if(pinned) return;
    const rect=sc.getBoundingClientRect(); const x=e.clientX-rect.left+sc.scrollLeft;
    const i=Math.round((x-20)/PPD); if(i<0||i>=N) return;
    const l=document.getElementById("xh"); if(l){ l.setAttribute("x1",20+i*PPD); l.setAttribute("x2",20+i*PPD); }
    show(i); });
  sc.addEventListener("click",e=>{ const t=e.target&&e.target.dataset?e.target.dataset.tnav:null;
    if(t){ if(t==="next"&&TOUR){ TOUR.idx++; tourStep(); }
      else if(t==="back"&&TOUR){ TOUR.idx--; tourStep(); }
      else { TOUR=null; exNote=null; applyAnn(); }
      return; }
    pinned=!pinned; });

  function syncViewButtons(){ document.querySelectorAll(".view button").forEach(x=>
    x.setAttribute("aria-pressed",String(Math.abs(parseFloat(x.dataset.ppd)-PPD)<0.05))); }
  document.querySelectorAll(".view button").forEach(b=>b.onclick=()=>{
    const c=centerDate(); PPD=targetPPD=parseFloat(b.dataset.ppd); syncViewButtons(); render(c); });
  let zoomTimer=null;
  function queueZoom(anchorIdx,cursorX){ if(zoomTimer) return;
    zoomTimer=setTimeout(()=>{ zoomTimer=null; PPD=targetPPD; syncViewButtons(); render(null);
      sc.scrollLeft=Math.max(20+anchorIdx*PPD-cursorX,0); },90); }
  sc.addEventListener("wheel",e=>{ if(!(e.ctrlKey||e.metaKey)) return; e.preventDefault();
    const rect=sc.getBoundingClientRect(); const cx=e.clientX-rect.left;
    const idx=(sc.scrollLeft+cx-20)/PPD;
    targetPPD=Math.min(Math.max(targetPPD*Math.exp(-e.deltaY*0.008),0.5),14);
    queueZoom(idx,cx); },{passive:false});
  const pts=new Map(); let pinch0=null;
  sc.addEventListener("pointerdown",e=>{ pts.set(e.pointerId,e); if(pts.size===2){ const [a,b]=[...pts.values()];
    pinch0={d:Math.hypot(a.clientX-b.clientX,a.clientY-b.clientY),ppd:targetPPD,mid:(a.clientX+b.clientX)/2}; }});
  sc.addEventListener("pointermove",e=>{ if(!pts.has(e.pointerId)) return; pts.set(e.pointerId,e);
    if(pts.size===2&&pinch0){ const [a,b]=[...pts.values()];
      const d=Math.hypot(a.clientX-b.clientX,a.clientY-b.clientY);
      const rect=sc.getBoundingClientRect(); const cx=pinch0.mid-rect.left;
      const idx=(sc.scrollLeft+cx-20)/PPD;
      targetPPD=Math.min(Math.max(pinch0.ppd*d/pinch0.d,0.5),14); queueZoom(idx,cx); }});
  ["pointerup","pointercancel","pointerleave"].forEach(t=>sc.addEventListener(t,e=>{ pts.delete(e.pointerId); if(pts.size<2) pinch0=null; }));

  const jumps=document.getElementById("jumps");
  { const o=document.createElement("option"); o.value=""; o.textContent="Jump to year…"; jumps.appendChild(o); }
  for(let yy=2000; yy<=2026; yy++){ const o=document.createElement("option"); o.value=String(yy); o.textContent=String(yy); jumps.appendChild(o); }
  jumps.onchange=()=>{ if(!jumps.value) return;
    sc.scrollTo({left:Math.max(20+dayIdx(`${jumps.value}-01-01`)*PPD-sc.clientWidth/2,0),behavior:"smooth"});
    jumps.value=""; };

  // ---- GEO VIEW ----
  const GEO=DATA.geo;
  // --- merged multi-source model: the map mirrors the SELECTED sample sources, over the full record ---
  const siteRd=(d,code)=>{ const st=siteBy.get(d), r=st&&st[code]; return r?{ent:r.ent,ec:r.ec}:null; };
  const GSRC={
    beach:{pt:"LM5", get:d=>{const r=bcBy.get(d);return r?{ent:r.v,ec:r.ec}:null;}, std:"LM5"},
    creek:{pt:"SPCM",get:d=>{const r=ckBy.get(d);return r?{ent:r.ent,ec:r.v}:null;}, std:"SPCM"},
    bwtf: {pt:"SPCM",get:d=>{const r=bwBy.get(d);return r?{ent:r.v,ec:r.ec}:null;}, std:"SPCM"},
    LMMS:{pt:"LMMS",get:d=>siteRd(d,"LMMS"),std:"LMMS"},
    ADMS:{pt:"ADMS",get:d=>siteRd(d,"ADMS"),std:"ADMS"},
    PRLT:{pt:"PRLT",get:d=>siteRd(d,"PRLT"),std:"PRLT"},
    SPCM:{pt:"SPCM",get:d=>siteRd(d,"SPCM"),std:"SPCM"}};
  const SRCDATES={beach:[...bcBy.keys()],creek:[...ckBy.keys()],bwtf:[...bwBy.keys()],LMMS:[],ADMS:[],PRLT:[],SPCM:[]};
  DATA.sites.forEach(r=>{ if(SRCDATES[r.s]) SRCDATES[r.s].push(r.d); });
  const SRCFIRST={}; for(const id in SRCDATES){ SRCFIRST[id]=SRCDATES[id].length?SRCDATES[id].reduce((a,b)=>a<b?a:b):null; }
  const effSrcs=()=>{ const s=new Set(sampleOn); if(s.has("AVG")){ SITES.forEach(x=>s.add(x)); s.delete("AVG"); } return [...s].filter(id=>GSRC[id]); };
  const geoDates=()=>{ const set=new Set(); effSrcs().forEach(id=>SRCDATES[id].forEach(d=>set.add(d))); return [...set].sort(); };
  let gdates=[];
  const M=BASEMAP.meta, GW=400, GH=Math.round(GW*M.h/M.w);
  const mY=lat=>Math.asinh(Math.tan(lat*Math.PI/180));
  const GX=lon=>(lon-M.lonW)/(M.lonE-M.lonW)*GW;
  const GY=lat=>(mY(M.latN)-mY(lat))/(mY(M.latN)-mY(M.latS))*GH;
  const gm=document.getElementById("geomap");
  const GYT=Math.round(GY(37.600)), GYB=Math.round(GY(37.578)), GHC=GYB-GYT;
  gm.setAttribute("viewBox",`0 ${GYT} ${GW} ${GHC}`); gm.setAttribute("height",GHC);
  const HALO=`paint-order="stroke" stroke="#ffffff" stroke-width="3"`;
  function geoBase(active){
    let s=`<image href="${BASEMAP.url}" x="0" y="0" width="${GW}" height="${GH}"></image>`;
    const OFFC={SPCM:[13,12,"start"],LM5:[-12,2,"end"]};
    for(const [c,g] of Object.entries(GEO)){
      const on2=!active||active.has(c);
      const [dx,dy,an]=OFFC[c]||[12,4,"start"];
      s+=`<text x="${GX(g.lon)+dx}" y="${GY(g.lat)+dy}" text-anchor="${an}" font-size="10.5" font-weight="${on2?700:600}" fill="${on2?"#1b201e":"#6b7075"}" ${HALO}>${c}</text>`; }
    s+=`<text x="${GW-4}" y="${GYB-5}" text-anchor="end" font-size="8" fill="#555" ${HALO}>© OpenStreetMap</text>`;
    return s;
  }
  function geoFrame(k){
    const d=gdates[k];
    document.getElementById("geodate").textContent=d||"—";
    const srcs=d?effSrcs():[];
    const active=new Set(); srcs.forEach(id=>{ if(SRCFIRST[id]&&d>=SRCFIRST[id]) active.add(GSRC[id].pt); });
    let s=""; const hasRes=new Set();
    if(d){
      const byPt={}; srcs.forEach(id=>{ const p=GSRC[id].pt; (byPt[p]=byPt[p]||[]).push(id); });
      srcs.forEach(id=>{
        const src=GSRC[id], g=GEO[src.pt]; if(!g) return;
        const grp=byPt[src.pt], slot=grp.indexOf(id), n=grp.length;
        const cx=GX(g.lon)+(slot-(n-1)/2)*(n>1?18:0), cy=GY(g.lat);
        const rd=src.get(d), vs=[];
        if(rd){ if(anOn.has("ent")&&rd.ent!=null) vs.push(["ent",rd.ent]); if(anOn.has("ec")&&rd.ec!=null) vs.push(["ec",rd.ec]); }
        const scol=SERCOL[id]||"--samp";
        if(!vs.length) return;
        hasRes.add(src.pt); let anyOver=false;
        vs.forEach(([an,v])=>{ const over=v>stdFor(src.std,an); anyOver=anyOver||over;
          const rr=(4+Math.max(0,Math.min(1,Math.log10(Math.max(v,10)/10)/3))*13).toFixed(1);
          const col=colorBySite?css(scol):(over?css('--std'):css('--samp'));
          const ttl=`${esc(g.name)} — ${id} ${an==="ent"?"entero":"E. coli"}: ${Math.round(v).toLocaleString()}${over?" ✕":""}`;
          s+= an==="ent"
            ? `<circle cx="${cx}" cy="${cy}" r="${rr}" fill="${col}" opacity=".78" stroke="#ffffff" stroke-width="1.2"><title>${ttl}</title></circle>`
            : `<circle cx="${cx}" cy="${cy}" r="${rr}" fill="none" stroke="${col}" stroke-width="2.4"><title>${ttl}</title></circle>`; });
        const num=vs.map(([a2,v])=>Math.round(v).toLocaleString()).join(" / ");
        const lcol=colorBySite?css(scol):(anyOver?"#c22":"#1b201e");
        s+=`<text x="${cx}" y="${cy+18+slot*11}" text-anchor="middle" font-size="9.5" font-weight="700" fill="${lcol}" ${HALO}>${num}${(colorBySite&&anyOver)?" ✕":""}</text>`;
      });
    }
    let rings=""; for(const [c,g] of Object.entries(GEO)){ if(hasRes.has(c)) continue;
      rings+=`<circle cx="${GX(g.lon)}" cy="${GY(g.lat)}" r="4.5" fill="#ffffff" fill-opacity=".6" stroke="#80868b" stroke-width="1.6"></circle>`; }
    gm.innerHTML=geoBase(hasRes)+rings+s;
  }
  function graphTo(d){ if(d==null) return;
    const gi=idxOf.has(d)?idxOf.get(d):dayIdx(d);
    { const x=20+gi*PPD; if(x<sc.scrollLeft+30||x>sc.scrollLeft+sc.clientWidth-30) sc.scrollLeft=Math.max(x-sc.clientWidth/2,0); }
    const l=document.getElementById("xh"); if(l){ l.setAttribute("x1",20+gi*PPD); l.setAttribute("x2",20+gi*PPD); }
    show(gi); }
  const slider=document.getElementById("geoslider");
  slider.max=gdates.length-1; slider.value=gdates.length-1;
  slider.oninput=()=>{ const k=+slider.value; geoSync=true; geoFrame(k); graphTo(gdates[k]); geoSync=false; };
  let playing=null;
  document.getElementById("geoplay").onclick=function(){
    if(playing){ clearInterval(playing); playing=null; this.textContent="▶ Play the record"; return; }
    if(matchMedia("(prefers-reduced-motion: reduce)").matches){ return; }
    const n=gdates.length; if(n<2) return;
    let k=+slider.value>=n-1?0:+slider.value;
    this.textContent="⏸ Pause";
    // deliberate day-by-day pace: every frame shown, held long enough to read the change
    playing=setInterval(()=>{
      k=Math.min(k+1,n-1); slider.value=k; geoSync=true; geoFrame(k); graphTo(gdates[k]); geoSync=false;
      if(k>=n-1){ clearInterval(playing); playing=null; document.getElementById("geoplay").textContent="▶ Play the record"; }
    },500);
  };
  document.getElementById("mapbtn").onclick=function(){
    const g=document.getElementById("geo"); g.hidden=!g.hidden; geoFollow=!g.hidden;
    this.setAttribute("aria-pressed",String(!g.hidden)); };
  function geoRebuild(){
    const cur=gdates[+slider.value];
    gdates=geoDates(); slider.max=Math.max(gdates.length-1,0);
    let k=gdates.length-1;
    if(cur&&gdates.length){ let bd=Infinity; for(let j=0;j<gdates.length;j++){ const dd=Math.abs(+new Date(gdates[j])-+new Date(cur)); if(dd<bd){bd=dd;k=j;} } }
    slider.value=k; geoFrame(k);
  }
  function geoLegend(){
    const el=document.getElementById("geoleg"); if(!el) return;
    const mode=colorBySite
      ? 'Each source shows in its own color; <b>✕</b> marks a reading over the limit.'
      : '<b style="color:var(--std)">Red</b> = over the limit, orange = under.';
    el.innerHTML='Filled circle = enterococcus, ring = E. coli (set by the Bacteria filter); size = concentration (log scale); numbers = that day’s readings, in MPN per 100 mL. '+mode+' Grey ring = no result shown that day.';
  }
  geoLegend(); geoRebuild();

  // One row per summer: the winter before it (rain as % of normal on June 15) and the
  // typical result of that summer's rain-free creek tests (June–September, 7+ days after rain).
  // Shared by the Wet winters labels on the timeline and the summer-by-summer chart below.
  function summerRows(){ const out=[], last=+D[N-1].d.slice(0,4);
    for(let yy=2015; yy<=last; yy++){
      const wyv=(D[idxOf.get(`${yy}-06-15`)]||{}).wy; if(wyv==null) continue;
      const vals=DATA.creek.filter(pp=>{ const m=+pp.d.slice(5,7);
        return pp.v!=null&&pp.d.startsWith(String(yy))&&m>=6&&m<=9&&pp.dsr!=null&&pp.dsr>=7; }).map(pp=>pp.v);
      const gm=vals.length?10**(vals.reduce((a,v)=>a+Math.log10(Math.max(v,1)),0)/vals.length):null;
      out.push({y:yy, wy:wyv, cls:wyv>130?"wet":(wyv<70?"dry":"norm"), n:vals.length, gm, vals}); }
    return out; }

  // ---- FACTOR EXPLORER ----
  const dailyBy=new Map(D.map(r=>[r.d,r]));
  const XS=DATA.creek.filter(p=>p.v!=null).map(p=>({...p, dl:dailyBy.get(p.d)})).filter(p=>p.dl);
  const FACT=[
    ["wt","Does warm water matter?",p=>p.dl.wt,"°C",["cooler","middle","warmer"],
      ["Cooler water: bacteria die off faster.","","Warm water helps bacteria survive and regrow."]],
    ["dsr","Does recent rain matter?",p=>p.dsr,"d",["rain recently","in between","long dry"],
      ["Storm runoff is washing contamination in.","The storm's effect has faded — the creek's cleaner window.","Weeks without rain, yet results rise again. The data suggests a year-round source, not weather — see the Contamination without rain view."]],
    ["ev","Do bigger storms matter?",p=>(p.dsr!=null&&p.dsr<=3)?p.ev:null,"mm",["small storms","medium","big storms"],
      ["Smaller storms wash in less.","Middle-sized storms — the effect climbs steadily with size rather than jumping at a threshold.","Bigger storms wash in more."],
      "Only days within three days of a storm are counted here, so the size refers to the storm that just happened."],
    ["flow","Does creek flow matter?",p=>p.dl.f,"",["low flow","middle","high flow"],
      ["Little runoff — what remains may be the year-round source.","","High flow follows storms."]],
    ["grnd","Does wet ground matter?",p=>p.dl.s,"",["dry ground","middle","wet ground"],
      ["Little water moving underground.","","Wet ground keeps feeding the creek after the rain ends."]],
    ["wy","Does the winter's rain matter?",null,"%",["dry winters","normal","wet winters"],
      ["After a dry winter the ground holds less water, and summer tests have mostly run cleaner.","","After a wet winter, stored water keeps feeding the creek for months, and may carry contamination with it. That would explain why summers after wet winters have tested worse."],
      "County creek record, June through September, tests taken at least 7 days after rain. One dot per summer."],
    ["site","Does the location matter?",null,"cat",null,null,
      "Coalition data, 2024 onward, E. coli. One bar per site, upstream to downstream. Restrictions still apply."],
    ["hr","Does time of day matter?",p=>p.hr,"h",["early","mid-morning","later"],
      ["Earlier samples run higher — the data suggests overnight build-up.","","By late morning, levels have usually dropped."]],
    ["tide","Does the tide matter?",null,"cat",null,null,
      "County beach station tests at the recorded sampling minute; the one station standing in tidal water. The 2014 → restriction is on by default so the comparison reflects today\u2019s beach — turn it off to include the cleaner early record (see The beach used to be cleaner)."],
  ];
  const RES=[["dry","rain-free (≥7d)",p=>p.dsr>=7],
             ["summer","summer (Jun–Sep)",p=>{const m=+p.d.slice(5,7);return m>=6&&m<=9;}],
             ["decline","2014 → (the decline era)",p=>p.d>="2014"],
             ["modern","2022 → (after the level jump)",p=>p.d>="2022"]];
  const ELAB={
    wt:"Warmth matters. Warmer weeks test worse even without rain, which fits bacteria surviving and regrowing in warm water. This is part of why late summer is often the worst season.",
    dsr:"Rain matters most in the first two days, and the effect fades within about four. But notice the long-dry days: results rise again with no rain at all, which points to a year-round source beyond weather.",
    ev:"The more rain a storm brings, the worse the following days test. The effect climbs steadily with storm size rather than switching on at a threshold.",
    flow:"Results track the creek's estimated flow: high flow follows storms and carries runoff in. The low-flow days that still test high are the ones weather cannot explain.",
    grnd:"Wet ground keeps feeding the creek after storms end, and the tests follow: the wetter the ground, the worse the results, even days after the rain stops.",
    wy:"The winter's total appears to echo for months: a wet winter leaves more water in the ground, and the summers that follow have mostly tested worse. But a handful of summers cannot settle it, and the dots do not all fall in line. Treat this as a lead to keep testing. The Wet winters view shows the same summers on the timeline.",
    hr:"Morning samples run higher than late-morning ones. Part of the week-to-week difference is simply what time the bottle was filled.",
    site:"What this suggests: water flows Linda Mar Bridge → Sanchez Adobe → Peralta Bridge → the creek mouth. On rain-free days the level climbs through the middle of that path and eases again by the mouth. Storm runoff cannot produce a pattern that persists without rain; a steady entry in the Sanchez Adobe–to–Peralta Bridge stretch can. That reading is consistent with the DNA source-tracking, which points to human waste — and that stretch is where the search for the source is focused.",
    tide:"Since the decline began in 2014, the typical result sits well above the geometric-mean standard in every tide window — no tide window makes today\u2019s beach reliably clean — and tests near low tide fail modestly more often than tests near high tide, which fits the creek\u2019s plume being drawn across the beach as the water drops. The full record since 2001 shows the same pattern, about 1.3×. The creek itself shows no tide pattern at all — it flows out regardless of tide, as anyone standing at it can see: the tide does not change what the creek carries, it moves the creek\u2019s plume around on the beach. Tide height on its own, and direction — coming in versus going out — show no effect either way."};
  let xfSel="wt", xres=new Set(), xdep=false;
  const bkey=p=>p.d.slice(5,7)+"|"+(p.d<"2020"?"a":"b");
  const bl=new Map();
  { const acc={}; XS.forEach(p=>{ const k=bkey(p); (acc[k]=acc[k]||[]).push(Math.log10(Math.max(p.v,1))); });
    for(const k in acc) bl.set(k, acc[k].reduce((a,b)=>a+b,0)/acc[k].length); }
  const qtl=(arr,f)=>{ const s=[...arr].sort((a,b)=>a-b); return s[Math.floor(f*(s.length-1))]; };
  const fmtv=v=>v>=100?String(Math.round(v)):(v>=10?v.toFixed(0):v.toFixed(1));
  const XHOW=document.getElementById("xhow").textContent;
  let LASTS=null;
  function xrender(){ LASTS=null;
    const fd=FACT.find(f=>f[0]===xfSel);
    document.getElementById("xhow").textContent=XHOW;
    if(fd[0]==="site"){
      const ORDER=["LMMS","ADMS","PRLT","SPCM"], SUB={LMMS:"upstream",ADMS:"mid-valley",PRLT:"lower valley",SPCM:"creek mouth"};
      const SN={LMMS:"Top of the urban reach — water arriving from the parkland forks.",
        ADMS:"At the Sanchez Adobe — upstream of where the dry-weather load enters.",
        PRLT:"In dry weather the level roughly doubles between Adobe Sanchez and here.",
        SPCM:"Where the creek crosses the beach."};
      const pool=DATA.sites.filter(pp=>{ const i=idxOf.get(pp.d); if(i==null||pp.ec==null) return false;
        return [...xres].every(id=>RES.find(r=>r[0]===id)[2]({dsr:DSR[i], d:pp.d})); });
      const stat2=vals=>{ if(!vals.length) return {n:0};
        const ls=vals.map(v=>Math.log10(Math.max(v,1))), m=ls.reduce((a2,b2)=>a2+b2,0)/ls.length, bs=[];
        for(let i2=0;i2<200;i2++){ let s3=0; for(let j=0;j<ls.length;j++) s3+=ls[Math.floor(Math.random()*ls.length)]; bs.push(s3/ls.length); }
        bs.sort((a2,b2)=>a2-b2);
        return {n:vals.length, gm:10**m, lo:10**bs[4], hi:10**bs[194], over:vals.filter(v=>v>320).length/vals.length}; };
      const S=ORDER.map(code=>({l:code, rng:SUB[code], note:SN[code], ...stat2(pool.filter(pp=>pp.s===code).map(pp=>pp.ec))}));
      const vmax=Math.max(...S.map(s2=>s2.hi||0),650)*1.15, vmin=10;
      const Yb=v=>150-130*(Math.log10(Math.max(v,vmin))-Math.log10(vmin))/(Math.log10(vmax)-Math.log10(vmin));
      let sv=`<svg width="${44+S.length*136}" height="200" role="img">
        <line x1="0" x2="${44+S.length*136}" y1="${Yb(100)}" y2="${Yb(100)}" stroke="${css('--std')}" stroke-dasharray="1 3" opacity=".85"></line>
        <text x="${S.length*136-8}" y="${Yb(100)-4}" font-size="9" fill="${css('--std')}">geo-mean std 100</text>`;
      S.forEach((s2,i)=>{ if(!s2.n) return;
        const x=44+i*136, ok=s2.n>=15, col=ok?css('--creek'):css('--muted');
        sv+=`<rect x="${x}" y="${Yb(s2.gm)}" width="66" height="${Math.max(150-Yb(s2.gm),2)}" rx="4" fill="${col}" opacity="${ok?0.9:0.35}" data-note="${s2.note}"></rect>
          <line x1="${x+33}" x2="${x+33}" y1="${Yb(s2.hi)}" y2="${Yb(s2.lo)}" stroke="${css('--card')}" stroke-width="4.5" opacity=".9"></line>
          <line x1="${x+33}" x2="${x+33}" y1="${Yb(s2.hi)}" y2="${Yb(s2.lo)}" stroke="${css('--ink')}" stroke-width="1.6"></line>
          <line x1="${x+25}" x2="${x+41}" y1="${Yb(s2.hi)}" y2="${Yb(s2.hi)}" stroke="${css('--ink')}" stroke-width="1.6"></line>
          <line x1="${x+25}" x2="${x+41}" y1="${Yb(s2.lo)}" y2="${Yb(s2.lo)}" stroke="${css('--ink')}" stroke-width="1.6"></line>
          <text x="${x+33}" y="${Yb(s2.hi)-11}" text-anchor="middle" font-size="11.5" font-weight="600" fill="${css('--ink')}">${Math.round(s2.gm)}</text>
          <text x="${x+33}" y="170" text-anchor="middle" font-size="11" fill="${css('--ink2')}">${s2.l} (${s2.rng})</text>
          <text x="${x+33}" y="186" text-anchor="middle" font-size="10" fill="${css('--muted')}">n=${s2.n}${ok?"":" — too few"}</text>`; });
      document.getElementById("xplot").innerHTML=sv+"</svg>"; LASTS=S;
      const good=S.filter(s2=>s2.n>=15);
      let read="Bins too thin — loosen the restrictions.";
      if(good.length>=2){ const hi2=good.reduce((a2,b2)=>b2.gm>a2.gm?b2:a2), lo2=good.reduce((a2,b2)=>b2.gm<a2.gm?b2:a2);
        const FULLN={LMMS:"Linda Mar Bridge",ADMS:"Sanchez Adobe",PRLT:"Peralta Bridge",SPCM:"the creek mouth"};
        const nn=hi2.n===lo2.n?`${hi2.n} tests at each site`:`${hi2.n} vs ${lo2.n} tests`;
        read=`<b>Location:</b> the typical result at ${FULLN[hi2.l]||hi2.l} is <b>${(hi2.gm/lo2.gm).toFixed(1)}×</b> ${FULLN[lo2.l]||lo2.l}’s (${nn}) — ${Math.round(hi2.over*100)}% vs ${Math.round(lo2.over*100)}% of samples over the standard.`; }
      const scope2=fd[6]?`<div class="small" style="margin-top:5px">${fd[6]}</div>`:"";
      document.getElementById("xread").innerHTML=read+scope2
        +((good.length>=2&&ELAB.site)?`<div style="margin-top:6px">${ELAB.site}</div>`:"");
      const xc2=document.getElementById("xcard");
      if(xc2){ xc2.classList.remove("xpulse"); void xc2.offsetWidth; xc2.classList.add("xpulse"); }
      document.getElementById("xfoot").textContent="Bars are typical results (geometric means), so the dotted line is the freshwater geometric-mean standard, 100 — the stricter primary standard. Single tests are judged against 320; the verdict counts how often tests exceed it. Coalition data, cfu per 100 mL. Sites are categories, not a scale — no correlation score applies. Whiskers are 95% bootstrap confidence intervals.";
      return;
    }
    if(fd[0]==="tide"){
      const W=[["near high tide",pp=>Math.abs(pp.tp)<=2.07,"within ~2h of high"],
               ["in between",pp=>Math.abs(pp.tp)>2.07&&Math.abs(pp.tp)<4.14,"mid-cycle"],
               ["near low tide",pp=>Math.abs(pp.tp)>=4.14,"within ~2h of low"]];
      const BN=["The ocean stands at or near full — the creek\u2019s outflow is held close to the mouth.","",
        "The creek\u2019s outflow has been drawn farthest across the beach face."];
      const pool=DATA.beach.filter(pp=>pp.tp!=null&&pp.v!=null&&[...xres].every(id=>RES.find(r=>r[0]===id)[2](pp)));
      const stat2=vals=>{ if(!vals.length) return {n:0};
        const ls=vals.map(v=>Math.log10(Math.max(v,1))), m=ls.reduce((a2,b2)=>a2+b2,0)/ls.length, bs=[];
        for(let i2=0;i2<200;i2++){ let s3=0; for(let j=0;j<ls.length;j++) s3+=ls[Math.floor(Math.random()*ls.length)]; bs.push(s3/ls.length); }
        bs.sort((a2,b2)=>a2-b2);
        return {n:vals.length, gm:10**m, lo:10**bs[4], hi:10**bs[194], over:vals.filter(v=>v>104).length/vals.length}; };
      const S=W.map(([l,f,rng],i)=>({l,rng,note:BN[i],...stat2(pool.filter(f).map(pp=>pp.v))}));
      const vmax=Math.max(...S.map(s2=>s2.hi||0),160)*1.15, vmin=10;
      const Yb=v=>150-130*(Math.log10(Math.max(v,vmin))-Math.log10(vmin))/(Math.log10(vmax)-Math.log10(vmin));
      let sv=`<svg width="${44+S.length*136}" height="200" role="img">
        <line x1="0" x2="${44+S.length*136}" y1="${Yb(35)}" y2="${Yb(35)}" stroke="${css('--std')}" stroke-dasharray="4 4" opacity=".7"></line>
        <text x="${S.length*136-8}" y="${Yb(35)-4}" font-size="9" fill="${css('--std')}">geo-mean standard 35</text>`;
      S.forEach((s2,i)=>{ if(!s2.n) return;
        const x=44+i*136, ok=s2.n>=15, col=ok?css('--creek'):css('--muted');
        sv+=`<rect x="${x}" y="${Yb(s2.gm)}" width="66" height="${Math.max(150-Yb(s2.gm),2)}" rx="4" fill="${col}" opacity="${ok?0.9:0.35}"${s2.note?` data-note="${s2.note}"`:""}></rect>
          <line x1="${x+33}" x2="${x+33}" y1="${Yb(s2.hi)}" y2="${Yb(s2.lo)}" stroke="${css('--card')}" stroke-width="4.5" opacity=".9"></line>
          <line x1="${x+33}" x2="${x+33}" y1="${Yb(s2.hi)}" y2="${Yb(s2.lo)}" stroke="${css('--ink')}" stroke-width="1.6"></line>
          <line x1="${x+25}" x2="${x+41}" y1="${Yb(s2.hi)}" y2="${Yb(s2.hi)}" stroke="${css('--ink')}" stroke-width="1.6"></line>
          <line x1="${x+25}" x2="${x+41}" y1="${Yb(s2.lo)}" y2="${Yb(s2.lo)}" stroke="${css('--ink')}" stroke-width="1.6"></line>
          <text x="${x+33}" y="${Yb(s2.hi)-11}" text-anchor="middle" font-size="11.5" font-weight="600" fill="${css('--ink')}">${Math.round(s2.gm)}</text>
          <text x="${x+33}" y="170" text-anchor="middle" font-size="11" fill="${css('--ink2')}">${s2.l}</text>
          <text x="${x+33}" y="186" text-anchor="middle" font-size="10" fill="${css('--muted')}">${s2.rng} · n=${s2.n}${ok?"":" — too few"}</text>`; });
      document.getElementById("xplot").innerHTML=sv+"</svg>"; LASTS=S;
      const a2=S[0], c2=S[2], okC=a2.n>=15&&c2.n>=15;
      const ratio=c2.gm/a2.gm;
      const read=!okC
        ? "Bins too thin for a fair comparison — loosen the restrictions."
        : (ratio<1.15&&ratio>0.87)
        ? `<b>The tide:</b> the three windows are close — ${Math.round(a2.over*100)}%, ${Math.round(S[1].over*100)}% and ${Math.round(c2.over*100)}% of tests over the single-test standard (104). On today's beach the tide barely changes the odds.`
        : `<b>The tide:</b> the typical result near low tide is <b>${ratio.toFixed(1)}×</b> the result near high tide (${c2.n} vs ${a2.n} tests) — ${Math.round(c2.over*100)}% vs ${Math.round(a2.over*100)}% of tests over the single-test standard (104).`;
      const scope2=fd[6]?`<div class="small" style="margin-top:5px">${fd[6]}</div>`:"";
      document.getElementById("xread").innerHTML=read+scope2
        +((okC&&ELAB.tide)?`<div style="margin-top:6px">${ELAB.tide}</div>`:"");
      const xc2=document.getElementById("xcard");
      if(xc2){ xc2.classList.remove("xpulse"); void xc2.offsetWidth; xc2.classList.add("xpulse"); }
      document.getElementById("xfoot").textContent="Bars are typical results (geometric means), so the dashed line is the ocean geometric-mean standard, 35 — the stricter primary standard. Single tests are judged against 104; the verdict counts how often tests exceed it. County beach station, enterococcus per 100 mL, at the recorded sampling minute; tide from NOAA predictions (Half Moon Bay open-coast station); fixed ~2-hour windows around each turn. Whiskers are 95% bootstrap confidence intervals.";
      return;
    }
    if(fd[0]==="wy"){
      const S=summerRows().filter(s2=>s2.gm!=null), ok=S.filter(s2=>s2.n>=5);
      if(ok.length<4){ document.getElementById("xplot").innerHTML="";
        document.getElementById("xread").textContent="Not enough summers on record yet.";
        document.getElementById("xfoot").textContent=""; return; }
      // fit the chart to narrow screens: the comparison is left against right, so it must not scroll sideways
      const W=Math.max(300,Math.min(440,document.getElementById("xwrap").clientWidth||440)), H=256, L=40, R=W-26, T=24, B=204;
      const ws=S.map(s2=>s2.wy), gs=S.map(s2=>s2.gm);
      const lo=Math.min(30,Math.floor((Math.min(...ws)-8)/10)*10), hi=Math.max(190,Math.ceil((Math.max(...ws)+8)/10)*10);
      const ymin=Math.min(40,Math.min(...gs)*0.8), ymax=Math.max(1000,Math.max(...gs)*1.25);
      const X=v=>L+(v-lo)/(hi-lo)*(R-L);
      const Y=v=>B-(Math.log10(v)-Math.log10(ymin))/(Math.log10(ymax)-Math.log10(ymin))*(B-T);
      const pool=cls=>{ const v=S.filter(s2=>s2.cls===cls).flatMap(s2=>s2.vals); if(!v.length) return null;
        return {n:v.length, gm:10**(v.reduce((a2,x)=>a2+Math.log10(Math.max(x,1)),0)/v.length), over:v.filter(x=>x>320).length/v.length}; };
      const dry=pool("dry"), wet=pool("wet");
      const nDry=ok.filter(s2=>s2.cls==="dry").length, nWet=ok.filter(s2=>s2.cls==="wet").length;
      const wetLow=Math.min(...ok.filter(s2=>s2.cls==="wet").map(s2=>s2.gm));
      const odd=ok.filter(s2=>s2.cls==="dry"&&s2.gm>=wetLow).map(s2=>s2.y);
      let sv=`<svg width="${W}" height="${H}" role="img" aria-label="One dot per summer: the winter's rain against that summer's typical rain-free result.">`;
      [50,100,200,400,800].filter(v=>v>=ymin&&v<=ymax).forEach(v=>{
        sv+=(v===100
          ? `<line x1="${L}" x2="${R}" y1="${Y(v)}" y2="${Y(v)}" stroke="${css('--std')}" stroke-dasharray="1 3" opacity=".85"></line>`
          : `<line x1="${L}" x2="${R}" y1="${Y(v)}" y2="${Y(v)}" stroke="${css('--line')}"></line>`)
          +`<text x="${L-6}" y="${Y(v)+3}" text-anchor="end" font-size="9.5" fill="${css('--muted')}">${v}</text>`; });
      sv+=`<text x="6" y="12" font-size="10" fill="${css('--muted')}">each summer’s typical result</text>
        <text x="${R}" y="${Y(100)-4}" text-anchor="end" font-size="9" fill="${css('--std')}">geo-mean std 100</text>
        <line x1="${L}" x2="${R}" y1="${B}" y2="${B}" stroke="${css('--muted')}" opacity=".55"></line>`;
      [70,130].forEach(v=>{ sv+=`<line x1="${X(v)}" x2="${X(v)}" y1="${T}" y2="${B}" stroke="${css('--muted')}" stroke-dasharray="3 4" opacity=".6"></line>`; });
      [50,100,150,200].filter(v=>v>lo&&v<hi).forEach(v=>{
        sv+=`<text x="${X(v)}" y="${B+13}" text-anchor="middle" font-size="9.5" fill="${css('--muted')}">${v}%</text>`; });
      [[(lo+70)/2,0],[100,1],[(130+hi)/2,2]].forEach(([v,i])=>{ const note=(fd[5]&&fd[5][i])||"";
        sv+=`<text x="${X(v)}" y="${B+29}" text-anchor="middle" font-size="10.5" fill="${css('--ink2')}"${note?` data-note="${note}" style="cursor:default"`:""}>${fd[4][i]}</text>`; });
      sv+=`<text x="${(L+R)/2}" y="${B+46}" text-anchor="middle" font-size="10" fill="${css('--muted')}">rain in the winter before, as % of normal</text>`;
      // year labels: take the first spot beside each dot that touches no other dot or label
      // (most crowded dots choose first; if every spot touches something, take the one that overlaps least)
      S.forEach(s2=>{ s2.px=X(s2.wy); s2.py=Y(s2.gm); });
      const boxes=[[R-90,Y(100)-14,R,Y(100)-1]].concat(S.map(s2=>[s2.px-6.5,s2.py-6.5,s2.px+6.5,s2.py+6.5]));
      const ovl=(b,skip)=>boxes.reduce((a2,o,i)=>i===skip?a2:a2+Math.max(0,Math.min(b[2],o[2])-Math.max(b[0],o[0]))*Math.max(0,Math.min(b[3],o[3])-Math.max(b[1],o[1])),0);
      const crowd=s2=>S.filter(o=>o!==s2&&Math.abs(o.px-s2.px)<44&&Math.abs(o.py-s2.py)<26).length;
      [...S].sort((a2,b2)=>crowd(b2)-crowd(a2)||a2.y-b2.y).forEach(s2=>{ const {px,py}=s2, lw=27, own=1+S.indexOf(s2);
        const spots=[["start",px+9,py+3.5,[px+8,py-6,px+8+lw,py+6]],["end",px-9,py+3.5,[px-8-lw,py-6,px-8,py+6]],
                    ["middle",px,py-10,[px-lw/2,py-19,px+lw/2,py-8]],["middle",px,py+18,[px-lw/2,py+8,px+lw/2,py+20]],
                    ["start",px+6,py-8,[px+5,py-18,px+5+lw,py-6.6]],["start",px+6,py+15,[px+5,py+6.6,px+5+lw,py+18]],
                    ["end",px-6,py-8,[px-5-lw,py-18,px-5,py-6.6]],["end",px-6,py+15,[px-5-lw,py+6.6,px-5,py+18]]];
        const inside=spots.filter(c=>c[3][0]>=L-2&&c[3][2]<=W-2&&c[3][1]>=T-10&&c[3][3]<=B+1), cand=inside.length?inside:spots;
        s2.lab=cand.find(c=>ovl(c[3],own)===0)||[...cand].sort((a2,b2)=>ovl(a2[3],own)-ovl(b2[3],own))[0];
        boxes.push(s2.lab[3]); });
      S.forEach(s2=>{ const few=s2.n<5, call=odd.includes(s2.y);
        const note=`Summer ${s2.y}: typical ${Math.round(s2.gm)} across ${s2.n} rain-free test${s2.n===1?"":"s"}, ${s2.vals.filter(x=>x>320).length} over the single-test standard (320). The winter before brought ${Math.round(s2.wy)}% of normal rain.${few?" Too few tests to judge this summer.":""}`;
        sv+=(few
          ? `<circle cx="${s2.px}" cy="${s2.py}" r="4.5" fill="${css('--card')}" stroke="${css('--muted')}" stroke-width="1.4" opacity=".8"></circle>`
          : `<circle cx="${s2.px}" cy="${s2.py}" r="5.5" fill="${css('--creek')}" stroke="${css('--card')}" stroke-width="2"></circle>`)
          +`<text x="${s2.lab[1]}" y="${s2.lab[2]}" text-anchor="${s2.lab[0]}" font-size="10.5" font-weight="${call?650:400}" fill="${css(few?'--muted':(call?'--ink':'--ink2'))}">${s2.y}</text>
          <circle cx="${s2.px}" cy="${s2.py}" r="13" fill="transparent" data-note="${note}"></circle>`; });
      document.getElementById("xplot").innerHTML=sv+"</svg>"; LASTS=S;
      const yrs=odd.length>1?odd.slice(0,-1).join(", ")+" and "+odd[odd.length-1]:String(odd[0]);
      const read=(dry&&wet&&nDry&&nWet
        ? `<b>${fd[1]}</b> Each dot is one summer. After wet winters the creek’s rain-free summer tests have typically run <b>${(wet.gm/dry.gm).toFixed(1)}×</b> those after dry winters (${Math.round(wet.gm)} vs ${Math.round(dry.gm)}; ${Math.round(wet.over*100)}% vs ${Math.round(dry.over*100)}% over the standard). That rests on <b>${ok.length} summers</b> — ${nWet} after wet winters, ${nDry} after dry.`
          +(odd.length?` Summer${odd.length>1?"s":""} ${yrs} followed ${odd.length>1?"dry winters":"a dry winter"} yet tested as high as the wet-winter summers.`:"")
        : `<b>${fd[1]}</b> Each dot is one summer. There are not yet enough dry-winter and wet-winter summers to compare.`);
      document.getElementById("xread").innerHTML=read+`<div class="small" style="margin-top:5px">${fd[6]}</div>`
        +(ELAB.wy?`<div style="margin-top:6px">${ELAB.wy}</div>`:"");
      document.getElementById("xhow").textContent="How to read it: each dot is one summer. Left to right is how much rain the winter before brought; up and down is that summer’s typical result (geometric mean) in rain-free weeks. If wet winters make for worse summers, the dots climb from lower left to upper right. Hover over or tap a dot for its numbers.";
      const rk2=v=>{ const o=v.map((x,i)=>[x,i]).sort((a2,b2)=>a2[0]-b2[0]), out=new Array(v.length); o.forEach(([_,i],r2)=>out[i]=r2); return out; };
      const rx2=rk2(ok.map(s2=>s2.wy)), ry2=rk2(ok.map(s2=>s2.gm)), m2=(ok.length-1)/2; let nu=0, d1=0, d2=0;
      for(let i=0;i<rx2.length;i++){ nu+=(rx2[i]-m2)*(ry2[i]-m2); d1+=(rx2[i]-m2)**2; d2+=(ry2[i]-m2)**2; }
      const xc3=document.getElementById("xcard");
      if(xc3){ xc3.classList.remove("xpulse"); void xc3.offsetWidth; xc3.classList.add("xpulse"); }
      document.getElementById("xfoot").textContent=`Each dot is the geometric mean of one summer’s tests, so the dotted line is the geometric-mean standard, 100 — the stricter primary standard; single tests are judged against 320. Winter rain is the season’s total on June 15 as a percent of the long-term average for that date, from the weather-model rain record. The dashed lines at 70% and 130% divide dry, normal and wet winters, as in the Wet winters view. Faint rings are summers with fewer than 5 such tests. Expert footnote: Spearman ρ = ${(nu/Math.sqrt(d1*d2)).toFixed(2)} across the ${ok.length} summers with 5 or more tests — on so few points, suggestive rather than established. Grouping the tests into bars would hide how few summers there are, which is why each one is drawn.`;
      return;
    }
    const g=XS.filter(p=>[...xres].every(id=>RES.find(r=>r[0]===id)[2](p)));
    const rows=g.map(p=>({x:fd[2](p), y:Math.log10(Math.max(p.v,1))-(xdep?bl.get(bkey(p)):0), raw:p.v}))
                .filter(r=>r.x!=null&&isFinite(r.x));
    if(rows.length<30){ document.getElementById("xplot").innerHTML="";
      document.getElementById("xread").textContent="Not enough samples under these restrictions.";
      document.getElementById("xfoot").textContent=""; return; }
    const xs=rows.map(r=>r.x), t1=qtl(xs,1/3), t2=qtl(xs,2/3);
    const W3=fd[4]||["low","mid","high"];
    const bins=[[W3[0],rows.filter(r=>r.x<=t1),"≤"+fmtv(t1)],[W3[1],rows.filter(r=>r.x>t1&&r.x<=t2),fmtv(t1)+"–"+fmtv(t2)],[W3[2],rows.filter(r=>r.x>t2),">"+fmtv(t2)]];
    const stat=b=>{ const ys=b.map(r=>r.y); if(!ys.length) return {n:0};
      const m=ys.reduce((a,c)=>a+c,0)/ys.length, bs=[];
      for(let i=0;i<200;i++){ let s2=0; for(let j=0;j<ys.length;j++) s2+=ys[Math.floor(Math.random()*ys.length)]; bs.push(s2/ys.length); }
      bs.sort((a,b2)=>a-b2);
      return {n:ys.length, gm:10**m, lo:10**bs[4], hi:10**bs[194], over:b.filter(r=>r.raw>320).length/ys.length}; };
    const S=bins.map(([l,b,rng])=>({l,rng,...stat(b)}));
    const vmax=Math.max(...S.map(s=>s.hi||0), xdep?2.5:650)*1.15, vmin=xdep?0.25:10;
    const Yb=v=>150-130*(Math.log10(Math.max(v,vmin))-Math.log10(vmin))/(Math.log10(vmax)-Math.log10(vmin));
    let sv=`<svg width="440" height="200" role="img">`;
    sv+= xdep
      ? `<line x1="0" x2="440" y1="${Yb(1)}" y2="${Yb(1)}" stroke="${css('--muted')}" stroke-dasharray="3 3"></line><text x="400" y="${Yb(1)-4}" font-size="9" fill="${css('--muted')}">typical</text>`
      : `<line x1="0" x2="440" y1="${Yb(100)}" y2="${Yb(100)}" stroke="${css('--std')}" stroke-dasharray="1 3" opacity=".85"></line><text x="378" y="${Yb(100)-4}" font-size="9" fill="${css('--std')}">geo-mean std 100</text>`;
    S.forEach((s2,i)=>{ if(!s2.n) return;
      const x=44+i*136, ok=s2.n>=15, col=ok?css('--creek'):css('--muted');
      const note=(fd[5]&&fd[5][i])||"";
      sv+=`<rect x="${x}" y="${Yb(s2.gm)}" width="66" height="${Math.max(150-Yb(s2.gm),2)}" rx="4" fill="${col}" opacity="${ok?0.9:0.35}"${note?` data-note="${note}"`:""}></rect>
        <line x1="${x+33}" x2="${x+33}" y1="${Yb(s2.hi)}" y2="${Yb(s2.lo)}" stroke="${css('--card')}" stroke-width="4.5" opacity=".9"></line>
          <line x1="${x+33}" x2="${x+33}" y1="${Yb(s2.hi)}" y2="${Yb(s2.lo)}" stroke="${css('--ink')}" stroke-width="1.6"></line>
          <line x1="${x+25}" x2="${x+41}" y1="${Yb(s2.hi)}" y2="${Yb(s2.hi)}" stroke="${css('--ink')}" stroke-width="1.6"></line>
          <line x1="${x+25}" x2="${x+41}" y1="${Yb(s2.lo)}" y2="${Yb(s2.lo)}" stroke="${css('--ink')}" stroke-width="1.6"></line>
        <text x="${x+33}" y="${Yb(s2.hi)-11}" text-anchor="middle" font-size="11.5" font-weight="600" fill="${css('--ink')}">${xdep?s2.gm.toFixed(2)+"×":Math.round(s2.gm)}</text>
        <text x="${x+33}" y="170" text-anchor="middle" font-size="11" fill="${css('--ink2')}">${s2.l} (${s2.rng}${fd[3]})</text>
        <text x="${x+33}" y="186" text-anchor="middle" font-size="10" fill="${css('--muted')}">n=${s2.n}${ok?"":" — too few"}</text>`; });
    sv+="</svg>";
    document.getElementById("xplot").innerHTML=sv; LASTS=S;
    const a=S[0], c=S[2];
    const scope=fd[6]?`<div class="small" style="margin-top:5px">${fd[6]}</div>`:"";
    const okCmp=a.n>=15&&c.n>=15;
    document.getElementById("xread").innerHTML = (okCmp
      ? `<b>${fd[1]}:</b> the typical result on ${W3[2]} days is <b>${(c.gm/a.gm).toFixed(1)}×</b> the ${W3[0]} days’${xdep?" (each measured against its season’s average)":""} — ${Math.round(c.over*100)}% vs ${Math.round(a.over*100)}% of samples over the standard (${c.n} vs ${a.n} tests).`
      : "Bins too thin for a fair comparison — loosen the restrictions.")+scope
      +(xdep?`<div class="small" style="margin-top:5px">Shown as multiples of the seasonal average. 1× equals that season's average — which is not a safe level; at this creek the average often exceeds the health standard.</div>`:"")
      +((okCmp&&ELAB[xfSel])?`<div style="margin-top:6px">${ELAB[xfSel]}</div>`:"");
    const rk=v=>{ const idx=v.map((x,i)=>[x,i]).sort((p2,q2)=>p2[0]-q2[0]); const out=new Array(v.length);
      idx.forEach(([_,i],r2)=>out[i]=r2); return out; };
    const rx=rk(rows.map(r=>r.x)), ry=rk(rows.map(r=>r.y));
    const mx=(rows.length-1)/2, my=mx; let num=0,dx=0,dy=0;
    for(let i=0;i<rx.length;i++){ num+=(rx[i]-mx)*(ry[i]-my); dx+=(rx[i]-mx)**2; dy+=(ry[i]-my)**2; }
    const xc=document.getElementById("xcard");
    if(xc){ xc.classList.remove("xpulse"); void xc.offsetWidth; xc.classList.add("xpulse"); }
    document.getElementById("xfoot").textContent=`Bars are typical results (geometric means), so the dotted line is the geometric-mean standard, 100 — the stricter primary standard; single tests are judged against 320, and the verdict counts how often tests exceed it. Expert footnote: Spearman ρ = ${(num/Math.sqrt(dx*dy)).toFixed(2)} on n=${rows.length}. Grab-sample noise caps any correlation near ~0.6 — small coefficients here can be large real effects; the ratio above is the meaningful number. Whiskers are 95% bootstrap confidence intervals.`;
  }
  const xfp=document.getElementById("xf");
  FACT.forEach(([id,label])=>{ const b=document.createElement("button"); b.textContent=label;
    b.setAttribute("aria-pressed",String(id===xfSel));
    b.onclick=()=>{ xfSel=id; xfp.querySelectorAll("button").forEach(x=>x.setAttribute("aria-pressed","false"));
      b.setAttribute("aria-pressed","true"); if(typeof syncConflicts==="function") syncConflicts(); xrender(); };
    xfp.appendChild(b); });
  const xrp=document.getElementById("xr");
  const allBtn=document.createElement("button"); allBtn.textContent="All days";
  allBtn.setAttribute("aria-pressed","true");
  attachTip(allBtn,"All days","No restriction — every water test is included.",null);
  allBtn.onclick=()=>{ xres.clear(); syncXres(); xrender(); };
  xrp.appendChild(allBtn);
  function syncXres(){ allBtn.setAttribute("aria-pressed",String(xres.size===0));
    xrp.querySelectorAll("button").forEach(b2=>{ if(b2!==allBtn&&b2.dataset.r) b2.setAttribute("aria-pressed",String(xres.has(b2.dataset.r))); }); }
  const RTIP={dry:["Rain-free days","Only tests taken at least 7 days after any rain — isolates the creek's dry-weather behavior. Hidden on the rain questions, which need rainy days included."],
    summer:["Summer (Jun–Sep)","Only tests from June through September — the warm, low-flow season."],
    decline:["2014 → (the decline era)","The county beach record turns in 2014. Before it, the beach passed almost every test — 9% of tests over the standard, typical level 19. Since: 35% over (typical 57) through 2021, then 61% over (typical 155) from 2022 on. On by default for the tide question so the comparison reflects today\u2019s beach; turn it off — or press All days — to include the cleaner early record. The beach used to be cleaner view tells this story on the timeline."],
    modern:["2022 → (after the level jump)","In 2022 the creek\u2019s typical level jumped to roughly four times its calmest years — 2020\u201321 ran near the geometric-mean standard, with only 20% of tests over the single-test standard — and it has stayed near that higher level since. The current regime. The jump is documented in the project findings; this restriction checks whether a pattern still holds in these recent years."]};
  const QCHIPS={wt:["dry","summer","modern"], dsr:["modern"], ev:["modern"],
    flow:["dry","summer","modern"], grnd:["dry","summer","modern"], wy:[],
    site:["dry","summer"], hr:["dry","summer","modern"], tide:["decline","dry","summer","modern"]};
  RES.forEach(([id,label])=>{ const b=document.createElement("button"); b.textContent=label; b.dataset.r=id;
    b.setAttribute("aria-pressed","false");
    if(RTIP[id]) attachTip(b,RTIP[id][0],RTIP[id][1],null);
    b.onclick=()=>{ if(b.disabled) return; xres.has(id)?xres.delete(id):xres.add(id); syncXres(); xrender(); };
    xrp.appendChild(b); });
  function syncConflicts(){ const vis=QCHIPS[xfSel]||[];
    RES.forEach(([id])=>{ if(!vis.includes(id)) xres.delete(id); });
    if(xfSel==="tide") xres.add("decline");
    xrp.querySelectorAll("button").forEach(b2=>{ if(b2.dataset.r) b2.style.display=vis.includes(b2.dataset.r)?"":"none"; });
    const own=xfSel==="wy";   // this question sets its own scope (rain-free summer tests)
    xrp.closest(".frow").style.display=own?"none":"";
    document.getElementById("xv-raw").closest(".frow").style.display=own?"none":"";
    syncXres(); }
  syncConflicts();
  document.getElementById("xv-raw").onclick=()=>{ xdep=false; syncXV(); };
  document.getElementById("xv-dep").onclick=()=>{ xdep=true; syncXV(); };
  attachTip(document.getElementById("xv-raw"),"Raw levels",
    "Bars show the actual typical level for each group of days, in the same units as the graph above. Simple — but some factors travel with the seasons, so part of a difference can be the time of year itself.",null);
  attachTip(document.getElementById("xv-dep"),"Compared to the seasonal average",
    "Each test is first compared to the average for that month and era, so bars show how many times above or below that average each group runs (1× = the seasonal average). This removes the calendar from the comparison. Note: the seasonal average is not a safe level — at this creek it often exceeds the health standard.",null);
  function syncXV(){ document.getElementById("xv-raw").setAttribute("aria-pressed",String(!xdep));
    document.getElementById("xv-dep").setAttribute("aria-pressed",String(xdep)); xrender(); }
  { const xp=document.getElementById("xplot"), tc=document.getElementById("tipcard");
    xp.addEventListener("mousemove",e=>{ const t=e.target.closest("[data-note]");
      if(t&&tc){ tc.innerHTML=`<div>${t.dataset.note}</div>`;
        tc.style.left=Math.max(6,Math.min(e.clientX+12,innerWidth-272))+"px";
        tc.style.top=Math.min(e.clientY+16,innerHeight-120)+"px"; tc.style.display="block"; }
      else if(tc) tc.style.display="none"; });
    xp.addEventListener("mouseleave",()=>{ if(tc) tc.style.display="none"; }); }
  xrender();


  const tbl=document.getElementById("tbl");
  const COLS=[["date","d"],["value","v"],["hour","hr"],["days since rain","dsr"],["last event mm","ev"],["rain 72h mm","p3"],["rain vs normal %","wy"],["air °C (7d)","t7"],["water °C est.","wt"],["spill ≤7d","sp"]];
  const SCOLS=[["date","d"],["site","s"],["entero","ent"],["E. coli","ec"],["days since rain","dsr"],["flow est.","f"],["water °C est.","wt"]];
  const SROWS=DATA.sites.filter(r=>SITES.includes(r.s)).map(r=>{ const i=idxOf.get(r.d);
    return {d:r.d, s:r.s, ent:r.ent, ec:r.ec, dsr:i!=null?DSR[i]:null,
            f:i!=null?D[i].f:null, wt:i!=null?D[i].wt:null}; });
  let cur="sites", sortK="d", asc=false;
  function renderTbl(){
    const isSites=cur==="sites";
    const cols=isSites?SCOLS:COLS.filter(c=>cur==="creek"||c[1]!=="sp");
    const data=isSites?SROWS:DATA[cur];
    const std=cur==="creek"?320:(cur==="bwtf"?110:104);
    const val=(r,k)=>{ if(k==="wt"&&!isSites){ const dd=dailyBy.get(r.d); return dd?dd.wt:null; } return r[k]; };
    const rows=[...data].sort((a,b)=>{ const x=val(a,sortK),y=val(b,sortK);
      return (x==null)-(y==null)||(x>y?1:x<y?-1:0)*(asc?1:-1); });
    let hh="<thead><tr>"+cols.map(c=>`<th data-k="${c[1]}">${c[0]}</th>`).join("")+"</tr></thead><tbody>";
    rows.forEach(r=>{ hh+="<tr>"+cols.map(([_,k])=>{
      let v=val(r,k); if(k==="sp") v=v?"▲":""; if(v==null) v="–";
      let over=false;
      if(!isSites&&k==="v") over=r.v>std;
      if(isSites&&(k==="ent"||k==="ec")&&v!=="–") over=v>stdFor(r.s,k);
      return `<td${over?' class="over"':''}>${v}${over?" ✕":""}</td>`; }).join("")+"</tr>"; });
    tbl.innerHTML=hh+"</tbody>";
    const SRC={creek:`Source: San Mateo County Environmental Health weekly grab samples, published through CEDEN — <a href="https://data.ca.gov/dataset/surface-water-fecal-indicator-bacteria-results" target="_blank" rel="noopener">raw data at data.ca.gov</a>. E. coli (enterococcus on some 2026 dates), MPN per 100 mL.`,
      beach:`Source: San Mateo County Environmental Health weekly grab samples at Linda Mar Beach #5, published through CEDEN — <a href="https://data.ca.gov/dataset/surface-water-fecal-indicator-bacteria-results" target="_blank" rel="noopener">raw data at data.ca.gov</a>. Enterococcus and E. coli, MPN per 100 mL.`,
      bwtf:`Source: Surfrider Foundation Blue Water Task Force volunteer samples at the creek mouth — <a href="https://bwtf.surfrider.org/" target="_blank" rel="noopener">bwtf.surfrider.org</a>. Enterococcus, MPN per 100 mL; judged against the freshwater standard (110), following county practice for the brackish mouth.`,
      sites:`Source: Linda Mar Water Quality Coalition volunteer sampling — <a href="https://www.lindamarwaterquality.org/test-results" target="_blank" rel="noopener">raw spreadsheets at lindamarwaterquality.org</a>. Both organisms, cfu per 100 mL. Flow and water temperature columns are estimates — see Methods.`};
    const se=document.getElementById("tblsrc"); if(se) se.innerHTML=SRC[cur]||"";
    tbl.querySelectorAll("th").forEach(th=>th.onclick=()=>{ const k=th.dataset.k;
      if(sortK===k) asc=!asc; else{sortK=k; asc=k==="d";} renderTbl(); });
  }
  document.querySelectorAll(".tabs button").forEach(b=>b.onclick=()=>{
    document.querySelectorAll(".tabs button").forEach(x=>x.setAttribute("aria-selected","false"));
    b.setAttribute("aria-selected","true"); cur=b.dataset.t; sortK="d"; asc=false; renderTbl(); });

  const DEF={on:[...on], sampleOn:[...sampleOn], anOn:[...anOn], ann:[...ann]};
  window.__pbw={PHONE, D, N, VIEWS, TRACKS, DATA, summerRows:()=>summerRows(),
    get PPD(){ return PPD; }, get LAY(){ return LAY; }, get DOTPOS(){ return DOTPOS; }, get curI(){ return curI; },
    get gdates(){ return gdates; }, get LASTS(){ return LASTS; }, geoFrame:k=>geoFrame(k), geoRebuild:()=>geoRebuild(), graphTo:d=>graphTo(d),
    setPPD(p,d){ PPD=targetPPD=p; syncViewButtons(); render(d||centerDate()); },
    rerender(d){ render(d||centerDate()); }, centerDate:()=>centerDate(), show:i=>show(i), setPinned(v){ pinned=!!v; },
    applyView:k=>applyView(k),
    setLayers(list){ const L=new Set(list); sampleOn.clear();
      ["creek","beach","bwtf","LMMS","ADMS","PRLT","SPCM"].forEach(x=>{ if(L.has(x)) sampleOn.add(x); }); if(L.has("avg")) sampleOn.add("AVG");
      on.clear(); TRACKS.forEach(t=>{ if(t.id!=="bact"&&L.has(t.id)) on.add(t.id); });
      ann.clear(); Object.keys(ANN).forEach(k=>{ if(L.has(k)) ann.add(k); });
      clearViewHighlight(); exNote=null; TOUR=null; colorBySite=false; syncBySite(); syncPanel(); render(centerDate()); geoRebuild(); },
    layers(){ return [...sampleOn].map(x=>x==="AVG"?"avg":x).concat([...on],[...ann]); },
    reset(){ clearViewHighlight(); exNote=null; TOUR=null; colorBySite=false; syncBySite();
      [[on,DEF.on],[sampleOn,DEF.sampleOn],[anOn,DEF.anOn],[ann,DEF.ann]].forEach(([s,v])=>{ s.clear(); v.forEach(x=>s.add(x)); });
      syncPanel(); render(centerDate()); geoRebuild(); } };
  render(); renderTbl();
};

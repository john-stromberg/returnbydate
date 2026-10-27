(function(){
  var D = window.RBD || {retailers:[],affiliates:{}};
  var $ = function(s){return document.querySelector(s)};
  var pad = function(n){return String(n).padStart(2,"0")};
  var iso = function(d){return d.getFullYear()+"-"+pad(d.getMonth()+1)+"-"+pad(d.getDate())};
  var ymd = function(d){return d.getFullYear()+pad(d.getMonth()+1)+pad(d.getDate())};
  var parse = function(s){var p=s.split("-").map(Number);return new Date(p[0],p[1]-1,p[2])};
  var addDays = function(d,n){var x=new Date(d);x.setDate(x.getDate()+n);return x};
  var fmt = function(d){return d.toLocaleDateString("en-US",{month:"short",day:"numeric",year:"numeric"})};
  var esc = function(s){return String(s).replace(/[&<>"]/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]})};
  var today = function(){var t=new Date();return new Date(t.getFullYear(),t.getMonth(),t.getDate())};
  var PM = {comp:["Matches competitors","p-comp"],own:["Own prices only","p-own"],none:["No price match","p-none"]};
  var HOL = {confirmed:["2026 confirmed","s-confirmed"],expected:["Expected","s-expected"],none:["None","s-none"]};

  /* Return-by date for a retailer, purchase date and item type (category key or "most"). */
  function due(r,bought,catKey){
    var cat=null;
    (r.categories||[]).forEach(function(c){if(c.key===catKey)cat=c});
    var days = cat ? cat.days : r.window_days;
    if(days===null||days===undefined) return {t:null,hol:false,cat:cat};
    var std=addDays(bought,days);
    var h = cat && cat.holiday && typeof cat.holiday==="object" ? Object.assign({status:"confirmed"},cat.holiday)
          : cat && cat.holiday==="excluded" ? {status:"none"} : r.holiday;
    if(h.status==="confirmed" && bought>=parse(h.start) && bought<=parse(h.end)){
      var hb=parse(h.by); if(hb>std) return {t:hb,hol:true,cat:cat};
    }
    return {t:std,hol:false,cat:cat};
  }
  function left(t){
    if(!t) return {txt:"",cls:""};
    var n=Math.round((t-today())/864e5);
    if(n<0) return {txt:"Window passed",cls:"d-past"};
    if(n===0) return {txt:"Last day today",cls:"d-crit"};
    return {txt:n+(n===1?" day left":" days left"),cls:n<7?"d-crit":n<14?"d-warn":"d-ok"};
  }
  function shopLink(r){return D.affiliates[r.id]||r.homepage}
  function shortName(r){return r.name.replace(/,/g,"&").split("&")[0].trim()}

  /* ---------- Calendar reminders ---------- */
  function calTitle(r,item){return "Last day to return "+(item?item+" ":"")+"to "+shortName(r)}
  function gcalUrl(r,item,t){
    var details="Return-by date from returnbydate.com. Policies change, so confirm on "+r.homepage+" before you go.\n"+location.href;
    return "https://calendar.google.com/calendar/render?action=TEMPLATE&text="+encodeURIComponent(calTitle(r,item))+
      "&dates="+ymd(t)+"/"+ymd(addDays(t,1))+"&details="+encodeURIComponent(details);
  }
  function ics(r,item,t){
    var now=new Date(), stamp=now.toISOString().replace(/[-:]/g,"").replace(/\.\d+/,"");
    var fold=function(s){return s.replace(/[\\,;]/g,function(c){return "\\"+c}).replace(/\n/g,"\\n")};
    return ["BEGIN:VCALENDAR","VERSION:2.0","PRODID:-//Return by Date//EN","CALSCALE:GREGORIAN","BEGIN:VEVENT",
      "UID:"+r.id+"-"+ymd(t)+"-"+now.getTime()+"@returnbydate.com","DTSTAMP:"+stamp,
      "DTSTART;VALUE=DATE:"+ymd(t),"DTEND;VALUE=DATE:"+ymd(addDays(t,1)),
      "SUMMARY:"+fold(calTitle(r,item)),
      "DESCRIPTION:"+fold("Return-by date from returnbydate.com. Confirm the policy on "+r.homepage+" before you go."),
      "BEGIN:VALARM","TRIGGER:-P3D","ACTION:DISPLAY","DESCRIPTION:"+fold(calTitle(r,item)+" in 3 days"),"END:VALARM",
      "END:VEVENT","END:VCALENDAR"].join("\r\n");
  }

  /* ---------- Retailer page calculator ---------- */
  var calc=$("#calc-date");
  if(calc){
    var r=D.retailers.filter(function(x){return x.id===calc.dataset.id})[0];
    var catSel=$("#calc-cat"), item=$("#calc-item"), result={};
    var show=function(){
      var b=calc.value?parse(calc.value):today(), d=due(r,b,catSel?catSel.value:"most"), v=$("#calc-v"), why=$("#calc-why"), lf=left(d.t), dl=$("#calc-left");
      result=d;
      v.textContent=d.t?fmt(d.t):"No set limit";
      dl.textContent=lf.txt; dl.className="dleft "+lf.cls; dl.hidden=!lf.txt;
      why.textContent=d.hol?"Holiday extension applies to this purchase date."
        : d.cat?(d.cat.label+": "+d.cat.days+"-day window"+(d.cat.holiday==="excluded"?", not covered by the holiday extension.":"."))
        : d.t?("Standard "+r.window_days+"-day window.")
        : "Most items have no fixed deadline.";
      $("#cal").hidden=!d.t||lf.cls==="d-past";
      if(d.t) $("#cal-g").href=gcalUrl(r,item.value.trim(),d.t);
    };
    $("#cal-ics").addEventListener("click",function(){
      if(!result.t) return;
      var blob=new Blob([ics(r,item.value.trim(),result.t)],{type:"text/calendar"});
      var a=document.createElement("a"); a.href=URL.createObjectURL(blob);
      a.download="return-"+r.slug+"-"+iso(result.t)+".ics"; document.body.appendChild(a); a.click();
      setTimeout(function(){URL.revokeObjectURL(a.href);a.remove()},1000);
    });
    calc.value=iso(today());
    [calc,catSel,item].forEach(function(el){if(el)el.addEventListener("input",show)});
    show();
  }

  /* ---------- Homepage table ---------- */
  var list=$("#list");
  if(!list) return;
  var tog=$("#filters-toggle"), rail=$("#rail");
  if(tog) tog.addEventListener("click",function(){
    var open=rail.classList.toggle("open"); tog.setAttribute("aria-expanded",open?"true":"false");
  });
  function render(){
    var q=$("#q").value.trim().toLowerCase(), pm=$("#pm").value, hol=$("#hol").value, sort=$("#sort").value, cat=$("#cat").value;
    var bought=$("#d").value?parse($("#d").value):today();
    $("#when").textContent="Return-by dates for "+($("#cat").selectedOptions[0].text.toLowerCase())+" bought "+fmt(bought);
    var active=[pm,hol,cat!=="most"?cat:""].filter(Boolean).length;
    if(tog) tog.textContent="Filters"+(active?" ("+active+")":"");
    var rows=D.retailers.map(function(r){return {r:r,d:due(r,bought,cat)}}).filter(function(x){
      var r=x.r;
      if(pm && r.price_match!==pm) return false;
      if(hol && r.holiday.status!==hol) return false;
      if(!q) return true;
      var hay=[r.name,r.category,r.window_note,r.price_match_note,r.holiday.note,PM[r.price_match][0]].join(" ").toLowerCase();
      return q.split(/\s+/).every(function(w){return hay.indexOf(w)>-1});
    });
    var rk=function(r){return typeof r.nrf_rank==="number"?r.nrf_rank:1.5};
    var far=function(x){return x.d.t?x.d.t.getTime():Infinity};
    rows.sort(function(a,b){
      if(sort==="az") return a.r.name.localeCompare(b.r.name);
      if(sort==="window") return ((b.r.window_days==null?99999:b.r.window_days)-(a.r.window_days==null?99999:a.r.window_days))||rk(a.r)-rk(b.r);
      if(sort==="due") return (far(b)-far(a))||rk(a.r)-rk(b.r);
      return rk(a.r)-rk(b.r);
    });
    $("#n").textContent=rows.length;
    if(!rows.length){list.innerHTML='<div class="empty">No retailers match those filters. Clear the search or set the filters to “Any”.</div>';return;}
    list.innerHTML=rows.map(function(x){
      var r=x.r,d=x.d,page="/returns/"+r.slug+"/",lf=left(d.t);
      var basis=d.hol?"Holiday extension":d.cat?d.cat.label:(cat!=="most"&&d.t?"No separate rule listed":d.t?"Standard window":"Most items");
      return '<article class="row">'+
        '<div class="rank">'+esc(r.nrf_rank)+'</div>'+
        '<div class="c-name"><div class="name"><a href="'+page+'">'+esc(r.name)+'</a></div><div class="cat">'+esc(r.category)+'</div>'+
          '<div class="src">'+(r.verified==="retailer"?"Checked on retailer page":"Secondary sources, confirm")+'</div></div>'+
        '<div class="c-win"><span class="lbl">Standard window</span><div class="big">'+(r.window_days===null?"No limit":r.window_days+" days")+'</div><div class="note">'+esc(r.window_note)+'</div></div>'+
        '<div class="c-pm"><span class="lbl">Price match</span><span class="pill '+PM[r.price_match][1]+'">'+PM[r.price_match][0]+'</span><div class="note">'+esc(r.price_match_note)+'</div></div>'+
        '<div class="c-hol"><span class="lbl">Holiday 2026</span><span class="stamp '+HOL[r.holiday.status][1]+'">'+HOL[r.holiday.status][0]+'</span><div class="note">'+esc(r.holiday.note)+'</div></div>'+
        '<div class="c-due"><span class="lbl">Return by</span><div class="due">'+(d.t?fmt(d.t):"No set limit")+'</div>'+
          (lf.txt?'<span class="dleft '+lf.cls+'">'+lf.txt+'</span>':'')+'<div class="note'+(d.hol?" hol":"")+'">'+esc(basis)+'</div></div>'+
        '<div class="c-shop"><a class="shop" href="'+esc(shopLink(r))+'" target="_blank" rel="sponsored noopener">Shop '+esc(shortName(r))+' ↗</a></div>'+
      '</article>';
    }).join("");
  }
  $("#d").value=iso(today());
  try{var s=JSON.parse(localStorage.getItem("rbd")||"{}");["q","pm","hol","sort","cat"].forEach(function(k){if(s[k]!=null&&$("#"+k))$("#"+k).value=s[k]})}catch(e){}
  ["q","d","pm","hol","sort","cat"].forEach(function(k){$("#"+k).addEventListener("input",function(){
    render();
    try{localStorage.setItem("rbd",JSON.stringify({q:$("#q").value,pm:$("#pm").value,hol:$("#hol").value,sort:$("#sort").value,cat:$("#cat").value}))}catch(e){}
  })});
  render();
})();

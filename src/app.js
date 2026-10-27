(function(){
  var D = window.RBD || {retailers:[],affiliates:{}};
  var $ = function(s){return document.querySelector(s)};
  var pad = function(n){return String(n).padStart(2,"0")};
  var iso = function(d){return d.getFullYear()+"-"+pad(d.getMonth()+1)+"-"+pad(d.getDate())};
  var parse = function(s){var p=s.split("-").map(Number);return new Date(p[0],p[1]-1,p[2])};
  var fmt = function(d){return d.toLocaleDateString("en-US",{month:"short",day:"numeric",year:"numeric"})};
  var esc = function(s){return String(s).replace(/[&<>"]/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]})};
  var PM = {comp:["Matches competitors","p-comp"],own:["Own prices only","p-own"],none:["No price match","p-none"]};
  var HOL = {confirmed:["2026 confirmed","s-confirmed"],expected:["Expected","s-expected"],none:["None","s-none"]};

  function due(r,bought){
    if(r.window_days===null) return {t:null,hol:false};
    var std=new Date(bought); std.setDate(std.getDate()+r.window_days);
    var h=r.holiday;
    if(h.status==="confirmed" && bought>=parse(h.start) && bought<=parse(h.end)){
      var hb=parse(h.by); return hb>std?{t:hb,hol:true}:{t:std,hol:false};
    }
    return {t:std,hol:false};
  }
  function shopLink(r){return D.affiliates[r.id]||r.homepage}

  /* ---------- Retailer page calculator ---------- */
  var calc=$("#calc-date");
  if(calc){
    var r=D.retailers.filter(function(x){return x.id===calc.dataset.id})[0];
    var show=function(){
      var b=calc.value?parse(calc.value):new Date(), d=due(r,b), v=$("#calc-v"), why=$("#calc-why");
      v.textContent=d.t?fmt(d.t):"No set limit";
      v.classList.toggle("hol",d.hol);
      why.textContent=d.hol?"Holiday extension applies to this purchase date."
        : d.t?("Standard "+r.window_days+"-day window. Some categories are shorter.")
        : "Most items have no fixed deadline. Some categories do.";
    };
    calc.value=iso(new Date()); calc.addEventListener("input",show); show();
  }

  /* ---------- Homepage table ---------- */
  var list=$("#list");
  if(!list) return;
  function render(){
    var q=$("#q").value.trim().toLowerCase(), pm=$("#pm").value, hol=$("#hol").value, sort=$("#sort").value;
    var bought=$("#d").value?parse($("#d").value):new Date();
    $("#when").textContent="Return-by dates for a purchase on "+fmt(bought);
    var rows=D.retailers.map(function(r){return {r:r,d:due(r,bought)}}).filter(function(x){
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
      var r=x.r,d=x.d,page="/returns/"+r.slug+"/";
      return '<article class="row">'+
        '<div class="rank">'+esc(r.nrf_rank)+'</div>'+
        '<div class="c-name"><div class="name"><a href="'+page+'">'+esc(r.name)+'</a></div><div class="cat">'+esc(r.category)+'</div>'+
          '<div class="src">'+(r.verified==="retailer"?"Checked on retailer page":"Secondary sources, confirm")+'</div></div>'+
        '<div><span class="lbl">Standard window</span><div class="big">'+(r.window_days===null?"No limit":r.window_days+" days")+'</div><div class="note">'+esc(r.window_note)+'</div></div>'+
        '<div><span class="lbl">Price match</span><span class="pill '+PM[r.price_match][1]+'">'+PM[r.price_match][0]+'</span><div class="note">'+esc(r.price_match_note)+'</div></div>'+
        '<div class="c-hol"><span class="lbl">Holiday 2026</span><span class="stamp '+HOL[r.holiday.status][1]+'">'+HOL[r.holiday.status][0]+'</span><div class="note">'+esc(r.holiday.note)+'</div></div>'+
        '<div><span class="lbl">Return by</span><div class="due '+(d.hol?"hol":"")+'">'+(d.t?fmt(d.t):"No set limit")+'</div><div class="note">'+(d.hol?"Holiday extension":d.t?"Standard window":"Most items")+'</div></div>'+
        '<div class="c-shop"><a class="shop" href="'+esc(shopLink(r))+'" target="_blank" rel="sponsored noopener">Shop '+esc(r.name.split(/[,&]/)[0].trim())+' ↗</a></div>'+
      '</article>';
    }).join("");
  }
  $("#d").value=iso(new Date());
  try{var s=JSON.parse(localStorage.getItem("rbd")||"{}");["q","pm","hol","sort"].forEach(function(k){if(s[k]!=null)$("#"+k).value=s[k]})}catch(e){}
  ["q","d","pm","hol","sort"].forEach(function(k){$("#"+k).addEventListener("input",function(){
    render();
    try{localStorage.setItem("rbd",JSON.stringify({q:$("#q").value,pm:$("#pm").value,hol:$("#hol").value,sort:$("#sort").value}))}catch(e){}
  })});
  render();
})();

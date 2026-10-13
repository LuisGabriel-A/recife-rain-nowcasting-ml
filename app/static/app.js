"use strict";
const $ = (id) => document.getElementById(id);
let demonstration = false, deferredInstall = null, registration = null, requestNumber = 0;
const serviceWorkerReady = "serviceWorker" in navigator ? navigator.serviceWorker.register("/sw.js").then(() => navigator.serviceWorker.ready).then((value) => { registration = value; return value; }).catch(() => null) : Promise.resolve(null);
async function api(path, body) {
  const controller = new AbortController(), timeout = setTimeout(() => controller.abort(), 15000);
  try {
    const response = await fetch(path, {cache:"no-store", signal:controller.signal, ...(body ? {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(body)} : {})});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Não foi possível conectar ao serviço.");
    return data;
  } finally { clearTimeout(timeout); }
}
function render(status) {
  $("aviso").className = `status-card ${status.state}`; $("aviso").setAttribute("aria-busy","false");
  $("status-title").textContent = status.title; $("status-message").textContent = status.message;
  $("status-symbol").textContent = status.state === "attention" ? "!" : status.state === "unavailable" ? "…" : "☂";
  $("status-badge").textContent = status.demo ? "Exemplo histórico" : status.state === "attention" ? "Atenção" : status.state === "unavailable" ? "Aguardando dados" : "Atualizado";
  $("demo-banner").hidden = !status.demo;
  if (status.observation_at_utc && status.state !== "unavailable") {
    const date = new Date(status.observation_at_utc).toLocaleDateString("pt-BR",{timeZone:"America/Fortaleza"});
    $("updated").textContent = `${status.demo ? "Exemplo de" : "Medição do INMET em"} ${date}, às ${status.observation_time_local}.`;
  } else $("updated").textContent = "O aviso será atualizado quando houver dados recentes e completos.";
  const hours = $("hours"); hours.replaceChildren();
  if (!status.hours.length) { const empty = document.createElement("p"); empty.className="empty-hours"; empty.textContent="Sem horários disponíveis neste momento."; hours.append(empty); }
  for (const row of status.hours) {
    const item = document.createElement("div"); item.className=`hour ${!row.valid ? "expired" : row.alert ? "warned" : ""}`;
    const hour=document.createElement("strong"); hour.textContent=row.time_local;
    const symbol=document.createElement("span"); symbol.className="weather"; symbol.setAttribute("aria-hidden","true"); symbol.textContent=!row.valid ? "–" : row.alert ? "☂" : "☁";
    const label=document.createElement("span"); label.textContent=row.label;
    item.append(hour,symbol,label); hours.append(item);
  }
  $("current-section").hidden=!status.current;
  if (status.current) {
    const number=(value)=>Number(value).toLocaleString("pt-BR",{maximumFractionDigits:1});
    $("current-temperature").textContent=`${number(status.current.temperature_c)} °C`; $("current-humidity").textContent=`${number(status.current.humidity_pct)}%`; $("current-rain").textContent=`${number(status.current.precipitation_mm)} mm`;
    $("current-title").textContent=status.demo ? "Medições do exemplo histórico" : "Medido na última atualização";
  }
}
async function refresh() {
  if (demonstration) return;
  const number=++requestNumber;
  try { const status=await api("/api/status"); if(number===requestNumber) render(status); }
  catch { if(number===requestNumber) render({state:"unavailable",demo:false,title:"Sem conexão com o serviço",message:"Conecte-se à internet e tente novamente. Não temos uma previsão atual para mostrar.",hours:[],current:null}); }
}
async function notificationState() {
  await serviceWorkerReady;
  const subscription=registration && "PushManager" in window ? await registration.pushManager.getSubscription() : null;
  $("enable-notifications").textContent=subscription ? "Ver ajustes dos avisos" : "Receber avisos";
  $("notification-description").textContent=subscription ? "Este aparelho tem uma inscrição de avisos. O envio depende do serviço ativo e de dados recentes." : "Ative os avisos de chuva forte. Sem cadastro e sem senha.";
  return subscription;
}
function applicationKey(value) { const raw=atob(value.replace(/-/g,"+").replace(/_/g,"/")+"=".repeat((4-value.length%4)%4)); return Uint8Array.from(raw,(letter)=>letter.charCodeAt(0)); }
$("enable-notifications").addEventListener("click",async()=>{
  const button=$("enable-notifications"); button.disabled=true;
  try {
    if(!window.isSecureContext || !("Notification" in window) || !("PushManager" in window)) throw new Error("Este navegador não permite avisos. No iPhone, adicione à tela inicial e abra o aplicativo por lá.");
    if(!await serviceWorkerReady) throw new Error("Não foi possível preparar os avisos neste navegador.");
    const config=await api("/api/push/config"); if(!config.enabled) throw new Error("O envio de avisos ainda não está habilitado neste servidor.");
    let subscription=await registration.pushManager.getSubscription();
    if(subscription) { await api("/api/push/subscribe",subscription.toJSON()); $("settings").showModal(); }
    else {
      // Permission is requested only following the user's deliberate click.
      subscription=await registration.pushManager.subscribe({userVisibleOnly:true,applicationServerKey:applicationKey(config.public_key)});
      try { await api("/api/push/subscribe",subscription.toJSON()); } catch(error) { await subscription.unsubscribe(); throw error; }
      $("notification-feedback").textContent="Avisos ativados neste aparelho. Você pode desativar quando quiser em Ajustes.";
    }
    await notificationState();
  } catch(error) { $("notification-feedback").textContent="Notification" in window && Notification.permission==="denied" ? "Os avisos estão bloqueados. Para ativar, permita notificações nos ajustes do navegador." : error.message; }
  finally { button.disabled=false; }
});
$("open-settings").addEventListener("click",()=>$("settings").showModal()); $("close-settings").addEventListener("click",()=>$("settings").close());
$("disable-notifications").addEventListener("click",async()=>{
  try { const subscription=await notificationState(); if(subscription) { await api("/api/push/unsubscribe",subscription.toJSON()); await subscription.unsubscribe(); } await notificationState(); $("settings-feedback").textContent="Avisos desativados neste aparelho."; }
  catch { $("settings-feedback").textContent="Não foi possível desativar agora. Tente novamente com conexão."; }
});
$("test-notification").addEventListener("click",async()=>{
  if(!registration || !("Notification" in window) || Notification.permission!=="granted") { $("settings-feedback").textContent="Ative os avisos primeiro pelo botão Receber avisos."; return; }
  try { await registration.showNotification("AlertaChuva Recife · Teste",{body:"Este é apenas um teste de exibição. Não é uma previsão de chuva.",icon:"/icon-192.png",tag:"alertachuva-local-test",data:{url:"/"}}); $("settings-feedback").textContent="Teste enviado ao aparelho. Este teste verifica a exibição, sem testar a entrega pela internet."; }
  catch { $("settings-feedback").textContent="O aparelho não permitiu mostrar o teste."; }
});
$("show-demo").addEventListener("click",async()=>{
  demonstration=true; const number=++requestNumber;
  try { const status=await api("/api/demo/1"); if(number!==requestNumber) return; render(status); $("aviso").scrollIntoView({behavior:"smooth",block:"start"}); }
  catch { demonstration=false; $("install-feedback").textContent="A demonstração está indisponível agora."; refresh(); }
});
$("leave-demo").addEventListener("click",()=>{demonstration=false;refresh();});
window.addEventListener("beforeinstallprompt",(event)=>{event.preventDefault();deferredInstall=event;});
$("install-app").addEventListener("click",async()=>{
  if(deferredInstall) { await deferredInstall.prompt();deferredInstall=null; }
  else $("install-feedback").textContent="No celular, abra o menu do navegador e escolha Adicionar à tela inicial. No iPhone, use Compartilhar → Adicionar à Tela de Início. O acesso no celular exige um endereço HTTPS publicado.";
});
window.addEventListener("online",refresh);
window.addEventListener("offline",()=>{if(!demonstration){++requestNumber;render({state:"unavailable",demo:false,title:"Sem conexão com o serviço",message:"Os avisos precisam de conexão. Abra novamente quando estiver conectado.",hours:[],current:null});}});
document.addEventListener("visibilitychange",()=>{if(!document.hidden) refresh();});
setInterval(refresh,60000); notificationState().catch(()=>{}); refresh();

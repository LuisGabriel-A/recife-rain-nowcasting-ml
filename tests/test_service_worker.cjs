/* Node's built-in runner: notification expiry and offline data boundaries. */
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

function worker() {
  const handlers = {}, notices = [], opened = [];
  const context = {
    URL, Date, Number, Promise,
    self: {
      location:{origin:'https://alertachuva.example'},
      addEventListener:(name,callback)=>{handlers[name]=callback;},
      registration:{showNotification:async(title,options)=>{notices.push({title,options});}},
      clients:{matchAll:async()=>[],openWindow:async(url)=>{opened.push(url);}}
    }
  };
  vm.runInNewContext(fs.readFileSync('app/static/sw.js','utf8'),context);
  return {handlers,notices,opened};
}

test('a current encrypted push creates a visible notice with the forecast tag',async()=>{
  const {handlers,notices}=worker(); let done;
  handlers.push({data:{json:()=>({body:'Atenção para chuva forte',event_id:'forecast-1',expires_at_utc:new Date(Date.now()+60000).toISOString()})},waitUntil:(promise)=>{done=promise;}});
  await done;
  assert.equal(notices.length,1);
  assert.equal(notices[0].title,'AlertaChuva Recife');
  assert.equal(notices[0].options.tag,'rain-forecast-1');
});
test('expired, malformed or missing push content does not display a rain alert',()=>{
  const {handlers,notices}=worker();
  const invalid=[{body:'Old',event_id:'old',expires_at_utc:new Date(Date.now()-1).toISOString()},{body:'Old',event_id:'old',expires_at_utc:'broken'},{}];
  for(const value of invalid) handlers.push({data:{json:()=>value},waitUntil:()=>assert.fail('Invalid content displayed')});
  handlers.push({data:null});
  assert.equal(notices.length,0);
});
test('API data and subscriptions never enter offline caching',()=>{
  const {handlers}=worker();
  for(const path of ['/api/status','/api/predict','/api/push/config','/api/push/subscribe']) {
    handlers.fetch({request:{method:'GET',url:'https://alertachuva.example'+path},respondWith:()=>assert.fail('API cached offline')});
  }
});
test('notification links cannot send the family to an external website',async()=>{
  const {handlers,opened}=worker();let done,closed=false;
  handlers.notificationclick({notification:{data:{url:'https://untrusted.example'},close:()=>{closed=true;}},waitUntil:(promise)=>{done=promise;}});
  await done;
  assert.equal(closed,true);assert.deepEqual(opened,['/']);
});

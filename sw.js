/* Paycee. バージョン 19:更新のたびに番号が変わり、古いキャッシュは消える */
const V="paycee-v19";
const ASSETS=["./","./index.html","./manifest.webmanifest","./icon-192.png","./icon-512.png","./apple-touch-icon.png"];
self.addEventListener("install",e=>{e.waitUntil(caches.open(V).then(c=>c.addAll(ASSETS)));self.skipWaiting();});
self.addEventListener("activate",e=>{e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==V).map(k=>caches.delete(k)))).then(()=>self.clients.claim()));});
self.addEventListener("fetch",e=>{
  const r=e.request;if(r.method!=="GET")return;
  if(r.mode==="navigate"){
    const path=new URL(r.url).pathname,root=new URL(self.registration.scope).pathname;
    if(path!==root&&path!==root+"index.html")return; /* 紹介ページなどはそのまま通す */
    /* 画面本体はネット優先:つながっていれば常に最新版、圏外ならキャッシュ */
    e.respondWith(fetch(r).then(res=>{const cp=res.clone();caches.open(V).then(c=>c.put("./index.html",cp));return res;}).catch(()=>caches.match("./index.html")));
    return;
  }
  e.respondWith(caches.match(r).then(hit=>hit||fetch(r)));
});

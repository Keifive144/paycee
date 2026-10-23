"""paycee.html(Claude版)から独立版Webアプリ一式を作る。更新のたびにこれを実行する。"""
import re, os, shutil, sys
from PIL import Image
SRC='/home/claude/paycee.html'; OUT='/home/claude/paycee-pwa'
ICON=sys.argv[1] if len(sys.argv)>1 else '/home/claude/out/paycee-icon-gold.png'
s=open(SRC).read()
ver=re.search(r'バージョン (\d+)',s).group(1)
def swap(tag,new):
    global s
    if tag.startswith('<!--'):
        a=s.index(f'<!-- PLATFORM:{tag[4:]} -->');b=s.index(f'<!-- /PLATFORM:{tag[4:]} -->')+len(f'<!-- /PLATFORM:{tag[4:]} -->')
    else:
        a=s.index(f'/* PLATFORM:{tag} */');b=s.index(f'/* /PLATFORM:{tag} */')+len(f'/* /PLATFORM:{tag} */')
    s=s[:a]+new+s[b:]
swap('saveFile','''async function saveFile(name,data,mime){
  const blob=new Blob([data],{type:mime});
  try{const file=new File([blob],name,{type:mime});
    if(navigator.canShare&&navigator.canShare({files:[file]})){await navigator.share({files:[file]});return true;}}
  catch(e){if(e&&e.name==="AbortError")return false;}
  const a=document.createElement("a");a.href=URL.createObjectURL(blob);a.download=name;document.body.appendChild(a);a.click();
  setTimeout(()=>{URL.revokeObjectURL(a.href);a.remove();},1500);return true;
}''')
swap('flags','const LOCAL_DATA=true;')
swap('<!--notice','')
swap('<!--import','<label class="btn ghost" style="margin-bottom:10px;cursor:pointer">バックアップを読み込む<input type="file" id="bkIn" accept=".json,application/json" hidden></label>')
swap('cloud','''$("bkIn").addEventListener("change",async e=>{
  const f=e.target.files&&e.target.files[0];e.target.value="";if(!f)return;
  try{
    const o=JSON.parse(await f.text()),d=o&&o.app==="paycee"?o.data:o;
    if(!d||typeof d!=="object"||!("expenses" in d))throw new Error("not paycee");
    const n=migrate(d);
    if(!confirm(`バックアップ(記録${n.expenses.length}件・貯金${n.savings.length}件)で、この端末のデータを置き換えます。よろしいですか?`))return;
    S=n;save();draft=null;autoFixed();rollover();renderGroups();renderAll();toast("バックアップを読み込みました");
    if(S.pendingResult)showResult(S.pendingResult);
  }catch(err){toast("読み込めませんでした。Paycee.のバックアップファイルか確認してください");}
});
try{if(navigator.storage&&navigator.storage.persist)navigator.storage.persist();}catch(e){}
$("sync").textContent="この端末に保存しています。機種変更の前や月に一度、バックアップを書き出しておくと安心です。";
if("serviceWorker" in navigator)navigator.serviceWorker.register("./sw.js").catch(()=>{});''')
s=s.replace('<title>Paycee.</title>\n','',1).replace('<meta name="claude:viewport-fit-sides" content="cover">\n','',1)
head=f'''<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#FFFFFF" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#17191C" media="(prefers-color-scheme: dark)">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="apple-mobile-web-app-title" content="Paycee.">
<link rel="manifest" href="manifest.webmanifest">
<link rel="apple-touch-icon" href="apple-touch-icon.png">
<link rel="icon" href="icon-192.png">
<title>Paycee.</title>
<style>html,body{{margin:0}}[hidden]{{display:none!important}}img{{max-width:100%}}</style>
</head>
<body>
'''
os.makedirs(OUT,exist_ok=True)
open(f'{OUT}/index.html','w').write(head+s+'\n</body>\n</html>\n')
open(f'{OUT}/manifest.webmanifest','w').write('''{
  "name": "Paycee.",
  "short_name": "Paycee.",
  "description": "ペースいい、ペイシー。今日あといくら使えるかがわかる家計アプリ",
  "lang": "ja",
  "start_url": "./",
  "scope": "./",
  "display": "standalone",
  "background_color": "#F3F3F4",
  "theme_color": "#FFFFFF",
  "icons": [
    {"src": "icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
    {"src": "icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
    {"src": "icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"}
  ]
}
''')
open(f'{OUT}/sw.js','w').write(f'''/* Paycee. バージョン {ver}:更新のたびに番号が変わり、古いキャッシュは消える */
const V="paycee-v{ver}";
const ASSETS=["./","./index.html","./manifest.webmanifest","./icon-192.png","./icon-512.png","./apple-touch-icon.png"];
self.addEventListener("install",e=>{{e.waitUntil(caches.open(V).then(c=>c.addAll(ASSETS)));self.skipWaiting();}});
self.addEventListener("activate",e=>{{e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==V).map(k=>caches.delete(k)))).then(()=>self.clients.claim()));}});
self.addEventListener("fetch",e=>{{
  const r=e.request;if(r.method!=="GET")return;
  if(r.mode==="navigate"){{
    const path=new URL(r.url).pathname,root=new URL(self.registration.scope).pathname;
    if(path!==root&&path!==root+"index.html")return; /* 紹介ページなどはそのまま通す */
    /* 画面本体はネット優先:つながっていれば常に最新版、圏外ならキャッシュ */
    e.respondWith(fetch(r).then(res=>{{const cp=res.clone();caches.open(V).then(c=>c.put("./index.html",cp));return res;}}).catch(()=>caches.match("./index.html")));
    return;
  }}
  e.respondWith(caches.match(r).then(hit=>hit||fetch(r)));
}});
''')
im=Image.open(ICON).convert('RGB')
for name,size in [('icon-512.png',512),('icon-192.png',192),('apple-touch-icon.png',180)]:
    im.resize((size,size),Image.LANCZOS).save(f'{OUT}/{name}')
print('built version',ver,'->',OUT)

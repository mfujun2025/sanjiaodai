// 无头浏览器量化验证：渲染、布局、溢出、搜索功能
// 用法：NODE_PATH=<workspace>/node_modules node verify.js <baseUrl>
const http = require('http');
const WebSocket = require('ws');

const BASE = process.argv[2] || 'http://127.0.0.1:8912';
const CDP_PORT = 9223;

function httpJson(path) {
  return new Promise((resolve, reject) => {
    http.get({ host: '127.0.0.1', port: CDP_PORT, path }, (res) => {
      let d = '';
      res.on('data', (c) => (d += c));
      res.on('end', () => {
        try { resolve(JSON.parse(d)); } catch (e) { reject(new Error('bad json: ' + d.slice(0, 200))); }
      });
    }).on('error', reject);
  });
}

class Cdp {
  constructor(ws) { this.ws = ws; this.id = 0; this.pending = new Map(); }
  static async connect(url) {
    const ws = new WebSocket(url, { perMessageDeflate: false, maxPayload: 200 * 1024 * 1024 });
    await new Promise((res, rej) => { ws.on('open', res); ws.on('error', rej); });
    const c = new Cdp(ws);
    ws.on('message', (raw) => {
      let msg; try { msg = JSON.parse(raw.toString()); } catch (e) { return; }
      if (msg.id && c.pending.has(msg.id)) {
        const { res, rej } = c.pending.get(msg.id);
        c.pending.delete(msg.id);
        msg.error ? rej(new Error(JSON.stringify(msg.error))) : res(msg.result);
      }
    });
    return c;
  }
  send(method, params = {}) {
    const id = ++this.id;
    return new Promise((res, rej) => {
      this.pending.set(id, { res, rej });
      this.ws.send(JSON.stringify({ id, method, params }));
      setTimeout(() => { if (this.pending.has(id)) { this.pending.delete(id); rej(new Error('timeout ' + method)); } }, 45000);
    });
  }
  async eval(expr) {
    const r = await this.send('Runtime.evaluate', {
      expression: expr, returnByValue: true, awaitPromise: true,
    });
    if (r.exceptionDetails) {
      throw new Error('JS: ' + JSON.stringify(r.exceptionDetails.exception || r.exceptionDetails));
    }
    return r.result.value;
  }
}

const VIEWPORTS = [
  { name: 'desktop', w: 1440, h: 1200 },
  { name: 'laptop', w: 1024, h: 900 },
  { name: 'tablet', w: 768, h: 1000 },
  { name: 'mobile', w: 390, h: 844 },
];

const PAGES = [
  { name: '首页', url: '/' },
  { name: '速查表', url: '/specs/' },
  { name: '栏目-基础知识', url: '/category/basics/' },
  { name: '栏目-常见问题', url: '/category/faq/' },
  { name: '全部内容', url: '/news/' },
  { name: '站点地图', url: '/sitemap/' },
  { name: '搜索', url: '/search/' },
  { name: '关于', url: '/about/' },
  { name: '文章-选型计算', url: '/guide/sanjiaodai-xuanxing-jisuan/' },
  { name: '文章-选型计算(校验)', url: '/guide/sanjiaodai-xuanxing-jisuan/' },
  { name: '文章-安装张紧', url: '/guide/sanjiaodai-anzhuang-zhangjin/' },
  { name: '文章-型号命名', url: '/models/sanjiaodai-xingming-mingming-guize/' },
  { name: '文章-基础结构', url: '/basics/sanjiaodai-jiegou-yuanli/' },
  { name: '文章-材质', url: '/basics/sanjiaodai-cailiao-xuanze/' },
  { name: '文章-窄V对比', url: '/models/putong-vdai-yu-zhaivdai-duibi/' },
  { name: '文章-失效分析', url: '/guide/sanjiaodai-shibai-fenxi/' },
  { name: '文章-行业趋势', url: '/news/chuandongdai-hangye-qushi/' },
  { name: '文章-采购十问', url: '/news/caigou-sanjiaodai-shiwen/' },
  { name: '文章-常见问题', url: '/faq/sanjiaodai-changjian-wenti/' },
  { name: '文章-点检清单', url: '/faq/sanjiaodai-dianjian-qingdan/' },
  { name: '文章-三尺寸', url: '/basics/sanjiaodai-dingkuan-jiekuan-gaodu/' },
  { name: '404页', url: '/404.html' },
];

const PROBE = `(function(){
  var de = document.documentElement;
  var overflowEls = [];
  var all = document.querySelectorAll('body *');
  for (var i = 0; i < all.length; i++) {
    var el = all[i];
    var r = el.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) continue;
    if (r.right > de.clientWidth + 1.5) {
      // 排除在可横向滚动的容器内部的元素
      var p = el.parentElement, inScroll = false;
      while (p && p !== document.body) {
        var ov = getComputedStyle(p).overflowX;
        if (ov === 'auto' || ov === 'scroll') { inScroll = true; break; }
        p = p.parentElement;
      }
      if (!inScroll) overflowEls.push(el.tagName + '.' + (el.className || '').toString().split(' ')[0] + ' right=' + Math.round(r.right));
      if (overflowEls.length > 6) break;
    }
  }
  var links = document.querySelectorAll('a[href]').length;
  var imgs = document.querySelectorAll('img');
  var brokenImgs = 0;
  for (var j=0;j<imgs.length;j++){ if (imgs[j].naturalWidth===0) brokenImgs++; }
  return {
    url: location.pathname,
    title: (document.title||'').length,
    titleText: document.title,
    scrollW: de.scrollWidth,
    clientW: de.clientWidth,
    overflowX: de.scrollWidth - de.clientWidth,
    bodyH: document.body.scrollHeight,
    h1: document.querySelectorAll('h1').length,
    h1text: (document.querySelector('h1')||{}).textContent || '',
    h2: document.querySelectorAll('h2').length,
    tables: document.querySelectorAll('table').length,
    cards: document.querySelectorAll('.card').length,
    links: links,
    imgs: imgs.length,
    brokenImgs: brokenImgs,
    cssLoaded: getComputedStyle(document.body).fontFamily.indexOf('PingFang') > -1 || getComputedStyle(document.body).fontFamily.length > 5,
    bodyFontSize: getComputedStyle(document.body).fontSize,
    headerSticky: getComputedStyle(document.querySelector('.site-header')||document.body).position,
    navVisible: (function(){ var n=document.querySelector('.nav'); if(!n) return 'none';
      return getComputedStyle(n).display; })(),
    overflowEls: overflowEls,
    hasFooter: !!document.querySelector('.site-footer')
  };
})()`;

const SEARCH_TEST = `(function(){
  return new Promise(function(resolve){
    var box = document.getElementById('search-results');
    var input = document.getElementById('q');
    var cnt = document.getElementById('search-count');
    if (!box || !input) { resolve({ok:false, reason:'no search box'}); return; }
    fetch('/search-index.json').then(function(r){return r.json();}).then(function(data){
      var terms = ['选型'];
      var hits = data.filter(function(it){
        var hay = (it.title+it.keywords+it.category+it.desc+it.body).toLowerCase();
        return terms.every(function(t){ return hay.indexOf(t.toLowerCase())>=0; });
      });
      resolve({ ok:true, indexSize:data.length, hitCount:hits.length,
                firstTitle: (hits[0]||{}).title||'' });
    }).catch(function(e){ resolve({ok:false, reason:String(e)}); });
  });
})()`;

(async () => {
  const targets = await httpJson('/json/list');
  const page = targets.find((t) => t.type === 'page');
  if (!page) { console.error('no page target'); process.exit(1); }
  const cdp = await Cdp.connect(page.webSocketDebuggerUrl);
  await cdp.send('Page.enable');
  await cdp.send('Runtime.enable');
  await cdp.send('Network.enable');

  const consoleErrors = [];
  const failedReqs = [];
  cdp.ws.on('message', (raw) => {
    let m; try { m = JSON.parse(raw.toString()); } catch (e) { return; }
    if (m.method === 'Runtime.exceptionThrown') {
      consoleErrors.push(JSON.stringify(m.params.exceptionDetails.exception || m.params.exceptionDetails));
    }
    if (m.method === 'Runtime.consoleAPICalled' && m.params.type === 'error') {
      consoleErrors.push((m.params.args || []).map((a) => a.value || a.description).join(' '));
    }
    if (m.method === 'Network.loadingFailed') {
      failedReqs.push(m.params.errorText + ' ' + (m.params.type || ''));
    }
  });

  const results = [];
  let idx = 0;
  for (const vp of VIEWPORTS) {
    await cdp.send('Emulation.setDeviceMetricsOverride', {
      width: vp.w, height: vp.h, deviceScaleFactor: 1, mobile: vp.w <= 768,
    });
    for (const pg of PAGES) {
      idx++;
      const url = BASE + pg.url + '?cb=' + idx;
      await cdp.send('Page.navigate', { url });
      await new Promise((r) => setTimeout(r, 900));
      let data;
      try { data = await cdp.eval(PROBE); } catch (e) { data = { error: String(e) }; }
      results.push({ vp: vp.name, w: vp.w, page: pg.name, ...data });
    }
  }

  // 搜索功能测试（桌面视口）
  await cdp.send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 1000, deviceScaleFactor: 1, mobile: false });
  await cdp.send('Page.navigate', { url: BASE + '/search/?cb=search' });
  await new Promise((r) => setTimeout(r, 1200));
  let searchRes;
  try { searchRes = await cdp.eval(SEARCH_TEST); } catch (e) { searchRes = { ok: false, reason: String(e) }; }

  // 首页渲染后 DOM 计数
  await cdp.send('Page.navigate', { url: BASE + '/?cb=dom' });
  await new Promise((r) => setTimeout(r, 1000));
  const homeDom = await cdp.eval(`(function(){
    return { cards: document.querySelectorAll('.cat-card').length,
             featured: document.querySelectorAll('.card-feature').length,
             stats: document.querySelectorAll('.hero-stat').length,
             latest: document.querySelectorAll('.card-grid .card').length };
  })()`);

  console.log(JSON.stringify({ results, consoleErrors, failedReqs, searchRes, homeDom }, null, 1));
  process.exit(0);
})().catch((e) => { console.error('FATAL', e); process.exit(1); });

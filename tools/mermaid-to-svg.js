// ビルド済みサイトの Mermaid 図 (<pre class="mermaid">) を、ライト用・ダーク用の静的 SVG に置き換える。
// 閲覧時に JavaScript や CDN を使わないので、どの環境 (アーティファクトの CSP など) でも図が表示される。
//
//   node tools/mermaid-to-svg.js site

const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');

const siteDir = path.resolve(process.argv[2] || 'site');
const mermaidJs = require.resolve('mermaid/dist/mermaid.min.js', { paths: [__dirname] });

// 実際に計測するフォントと、閲覧側で使われるフォントの幅がずれても崩れにくいよう、
// 和文はどの環境でもほぼ全角幅になるゴシック体をそろえて指定する。
const FONT = "'Hiragino Sans','Noto Sans JP','Yu Gothic UI',Meiryo,'IPAPGothic',sans-serif";

const THEMES = {
  light: {
    darkMode: false,
    background: '#ffffff',
    primaryColor: '#eef1fb', primaryBorderColor: '#5c6bc0', primaryTextColor: '#1f2333',
    secondaryColor: '#fff4e6', tertiaryColor: '#f6f7fb',
    lineColor: '#6b7280', textColor: '#1f2333',
    clusterBkg: '#f7f8fc', clusterBorder: '#c5cae9', edgeLabelBackground: '#ffffff',
    noteBkgColor: '#fff8db', noteBorderColor: '#e0b400', noteTextColor: '#3d3200',
    actorBkg: '#eef1fb', actorBorder: '#5c6bc0', actorTextColor: '#1f2333', actorLineColor: '#9aa1b2',
    signalColor: '#3b4252', signalTextColor: '#1f2333',
    labelBoxBkgColor: '#eef1fb', labelBoxBorderColor: '#5c6bc0', labelTextColor: '#1f2333',
    loopTextColor: '#1f2333', activationBkgColor: '#dfe4f7', sequenceNumberColor: '#ffffff',
  },
  dark: {
    darkMode: true,
    background: '#0b0c0f',
    primaryColor: '#232838', primaryBorderColor: '#8c9eff', primaryTextColor: '#e8eaf2',
    secondaryColor: '#3a2a1c', tertiaryColor: '#171a22',
    lineColor: '#a0a7b8', textColor: '#e8eaf2',
    clusterBkg: '#14161c', clusterBorder: '#3d4466', edgeLabelBackground: '#0b0c0f',
    noteBkgColor: '#3b3520', noteBorderColor: '#a08b2a', noteTextColor: '#f3e9c2',
    actorBkg: '#232838', actorBorder: '#8c9eff', actorTextColor: '#e8eaf2', actorLineColor: '#6b7286',
    signalColor: '#c9cedb', signalTextColor: '#e8eaf2',
    labelBoxBkgColor: '#232838', labelBoxBorderColor: '#8c9eff', labelTextColor: '#e8eaf2',
    loopTextColor: '#e8eaf2', activationBkgColor: '#30364c', sequenceNumberColor: '#0b0c0f',
  },
};

const unescape = s => s
  .replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"')
  .replace(/&#39;/g, "'").replace(/&#x27;/g, "'").replace(/&amp;/g, '&');

// シーケンス図などは矢印の定義に "arrowhead" のような共通の ID を使う。
// ライト用とダーク用を同じページに置くと ID が重複し、非表示側の定義が参照されて矢印が消えるので、
// SVG ごとに固有の接頭辞を付けて参照も書き換える。
function scopeIds(svg) {
  const svgId = svg.match(/<svg[^>]*\sid="([^"]+)"/)[1];
  const ids = [...svg.matchAll(/\sid="([^"]+)"/g)].map(m => m[1])
    .filter(id => id !== svgId && !id.startsWith(svgId));
  for (const id of new Set(ids)) {
    const esc = id.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const scoped = `${svgId}-${id}`;
    svg = svg
      .replace(new RegExp(`(\\sid=")${esc}"`, 'g'), `$1${scoped}"`)
      .replace(new RegExp(`url\\(#${esc}\\)`, 'g'), `url(#${scoped})`)
      .replace(new RegExp(`(href=")#${esc}"`, 'g'), `$1#${scoped}"`);
  }
  return svg;
}

function htmlFiles(dir) {
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap(e => {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) return e.name === 'assets' ? [] : htmlFiles(p);
    return e.name.endsWith('.html') ? [p] : [];
  });
}

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.setContent(`<html><body style="font-family:${FONT}"></body></html>`);
  await page.addScriptTag({ path: mermaidJs });

  const PRE = /<pre class="mermaid"><code>([\s\S]*?)<\/code><\/pre>/g;
  let total = 0;
  for (const [fileNo, file] of htmlFiles(siteDir).entries()) {
    const html = fs.readFileSync(file, 'utf8');
    const sources = [...html.matchAll(PRE)].map(m => unescape(m[1]));
    if (!sources.length) continue;

    const rendered = await page.evaluate(async ({ sources, themes, font, fileNo }) => {
      const out = sources.map(() => ({}));
      for (const [name, vars] of Object.entries(themes)) {
        mermaid.initialize({
          startOnLoad: false, securityLevel: 'strict', theme: 'base', htmlLabels: false,
          themeVariables: { ...vars, fontFamily: font, fontSize: '15px' },
          flowchart: { htmlLabels: false, padding: 14, nodeSpacing: 64, rankSpacing: 56, useMaxWidth: true },
          sequence: { useMaxWidth: true, mirrorActors: true },
        });
        for (const [i, src] of sources.entries()) {
          const { svg } = await mermaid.render(`mmd-${fileNo}-${i}-${name}`, src);
          out[i][name] = svg;
        }
      }
      return out;
    }, { sources, themes: THEMES, font: FONT, fileNo });

    let i = 0;
    const replaced = html.replace(PRE, () => {
      const { light, dark } = Object.fromEntries(
        Object.entries(rendered[i++]).map(([k, svg]) => [k, scopeIds(svg)]));
      return `<div class="mmd"><div class="mmd-light">${light}</div><div class="mmd-dark">${dark}</div></div>`;
    });
    fs.writeFileSync(file, replaced);
    total += sources.length;
    console.log(`${path.relative(siteDir, file)}: ${sources.length} 図`);
  }
  await browser.close();
  console.log(`合計 ${total} 図を SVG にしました`);
})().catch(e => { console.error(e); process.exit(1); });

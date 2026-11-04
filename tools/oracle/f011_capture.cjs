/* Development-only pinned Mermaid/browser oracle. Never imported by Python. */
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const cp = require('node:child_process');
const {createRequire} = require('node:module');
const root = path.resolve(__dirname, '../..');
const depRoot = path.join(root, '.local/f011-oracle');
const req = createRequire(path.join(depRoot, 'package.json'));
const sha = value => crypto.createHash('sha256').update(value).digest('hex');
const upstream = path.join(root, '.local/upstream-mermaid');
const pkg = path.join(depRoot, 'node_modules/mermaid');

function sourceIdentity() {
  const sourceMap = JSON.parse(fs.readFileSync(path.join(pkg, 'dist/mermaid.js.map'), 'utf8'));
  const wanted = ['defaultConfig.ts', 'config.ts', 'diagrams/flowchart/flowDb.ts',
    'rendering-util/createText.ts', 'rendering-util/rendering-elements/shapes/squareRect.ts',
    'themes/theme-redux-color.js', 'styles.ts',
    'rendering-util/layout-algorithms/elk/render.ts', 'diagrams/flowchart/parser/flow.jison'];
  const sources = [];
  for (const target of wanted) {
    const index = sourceMap.sources.findIndex(name => name.endsWith('/src/' + target));
    if (index < 0) throw new Error('Missing oracle source-map entry: ' + target);
    const canonical = cp.execFileSync('git', ['-C', upstream, 'show', 'HEAD:packages/mermaid/src/' + target]);
    let expected = canonical.toString('utf8');
    let transformation = 'canonical git blob';
    if (target.endsWith('.jison')) {
      const jison = req('jison');
      const parser = new jison.Generator(expected, {moduleType:'js', 'token-stack':true});
      expected = parser.generate({moduleMain:'() => {}'}) + ' \n\tparser.parser = parser;\n\texport { parser };\n\texport default parser;\n\t';
      transformation = '.build/jisonTransformer.ts / jison@0.4.18';
    }
    const actual = sourceMap.sourcesContent[index];
    if (actual !== expected) throw new Error('Oracle source mismatch: ' + target);
    sources.push({path:'packages/mermaid/src/'+target, canonicalSha256:sha(canonical),
      artifactSourceSha256:sha(actual), transformation});
  }
  const head = cp.execFileSync('git', ['-C', upstream, 'rev-parse', 'HEAD'], {encoding:'utf8'}).trim();
  if (head !== '1fb7869866dd619168d840291c9c54b4f129758b') throw new Error('Upstream HEAD drift');
  const lock = JSON.parse(fs.readFileSync(path.join(depRoot, 'package-lock.json'), 'utf8'));
  return {commit:head, package:'mermaid@12.2.0', sources,
    integrity:lock.packages['node_modules/mermaid'].integrity,
    bundleSha256:sha(fs.readFileSync(path.join(pkg, 'dist/mermaid.js')))};
}

async function main() {
  const outArg = process.argv.indexOf('--out');
  if (outArg < 0) throw new Error('--out NEW_DIRECTORY is required');
  const out = path.resolve(process.argv[outArg+1]);
  fs.mkdirSync(out, {recursive:false});
  const identity = sourceIdentity();
  fs.writeFileSync(path.join(out, 'identity.json'), JSON.stringify(identity,null,2));
  if (process.argv.includes('--verify-only')) return;
  const {chromium} = req('playwright');
  const browser = await chromium.launch({channel:'chrome', headless:true});
  const fixtureArg = process.argv.indexOf('--fixtures');
  const fixturePath = fixtureArg < 0 ? path.join(root, 'tests/f011/cases.json') : path.resolve(process.argv[fixtureArg+1]);
  const fixture = JSON.parse(fs.readFileSync(fixturePath,'utf8'));
  const cases = fixture.cases;
  const manifest = {identity, browser:browser.version(), node:process.version, cases:[]};
  try {
    for (const item of cases) {
      const page = await browser.newPage({viewport:{width:1600,height:1200},deviceScaleFactor:1});
      await page.route('**/*', route => route.abort()); // no remote fonts/images/scripts
      await page.setContent('<!doctype html><html><body style="margin:0;background:white"><div id="host"></div></body></html>');
      await page.addScriptTag({path:path.join(pkg,'dist/mermaid.js')});
      try {
      const result = await page.evaluate(async ({text,id}) => {
        mermaid.initialize({startOnLoad:false});
        const d = await mermaid.mermaidAPI.getDiagramFromText(text);
        const nodes = [...d.db.getVertices().values()].map(n => ({id:n.id,label:n.text,type:n.type,domId:n.domId}));
        const edges = d.db.getEdges().map(e => ({source:e.start,target:e.end,type:e.type}));
        const direction = d.db.getDirection();
        const config = mermaid.mermaidAPI.getConfig();
        const rendered = await mermaid.render('oracle_'+id.replaceAll('-','_'),text);
        document.getElementById('host').innerHTML = rendered.svg;
        await document.fonts.ready;
        const svg = document.querySelector('svg');
        const rect = svg.getBoundingClientRect();
        const box = element => { const b=element.getBoundingClientRect();return {x:b.x-rect.x,y:b.y-rect.y,width:b.width,height:b.height}; };
        const drawnNodes = [...svg.querySelectorAll('g.node')].map(n => ({id:n.getAttribute('data-id') || nodes.find(v => n.id.endsWith('-'+v.domId))?.id,
          domId:n.id,label:n.querySelector('.nodeLabel')?.textContent,box:box(n),
          fill:getComputedStyle(n.querySelector('rect')).fill,
          stroke:getComputedStyle(n.querySelector('rect')).stroke,
          fontSize:getComputedStyle(n.querySelector('.nodeLabel')).fontSize,
          fontFamily:getComputedStyle(n.querySelector('.nodeLabel')).fontFamily}));
        const drawnEdges = [...svg.querySelectorAll('path.flowchart-link')].map(e => ({id:e.id,d:e.getAttribute('d'),markerEnd:e.getAttribute('marker-end'),box:box(e)}));
        return {nodes,edges,direction,drawnNodes,drawnEdges,svg:rendered.svg,
          config:{layout:config.layout,theme:config.theme,look:config.look,htmlLabels:config.htmlLabels,fontFamily:config.fontFamily,fontSize:config.fontSize},
          viewport:{width:rect.width,height:rect.height}};
      }, {text:item.text,id:item.id});
      fs.writeFileSync(path.join(out,item.id+'.svg'), result.svg);
      delete result.svg;
      fs.writeFileSync(path.join(out,item.id+'.json'),JSON.stringify(result,null,2));
      await page.locator('svg').screenshot({path:path.join(out,item.id+'.png')});
      manifest.cases.push({id:item.id,status:'captured'});
      } catch(error) {
        fs.writeFileSync(path.join(out,item.id+'.error.json'),JSON.stringify({message:String(error)},null,2));
        manifest.cases.push({id:item.id,status:'error',message:String(error)});
      }
      await page.close();
    }
    for (const item of fixture.negativeCases || []) {
      const page=await browser.newPage();
      await page.setContent('<html><body></body></html>');
      await page.addScriptTag({path:path.join(pkg,'dist/mermaid.js')});
      const result=await page.evaluate(async text=>{
        mermaid.initialize({startOnLoad:false});
        try {await mermaid.parse(text);return {rejected:false};}
        catch(error) {return {rejected:true,message:String(error),hash:error.hash};}
      },item.text);
      fs.writeFileSync(path.join(out,item.id+'.negative.json'),JSON.stringify(result,null,2));
      manifest.cases.push({id:item.id,status:result.rejected?'negative_rejected':'error'});
      await page.close();
    }
  } finally {
    fs.writeFileSync(path.join(out,'manifest.json'),JSON.stringify(manifest,null,2));
    await browser.close();
  }
  if (manifest.cases.some(item=>item.status==='error')) process.exitCode=1;
}
main().catch(error => {console.error(error);process.exitCode=1;});

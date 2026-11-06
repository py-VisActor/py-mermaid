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
const json = value => JSON.stringify(value,(_key,item)=>typeof item==='number'&&!Number.isFinite(item)?{$jsNumber:String(item)}:item,2);
const upstream = path.join(root, '.local/upstream-mermaid');
const pkg = path.join(depRoot, 'node_modules/mermaid');

function sourceIdentity() {
  const sourceMap = JSON.parse(fs.readFileSync(path.join(pkg, 'dist/mermaid.js.map'), 'utf8'));
  const wanted = ['defaultConfig.ts', 'config.ts', 'diagrams/flowchart/flowDb.ts',
    'rendering-util/createText.ts', 'rendering-util/rendering-elements/shapes/squareRect.ts',
    'themes/theme-redux-color.js', 'styles.ts',
    'rendering-util/layout-algorithms/elk/render.ts', 'diagrams/flowchart/parser/flow.jison'];
  wanted.push('rendering-util/rendering-elements/clusters.js','rendering-util/rendering-elements/edges.js',
    'rendering-util/rendering-elements/shapes.ts', ...['roundedRect','stadium','subroutine','cylinder',
    'circle','doubleCircle','question','hexagon','leanLeft','leanRight','trapezoid','invertedTrapezoid',
    'rectLeftInvArrow'].map(s=>'rendering-util/rendering-elements/shapes/'+s+'.ts'));
  wanted.push('preprocess.ts','diagram-api/frontmatter.ts','diagram-api/comments.ts','utils.ts',
    'rendering-util/handle-markdown-text.ts','rendering-util/splitText.ts',
    'diagrams/common/common.ts','diagrams/flowchart/styles.ts','rendering-util/insertLookDefs.ts',
    ...['base','dark','default','forest','neutral','neo','neo-dark','redux','redux-dark','redux-color','redux-dark-color'].map(s=>'themes/theme-'+s+'.js'));
  const sources = [];
  // F01.4: verify every bundled shared shape handler against the fixed git
  // blob, rather than trusting an unverified extension of the old 14 shapes.
  wanted.push(...sourceMap.sources.filter(name => /\/src\/rendering-util\/rendering-elements\/shapes\/[^/]+\.(?:ts|js)$/.test(name))
    .map(name => name.split('/src/')[1]));
  for (const target of new Set(wanted)) {
    const exact = sourceMap.sources.indexOf('../src/'+target);
    const index = exact>=0?exact:sourceMap.sources.findIndex(name => name.endsWith('/src/' + target));
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
  const manifest = {identity, fixtureSha256:sha(fs.readFileSync(fixturePath)), browser:browser.version(), node:process.version, cases:[]};
  try {
    for (const item of cases) {
      const page = await browser.newPage({viewport:{width:1600,height:1200},deviceScaleFactor:1});
      await page.route('**/*', route => {
        const image=item.resources?.images?.find(value=>value.id===route.request().url());
        return image?route.fulfill({body:Buffer.from(image.dataBase64,'base64'),contentType:image.mime||'image/png'}):route.abort();
      }); // explicit fixture bytes only; no remote fonts/images/scripts
      await page.setContent('<!doctype html><html><body style="margin:0;background:white"><div id="host"></div></body></html>');
      await page.addScriptTag({path:path.join(pkg,'dist/mermaid.js')});
      for(const font of item.resources?.fonts||[]){
        const data=fs.readFileSync(path.resolve(root,font.path));
        if(font.sha256&&sha(data)!==font.sha256)throw new Error('Fixture font SHA mismatch');
        await page.addStyleTag({content:`@font-face{font-family:${JSON.stringify(font.family)};src:url(data:font/ttf;base64,${data.toString('base64')})}`});
      }
      try {
      const result = await page.evaluate(async ({text,id,config:siteConfig,resources}) => {
        mermaid.initialize({startOnLoad:false,...(siteConfig||{})});
        const packs={};
        for(const icon of resources?.icons||[]){
          const split=icon.id.indexOf(':');if(split<1)continue;
          const prefix=icon.id.slice(0,split),name=icon.id.slice(split+1);
          const svg=new DOMParser().parseFromString(icon.svg,'image/svg+xml').documentElement;
          const vb=(svg.getAttribute('viewBox')||'0 0 24 24').split(/[ ,]+/).map(Number);
          (packs[prefix]??={prefix,icons:{}}).icons[name]={body:svg.innerHTML,width:vb[2],height:vb[3]};
        }
        mermaid.registerIconPacks(Object.entries(packs).map(([name,icons])=>({name,icons})));
        const d = await mermaid.mermaidAPI.getDiagramFromText(text);
        const displayText=t=>String(t??'').replaceAll('ﬂ°°','&#').replaceAll('ﬂ°','&').replaceAll('¶ß',';').replaceAll('\\n','\n');
        const groups = d.db.getSubGraphs().map(g => ({id:g.id,label:displayText(g.title),labelKind:g.labelType||'text',members:[...g.nodes],direction:g.dir || null}));
        const groupIds = new Set(groups.map(g => g.id));
        const nodes = [...d.db.getVertices().values()].filter(n => !groupIds.has(n.id)).map(n => ({id:n.id,label:displayText(n.text),labelKind:n.labelType||'text',type:n.type||'square',domId:n.domId}));
        const edges = d.db.getEdges().map(e => ({id:e.id,source:e.start,target:e.end,type:e.type,label:displayText(e.text),labelKind:e.labelType||'text'}));
        const direction = d.db.getDirection();
        const data=d.db.getData?.();
        const sourceProjection=data?{
          nodes:data.nodes.filter(n=>!n.isGroup).map(n=>({id:n.id,domId:n.domId||n.id,label:displayText(n.label),shape:n.shape,parent_id:n.parentId||null})),
          groups:data.nodes.filter(n=>n.isGroup).map(n=>({id:n.id,label:displayText(n.label),parent_id:n.parentId||null})),
          edges:data.edges.map(e=>({id:e.id,source:e.start,target:e.end,label:displayText(e.label),markerStart:e.arrowTypeStart,markerEnd:e.arrowTypeEnd,stroke:e.thickness,curve:e.curve}))
        }:null;
        const config = mermaid.mermaidAPI.getConfig();
        const rendered = await mermaid.render('oracle_'+id.replaceAll('-','_'),text);
        document.getElementById('host').innerHTML = rendered.svg;
        let transport={kind:'svg'},originalOutput=null;
        if(!document.querySelector('#host svg')){
          const frame=document.querySelector('#host iframe');
          const source=frame?.getAttribute('src')||'';
          const encoded=source.match(/^data:text\/html[^,]*;base64,(.*)$/s);
          if(!encoded)throw new Error('Official render returned neither SVG nor recognized sandbox transport');
          originalOutput=rendered.svg;
          const decoded=new TextDecoder().decode(Uint8Array.from(atob(encoded[1]),c=>c.charCodeAt(0)));
          const container=document.createElement('template');container.innerHTML=decoded;
          const inner=container.content.querySelector('svg');
          if(!inner)throw new Error('Sandbox transport contains no SVG');
          // Preserve the complete original iframe output separately. Only its
          // transport is unwrapped: the source SVG/layout/styles are unchanged.
          document.getElementById('host').replaceChildren(inner);
          transport={kind:'sandbox-iframe-base64',unwrappedForSvgScreenshot:true};
        }
        await document.fonts.ready;
        // The requested product scope is the initial static frame, not playback.
        for(const animation of document.getAnimations()){animation.pause();animation.currentTime=0;}
        const svg = document.querySelector('svg');
        const rect = svg.getBoundingClientRect();
        const box = element => { const b=element.getBoundingClientRect();return {x:b.x-rect.x,y:b.y-rect.y,width:b.width,height:b.height}; };
        const shapeStyle=(node,key)=>{
          const container=node.querySelector('.label-container,.outer-path')||[...node.children].find(e=>/^(rect|circle|ellipse|polygon|path)$/i.test(e.tagName)||e.tagName.toLowerCase()==='g'&&!e.classList.contains('label')&&e.querySelector('path'))||node.querySelector('path,rect,circle,ellipse,polygon');
          const parts=container?.tagName.toLowerCase()==='g'?[...container.querySelectorAll('rect,circle,ellipse,polygon,path')]:[container];
          const allStrokeParts=[...node.querySelectorAll('path,rect,circle,ellipse,polygon,line')].filter(e=>!e.closest('g.label,.nodeLabel,defs,clipPath,mask')&&Number(getComputedStyle(e).strokeOpacity)!==0);
          const shape=sourceProjection?.nodes.find(value=>value.id===semanticNodeId(node))?.shape;
          const detachedStoreBorder=config.look==='handDrawn'&&['datastore','data-store'].includes(shape);
          // These handlers use .node, so CSS also fills the final rough outline.
          // Its opaque closed body covers the earlier fillSketch strokes.
          if(key==='fill'&&config.look==='handDrawn'&&['sm-circ','fr-circ','stateStart','stateEnd','small-circle','framed-circle','start','stop'].includes(shape)){
            const finalOutline=[...parts].reverse().find(e=>e.tagName.toLowerCase()==='path');
            if(finalOutline){const fill=getComputedStyle(finalOutline).fill;if(fill&&fill!=='none')return fill;}
          }
          const targets=(key==='filter'?[container,...parts]:key==='stroke'?[...(detachedStoreBorder&&allStrokeParts.length?allStrokeParts:parts)].reverse():parts).filter(Boolean);
          if(key==='fill'&&config.look==='handDrawn'&&parts.length>1&&parts[0].getAttribute('fill')==='none')return getComputedStyle(parts[0]).stroke;
          const direct=targets.map(e=>getComputedStyle(e)[key]).find(v=>v&&v!=='none');
          // RoughJS hachure is a fill-colored stroke followed by an outline.
          if(!direct&&key==='fill'&&config.look==='handDrawn'&&parts.length>1)return getComputedStyle(parts[0]).stroke;
          return direct||'none';
        };
        const labelSnapshot=el=>{
          if(!el)return {visible:'',runs:[],box:null};
          for(let ancestor=el;ancestor;ancestor=ancestor.parentElement){
            const css=getComputedStyle(ancestor);
            if(css.display==='none'||css.visibility==='hidden')return {visible:'',runs:[],box:box(el)};
            if(ancestor===svg)break;
          }
          const html=el.namespaceURI==='http://www.w3.org/1999/xhtml';
          const outer=el.querySelectorAll('tspan.text-outer-tspan');
          const visible=html?el.innerText:outer.length?[...outer].map(n=>n.textContent).join('\n'):el.textContent;
          const walker=document.createTreeWalker(el,NodeFilter.SHOW_TEXT),runs=[];
          let leaf;
          while((leaf=walker.nextNode())){
            if(!leaf.textContent)continue;
            const parent=leaf.parentElement,css=getComputedStyle(parent);
            if(css.display==='none'||css.visibility==='hidden')continue;
            const range=document.createRange();range.selectNodeContents(leaf);
            const b=range.getBoundingClientRect();
            runs.push({text:leaf.textContent,fontFamily:css.fontFamily,fontSize:css.fontSize,
              fontWeight:css.fontWeight,fontStyle:css.fontStyle,color:html?css.color:css.fill,
              background:css.backgroundColor,decoration:css.textDecorationLine,opacity:css.opacity,direction:css.direction,
              box:{x:b.x-rect.x,y:b.y-rect.y,width:b.width,height:b.height}});
          }
          return {visible,runs,box:box(el)};
        };
        const nodeLabel=n=>n.querySelector('.nodeLabel')||n.querySelector('g.label text')||n.querySelector('text');
        const semanticNodeId=n=>n.getAttribute('data-id')||[...nodes,...(sourceProjection?.nodes||[])].find(v=>n.id===v.domId||n.id==='oracle_'+id.replaceAll('-','_')+'-'+(v.domId||v.id)||n.id==='oracle_'+id.replaceAll('-','_')+'-'+v.id)?.id;
        const drawnNodes = [...svg.querySelectorAll('g.node,g.rough-node,g.image-shape,g.icon-shape')].filter(n=>semanticNodeId(n)).map(n => ({id:semanticNodeId(n),
          domId:n.id,label:nodeLabel(n)?.textContent,visibleLabel:labelSnapshot(nodeLabel(n)),box:box(n),
          fill:shapeStyle(n,'fill'),stroke:shapeStyle(n,'stroke'),
          filter:shapeStyle(n,'filter'),strokeWidth:shapeStyle(n,'strokeWidth'),
          fontSize:nodeLabel(n)?getComputedStyle(nodeLabel(n)).fontSize:null,
          fontFamily:nodeLabel(n)?getComputedStyle(nodeLabel(n)).fontFamily:null}));
        const drawnEdges = [...svg.querySelectorAll('path.flowchart-link')].map(e => {const css=getComputedStyle(e);return {id:e.id,d:e.getAttribute('d'),markerStart:e.getAttribute('marker-start'),markerEnd:e.getAttribute('marker-end'),stroke:css.stroke,strokeWidth:css.strokeWidth,dash:css.strokeDasharray,lineCap:css.strokeLinecap,box:box(e)};});
        const drawnGroups = [...svg.querySelectorAll('g.cluster')].map(g=>({id:g.id,label:g.querySelector('.cluster-label')?.textContent,
          visibleLabel:labelSnapshot(g.querySelector('.cluster-label .nodeLabel,.cluster-label span')||g.querySelector('.cluster-label text')),
          fill:getComputedStyle(g.querySelector('rect')||g).fill,stroke:getComputedStyle(g.querySelector('rect')||g).stroke,
          box:box(g),titleBox:g.querySelector('.cluster-label')?box(g.querySelector('.cluster-label')):null}));
        const drawnEdgeLabels = [...svg.querySelectorAll('g.edgeLabel')].filter(g=>{
          const b=g.getBBox();return g.querySelector('g.label')&&(g.textContent.trim()||b.width>0||b.height>0);
        }).map(g=>({id:g.querySelector('g.label')?.getAttribute('data-id'),label:g.textContent,
          visibleLabel:labelSnapshot(g.querySelector('span.edgeLabel')||g.querySelector('text')),box:box(g)}));
        const title=svg.querySelector('.flowchartTitleText');
        const gradients=[...svg.querySelectorAll('linearGradient')].map(g=>({id:g.id,x1:g.getAttribute('x1'),x2:g.getAttribute('x2'),
          stops:[...g.querySelectorAll('stop')].map(s=>({offset:s.getAttribute('offset'),color:getComputedStyle(s).stopColor,opacity:getComputedStyle(s).stopOpacity}))}));
        return {nodes,edges,groups,sourceProjection,direction,drawnNodes,drawnEdges,drawnGroups,drawnEdgeLabels,
          title:title?labelSnapshot(title):null,diagramTitle:displayText(d.db.getDiagramTitle?.()),gradients,transport,
          originalOutput,svg:originalOutput?svg.outerHTML:rendered.svg,
          config:{layout:config.layout,theme:config.theme,look:config.look,htmlLabels:config.htmlLabels,fontFamily:config.fontFamily,fontSize:config.fontSize,
            securityLevel:config.securityLevel,markdownAutoWrap:config.markdownAutoWrap,themeVariables:config.themeVariables,flowchart:config.flowchart},
          viewport:{width:rect.width,height:rect.height}};
      }, {text:item.text,id:item.id,config:item.config,resources:item.resources});
      fs.writeFileSync(path.join(out,item.id+'.svg'), result.svg);
      delete result.svg;
      if(result.originalOutput)fs.writeFileSync(path.join(out,item.id+'.sandbox.html'),result.originalOutput);
      delete result.originalOutput;
      fs.writeFileSync(path.join(out,item.id+'.json'),json(result));
      await page.locator('#host > svg').screenshot({path:path.join(out,item.id+'.png')});
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
    for (const item of fixture.renderErrorCases || []) {
      const page=await browser.newPage();
      await page.route('**/*',route=>route.abort());
      await page.setContent('<html><body></body></html>');
      await page.addScriptTag({path:path.join(pkg,'dist/mermaid.js')});
      const result=await page.evaluate(async ({text,id,expectedSourceBlank})=>{
        mermaid.initialize({startOnLoad:false});
        try {await mermaid.parse(text);} catch(error) {return {parsed:false,renderRejected:false,message:String(error)};}
        try {
          const rendered=await mermaid.render('error_'+id.replaceAll('-','_'),text);
          if(expectedSourceBlank){
            const holder=document.createElement('div');holder.innerHTML=rendered.svg;
            const drawnNodes=holder.querySelectorAll('g.node,g.rough-node,g.image-shape,g.icon-shape').length;
            const drawnInk=holder.querySelectorAll('.nodes path,.nodes rect,.nodes circle,.nodes text,.nodes image').length;
            return {parsed:true,renderRejected:false,missingShape:drawnNodes===0&&drawnInk===0,drawnNodes,drawnInk,svg:rendered.svg};
          }
          return {parsed:true,renderRejected:false};
        }
        catch(error) {return {parsed:true,renderRejected:true,message:String(error)};}
      },item);
      if(result.svg){fs.writeFileSync(path.join(out,item.id+'.source-defect.svg'),result.svg);delete result.svg;}
      fs.writeFileSync(path.join(out,item.id+'.render-error.json'),JSON.stringify(result,null,2));
      manifest.cases.push({id:item.id,status:result.parsed&&(result.renderRejected||item.expectedSourceBlank&&result.missingShape)?'expected_render_error':'error'});
      await page.close();
    }
    for (const item of fixture.unsupportedCases || []) {
      const page=await browser.newPage();
      await page.route('**/*',route=>route.abort());
      await page.setContent('<html><body></body></html>');
      await page.addScriptTag({path:path.join(pkg,'dist/mermaid.js')});
      const result=await page.evaluate(async ({text,config})=>{
        mermaid.initialize({startOnLoad:false,...(config||{})});
        try {await mermaid.parse(text);return {accepted:true,renderExecuted:false};}
        catch(error){return {accepted:false,renderExecuted:false,message:String(error)};}
      },item);
      fs.writeFileSync(path.join(out,item.id+'.unsupported.json'),json(result));
      manifest.cases.push({id:item.id,status:result.accepted?'outside_native_scope':'error'});
      await page.close();
    }
  } finally {
    fs.writeFileSync(path.join(out,'manifest.json'),JSON.stringify(manifest,null,2));
    await browser.close();
  }
  if (manifest.cases.some(item=>item.status==='error')) process.exitCode=1;
}
main().catch(error => {console.error(error);process.exitCode=1;});

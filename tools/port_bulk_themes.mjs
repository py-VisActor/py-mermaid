// Development-only static translation of fixed theme constructors/updateColors.
// Generated product code has no JS interpreter or development-file dependency.
import fs from 'node:fs';
import path from 'node:path';
import {createRequire} from 'node:module';
import crypto from 'node:crypto';
const root=path.resolve(import.meta.dirname,'..');
const require=createRequire(path.join(root,'.local/f011-oracle/package.json'));
const esprima=require('esprima');
const names=['base','dark','default','forest','neutral','neo','neo-dark','redux','redux-dark','redux-color','redux-dark-color'];
function body(text,name){
 const start=text.indexOf(`  ${name}() {`);if(start<0)throw Error('Missing '+name);
 let i=text.indexOf('{',start),level=0,quote=null,line=false,block=false;
 const opening=i;
 for(;i<text.length;i++){
  const c=text[i],next=text[i+1];
  if(line){if(c==='\n')line=false;continue;}
  if(block){if(c==='*'&&next==='/'){block=false;i++;}continue;}
  if(quote){if(c==='\\'){i++;continue;}if(c===quote)quote=null;continue;}
  if(c==='/'&&next==='/'){line=true;i++;continue;}
  if(c==='/'&&next==='*'){block=true;i++;continue;}
  if(c==='"'||c==="'"||c==='`'){quote=c;continue;}
  if(c==='{')level++;
  if(c==='}'&&--level===0)return text.slice(opening,i+1);
 }
 throw Error('Unclosed method '+name);
}
let source='',currentName='',symbols=new Set(),counts={};
const py=value=>JSON.stringify(value).replace(/\btrue\b/g,'True').replace(/\bfalse\b/g,'False').replace(/\bnull\b/g,'None');
function expr(n){
 if(!n)throw Error('Missing expression');counts[n.type]=(counts[n.type]||0)+1;
 switch(n.type){
 case 'Literal':return typeof n.value==='string'?JSON.stringify(n.value):py(n.value);
 case 'ThisExpression':return 'v';
 case 'Identifier':
  if(n.name==='undefined')return 'None';
  if(n.name==='oldAttributeBackgroundColorEven')return "'#f2f2f2'";
  if(n.name==='oldAttributeBackgroundColorOdd')return "'#ffffff'";
  return n.name;
 case 'MemberExpression':{
  const obj=expr(n.object),key=n.computed?expr(n.property):JSON.stringify(n.property.name);
  if(n.object.type==='ThisExpression')return `v.get(${key})`;
  if(n.computed)return `_js_get(${obj}, ${key})`;
  if(n.property.name==='length')return `len(${obj})`;
  return `(${obj} or {}).get(${key})`;
 }
 case 'CallExpression':{
  if(n.callee.type==='MemberExpression'&&n.callee.object.type==='ThisExpression'&&n.callee.property.name==='updateColors')return `${currentName.replaceAll('-','_')}_update(v)`;
  const fn=expr(n.callee);symbols.add(fn);
  if(n.callee.type==='MemberExpression'&&n.callee.object.type==='Identifier'&&n.callee.object.name==='Math')return `${({abs:'abs',max:'max',min:'min',round:'_js_round',floor:'math.floor',ceil:'math.ceil'})[n.callee.property.name]||(()=>{throw Error('Unknown Math method')})()}(${n.arguments.map(expr).join(', ')})`;
  return `${fn}(${n.arguments.map(expr).join(', ')})`;
 }
 case 'ObjectExpression':return '{'+n.properties.map(p=>`${p.computed?expr(p.key):JSON.stringify(p.key.name??p.key.value)}: ${expr(p.value)}`).join(', ')+'}';
 case 'ArrayExpression':return '['+n.elements.map(expr).join(', ')+']';
 case 'UnaryExpression':return n.operator==='!'?`(not truthy(${expr(n.argument)}))`:`(${n.operator}${expr(n.argument)})`;
 case 'BinaryExpression':{
  const a=expr(n.left),b=expr(n.right);
  if(n.operator==='+')return `_js_add(${a}, ${b})`;
  if(n.operator==='%')return `_js_mod(${a}, ${b})`;
  return `(${a} ${({'===':'==','!==':'!=','==':'==','!=':'!='})[n.operator]||n.operator} ${b})`;
 }
 case 'LogicalExpression':{
  const a=expr(n.left),b=expr(n.right),nullish=source.slice(n.left.range[1],n.right.range[0]).includes('??');
  if(nullish)return `(${a} if ${a} is not None else ${b})`;
  return n.operator==='||'?`(${a} if truthy(${a}) else ${b})`:`(${b} if truthy(${a}) else ${a})`;
 }
 case 'ConditionalExpression':return `(${expr(n.consequent)} if truthy(${expr(n.test)}) else ${expr(n.alternate)})`;
 case 'AssignmentExpression':throw Error('Assignment expression needs statement context');
 default:throw Error('Unsupported expression '+n.type+' '+source.slice(...n.range));
 }
}
function target(n){
 if(n.type==='Identifier')return n.name;
 if(n.type==='MemberExpression')return `${expr(n.object)}[${n.computed?expr(n.property):JSON.stringify(n.property.name)}]`;
 throw Error('Unsupported assignment target '+n.type);
}
function stmt(n,depth=1){
 const pad='    '.repeat(depth);counts[n.type]=(counts[n.type]||0)+1;
 switch(n.type){
 case 'BlockStatement':return n.body.map(x=>stmt(x,depth)).join('')||pad+'pass\n';
 case 'ExpressionStatement':{
  const e=n.expression;
  if(e.type==='AssignmentExpression')return pad+target(e.left)+' '+e.operator+' '+expr(e.right)+'\n';
  if(e.type==='CallExpression'&&e.callee.type==='MemberExpression'&&e.callee.property.name==='forEach'){
   const fn=e.arguments[0];
   if(fn.type!=='FunctionExpression'||fn.params.length!==2)throw Error('Unsupported forEach');
   return pad+`for ${expr(fn.params[1])}, ${expr(fn.params[0])} in enumerate(${expr(e.callee.object)}):\n`+stmt(fn.body,depth+1);
  }
  return pad+expr(e)+'\n';
 }
 case 'VariableDeclaration':return n.declarations.map(d=>pad+target(d.id)+' = '+(d.init?expr(d.init):'None')+'\n').join('');
 case 'IfStatement':return pad+'if truthy('+expr(n.test)+'):\n'+stmt(n.consequent,depth+1)+(n.alternate?pad+'else:\n'+stmt(n.alternate,depth+1):'');
 case 'ForStatement':{
  if(n.init.type!=='VariableDeclaration'||n.init.declarations.length!==1||n.test.type!=='BinaryExpression'||n.test.operator!=='<'||n.update.type!=='UpdateExpression'||n.update.operator!=='++')throw Error('Unsupported loop');
  const d=n.init.declarations[0];return pad+`for ${target(d.id)} in range(int(${expr(d.init)}), int(${expr(n.test.right)})):\n`+stmt(n.body,depth+1);
 }
 case 'ReturnStatement':return pad+'return'+(n.argument?' '+expr(n.argument):'')+'\n';
 case 'EmptyStatement':return '';
 default:throw Error('Unsupported statement '+n.type+' '+source.slice(...n.range));
 }
}
const output=['"""Complete static theme rules from fixed Mermaid constructors/updateColors.','Generated by tools/port_bulk_themes.mjs; no runtime JavaScript evaluation.','"""','import math','from .colors import adjust, darken, lighten, invert, isDark, rgba, mkBorder, truthy','','def _js_add(a,b):',"    if isinstance(a,str) or isinstance(b,str):return str(a)+str(b)",'    return a+b','','def _js_mod(a,b):',"    return math.fmod(a,b) if b else math.nan",'','def _js_get(value,key):','    if isinstance(value,dict):return value.get(key)','    if isinstance(value,(list,tuple)) and isinstance(key,(int,float)) and math.isfinite(key) and key==int(key) and 0<=key<len(value):return value[int(key)]','    return None','','def optional(value,key):','    return value.get(key) if isinstance(value,dict) else None','','def _js_round(value):','    return math.floor(value+.5)',''];
const files=[];
for(const name of names){
 currentName=name;
 const filename=path.join(root,'.local/upstream-mermaid/packages/mermaid/src/themes',`theme-${name}.js`);
 const raw=fs.readFileSync(filename,'utf8');files.push({path:path.relative(root,filename).replaceAll('\\','/'),sha256:crypto.createHash('sha256').update(raw).digest('hex')});
 for(const [method,suffix] of [['constructor','construct'],['updateColors','update']]){
  // Esprima's ES2017 frontend needs these two syntax-only rewrites. Their
  // semantics are retained explicitly in generated optional/nullish branches.
  source='function theme() '+body(raw,method).replace(/this\.([\w]+)\?\.([\w]+)/g,(_,a,b)=>`optional(this.${a}, ${JSON.stringify(b)})`).replace(/\(([\w]+\s*,\s*[\w]+)\)\s*=>\s*\{/g,'function($1){');
  let parsed;
  try{parsed=esprima.parse(source.replaceAll('??','||'),{range:true});}
  catch(error){throw Error(`${name}.${method}: ${error.message}\n${source.slice(Math.max(0,error.index-160),error.index+160)}`);}
  output.push(`def ${name.replaceAll('-','_')}_${suffix}(v):`+ '\n'+stmt(parsed.body[0].body));
 }
}
output.push('THEME_RULES = {',...names.map(n=>`    ${JSON.stringify(n)}: (${n.replaceAll('-','_')}_construct, ${n.replaceAll('-','_')}_update),`),'}','');
fs.writeFileSync(path.join(root,'src/py_mermaid/config/theme_rules_full.py'),output.join('\n'));
fs.writeFileSync(path.join(root,'references/bulk-themes-sources.json'),JSON.stringify({schema:'py-mermaid-static-theme-source/v1',upstreamCommit:'1fb7869866dd619168d840291c9c54b4f129758b',files,symbols:[...symbols].sort(),astNodeCounts:counts,status:'code_complete_unverified'},null,2)+'\n');
console.log(JSON.stringify({themes:names.length,methods:names.length*2,files:files.length,symbols:[...symbols].sort(),astNodeCounts:counts}));

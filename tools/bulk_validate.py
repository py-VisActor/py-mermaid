"""Native retained-batch execution and content/ink/geometry checks, no image editing.

Pure metrics are gates only where source-independent expected values exist.
Family unit suites own algorithm/relationship assertions; this tool never
promotes image similarity or successful export to whole-family compatibility.
"""
from __future__ import annotations
import argparse
from dataclasses import replace
from io import BytesIO
import json
import math
from pathlib import Path
import re
import sys
import traceback
from PIL import Image,ImageChops,ImageColor
from bulk_support import load_cases, resources, write, value_json
from run_support import source_identity,environment_identity


def norm(text):return re.sub(r'\s+','',str(text)).replace('\u00a0','')


def check_output(result,case,png=None,trace=None):
    """Independent visible-text, encoded geometry and actual ink checks.

    The per-family source tests additionally check identities, relations, ports,
    containment, ordering and nonoverlap. No oracle coordinates enter layout.
    """
    trace=trace if trace is not None else result.trace
    im=Image.open(BytesIO(result.data if png is None else png));im.load()
    im=im.convert('RGBA')
    errors=[]
    if im.size!=(result.width,result.height):errors.append('encoded-size-mismatch')
    empty=case.get('expectedEmpty')
    if empty:
        if not empty.get('reason') or case.get('expectedText'):errors.append('invalid-source-empty-contract')
        if 'width' in empty or 'height' in empty:
            if im.size!=(empty.get('width'),empty.get('height')):errors.append('source-empty-canvas-dimensions')
        color=ImageColor.getcolor(empty['background'],'RGBA')
        if any(extrema!=(channel,channel) for extrema,channel in zip(im.getextrema(),color)):errors.append('source-empty-canvas-has-unexpected-pixels')
        if any(e.opacity>0 and e.box and e.box.width>0 and e.box.height>0 for e in trace):errors.append('source-empty-canvas-has-draw-events')
        return errors
    bg=Image.new('RGBA',im.size,'white');rgb=Image.alpha_composite(bg,im).convert('RGB')
    if not ImageChops.difference(rgb,Image.new('RGB',rgb.size,'white')).getbbox():errors.append('white-noop-output')
    visible=norm(''.join(e.text or '' for e in trace if e.opacity>0))
    for expected in case.get('expectedText',[]):
        if norm(expected) not in visible:errors.append('missing-visible-text:'+expected)
    for excluded in case.get('hiddenText',[]):
        if norm(excluded) in visible:errors.append('unexpected-visible-text:'+excluded)
    ink_checked=0
    for event in trace:
        box=event.box
        if box is None:continue
        coords=(box.x,box.y,box.width,box.height)
        if not all(isinstance(v,(int,float)) and math.isfinite(v) for v in coords) or min(box.width,box.height)<0:
            errors.append('nonfinite-negative-geometry:'+event.semantic_id);continue
        # Commands deliberately clipped by source retain the intersection box.
        if box.width and box.height and (box.x<-.5 or box.y<-.5 or box.x+box.width>result.width+.5 or box.y+box.height>result.height+.5):
            errors.append('canvas-clipping:'+event.semantic_id+':'+event.kind)
        if not event.text or not event.text.strip() or event.opacity==0 or box.width<=0 or box.height<=0:continue
        # Glyph paths and labels use actual Canvas ink. White text can be visible
        # over dark fills, so compare local variation rather than a dark cutoff.
        crop=rgb.crop((max(0,math.floor(box.x)),max(0,math.floor(box.y)),min(rgb.width,math.ceil(box.x+box.width)),min(rgb.height,math.ceil(box.y+box.height))))
        if crop.width and crop.height:
            ink_checked+=1
            if all(low==high for low,high in crop.getextrema()):errors.append('unpainted-label:'+event.semantic_id+':'+event.text)
    if case.get('expectedText') and ink_checked==0:errors.append('no-painted-label-regions')
    return sorted(set(errors))


def controls(result,case):
    """No-op and missing-content mutations must be rejected; original is untouched."""
    if case.get('expectedEmpty'):
        changed=Image.open(BytesIO(result.data)).convert('RGBA')
        pixel=changed.getpixel((0,0));changed.putpixel((0,0),tuple(255-c for c in pixel[:3])+(255,))
        b=BytesIO();changed.save(b,format='PNG')
        return {'sourceEmptyNonemptyMutationRejected':bool(check_output(result,case,png=b.getvalue()))}
    b=BytesIO();Image.new('RGB',(result.width,result.height),'white').save(b,format='PNG')
    return {'whiteNoopRejected':bool(check_output(result,case,png=b.getvalue())),
            'missingTextRejected':not case.get('expectedText') or bool(check_output(result,case,trace=tuple(e for e in result.trace if not e.text)))}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--fixtures',nargs='+',required=True,type=Path)
    parser.add_argument('--out',required=True,type=Path)
    parser.add_argument('--backend',choices=('cpu','auto','gpu'),required=True)
    parser.add_argument('--group')
    parser.add_argument('--case')
    args=parser.parse_args();args.out.mkdir(parents=True,exist_ok=False)
    cases=load_cases(args.fixtures)
    if args.group:cases=[c for c in cases if c['group']==args.group]
    if args.case:cases=[c for c in cases if c['id']==args.case]
    if not cases:raise ValueError('No selected cases')
    from py_mermaid import render,MermaidError
    candidate=source_identity();rows=[]
    write(args.out/'identity.json',{'source':candidate,'environment':environment_identity(),'backend':args.backend})
    for case in cases:
        id=case['id'];row={'id':id,'kind':case['kind'],'group':case['group'],'expect':case['expect'],'status':'ERROR','checks':[]}
        if case['expect']=='excluded_by_static_scope':row['status']='EXCLUDED';rows.append(row);continue
        try:
            result=render(case['source'],config=case.get('config'),resources=resources(case),backend=args.backend)
            from py_mermaid.model.scene import Diagram
            from py_mermaid.runtime.common import config_dict
            from py_mermaid.config.values import thaw_value
            effective=config_dict(result.diagram) if isinstance(result.diagram,Diagram) else {
                'theme':result.diagram.config.theme,'look':result.diagram.config.look,'layout':result.diagram.config.layout,
                'themeVariables':thaw_value(result.diagram.config.theme_variables)}
            (args.out/(id+'.png')).write_bytes(result.data)
            write(args.out/(id+'.scene.json'),{'width':result.width,'height':result.height,'diagram':result.diagram,
                'layout':result.layout,'measured':result.measured,'annotations':result.annotations,'trace':result.trace,
                'backend':result.backend,'diagnostics':result.diagnostics,'effectiveConfig':effective})
            if case['expect'] in ('syntax_error','error'):row.update(status='FAILED',checks=['expected-error-was-accepted'])
            else:
                errors=check_output(result,case)
                faults=controls(result,case)
                if not all(faults.values()):errors.append('checker-negative-controls-failed')
                row.update(status='FAILED' if errors else 'CHECKS_PASSED',checks=errors,controls=faults,
                           width=result.width,height=result.height,backend=dict(result.backend))
        except MermaidError as exc:
            codes=case.get('expectedErrorCodes',[])
            accepted=case['expect'] in ('syntax_error','error','upstream_defect') and exc.code in codes
            row.update(status='EXPECTED_ERROR' if accepted else 'FAILED',errorCode=exc.code,message=str(exc),span=value_json(exc.span))
        except Exception as exc:
            row.update(status='ERROR',exception=type(exc).__name__,message=str(exc),traceback=traceback.format_exc())
        rows.append(row);write(args.out/(id+'.result.json'),row)
        print(json.dumps({k:row[k] for k in ('id','status')},ensure_ascii=True),flush=True)
        write(args.out/'results.partial.json',{'cases':rows})
    unchanged=candidate==source_identity()
    failed=sum(r['status'] in ('FAILED','ERROR') for r in rows)
    write(args.out/'results.json',{'schema':'py-mermaid-bulk-results/v1','source':candidate,'sourceUnchanged':unchanged,
        'backend':args.backend,'cases':rows,'failed':failed,'functionalStatus':'SOURCE_TESTS_AND_VISUAL_REVIEW_REQUIRED',
        'pixelMetrics':'diagnostic only; raw images never transformed'})
    return 1 if failed or not unchanged else 0


if __name__=='__main__':raise SystemExit(main())

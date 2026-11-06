"""Read-only evidence checks for explicitly declared fixed-source content loss."""
import json
from pathlib import Path
import re


def content_loss_errors(case,directory):
    from PIL import Image,ImageChops
    directory=Path(directory);id=case['id'];source=directory/(id+'.json');png=directory/(id+'.png')
    errors=[];contract=case.get('sourceContent',{})
    if not contract.get('missingText'):errors.append('missing-source-content-loss-contract')
    if not source.is_file() or not png.is_file():return errors+['missing-original-content-loss-evidence']
    data=json.loads(source.read_text('utf-8'))
    norm=lambda text:re.sub(r'\s+','',text)
    visible=norm(''.join(t.get('text') or '' for t in data.get('texts',[])))
    for text in contract.get('missingText',[]):
        if norm(text) in visible:errors.append('original-does-not-confirm-missing:'+text)
    for text in contract.get('presentText',[]):
        if norm(text) not in visible:errors.append('original-does-not-confirm-present:'+text)
    im=Image.open(png).convert('RGBA');rgb=Image.alpha_composite(Image.new('RGBA',im.size,'white'),im).convert('RGB')
    if not ImageChops.difference(rgb,Image.new('RGB',rgb.size,'white')).getbbox():errors.append('original-partial-output-is-blank')
    return errors

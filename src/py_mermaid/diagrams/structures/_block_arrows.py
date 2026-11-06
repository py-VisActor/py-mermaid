"""Source blockArrow.ts direction factories, values only (MIT)."""
_FACTORIES={
    'right|left|up|down':lambda height,midpoint,padding,width:((0,0),(midpoint,0),(width / 2,2 * padding),(width - midpoint,0),(width,0),(width,-height / 3),(width + 2 * padding,-height / 2),(width,(-2 * height) / 3),(width,-height),(width - midpoint,-height),(width / 2,-height - 2 * padding),(midpoint,-height),(0,-height),(0,(-2 * height) / 3),(-2 * padding,-height / 2),(0,-height / 3),),
    'right|left|up':lambda height,midpoint,padding,width:((midpoint,0),(width - midpoint,0),(width,-height / 2),(width - midpoint,-height),(midpoint,-height),(0,-height / 2),),
    'right|left|down':lambda height,midpoint,padding,width:((0,0),(midpoint,-height),(width - midpoint,-height),(width,0),),
    'right|up|down':lambda height,midpoint,padding,width:((0,0),(width,-midpoint),(width,-height + midpoint),(0,-height),),
    'left|up|down':lambda height,midpoint,padding,width:((width,0),(0,-midpoint),(0,-height + midpoint),(width,-height),),
    'right|left':lambda height,midpoint,padding,width:((midpoint,0),(midpoint,-padding),(width - midpoint,-padding),(width - midpoint,0),(width,-height / 2),(width - midpoint,-height),(width - midpoint,-height + padding),(midpoint,-height + padding),(midpoint,-height),(0,-height / 2),),
    'up|down':lambda height,midpoint,padding,width:((width / 2,0),(0,-padding),(midpoint,-padding),(midpoint,-height + padding),(0,-height + padding),(width / 2,-height),(width,-height + padding),(width - midpoint,-height + padding),(width - midpoint,-padding),(width,-padding),),
    'right|up':lambda height,midpoint,padding,width:((0,0),(width,-midpoint),(0,-height),),
    'right|down':lambda height,midpoint,padding,width:((0,0),(width,0),(0,-height),),
    'left|up':lambda height,midpoint,padding,width:((width,0),(0,-midpoint),(width,-height),),
    'left|down':lambda height,midpoint,padding,width:((width,0),(0,0),(width,-height),),
    'right':lambda height,midpoint,padding,width:((midpoint,-padding),(midpoint,-padding),(width - midpoint,-padding),(width - midpoint,0),(width,-height / 2),(width - midpoint,-height),(width - midpoint,-height + padding),(midpoint,-height + padding),(midpoint,-height + padding),),
    'left':lambda height,midpoint,padding,width:((midpoint,0),(midpoint,-padding),(width - midpoint,-padding),(width - midpoint,-height + padding),(midpoint,-height + padding),(midpoint,-height),(0,-height / 2),),
    'up':lambda height,midpoint,padding,width:((midpoint,-padding),(midpoint,-height + padding),(0,-height + padding),(width / 2,-height),(width,-height + padding),(width - midpoint,-height + padding),(width - midpoint,-padding),),
    'down':lambda height,midpoint,padding,width:((width / 2,0),(0,-padding),(midpoint,-padding),(midpoint,-height + padding),(width - midpoint,-height + padding),(width - midpoint,-padding),(width,-padding),),
}

def points(directions,label_width,label_height,padding,total_width=None):
    expanded=set()
    for direction in directions:
        expanded.update(('right','left') if direction=='x' else ('up','down') if direction=='y' else (direction,))
    key='|'.join(d for d in ('right','left','up','down') if d in expanded)
    half=padding/2;height=label_height+4*half;midpoint=height/2;width=total_width if total_width is not None else label_width+2*midpoint+2*half
    factory=_FACTORIES.get(key)
    values=factory(height,midpoint,half,width) if factory else ((0.,0.),)
    left=min(x for x,y in values);top=min(y for x,y in values)
    return tuple((x-left,y-top) for x,y in values),max(x for x,y in values)-left,max(y for x,y in values)-top

"""Source ELK degenerate-side alignment; raw engine frames stay immutable.

Fixed render.ts alignDegenerateNodeToAnchor runs before constructing paint
points. It moves the node onto the routed line rather than bending that line.
"""
from __future__ import annotations
from dataclasses import replace


def align_degenerate_boxes(diagram, routes, boxes, edge_order):
    """Return only source-translated paint boxes, in native edge/anchor order.

    A group is not excluded by the source. Its frame may move, but its
    children and immutable engine coordinate origin must not move with it.
    The only source shape exclusion is rect33. First qualifying anchor wins,
    including a <.01 no-op anchor; exactly24 is not degenerate.
    """
    nodes={node.id:node for node in diagram.nodes}
    by_id={edge.id:edge for edge in diagram.edges}
    routed={route.id:route for route in routes}
    aligned=set();changed={}
    for identifier in edge_order:
        edge=by_id[identifier];route=routed[identifier]
        if not route.sections:continue
        section=route.sections[0]
        for endpoint,anchor in ((edge.source,section.start),(edge.target,section.end)):
            if endpoint in nodes and nodes[endpoint].shape=='rect33':continue
            box=changed.get(endpoint,boxes[endpoint])
            along_width=abs(anchor.y-box.y)<=.5 or abs(anchor.y-box.y-box.height)<=.5
            if (box.width if along_width else box.height)>=24:continue
            if endpoint in aligned:continue
            aligned.add(endpoint)
            delta=anchor.x-(box.x+box.width/2) if along_width else anchor.y-(box.y+box.height/2)
            if abs(delta)<.01:continue
            changed[endpoint]=replace(box,x=box.x+delta) if along_width else replace(box,y=box.y+delta)
    return changed

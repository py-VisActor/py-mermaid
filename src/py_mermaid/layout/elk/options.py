"""Fixed Mermaid ELK public configuration and preset expansion; pure JSON only."""
from __future__ import annotations
from py_mermaid.model.flowchart import MermaidError
DIRECTIONS = {"TD":"DOWN", "TB":"DOWN", "BT":"UP", "LR":"RIGHT", "RL":"LEFT"}
ROOT_ALGORITHMS = frozenset(("elk", "elk.stress", "elk.force", "elk.mrtree", "elk.sporeOverlap", "elk.box", "elk.rectpacking"))
CONTAINER_ALGORITHMS = (ROOT_ALGORITHMS - {"elk"}) | {"elk.layered", "elk.radial"}
PRESETS = {
 "default":("NETWORK_SIMPLEX","BRANDES_KOEPF","BRANDES_KOEPF","BALANCED","DEPTH_FIRST"),
 "legacy":("NETWORK_SIMPLEX","BRANDES_KOEPF","BRANDES_KOEPF","NONE","GREEDY"),
 "modelOrder":("NETWORK_SIMPLEX","NETWORK_SIMPLEX","BRANDES_KOEPF","NONE","GREEDY_MODEL_ORDER"),
 "depthFirst":("NETWORK_SIMPLEX","NETWORK_SIMPLEX","BRANDES_KOEPF","NONE","DEPTH_FIRST")}
DEFAULTS = {"mergeEdges":False,"straightenEdges":True,"lineHops":True,"preset":"default","layeringLayerBound":4,
 "forceNodeModelOrder":False,"considerModelOrder":"NODES_AND_EDGES","keepEntryNodeOnTop":False,"orientFeedbackEdges":True}
RECTPACKING = {"spacing.baseValue":15,"spacing.nodeNode":15,"elk.aspectRatio":"1.6","elk.expandNodes":"true",
 "elk.rectpacking.trybox":"true","elk.rectpacking.packing.compaction.rowHeightReevaluation":"true",
 "elk.rectpacking.packing.compaction.iterations":10,"elk.rectpacking.whiteSpaceElimination.strategy":"EQUAL_BETWEEN_STRUCTURES",
 "elk.rectpacking.widthApproximation.strategy":"SCANLINE"}
CONTAINER_OVERRIDES = {"nodeSize.constraints","nodeSize.minimum","elk.algorithm","elk.aspectRatio","elk.contentAlignment","elk.expandNodes","elk.padding",*RECTPACKING}

def settings(config):
    return dict(DEFAULTS, **dict(config.elk_options))

def algorithm(config):
    if config.layout not in ROOT_ALGORITHMS:
        raise MermaidError("Flowchart requires a supported ELK algorithm",code="UNSUPPORTED_LAYOUT")
    return "elk.layered" if config.layout == "elk" else config.layout

def strategies(config, *, container=False):
    values=settings(config); preset=PRESETS.get(values.get("preset"),PRESETS["default"])
    return {"elk.layered.nodePlacement.strategy":values.get("nodePlacementStrategy") or preset[2 if container else 1],
      "elk.layered.nodePlacement.bk.fixedAlignment":values.get("nodePlacementAlignment") or preset[3],
      "elk.layered.cycleBreaking.strategy":values.get("cycleBreakingStrategy") or preset[4],
      "elk.layered.mergeEdges":values["mergeEdges"],
      **({} if container else {"elk.layered.layering.strategy":values.get("layeringStrategy") or preset[0],
       "elk.layered.layering.coffmanGraham.layerBound":values["layeringLayerBound"],
       "elk.layered.crossingMinimization.forceNodeModelOrder":values["forceNodeModelOrder"],
       "elk.layered.considerModelOrder.strategy":values["considerModelOrder"]})}

def container_algorithm(group, *, warn=False):
    requested=dict(group.metadata).get("algorithm")
    if warn and isinstance(requested,str) and requested not in CONTAINER_ALGORITHMS:
        import warnings
        warnings.warn(f'Unknown container layout algorithm {requested!r}; using the diagram algorithm',RuntimeWarning,stacklevel=2)
    return requested if isinstance(requested,str) and requested in CONTAINER_ALGORITHMS else None

def cyclic_entries(elements, edges):
    """findCyclicEntryNodes: weak components, source-less, greedy edge order."""
    groups={}
    for node in elements:groups.setdefault(node.parent_id,[]).append(node.id)
    entries=set()
    for ids in groups.values():
        inside=set(ids); incoming=dict.fromkeys(ids,0); neighbors={i:[] for i in ids}
        internal=[(e.source,e.target) for e in edges if e.source!=e.target and e.source in inside and e.target in inside]
        for a,b in internal:incoming[b]+=1;neighbors[a].append(b);neighbors[b].append(a)
        components=[];seen=set()
        for identifier in ids:
            if identifier in seen:continue
            todo=[identifier];component=set()
            while todo:
                node=todo.pop()
                if node in component:continue
                component.add(node);todo.extend(neighbors[node])
            components.append(component);seen.update(component)
        forward={i:[] for i in ids};residual=dict.fromkeys(ids,0)
        def reaches(start,target):
            stack=[start];visited=set()
            while stack:
                node=stack.pop()
                if node==target:return True
                if node not in visited:visited.add(node);stack.extend(forward[node])
            return False
        for a,b in internal:
            if not reaches(b,a):forward[a].append(b);residual[b]+=1
        for component in components:
            if not any(incoming[n]==0 for n in component):
                entries.add(next(n for n in ids if n in component and residual[n]==0))
    return entries

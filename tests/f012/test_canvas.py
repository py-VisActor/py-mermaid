"""Source-derived classic-shape and Canvas content tests, never saved B goldens.

Coordinates supplied below are test-only fixtures to isolate drawing. Expected
shape dimensions come from the fixed upstream handlers; expected topology/text
comes from independently specified input. Public a18 Path2D supplies a separate
geometric predicate and PNG pixels prove that trace/model values were drawn.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from io import BytesIO
import math
import unittest

from PIL import Image
from py_skia_canvas import Path2D

from py_mermaid.api import render
from py_mermaid.config import resolve_config
from py_mermaid.geometry.shapes import shape_geometry, shape_outline_intersection
from py_mermaid.model.flowchart import (
    Box, EdgeSection, Flowchart, FlowEdge, FlowGroup, FlowLayout, FlowNode,
    MermaidError, PlacedEdgeLabel, PlacedGroup, PlacedNode, Point, RoutedEdge,
    SourcePosition, SourceSpan,
)
from py_mermaid.rendering.skia import CanvasSession


SHAPES = ("square", "round", "stadium", "subroutine", "cylinder", "circle",
          "doublecircle", "diamond", "hexagon", "odd", "trapezoid",
          "inv_trapezoid", "lean_right", "lean_left")
SPAN = SourceSpan(SourcePosition(0, 0, 1, 0), SourcePosition(1, 1, 1, 1))


def source_dimensions(kind: str, label_width: float, label_height: float) -> tuple[float, float]:
    """Independent fixed-source algebra for effective redux-color/neo defaults."""
    a, b = label_width, label_height
    if kind == "square":
        return a+32, b+24
    if kind == "round":
        return a+30, b+30
    if kind == "circle":
        return (math.hypot(a, b)+32,)*2
    if kind == "doublecircle":
        return (math.hypot(a, b)+56,)*2
    if kind == "stadium":
        height = b+24
        inscribed = height*math.cos(math.pi/98)
        chord = math.sqrt(max(0, inscribed**2-b**2))
        nominal_width = max(a+height/4+40, 2.5*height-inscribed, a+40+height-chord)
        # Both source semicircle extrema fall halfway between sample indices.
        return nominal_width-height+inscribed, height
    if kind == "subroutine":
        return a+44, b+12
    if kind == "cylinder":
        width = a+24
        cap_radius_y = (width/2)/(2.5+width/50)
        return width, b+24+3*cap_radius_y
    if kind == "diamond":
        return (a+b+30,)*2
    if kind == "hexagon":
        height = b+70
        return a+2*height/3.5+32, height
    if kind == "odd":
        height = b+24
        return a+42+height/4, height
    if kind == "inv_trapezoid":
        height = b+30
        return a+60+height, height
    if kind in {"trapezoid", "lean_right", "lean_left"}:
        height = b+15
        return a+30+height, height
    raise AssertionError(f"Unlisted source shape {kind}")


def diagram(nodes=(), edges=(), groups=(), *, colored_background=False):
    config = resolve_config()
    if colored_background:
        # Test-only paint contrast isolates white shape silhouette from outside.
        config = replace(config, background="#ff0000")
    return Flowchart("independent test-only semantic fixture", "TD", tuple(nodes), tuple(edges),
                     config, groups=tuple(groups))


def decode(result):
    image = Image.open(BytesIO(result.data))
    image.load()
    return image.convert("RGB")


def pixels(image, box):
    left, top = max(0, math.floor(box.x)), max(0, math.floor(box.y))
    right = min(image.width, math.ceil(box.x+box.width))
    bottom = min(image.height, math.ceil(box.y+box.height))
    return tuple(image.crop((left, top, right, bottom)).get_flattened_data())


def dark_count(image, box):
    return sum(max(pixel)<130 for pixel in pixels(image,box))


def check_visible_labels(result, kind, expected):
    """Independent negative-control target: exact content AND actual glyph pixels."""
    image = decode(result)
    events = [event for event in result.trace if event.kind == kind]
    actual = {}
    for event in events:
        actual.setdefault(event.semantic_id, "")
        actual[event.semantic_id] += event.text or ""
        if event.text and event.text.strip():
            assert event.box is not None and dark_count(image,event.box)>2, "trace label has no actual dark glyphs"
    assert actual == expected, (actual,expected)


def on_box(point, box, tolerance=1e-4):
    inside = box.x-tolerance <= point.x <= box.x+box.width+tolerance and box.y-tolerance <= point.y <= box.y+box.height+tolerance
    boundary = min(abs(point.x-box.x),abs(point.x-box.x-box.width),abs(point.y-box.y),abs(point.y-box.y-box.height))<=tolerance
    return inside and boundary


class ShapeGeometrySourceTests(unittest.TestCase):
    def test_all_fourteen_source_dimension_formulas(self):
        config = resolve_config()
        for kind in SHAPES:
            for label_width,label_height in ((120,21),(43,63),(0,21)):
                with self.subTest(kind=kind,label=(label_width,label_height)):
                    actual = shape_geometry(kind,label_width,label_height,config)
                    expected = source_dimensions(kind,label_width,label_height)
                    self.assertAlmostEqual(actual.width,expected[0],places=7)
                    self.assertAlmostEqual(actual.height,expected[1],places=7)
                    self.assertTrue(actual.outline)
                    path_bounds = Path2D(actual.outline).bounds
                    self.assertAlmostEqual(path_bounds["left"],0,delta=2e-4)
                    self.assertAlmostEqual(path_bounds["top"],0,delta=2e-4)
                    self.assertAlmostEqual(path_bounds["width"],actual.width,delta=2e-4)
                    self.assertAlmostEqual(path_bounds["height"],actual.height,delta=2e-4)

    def test_label_boxes_fit_true_outlines_not_just_bounding_rects(self):
        config=resolve_config()
        for kind in SHAPES:
            with self.subTest(kind=kind):
                geometry=shape_geometry(kind,120,42,config)
                box=geometry.label_box
                path=Path2D(geometry.outline)
                for x in (box.x,box.x+box.width):
                    for y in (box.y,box.y+box.height):
                        self.assertTrue(path.contains(x,y),f"{kind}: label corner {(x,y)} falls outside actual shape")

    def test_circle_measurement_has_no_rectangular_minimum(self):
        session=CanvasSession("cpu")
        source=diagram([FlowNode("circle","i",SPAN,"circle"),FlowNode("double","i",SPAN,"doublecircle"),FlowNode("rect","i",SPAN)])
        measured=session.measure(source)
        self.assertLess(measured[0].label_width,120)
        self.assertLess(measured[1].label_width,120)
        self.assertEqual(measured[2].label_width,120)
        self.assertAlmostEqual(measured[1].width-measured[0].width,24,places=8)

    def test_source_inner_detail_paths_and_asymmetric_labels(self):
        config=resolve_config()
        for kind,count in (("subroutine",2),("cylinder",1),("doublecircle",1)):
            with self.subTest(kind=kind):
                shape=shape_geometry(kind,120,21,config)
                self.assertEqual(len(shape.details),count)
                for detail in shape.details:
                    bounds=Path2D(detail).bounds
                    self.assertGreater(bounds["width"]+bounds["height"],0)
        cylinder=shape_geometry("cylinder",120,21,config)
        self.assertAlmostEqual(cylinder.label_box.y-(cylinder.height-21)/2,10)
        odd=shape_geometry("odd",120,21,config)
        self.assertAlmostEqual(odd.label_box.x-(odd.width-120)/2,odd.height/8)

    def test_offcenter_ports_stay_orthogonal_and_touch_real_outline(self):
        config=resolve_config()
        for kind in SHAPES:
            geometry=shape_geometry(kind,120,42,config)
            width,height=geometry.width,geometry.height
            box=Box(30,70,width,height)
            path=Path2D(geometry.outline)
            cases=[(Point(box.x+width,box.y+height*.07),Point(box.x+width+30,box.y+height*.07),True,1),
                   (Point(box.x,box.y+height*.83),Point(box.x-30,box.y+height*.83),True,-1),
                   (Point(box.x+width*.07,box.y),Point(box.x+width*.07,box.y-30),False,-1),
                   (Point(box.x+width*.91,box.y+height),Point(box.x+width*.91,box.y+height+30),False,1)]
            for port,toward,horizontal,sign in cases:
                with self.subTest(kind=kind,port=port):
                    actual=shape_outline_intersection(kind,box,port,toward)
                    self.assertAlmostEqual(actual.y if horizontal else actual.x,port.y if horizontal else port.x,places=8)
                    x,y=actual.x-box.x,actual.y-box.y
                    inside=(x-sign*.2,y) if horizontal else (x,y-sign*.2)
                    outside=(x+sign*.2,y) if horizontal else (x,y+sign*.2)
                    self.assertTrue(path.contains(*inside),f"{kind} returned point not entering actual filled silhouette")
                    self.assertFalse(path.contains(*outside),f"{kind} endpoint is still within actual outline")

    def test_ellipse_preserves_upstream_missing_handler_error(self):
        with self.assertRaises(MermaidError) as caught:
            shape_geometry("ellipse",100,21,resolve_config())
        self.assertEqual(caught.exception.code,"UPSTREAM_SHAPE_MISSING")
        session=CanvasSession("cpu")
        with self.assertRaises(MermaidError) as caught:
            session.measure(diagram([FlowNode("A","Missing upstream",SPAN,"ellipse")]))
        self.assertEqual(caught.exception.code,"UPSTREAM_SHAPE_MISSING")
        self.assertIsNotNone(caught.exception.span)


class ClassicShapePixelTests(unittest.TestCase):
    def test_all_fourteen_are_drawn_with_visible_label_and_true_silhouette(self):
        session=CanvasSession("cpu")
        for kind in SHAPES:
            with self.subTest(kind=kind):
                source=diagram([FlowNode("A","Shape",SPAN,kind)],colored_background=True)
                measured=session.measure(source)
                size=measured[0]
                layout=FlowLayout((PlacedNode("A",Box(20,20,size.width,size.height)),),(),size.width+40,size.height+40,"test-only","fixture")
                result=session.render(source,measured,layout)
                image=decode(result)
                box=next(event.box for event in result.trace if event.kind=="node")
                self.assertEqual(image.getpixel((0,0)),(255,0,0))
                self.assertGreater(dark_count(image,Box(box.x+box.width/2-3,box.y-2,6,5)),2,"true top outline not drawn")
                check_visible_labels(result,"text",{"A":"Shape"})
                if kind not in {"square","subroutine"}:
                    x,y=(1,size.height/2) if kind in {"odd","lean_left","inv_trapezoid"} else (1,1)
                    self.assertEqual(image.getpixel((math.floor(box.x+x),math.floor(box.y+y))),(255,0,0),
                                     "nonrectangular outer area was falsely filled as a rectangle")
                self.assertTrue(any(event.kind=="shadow" for event in result.trace))

    def test_circle_and_doublecircle_actual_outer_and_inner_shadows(self):
        """styles.ts circle filter and independent inner/outer SVG compositing."""
        session=CanvasSession("cpu")
        for kind in ("circle","doublecircle"):
            with self.subTest(kind=kind):
                source=diagram([FlowNode("A","Circle",SPAN,kind)])
                measured=session.measure(source);size=measured[0]
                result=session.render(source,measured,FlowLayout((PlacedNode("A",Box(20,20,size.width,size.height)),),(),size.width+40,size.height+40,"test-only","fixture"))
                image=decode(result)
                box=next(event.box for event in result.trace if event.kind=="node")
                outer_pixel=image.getpixel((math.floor(box.x+box.width/2+4),math.floor(box.y+box.height+3)))
                self.assertTrue(all(237<=value<=243 for value in outer_pixel),outer_pixel)
                if kind=="doublecircle":
                    inner_pixel=image.getpixel((math.floor(box.x+box.width/2+4),math.floor(box.y+box.height-12+3)))
                    self.assertTrue(all(237<=value<=243 for value in inner_pixel),inner_pixel)
                    self.assertEqual(len([event for event in result.trace if event.kind=="node-detail-shadow"]),1)
                shadow=next(event.box for event in result.trace if event.kind=="shadow")
                self.assertLessEqual(shadow.x+shadow.width,result.width-8)
                self.assertLessEqual(shadow.y+shadow.height,result.height-8)

    def test_subroutine_doublecircle_and_cylinder_internal_marks_are_pixels(self):
        session=CanvasSession("cpu")
        for kind in ("subroutine","doublecircle","cylinder"):
            source=diagram([FlowNode("A","Detail",SPAN,kind)])
            measured=session.measure(source);size=measured[0]
            result=session.render(source,measured,FlowLayout((PlacedNode("A",Box(10,10,size.width,size.height)),),(),size.width+20,size.height+20,"test-only","fixture"))
            box=next(event.box for event in result.trace if event.kind=="node")
            if kind=="subroutine":
                point=Point(box.x+8,box.y+box.height/2)
            elif kind=="doublecircle":
                point=Point(box.x+box.width/2,box.y+12)
            else:
                width=size.width;ry=(width/2)/(2.5+width/50)
                point=Point(box.x+box.width/2,box.y+2*ry)
            self.assertGreater(dark_count(decode(result),Box(point.x-2,point.y-2,4,4)),1,kind)


class AnnotationAndGroupCanvasTests(unittest.TestCase):
    def test_annotation_measurement_has_role_specific_width_policy(self):
        session=CanvasSession("cpu")
        source=diagram([FlowNode("A","Node",SPAN)],
                       [FlowEdge("e","A","A",SPAN,"edge words "*30)],
                       [FlowGroup("G","Group title "*25,SPAN)])
        annotations=session.measure_annotations(source)
        self.assertGreater(annotations.groups[0].label_width,120)
        self.assertEqual(len(annotations.groups[0].lines),1)
        self.assertGreater(len(annotations.edge_labels[0].lines),1)
        self.assertLessEqual(annotations.edge_labels[0].width,200)
        self.assertEqual("".join(line.text for line in annotations.edge_labels[0].lines),"edge words "*30)
        tiny=session.measure_annotations(diagram([FlowNode("A","Node",SPAN)],
                                                [FlowEdge("e","A","A",SPAN,"i")],
                                                [FlowGroup("G","i",SPAN)]))
        self.assertLess(tiny.groups[0].label_width,120)
        self.assertLess(tiny.edge_labels[0].width,120)

    def test_edge_label_background_masks_route_and_text_is_visible(self):
        source=diagram([FlowNode("A","Start",SPAN),FlowNode("B","Finish",SPAN)],
                       [FlowEdge("e","A","B",SPAN,"yes")])
        session=CanvasSession("cpu");measured=session.measure(source);annotations=session.measure_annotations(source)
        a,b=measured;label=annotations.edge_labels[0]
        center=max(a.width,b.width)/2+20
        start=Point(center,20+a.height);end=Point(center,220)
        label_box=Box(center-label.width/2,140,label.width,label.height)
        layout=FlowLayout((PlacedNode("A",Box(center-a.width/2,20,a.width,a.height)),
                           PlacedNode("B",Box(center-b.width/2,220,b.width,b.height))),
                          (RoutedEdge("e",(EdgeSection(start,(),end),)),),400,350,"test-only","fixture",
                          edge_labels=(PlacedEdgeLabel("e",label_box),))
        result=session.render(source,measured,layout,annotations=annotations)
        image=decode(result)
        check_visible_labels(result,"edge-label",{"e":"yes"})
        bg=next(event.box for event in result.trace if event.kind=="edge-label-background")
        self.assertEqual(image.getpixel((math.floor(bg.x+bg.width/2),math.floor(bg.y+1))),(204,204,204),
                         "line must be occluded behind the real edge-label background")
        order=[event.kind for event in result.trace]
        self.assertGreater(order.index("edge-label-background"),order.index("edge"))
        self.assertGreater(order.index("edge-label"),order.index("edge-label-background"))

    def test_nested_groups_have_palette_actual_pixels_and_visible_titles(self):
        source=diagram([FlowNode("A","Leaf",SPAN,parent_id="inner")],groups=(
            FlowGroup("inner","Inner",SPAN,("A",),"outer",color_index=1),
            FlowGroup("outer","Outer",SPAN,("inner",),color_index=0)))
        session=CanvasSession("cpu");measured=session.measure(source);annotations=session.measure_annotations(source)
        titles={group.id:group for group in annotations.groups}
        outer,inner=Box(20,20,400,260),Box(50,80,300,160)
        layout=FlowLayout((PlacedNode("A",Box(100,140,measured[0].width,measured[0].height)),),(),450,310,"test-only","fixture",
                          groups=(PlacedGroup("inner",inner,"outer",Point(50,80),Box(160,80,titles["inner"].label_width,titles["inner"].label_height)),
                                  PlacedGroup("outer",outer,None,Point(20,20),Box(180,20,titles["outer"].label_width,titles["outer"].label_height))))
        result=session.render(source,measured,layout,annotations=annotations);image=decode(result)
        groups={event.semantic_id:event.box for event in result.trace if event.kind=="group"}
        self.assertEqual([event.semantic_id for event in result.trace if event.kind=="group"],["outer","inner"])
        self.assertEqual(image.getpixel((int(groups["outer"].x+10),int(groups["outer"].y+45))),(253,244,255))
        self.assertEqual(image.getpixel((int(groups["inner"].x+10),int(groups["inner"].y+45))),(240,253,250))
        check_visible_labels(result,"group-title",{"outer":"Outer","inner":"Inner"})
        check_visible_labels(result,"text",{"A":"Leaf"})
        self.assertEqual(len([event for event in result.trace if event.kind=="group-shadow"]),2)

    def test_group_only_diagram_is_actually_drawn(self):
        source=diagram(groups=(FlowGroup("G","Empty group",SPAN),))
        session=CanvasSession("cpu");annotations=session.measure_annotations(source)
        title=annotations.groups[0]
        box=Box(10,10,max(100,title.label_width+16),70)
        placed=PlacedGroup("G",box,None,Point(10,10),Box(box.x+(box.width-title.label_width)/2,box.y,title.label_width,title.label_height))
        result=session.render(source,(),FlowLayout((),(),box.width+20,90,"test-only","fixture",groups=(placed,)),annotations=annotations)
        check_visible_labels(result,"group-title",{"G":"Empty group"})
        self.assertEqual(len([event for event in result.trace if event.kind=="node"]),0)
        self.assertEqual(len([event for event in result.trace if event.kind=="group"]),1)

    def test_real_nested_group_cross_connection_and_edge_label_pixels(self):
        result=render('flowchart TD\nsubgraph outer[Outer]\nsubgraph inner[Inner]\nA((Circle)) -->|yes| B{Decision}\nend\nend\nB --> C[(Store)]',backend="cpu")
        check_visible_labels(result,"text",{"A":"Circle","B":"Decision","C":"Store"})
        check_visible_labels(result,"group-title",{"outer":"Outer","inner":"Inner"})
        check_visible_labels(result,"edge-label",{result.diagram.edges[0].id:"yes"})
        self.assertEqual(len(result.layout.groups),2)
        self.assertEqual(len(result.layout.edge_labels),1)
        image=decode(result)
        for event in result.trace:
            if event.box is not None:
                self.assertGreaterEqual(event.box.x,0)
                self.assertGreaterEqual(event.box.y,0)
                self.assertLessEqual(event.box.x+event.box.width,result.width+1e-4)
                self.assertLessEqual(event.box.y+event.box.height,result.height+1e-4)
        self.assertEqual(image.size,(result.width,result.height))

    def test_annotations_owner_thread_and_repeat_call_isolation(self):
        session=CanvasSession("cpu")
        first=diagram(groups=(FlowGroup("G","First title",SPAN),))
        second=diagram([FlowNode("A","Leaf",SPAN)],[FlowEdge("e","A","A",SPAN,"Second label")])
        self.assertEqual(len(session.measure_annotations(first).groups),1)
        second_measure=session.measure_annotations(second)
        self.assertEqual(second_measure.groups,())
        self.assertEqual("".join(line.text for line in second_measure.edge_labels[0].lines),"Second label")
        with ThreadPoolExecutor(max_workers=1) as pool:
            future=pool.submit(session.measure_annotations,first)
            with self.assertRaises(MermaidError) as caught:future.result()
        self.assertEqual(caught.exception.code,"THREAD_OWNERSHIP")

    def test_missing_annotations_are_an_error_not_silent_content_loss(self):
        source=diagram(groups=(FlowGroup("G","Required title",SPAN),))
        session=CanvasSession("cpu")
        with self.assertRaises(MermaidError) as caught:
            session.render(source,(),FlowLayout((),(),100,100,"test-only","fixture"))
        self.assertEqual(caught.exception.code,"INVALID_LAYOUT")


class PixelContentNegativeControls(unittest.TestCase):
    def test_blank_png_cannot_pass_unchanged_trace(self):
        result=render('flowchart TD\nA[Visible]',backend="cpu")
        blank=Image.new("RGB",(result.width,result.height),"white")
        stream=BytesIO();blank.save(stream,format="PNG")
        with self.assertRaises(AssertionError):
            check_visible_labels(replace(result,data=stream.getvalue()),"text",{"A":"Visible"})

    def test_missing_text_trace_cannot_pass_a_plausible_png(self):
        result=render('flowchart TD\nA[Visible]',backend="cpu")
        with self.assertRaises(AssertionError):
            check_visible_labels(replace(result,trace=tuple(event for event in result.trace if event.kind!="text")),"text",{"A":"Visible"})


if __name__=="__main__":
    unittest.main()

"""Source clear/reset, input safety, syntax locations and semantic error classes."""
import copy
import unittest
from dataclasses import FrozenInstanceError
from py_mermaid.runtime.registry import parse_diagram
from py_mermaid.model.flowchart import MermaidError
from .support import plain


class SourceStateAndErrors(unittest.TestCase):
    def test_class_parse_calls_do_not_accumulate_members_or_notes(self):
        text='classDiagram\nclass A {\n+field\n}\nnote for A "Remember"';first=parse_diagram(text);snapshot=plain(first.model);other=parse_diagram('classDiagram\nclass B');last=parse_diagram(text)
        self.assertEqual(plain(first.model),snapshot);self.assertEqual(plain(last.model),snapshot);self.assertEqual([n.id for n in other.model.classes],['B'])
    def test_state_direction_does_not_leak(self):
        a=parse_diagram('stateDiagram-v2\ndirection LR\nA --> B');b=parse_diagram('stateDiagram-v2\nC --> D')
        self.assertEqual(a.model.direction,'LR');self.assertEqual(b.model.direction,'TB');self.assertEqual([n.id for n in b.model.states],['C','D'])
    def test_er_attribute_lists_are_request_local(self):
        a=parse_diagram('erDiagram\nA {\nint id PK\n}');b=parse_diagram('erDiagram\nA')
        self.assertEqual(len(a.model.entities[0].attributes),1);self.assertEqual(len(b.model.entities[0].attributes),0)
    def test_packet_words_reset_between_calls(self):
        a=parse_diagram('packet\n0-63: "Long"');b=parse_diagram('packet\n0: "Bit"')
        self.assertEqual(len(a.model.words),2);self.assertEqual(len(b.model.words),1);self.assertEqual(b.model.words[0][0].end,0)
    def test_kanban_sections_do_not_accumulate(self):
        a=parse_diagram('kanban\nTodo\n  A');b=parse_diagram('kanban\nDone\n  B')
        self.assertEqual(a.model.sections,('Todo',));self.assertEqual(b.model.sections,('Done',));self.assertEqual(b.model.nodes[1].parent,'Done')
    def test_architecture_failure_does_not_publish_partial_next_model(self):
        with self.assertRaises(MermaidError):parse_diagram('architecture-beta\nservice a\na:R -- L:missing')
        b=parse_diagram('architecture-beta\nservice b');self.assertEqual([n.id for n in b.model.nodes],['b']);self.assertEqual(len(b.model.edges),0)
    def test_config_input_is_not_mutated_by_mindmap_layout_default(self):
        config={'mindmap':{'colorBy':'depth'},'themeVariables':{'primaryColor':'#abcdef'}};snapshot=copy.deepcopy(config);parse_diagram('mindmap\nroot\n  Child',config=config)
        self.assertEqual(config,snapshot);self.assertNotIn('layout',config)
    def test_semantic_packet_error_maps_crlf_unicode_raw_utf16(self):
        text='---\r\ntitle: "\u4f8b\U0001f642"\r\n---\r\npacket\r\n0: "First"\r\n2: "Gap"'
        with self.assertRaises(MermaidError) as caught:parse_diagram(text)
        error=caught.exception;index=text.index('2: "Gap"');self.assertEqual(error.code,'INVALID_PACKET_RANGE');self.assertEqual(error.span.start.index,index);self.assertEqual(error.span.start.utf16_offset,len(text[:index].encode('utf-16-le'))//2);self.assertEqual(error.span.start.line,6);self.assertEqual(error.span.start.column,0)
    def test_usecase_semantic_failure_does_not_leak_actor(self):
        with self.assertRaises(MermaidError):parse_diagram('usecase-beta\nactor User\nUser ..> : include Login')
        fresh=parse_diagram('usecase-beta\nFresh');self.assertEqual([n.id for n in fresh.model.nodes],['Fresh']);self.assertEqual(len(fresh.model.edges),0)
    def test_block_generated_spacers_have_no_global_counter(self):
        text='block\ncolumns 3\nA space:2 B';a=parse_diagram(text);b=parse_diagram(text)
        self.assertEqual(plain(a.model),plain(b.model));self.assertEqual(len([n for n in a.model.nodes if n.shape=='space']),2)
    def test_model_is_immutable_pure_public_contract(self):
        diagram=parse_diagram('classDiagram\nclass A')
        with self.assertRaises(FrozenInstanceError):diagram.model.classes[0].label='Mutated'
        self.assertEqual(diagram.model.classes[0].label,'A')

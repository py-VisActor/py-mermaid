"""Independent fault controls for source/native predicate reporting."""
from copy import deepcopy
import unittest
from probe_c import errors_for


class CProbeFaultControls(unittest.TestCase):
    def test_endpoint_shift_is_detected_without_requiring_absolute_engine_coordinates(self):
        p=dict(type='endpoint',sender='A',receiver='B',startOffset=1,endOffset=-4)
        projection=dict(actors={'A':200,'B':400},messages=[dict(start=(201,30),end=(396,30))])
        self.assertEqual(errors_for(p,projection),[])
        moved=deepcopy(projection);moved['messages'][0]['end']=(400,30)
        self.assertEqual(errors_for(p,moved),['end-offset'])

    def test_wrong_number_actor_and_missing_central_circle_are_not_accepted(self):
        self.assertEqual(errors_for(dict(type='number',anchor='A'),dict(actors={'A':10},numbers=[(10,'1')])),[])
        self.assertTrue(errors_for(dict(type='number',anchor='A'),dict(actors={'A':10},numbers=[(20,'1')])))
        self.assertTrue(errors_for(dict(type='central',circles=[dict(actor='A',offset=0)]),dict(actors={'A':10},circles=[])))

    def test_plain_text_cannot_substitute_for_source_marked_bold_and_italic(self):
        p=dict(type='comment',visible='Both',bold=True,italic=True)
        plain=dict(comments=[dict(text='Both',font_weight='400',font_style='normal')])
        self.assertEqual(set(errors_for(p,plain)),{'comment-bold-token','comment-italic-token'})

    def test_first_activation_correction_cannot_be_lost(self):
        p=dict(type='activation',sender='A',receiver='B',startOffset=1,endOffset=-8)
        actual=dict(actors={'A':100,'B':300},messages=[dict(start=(101,50),end=(292,50))])
        self.assertEqual(errors_for(p,actual),[])
        actual['messages'][0]['end']=(296,50)
        self.assertEqual(errors_for(p,actual),['end-offset'])

    def test_gallery_missing_marker_wrong_kind_and_missing_message_rejected(self):
        p=dict(type='arrows',expected=[dict(start='',end='arrowhead',dashed=False) for _ in range(26)])
        projection=dict(messages=[dict(dash=[]) for _ in range(26)],
                        arrowComponents={'message-'+str(i):[dict(kind='marker',marker='point')] for i in range(26)})
        self.assertEqual(errors_for(p,projection),[])
        missing=deepcopy(projection);missing['arrowComponents']['message-3']=[]
        self.assertIn('arrow-3-component-count',errors_for(p,missing))
        wrong=deepcopy(projection);wrong['arrowComponents']['message-7'][0]['marker']='cross'
        self.assertIn('arrow-7-kind-multiplicity',errors_for(p,wrong))
        short=deepcopy(projection);short['messages'].pop()
        self.assertEqual(errors_for(p,short),['all-26-message-count'])
        # Two wanted point markers require two real point components, not one
        # point plus a foreign cross satisfying two identical any() queries.
        p['expected'][0]['start']='arrowhead'
        projection['arrowComponents']['message-0'].append(dict(kind='marker',marker='cross'))
        self.assertIn('arrow-0-kind-multiplicity',errors_for(p,projection))
        # The public painter emits two actual line paints for one cross.
        p['expected'][0]['start']='';projection['arrowComponents']['message-0']=[dict(kind='marker',marker='point')]
        p['expected'][6]['end']='crosshead'
        diagonals=[dict(kind='marker',marker='cross',path='M8 18L12 22'),
                   dict(kind='marker',marker='cross',path='M8 22L12 18')]
        projection['arrowComponents']['message-6']=diagonals
        self.assertEqual(errors_for(p,projection),[])
        for faulty in (diagonals[:1],[diagonals[0],diagonals[0]],
                       [diagonals[0],dict(kind='marker',marker='cross',path='M18 22L22 18')]):
            altered=deepcopy(projection);altered['arrowComponents']['message-6']=faulty
            self.assertTrue(errors_for(p,altered),'Incomplete/repeated/disconnected cross accepted')

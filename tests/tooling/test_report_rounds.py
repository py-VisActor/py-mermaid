"""Report presentation must never lose cases, mutate status or alter image bytes."""
import base64
import copy
from collections import Counter
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
from build_report_rounds import build, embedded_counts
from run_support import file_identity, write_json


class ReportRoundsTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.rows=[{'id':'A-first','kind':'classDiagram','status':'CHECKS_PASSED','native':{'cpu':{}}},
                   {'id':'B-failure','kind':'gantt','status':'REVIEW_FAILURE','native':{'cpu':{}}},
                   {'id':'gap-new','kind':'sequence','status':'EXCLUDED','native':{'cpu':{}}}]
        artifacts={};cards=[]
        for row in self.rows:
            raw=('raw-image-'+row['id']).encode();image=self.root/(row['id']+'.png');image.write_bytes(raw)
            artifacts[str(image)]=file_identity(image)
            cards.append(f'<article class="case" data-status="{row["status"]}" data-search="{row["id"].lower()} {row["kind"].lower()}"><h2>{row["id"]} <small>{row["kind"]}</small></h2><section class="image"><h3>A · 官方</h3><img src="data:image/png;base64,{base64.b64encode(raw).decode()}"></section><section class="image"><h3>B · Python cpu</h3></section></article>')
        self.html=self.root/'original.html';self.html.write_text('<html>'+''.join(cards)+'</html>',encoding='utf8')
        self.meta=self.root/'original.json'
        write_json(self.meta,{'report':file_identity(self.html),'cases':self.rows,'rawEmbeddedArtifacts':artifacts,'sourceTreeSha256':'original-candidate','functionalStatus':'SOURCE_TESTS_AND_VISUAL_REVIEW_REQUIRED','counts':{'CHECKS_PASSED':1,'REVIEW_FAILURE':1,'EXCLUDED':1}})
        self.spec={'schema':'py-mermaid-report-rounds-spec/v1','title':'Round <test>',
            'sourceReport':{'html':{'path':'original.html',**file_identity(self.html)},'metadata':{'path':'original.json',**file_identity(self.meta)}},
            'rounds':[{'id':'first','title':'First','caseIds':['A-first','B-failure']},{'id':'next','title':'Next','caseIds':['gap-new']}],
            'scopeNote':'No new acceptance <script>alert(1)</script>'}
        self.out=self.root/'out'

    def test_partition_preserves_all_cases_statuses_and_exact_images(self):
        before=self.html.read_bytes();result=build(self.spec,self.out,base=self.root,page_size=1)
        self.assertEqual(self.html.read_bytes(),before)
        self.assertEqual(result['functionalStatus'],'NOT_EVALUATED')
        self.assertEqual(result['sourceTreeSha256'],'original-candidate')
        self.assertEqual([p['caseIds'] for p in result['pages']],[['A-first'],['B-failure'],['gap-new']])
        self.assertEqual({k:v for p in result['pages'] for k,v in p['caseStatuses'].items()},{r['id']:r['status'] for r in self.rows})
        counts=sum((embedded_counts((self.out/p['path']).read_text('utf8')) for p in result['pages']),start=Counter())
        self.assertEqual(counts,embedded_counts(before.decode()))
        self.assertEqual(result['rawPNGVerified'],3)
        self.assertNotIn('<article ',(self.out/'index.html').read_text('utf8'))
        self.assertNotIn('<script>alert(1)',(self.out/'index.html').read_text('utf8'))

    def test_omitted_case_is_rejected_before_output(self):
        self.spec['rounds'][0]['caseIds'].pop()
        with self.assertRaisesRegex(ValueError,'omits'):build(self.spec,self.out,base=self.root)
        self.assertFalse(self.out.exists())

    def test_case_cannot_be_duplicated_across_rounds(self):
        self.spec['rounds'][1]['caseIds'].append('A-first')
        with self.assertRaisesRegex(ValueError,'membership'):build(self.spec,self.out,base=self.root)

    def test_unknown_case_or_round_path_escape_is_rejected(self):
        for key,value in [('caseIds',['unknown']),('id','../escape')]:
            spec=copy.deepcopy(self.spec);spec['rounds'][0][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):build(spec,self.out,base=self.root)

    def test_tampered_input_fingerprint_is_rejected(self):
        self.html.write_bytes(self.html.read_bytes()+b'changed')
        with self.assertRaisesRegex(ValueError,'fingerprint'):build(self.spec,self.out,base=self.root)

    def test_valid_html_hash_cannot_hide_changed_embedded_image(self):
        data=json.loads(self.meta.read_text('utf8'));first=next(iter(data['rawEmbeddedArtifacts'].values()));first['sha256']='0'*64
        write_json(self.meta,data);self.spec['sourceReport']['metadata'].update(file_identity(self.meta))
        with self.assertRaisesRegex(ValueError,'image bytes'):build(self.spec,self.out,base=self.root)

    def test_failed_case_cannot_be_displayed_as_passed(self):
        self.html.write_text(self.html.read_text('utf8').replace('data-status="REVIEW_FAILURE"','data-status="CHECKS_PASSED"'),encoding='utf8')
        data=json.loads(self.meta.read_text('utf8'));data['report']=file_identity(self.html);write_json(self.meta,data)
        self.spec['sourceReport']['html'].update(file_identity(self.html));self.spec['sourceReport']['metadata'].update(file_identity(self.meta))
        with self.assertRaisesRegex(ValueError,'HTML status'):build(self.spec,self.out,base=self.root)

    def test_page_size_and_existing_output_rejected(self):
        for size in [0,25,True]:
            with self.subTest(size=size),self.assertRaises(ValueError):build(self.spec,self.out,base=self.root,page_size=size)
        self.out.mkdir()
        with self.assertRaises(FileExistsError):build(self.spec,self.out,base=self.root)

    def test_case_files_allow_reuse_without_id_prefix_guessing(self):
        write_json(self.root/'fixtures.json',{'cases':[{'id':'A-first'},{'id':'B-failure'}]})
        group=self.spec['rounds'][0];group.pop('caseIds');group['caseFiles']=['fixtures.json']
        result=build(self.spec,self.out,base=self.root,page_size=2)
        self.assertEqual(result['rounds'][0]['caseCount'],2)


if __name__=='__main__':unittest.main()

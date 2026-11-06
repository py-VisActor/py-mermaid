"""Native public CLI/offline contracts; execution is deferred until P3."""
from contextlib import redirect_stderr,redirect_stdout
from io import StringIO
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from py_mermaid.cli import main


class CLIContracts(unittest.TestCase):
    def test_input_file_is_not_overwritten_by_either_output(self):
        with tempfile.TemporaryDirectory() as directory:
            file=Path(directory)/'source.mmd';file.write_text('info',encoding='utf-8')
            for flag in ('--output','--metadata'):
                stderr=StringIO()
                with self.subTest(flag=flag),redirect_stderr(stderr):code=main([str(file),flag,str(file),'--backend','cpu'])
                self.assertEqual(code,2);self.assertEqual(file.read_text('utf-8'),'info')
                self.assertEqual(json.loads(stderr.getvalue())['code'],'CLI_INPUT_ERROR')

    def test_real_stdin_and_metadata_explicit_output_with_unicode_path(self):
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/'静态.svg';metadata=Path(directory)/'result.json'
            with patch('sys.stdin',StringIO('info')):
                code=main(['-','-o',str(output),'--metadata',str(metadata),'--backend','cpu'])
            self.assertEqual(code,0);self.assertIn(b'<svg',output.read_bytes())
            data=json.loads(metadata.read_text('utf-8'))
            self.assertEqual(data['mime'],'image/svg+xml');self.assertEqual(data['backend']['renderer'],'CPU')
            self.assertGreater(data['width'],1);self.assertGreater(data['height'],1)

    def test_invalid_config_and_resource_manifest_are_json_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            bad=Path(directory)/'bad.json';bad.write_text('[]',encoding='utf-8')
            for flag in ('--config','--resources'):
                stderr=StringIO()
                with self.subTest(flag=flag),patch('sys.stdin',StringIO('info')),redirect_stderr(stderr):
                    code=main(['-',flag,str(bad),'-o',str(Path(directory)/'ignored.png')])
                self.assertEqual(code,2);self.assertEqual(json.loads(stderr.getvalue())['code'],'CLI_INPUT_ERROR')

    def test_parser_failure_preserves_precise_json_diagnostic(self):
        stderr=StringIO()
        with patch('sys.stdin',StringIO('not-a-diagram')),redirect_stderr(stderr):code=main(['-'])
        self.assertEqual(code,1);data=json.loads(stderr.getvalue())
        self.assertEqual(data['code'],'UNKNOWN_DIAGRAM');self.assertEqual(data['span']['start']['line'],1)

    def test_production_runs_without_node_browser_or_local_source_on_path(self):
        root=Path(__file__).resolve().parents[3]
        with tempfile.TemporaryDirectory() as directory:
            script=Path(directory)/'offline.py'
            script.write_text('''import importlib.abc,sys,socket,os\nclass Block(importlib.abc.MetaPathFinder):\n def find_spec(self,fullname,path=None,target=None):\n  if fullname.split('.')[0] in {'playwright','selenium','js2py','quickjs'}:raise ImportError('blocked development dependency')\nsys.meta_path.insert(0,Block())\ndef denied(*a,**kw):raise AssertionError('unexpected network access')\nsocket.create_connection=denied\nblocked=os.path.normcase(os.path.abspath(sys.argv[1]))\ndef audit(event,args):\n if event=='open' and isinstance(args[0],(str,bytes,os.PathLike)):\n  target=os.path.normcase(os.path.abspath(os.fsdecode(args[0])))\n  if target==blocked or target.startswith(blocked+os.sep):raise AssertionError('unexpected development-source dependency')\n if event=='subprocess.Popen':raise AssertionError('unexpected external renderer')\nsys.addaudithook(audit)\nfrom py_mermaid import render\nr=render('info',backend='cpu')\nassert r.data.startswith(b'\\x89PNG')\nassert r.width>1 and r.height>1\nprint(dict(r.backend)['renderer'])\n''',encoding='utf-8')
            env=os.environ.copy();env.update(PATH=str(Path(sys.executable).parent),PYTHONPATH=str(root/'src'),PYTHONUTF8='1')
            process=subprocess.run([sys.executable,str(script),str(root/'.local')],cwd=directory,env=env,capture_output=True,text=True,timeout=120)
            self.assertEqual(process.returncode,0,process.stderr);self.assertEqual(process.stdout.strip(),'CPU')


if __name__=='__main__':unittest.main()

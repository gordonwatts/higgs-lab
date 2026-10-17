"""Workshop bootstrap rehearsal against an in-memory GitHub interface."""
import json
import base64
import pytest
from higgslab import instructor

class GitHubFixture:
    def __init__(self):
        self.variables={}
        self.secret=False
        self.secret_writes=0
        self.issue=None
        self.calls=[]

    def __call__(self,args,*,input_text=None):
        self.calls.append(args)
        if args[:2]==['auth','status']: return ''
        if args[:2]==['api','repos/example/workshop']:
            return json.dumps({'full_name':'example/workshop','default_branch':'main','permissions':{'admin':True},'template_repository':{'full_name':'gordonwatts/higgs-lab'}})
        if args[:2]==['issue','list']:
            return json.dumps([{'number':27,'title':instructor.ISSUE_TITLE,'state':'OPEN'}] if self.issue else [])
        if args[:2]==['issue','create']:
            self.issue=27; return 'https://github.com/example/workshop/issues/27'
        if args[:2]==['secret','list']: return '[{"name":"SEALED_SEED"}]' if self.secret else '[]'
        if args[:2]==['secret','set']:
            assert input_text and len(input_text)>=32
            self.secret=True; self.secret_writes+=1; return ''
        if args[:2]==['variable','set']:
            self.variables[args[2]]=args[args.index('--body')+1]; return ''
        if args[:2]==['variable','list']: return json.dumps([{'name':k,'value':v} for k,v in self.variables.items()])
        if args[:2]==['issue','close']: return ''
        if args[:2]==['workflow','run']: return ''
        raise AssertionError(f'unhandled fixture call {args}')

def config(tmp_path,open=False):
    path=tmp_path/'workshop.toml'
    path.write_text('[workshop]\nname="Fixture event"\nevent_title="Fixture title"\ntemplate_repository="gordonwatts/higgs-lab"\nsubmissions_open='+str(open).lower()+'\n')
    return path

def test_init_is_idempotent_and_doctor_uses_new_repo(tmp_path,monkeypatch,capsys):
    fake=GitHubFixture(); monkeypatch.setattr(instructor,'_gh',fake)
    path=config(tmp_path)
    first=instructor.init('example/workshop',path)
    second=instructor.init('example/workshop',path)
    assert first['issue']==second['issue']==27
    assert fake.secret_writes==1
    assert fake.variables['WORKSHOP_CONFIGURED']=='true'
    assert fake.variables['WORKSHOP_ENABLED']=='false'
    assert instructor.doctor('example/workshop',path)['ok'] is True
    assert capsys.readouterr().out==''

def test_no_remote_changes_before_failed_isolation_gate(tmp_path,monkeypatch):
    fake=GitHubFixture(); monkeypatch.setattr(instructor,'_gh',fake)
    with pytest.raises(instructor.InstructorError,match='report'):
        instructor.init('example/workshop',config(tmp_path,True))
    assert fake.calls==[]

def test_reset_preserves_secret_unless_explicit_replace(tmp_path,monkeypatch):
    fake=GitHubFixture(); fake.secret=True; monkeypatch.setattr(instructor,'_gh',fake)
    path=config(tmp_path)
    instructor.reset('example/workshop',suite='preserve',config_path=path)
    assert fake.secret_writes==0
    instructor.reset('example/workshop',suite='replace',config_path=path)
    assert fake.secret_writes==1
    assert fake.variables['SUBMISSIONS_OPEN']=='false'

def test_mirror_mode_requires_explicit_allow_and_matching_marker(tmp_path,monkeypatch):
    path=config(tmp_path)
    text=path.read_text()+"source_mode=\"mirror\"\nmirror_import_allowed=true\nmirror_source_repository=\"gordonwatts/higgs-lab\"\n"
    path.write_text(text)
    marker={"schema_version":1,"source_repository":"gordonwatts/higgs-lab","template_marker":"higgslab-workshop-template-v1"}
    encoded=base64.b64encode(json.dumps(marker).encode()).decode()
    monkeypatch.setattr(instructor,"_gh",lambda args,**kwargs:json.dumps({"content":encoded}) if args[:2]==["api","repos/example/workshop/contents/.higgslab-template.json"] else "")
    mirror_config={"source_mode":"mirror","mirror_import_allowed":True,"mirror_source_repository":"gordonwatts/higgs-lab"}
    instructor._check_template_origin({"full_name":"example/workshop","fork":False,"template_repository":None},mirror_config)
    with pytest.raises(instructor.InstructorError,match="explicitly"):
        instructor._check_template_origin({"full_name":"example/workshop","fork":False},
                                           {"source_mode":"mirror","mirror_import_allowed":False})

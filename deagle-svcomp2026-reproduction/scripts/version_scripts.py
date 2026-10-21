"""Version only this reproduction's generated scripts, never the user's preexisting files."""
import pathlib,subprocess,json,hashlib,time
R=pathlib.Path(__file__).resolve().parents[1];S=R/'scripts'
def run(*args):return subprocess.check_output(['git','-C',str(S),*args],stderr=subprocess.STDOUT,text=True).strip()
if not (S/'.git').exists():
 run('init');run('config','user.name','Deagle reproduction record');run('config','user.email','reproduction@local.invalid')
(S/'.gitignore').write_text('__pycache__/\n*.pyc\n')
run('add','--all')
if subprocess.run(['git','-C',str(S),'diff','--cached','--quiet']).returncode:run('commit','-m','Record SV-COMP 2026 reproduction and evidence-analysis scripts')
files={str(p.relative_to(S)):hashlib.sha256(p.read_bytes()).hexdigest() for p in S.rglob('*') if p.is_file() and '.git' not in p.parts and '__pycache__' not in p.parts and p.suffix!='.pyc'}
out={'commit':run('rev-parse','HEAD'),'status':run('status','--porcelain'),'recorded_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'scope':'Local generated reproduction scripts only; separate from official Deagle source/binary versions.','files_sha256':files}
assert out['status']=='',out['status'];(R/'reports/script-version.json').write_text(json.dumps(out,indent=2));print('SCRIPT COMMIT',out['commit'])

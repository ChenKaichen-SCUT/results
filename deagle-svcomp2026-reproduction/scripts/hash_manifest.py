import pathlib,hashlib,json,os
R=pathlib.Path(__file__).resolve().parents[1];lines=[];symlinks=[]
# Hash exactly the evidence/report/script package roots, and the static package as one artifact.
for base in ['runs','diagnostics','reports','scripts','evidence','archives/official-results','archives/validation-evidence','archives/competition-inputs']:
 for p in sorted((R/base).rglob('*')):
  if '.git' in p.parts or '__pycache__' in p.parts:continue
  if p.is_symlink():symlinks.append({'path':str(p.relative_to(R)),'target':os.readlink(p)});continue
  if not p.is_file():continue
  if p.name in ['SHA256SUMS','symlinks.json']:continue
  h=hashlib.sha256()
  with p.open('rb') as f:
   while b:=f.read(1024*1024):h.update(b)
  lines.append(h.hexdigest()+'  '+str(p.relative_to(R)))
(R/'reports/SHA256SUMS').write_text('\n'.join(lines)+'\n');(R/'reports/symlinks.json').write_text(json.dumps(symlinks,indent=2));print('HASHED',len(lines),'SYMLINKS',len(symlinks))

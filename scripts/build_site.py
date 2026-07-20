from pathlib import Path
import json
R=Path(__file__).resolve().parents[1]
p=json.loads((R/'products.json').read_text(encoding='utf-8'))
required={'id','name','description','category','price','rating','image','link','active','order'}
for i,x in enumerate(p,1):
 missing=required-set(x)
 if missing: raise SystemExit(f'Produto {i} sem campos: {sorted(missing)}')
print(f'Catálogo validado: {len(p)} produtos.')

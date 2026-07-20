import json
from pathlib import Path
p=json.loads((Path(__file__).parents[1]/'products.json').read_text(encoding='utf-8'))
assert len(p)==27
print('Catálogo validado com 27 produtos.')

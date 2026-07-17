from pathlib import Path
import json,re,html as H
R=Path(__file__).resolve().parents[1];ps=sorted((p for p in json.loads((R/'products.json').read_text(encoding='utf-8')) if p.get('active',True)),key=lambda p:p.get('order',999))
def e(v):return H.escape(str(v or ''),quote=True)
def brl(v):return f"R$ {float(v):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
def card(p):
 price=float(p.get('price') or 0);old=float(p.get('oldPrice') or 0);d=round((1-price/old)*100) if old>price>0 else 0;ds=f'<span class="discount">-{d}%</span>' if d else '';oh=f'<span class="old-price">{brl(old)}</span>' if old>price else '<span class="old-price"></span>'
 return f"""<article class="product-card" data-name="{e(p['name']).lower()}" data-cat="{e(p['category'])}" data-id="{p['id']}"><div class="product-image"><img src="{e(p['image'])}" alt="{e(p['name'])}" loading="lazy"><span class="badge">{e(p.get('badge','Destaque'))}</span>{ds}<button class="heart" type="button" data-fav="{p['id']}">♡</button></div><div class="product-info"><div class="row"><span class="category">{e(p['category'])}</span><span class="rating">★ {float(p.get('rating') or 0):.1f}</span></div><h3>{e(p['name'])}</h3><p class="description">{e(p.get('description',''))}</p><div class="price-line"><div>{oh}<strong>{brl(price)}</strong></div><span class="installment">Compra segura</span></div><a class="buy" href="{e(p['link'])}" target="_blank" rel="nofollow sponsored noopener">Ver produto <span>↗</span></a></div></article>"""
block='\n'.join(card(x) for x in ps)
for tpl,out in [('template.html','index.html'),('produtos-template.html','produtos.html')]:
 t=(R/tpl).read_text(encoding='utf-8');(R/out).write_text(re.sub(r'<!-- PRODUCTS_START -->.*?<!-- PRODUCTS_END -->','<!-- PRODUCTS_START -->\n'+block+'\n<!-- PRODUCTS_END -->',t,flags=re.S),encoding='utf-8')
print('Atualizado:',len(ps))

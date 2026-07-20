#!/usr/bin/env python3
"""Importador manual e de baixo volume para páginas públicas da Shopee.

Não contorna login, CAPTCHA, bloqueios ou proteções anti-bot.
Atualiza products.json e baixa a imagem principal quando os metadados
públicos estiverem disponíveis.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import httpx
from playwright.async_api import async_playwright

ID_RE = re.compile(r"-i\.(\d+)\.(\d+)(?:\?|$)")
MONEY_RE = re.compile(r"R\$\s*([\d.]+,\d{2})")


def brl_to_float(value: str) -> float:
    return float(value.replace(".", "").replace(",", "."))


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_text).strip("-").lower()
    return slug[:75] or "produto"


def validate_url(url: str) -> tuple[str, str]:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or parsed.netloc not in {
        "shopee.com.br",
        "www.shopee.com.br",
    }:
        raise ValueError("Use um link público de produto em shopee.com.br.")
    match = ID_RE.search(url)
    if not match:
        raise ValueError("Não encontrei shopId e itemId no final do link.")
    return match.group(1), match.group(2)


async def first_text(page, selectors: list[str]) -> str:
    for selector in selectors:
        locator = page.locator(selector).first
        try:
            if await locator.count():
                text = (await locator.inner_text(timeout=1500)).strip()
                if text:
                    return text
        except Exception:
            pass
    return ""


async def meta(page, selector: str) -> str:
    locator = page.locator(selector).first
    try:
        return (await locator.get_attribute("content", timeout=1500) or "").strip()
    except Exception:
        return ""


async def parse_json_ld(page) -> list[dict]:
    output: list[dict] = []
    scripts = page.locator('script[type="application/ld+json"]')
    for i in range(await scripts.count()):
        try:
            raw = await scripts.nth(i).text_content()
            data = json.loads(raw or "null")
            if isinstance(data, dict):
                output.append(data)
            elif isinstance(data, list):
                output.extend(x for x in data if isinstance(x, dict))
        except Exception:
            continue
    return output


async def collect(url: str, headed: bool) -> dict:
    shop_id, item_id = validate_url(url)
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=not headed)
        context = await browser.new_context(
            locale="pt-BR",
            viewport={"width": 1440, "height": 1000},
        )
        page = await context.new_page()
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(5000)

        title = await first_text(page, ["h1", '[data-testid="pdp-product-name"]'])
        if not title:
            title = await meta(page, 'meta[property="og:title"]')
        description = await meta(page, 'meta[name="description"]')
        if not description:
            description = await meta(page, 'meta[property="og:description"]')
        image_url = await meta(page, 'meta[property="og:image"]')

        current = None
        old = None
        rating = None
        json_ld = await parse_json_ld(page)
        for obj in json_ld:
            candidates = [obj]
            graph = obj.get("@graph")
            if isinstance(graph, list):
                candidates.extend(x for x in graph if isinstance(x, dict))
            for candidate in candidates:
                candidate_type = candidate.get("@type")
                is_product = candidate_type == "Product" or (isinstance(candidate_type, list) and "Product" in candidate_type)
                if not is_product:
                    continue
                title = title or str(candidate.get("name") or "")
                description = description or str(candidate.get("description") or "")
                image = candidate.get("image")
                if not image_url:
                    image_url = image[0] if isinstance(image, list) and image else str(image or "")
                offers = candidate.get("offers") or {}
                if isinstance(offers, list) and offers:
                    offers = offers[0]
                if isinstance(offers, dict):
                    raw_price = offers.get("lowPrice") or offers.get("price")
                    if raw_price is not None:
                        try:
                            current = float(raw_price)
                        except (TypeError, ValueError):
                            pass
                aggregate = candidate.get("aggregateRating") or {}
                if isinstance(aggregate, dict):
                    try:
                        rating = float(aggregate.get("ratingValue"))
                    except (TypeError, ValueError):
                        pass

        body_text = await page.locator("body").inner_text(timeout=5000)
        if any(message in body_text.lower() for message in ["captcha", "verifique que você é humano"]):
            raise RuntimeError("A Shopee apresentou uma verificação. Abra com --headed e conclua manualmente.")

        values = [brl_to_float(x) for x in MONEY_RE.findall(body_text[:25000])]
        unique_values = []
        for value in values:
            if value not in unique_values:
                unique_values.append(value)
        if current is None and unique_values:
            current = unique_values[0]
        if current is not None:
            old_candidates = [x for x in unique_values[1:8] if x > current]
            if old_candidates:
                old = old_candidates[0]

        if not title or current is None:
            raise RuntimeError(
                "Não foi possível obter nome e preço da página pública. "
                "A estrutura pode ter mudado ou o acesso pode ter sido bloqueado."
            )

        await browser.close()
        return {
            "shopId": shop_id,
            "itemId": item_id,
            "name": re.sub(r"\s+\|\s+Shopee.*$", "", title).strip(),
            "description": re.sub(r"\s+", " ", description).strip()[:500],
            "price": current,
            "oldPrice": old,
            "rating": rating,
            "imageUrl": image_url,
            "link": url,
        }


async def download_image(url: str, destination: Path) -> None:
    if not url:
        return
    async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
        response = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        if not content_type.startswith("image/"):
            raise RuntimeError("A URL de imagem não retornou um arquivo de imagem.")
        destination.write_bytes(response.content)


def upsert(products_path: Path, extracted: dict, product_id: int | None, category: str) -> dict:
    products = json.loads(products_path.read_text(encoding="utf-8")) if products_path.exists() else []
    if not isinstance(products, list):
        raise ValueError("products.json precisa conter uma lista JSON.")

    existing = None
    if product_id is not None:
        existing = next((p for p in products if int(p.get("id", -1)) == product_id), None)
    if existing is None:
        existing = next((p for p in products if str(p.get("itemId", "")) == extracted["itemId"]), None)

    new_id = product_id or (max([int(p.get("id", 0)) for p in products] or [0]) + 1)
    image_name = f"{slugify(extracted['name'])}-{extracted['itemId']}.jpg"
    order = int(existing.get("order", new_id)) if existing else new_id
    product = {
        "id": new_id,
        "itemId": extracted["itemId"],
        "shopId": extracted["shopId"],
        "name": extracted["name"],
        "description": extracted["description"] or "Confira os detalhes completos na plataforma de compra.",
        "category": existing.get("category", category) if existing else category,
        "price": round(float(extracted["price"]), 2),
        "oldPrice": round(float(extracted["oldPrice"]), 2) if extracted.get("oldPrice") else None,
        "rating": round(float(extracted["rating"]), 1) if extracted.get("rating") else 0,
        "badge": existing.get("badge", "Novidade") if existing else "Novidade",
        "image": f"images/{image_name}",
        "link": extracted["link"],
        "active": existing.get("active", True) if existing else True,
        "order": order,
        "lastUpdated": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    if existing:
        products[products.index(existing)] = product
    else:
        products.append(product)
    products.sort(key=lambda p: int(p.get("order", 999999)))
    products_path.write_text(json.dumps(products, ensure_ascii=False, indent=2), encoding="utf-8")
    product["_imageUrl"] = extracted.get("imageUrl", "")
    return product


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("url")
    parser.add_argument("--id", type=int, help="ID existente para substituir")
    parser.add_argument("--category", default="Eletrônicos")
    parser.add_argument("--products", default="products.json")
    parser.add_argument("--headed", action="store_true", help="Abre o navegador visível")
    args = parser.parse_args()

    products_path = Path(args.products).resolve()
    root = products_path.parent
    images = root / "images"
    images.mkdir(exist_ok=True)

    extracted = await collect(args.url, args.headed)
    product = upsert(products_path, extracted, args.id, args.category)
    image_url = product.pop("_imageUrl", "")
    if image_url:
        await download_image(image_url, root / product["image"])
    print(json.dumps(product, ensure_ascii=False, indent=2))
    print("\nRevise products.json antes de publicar, especialmente preço, descrição e imagem.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        raise SystemExit(1)

from __future__ import annotations

import csv
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "trade_leads.csv"
)

COLUMNS = [
    "company_name",
    "product_category",
    "source",
    "source_url",
    "research_method",
]

TRADE_LEADS = [
    {"company_name": "Союз Керамика (Soyuz Ceramica)", "product_category": "Porcelain & Ceramic Tiles", "source": "MosBuild Exhibitor List", "source_url": "https://soyuzceramica.ru", "research_method": "Manual Public Research"},
    {"company_name": "Линкер (Lincer)", "product_category": "Porcelain & Ceramic Tiles", "source": "MosBuild Exhibitor List", "source_url": "https://lincer.ru", "research_method": "Manual Public Research"},
    {"company_name": "А-Керамика (A-Ceramica)", "product_category": "Porcelain & Ceramic Tiles", "source": "MosBuild Exhibitor List", "source_url": "https://a-ceramica.ru", "research_method": "Manual Public Research"},
    {"company_name": "Арткерамика (Artkeramika)", "product_category": "Porcelain & Ceramic Tiles", "source": "MosBuild Exhibitor List", "source_url": "https://artkeramika-opt.ru", "research_method": "Manual Public Research"},
    {"company_name": "ТЕССЕР (Tesser)", "product_category": "Porcelain & Ceramic Tiles", "source": "MosBuild Exhibitor List", "source_url": "https://tesser.ru", "research_method": "Manual Public Research"},
    {"company_name": "Контакт-М (Contact-M)", "product_category": "Porcelain & Ceramic Tiles", "source": "MosBuild Exhibitor List", "source_url": "https://kontact-m.ru", "research_method": "Manual Public Research"},
    {"company_name": "Мосплитка (Mosplitka)", "product_category": "Porcelain & Ceramic Tiles", "source": "MosBuild Exhibitor List", "source_url": "https://mosplitka.ru", "research_method": "Manual Public Research"},
    {"company_name": "Керамотека (Keramoteka)", "product_category": "Porcelain & Ceramic Tiles", "source": "MosBuild Exhibitor List", "source_url": "https://keramoteka.ru", "research_method": "Manual Public Research"},
    {"company_name": "Estima", "product_category": "Porcelain & Ceramic Tiles", "source": "MosBuild Exhibitor List", "source_url": "https://estima.ru", "research_method": "Manual Public Research"},
    {"company_name": "Kerranova (Samarskiy Stroyfarfor)", "product_category": "Porcelain & Ceramic Tiles", "source": "MosBuild Exhibitor List", "source_url": "https://kerranova.ru", "research_method": "Manual Public Research"},
    {"company_name": "Laperet", "product_category": "Porcelain & Ceramic Tiles", "source": "MosBuild Exhibitor List", "source_url": "https://laperet.ru", "research_method": "Manual Public Research"},
    {"company_name": "Italon", "product_category": "Porcelain & Ceramic Tiles", "source": "MosBuild Exhibitor List", "source_url": "https://italonceramica.ru", "research_method": "Manual Public Research"},
    {"company_name": "Cersanit Russia", "product_category": "Porcelain & Ceramic Tiles", "source": "MosBuild Exhibitor List", "source_url": "https://cersanit.ru", "research_method": "Manual Public Research"},
    {"company_name": "Gracia Ceramica", "product_category": "Porcelain & Ceramic Tiles", "source": "MosBuild Exhibitor List", "source_url": "https://graciaceramica.com", "research_method": "Manual Public Research"},
    {"company_name": "Unitile", "product_category": "Porcelain & Ceramic Tiles", "source": "MosBuild Exhibitor List", "source_url": "https://unitile.ru", "research_method": "Manual Public Research"},
    {"company_name": "Creto", "product_category": "Porcelain & Ceramic Tiles", "source": "MosBuild Exhibitor List", "source_url": "https://creto.ru", "research_method": "Manual Public Research"},
    {"company_name": "Global Tile", "product_category": "Porcelain & Ceramic Tiles", "source": "MosBuild Exhibitor List", "source_url": "https://global-tile.ru", "research_method": "Manual Public Research"},
    {"company_name": "Уральский гранит (Ural Granit)", "product_category": "Porcelain & Ceramic Tiles", "source": "MosBuild Exhibitor List", "source_url": "https://uralgranit.ru", "research_method": "Manual Public Research"},
    {"company_name": "Берёзастройматериалы (Beryoza Ceramica)", "product_category": "Porcelain & Ceramic Tiles", "source": "MosBuild Exhibitor List", "source_url": "https://bereza-ceramica.by", "research_method": "Manual Public Research"},
    {"company_name": "Onetouch Ceramica", "product_category": "Porcelain & Ceramic Tiles", "source": "MosBuild Exhibitor List", "source_url": "https://onetouchceramica.ru", "research_method": "Manual Public Research"},
    {"company_name": "Nt Ceramic", "product_category": "Porcelain & Ceramic Tiles", "source": "MosBuild Exhibitor List", "source_url": "https://ntceramic.ru", "research_method": "Manual Public Research"},
    {"company_name": "Zerde Ceramics", "product_category": "Porcelain & Ceramic Tiles", "source": "MosBuild Exhibitor List", "source_url": "https://zerdeceramics.kz", "research_method": "Manual Public Research"},
    {"company_name": "Monalisa Tiles Russia", "product_category": "Porcelain & Ceramic Tiles", "source": "MosBuild Exhibitor List", "source_url": "https://monalisatiles.ru", "research_method": "Manual Public Research"},
    {"company_name": "Plitka-Podolsk", "product_category": "Porcelain & Ceramic Tiles", "source": "Supl.biz Directory", "source_url": "https://plitka-podolsk.ru", "research_method": "Manual Public Research"},
    {"company_name": "К-Импорт (K-Import)", "product_category": "Porcelain & Ceramic Tiles", "source": "Supl.biz Directory", "source_url": "https://www.k-import.ru", "research_method": "Manual Public Research"},
    {"company_name": "Керамир (Ceramir)", "product_category": "Porcelain & Ceramic Tiles", "source": "Supl.biz Directory", "source_url": "https://ceramir.ru", "research_method": "Manual Public Research"},
    {"company_name": "Керамогранит.ру (Keramogranit.ru)", "product_category": "Porcelain & Ceramic Tiles", "source": "Supl.biz Directory", "source_url": "https://www.keramogranit.ru", "research_method": "Manual Public Research"},
    {"company_name": "Cerammax", "product_category": "Porcelain & Ceramic Tiles", "source": "Supl.biz Directory", "source_url": "https://www.cerammax.ru", "research_method": "Manual Public Research"},
    {"company_name": "Atlas Concorde Russia", "product_category": "Porcelain & Ceramic Tiles", "source": "MosBuild Exhibitor List", "source_url": "https://atlasconcorde.ru", "research_method": "Manual Public Research"},
    {"company_name": "Primavera", "product_category": "Porcelain & Ceramic Tiles", "source": "MosBuild Exhibitor List", "source_url": "https://primavera-ceramica.ru", "research_method": "Manual Public Research"},
    {"company_name": "Ceramica Classic", "product_category": "Porcelain & Ceramic Tiles", "source": "MosBuild Exhibitor List", "source_url": "https://ceramicaclassic.ru", "research_method": "Manual Public Research"},
    {"company_name": "Lira Ceramica", "product_category": "Porcelain & Ceramic Tiles", "source": "MosBuild Exhibitor List", "source_url": "https://liraceramica.ru", "research_method": "Manual Public Research"},
]


def create_trade_template() -> None:
    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_FILE.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=COLUMNS,
        )

        writer.writeheader()
        writer.writerows(TRADE_LEADS)

    print(f"Created/Updated {OUTPUT_FILE} with {len(TRADE_LEADS)} manually researched trade leads.")


if __name__ == "__main__":
    create_trade_template()

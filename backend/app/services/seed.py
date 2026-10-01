"""Optional development food fixtures.

These are clearly labelled illustrative values, not a medical or authoritative
food database. Production deployments should import a cited dataset and keep
its provenance in ``source``.
"""

from app.core.database import SessionLocal
from app.models.food import Food
from app.nutrition.calculations import normalize_food_name

_DEMO_FOODS = [
    # Values are approximate development fixtures and intentionally labelled.
    dict(name="Œuf", basis_quantity=1, basis_unit="piece", calories=72, protein_g=6.3, carbohydrates_g=0.4, fat_g=4.8, fiber_g=0, sugar_g=0.2, sodium_mg=70),
    dict(name="Riz cuit", basis_quantity=100, basis_unit="g", calories=130, protein_g=2.7, carbohydrates_g=28.2, fat_g=0.3, fiber_g=0.4, sugar_g=0.1, sodium_mg=1),
    dict(name="Poulet grillé", basis_quantity=100, basis_unit="g", calories=165, protein_g=31, carbohydrates_g=0, fat_g=3.6, fiber_g=0, sugar_g=0, sodium_mg=74),
    dict(name="Pomme", basis_quantity=100, basis_unit="g", calories=52, protein_g=0.3, carbohydrates_g=13.8, fat_g=0.2, fiber_g=2.4, sugar_g=10.4, sodium_mg=1),
    dict(name="Lentilles cuites", basis_quantity=100, basis_unit="g", calories=116, protein_g=9, carbohydrates_g=20.1, fat_g=0.4, fiber_g=7.9, sugar_g=1.8, sodium_mg=2),
    dict(name="Flocons d'avoine", basis_quantity=100, basis_unit="g", calories=389, protein_g=16.9, carbohydrates_g=66.3, fat_g=6.9, fiber_g=10.6, sugar_g=0.9, sodium_mg=2),
    dict(name="Yaourt nature", basis_quantity=100, basis_unit="g", calories=61, protein_g=3.5, carbohydrates_g=4.7, fat_g=3.3, fiber_g=0, sugar_g=4.7, sodium_mg=46),
    dict(name="Tomate", basis_quantity=100, basis_unit="g", calories=18, protein_g=0.9, carbohydrates_g=3.9, fat_g=0.2, fiber_g=1.2, sugar_g=2.6, sodium_mg=5),
]


def seed_demo_foods() -> None:
    db = SessionLocal()
    try:
        for values in _DEMO_FOODS:
            normalized = normalize_food_name(values["name"])
            if db.query(Food).filter(Food.normalized_name == normalized).first():
                continue
            db.add(
                Food(
                    **values,
                    normalized_name=normalized,
                    source="demo_reference",
                    confidence="estimated",
                    notes="Fixture de développement illustrative; importer une source citée avant un usage de production.",
                    is_verified=False,
                )
            )
        db.commit()
    finally:
        db.close()

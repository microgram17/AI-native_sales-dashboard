
async def test_typo_resolution_returns_canonical_product(service):
    result = await service.resolve_product(
        supplier_id="NORDVALE",
        product="Minmal Logo Hoodie",
    )

    assert result.status == "success"
    assert result.product is not None
    assert result.product.id == "NORD-HOD-011"
    assert result.product.name == "Minimal Logo Hoodie"

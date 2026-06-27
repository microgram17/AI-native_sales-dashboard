from typing import Any

from pydantic import RootModel


class SupplierSummaryResponse(RootModel[dict[str, Any]]):
    pass


class SupplierRevenueTrendResponse(RootModel[dict[str, Any]]):
    pass


class TopProductsResponse(RootModel[dict[str, Any]]):
    pass


class SupplierListResponse(RootModel[dict[str, Any]]):
    pass

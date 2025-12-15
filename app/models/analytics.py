from typing import List, Optional
from pydantic import BaseModel


# -------- TOP PRODUCTS --------

class TopProduct(BaseModel):
    product_id: Optional[int]
    name: Optional[str]
    times_ordered: int
    total_quantity: Optional[int]


class TopProductsResponse(BaseModel):
    items: List[TopProduct]


# -------- BOTTLENECKS: LATE DELIVERIES BY DEPARTMENT --------

class DepartmentBottleneck(BaseModel):
    department_id: Optional[int]
    department_name: Optional[str]
    market: Optional[str]
    late_orders: int
    total_orders: int
    late_ratio: float  # percentage of late orders (0–100)

class DepartmentBottlenecksResponse(BaseModel):
    items: List[DepartmentBottleneck]

# Shortest paths algorithms

class ProductInPath(BaseModel):
    product_id: int
    name: Optional[str]


class ProductPath(BaseModel):
    products: List[ProductInPath]
    length: int  # number of hops


class ProductPathResponse(BaseModel):
    path: ProductPath


class AllProductPathsResponse(BaseModel):
    paths: List[ProductPath]

from typing import Optional, List
from pydantic import BaseModel


class CustomerModel(BaseModel):
    customer_id: Optional[int]
    first_name: Optional[str]
    last_name: Optional[str]
    city: Optional[str]
    country: Optional[str]


class ProductModel(BaseModel):
    product_id: Optional[int]
    name: Optional[str]
    price: Optional[float]


class OrderCore(BaseModel):
    order_id: int
    order_date: Optional[str]
    shipping_date: Optional[str]
    late_delivery_risk: Optional[int]
    shipping_mode: Optional[str]
    days_shipping_scheduled: Optional[int]
    days_shipping_real: Optional[int]
    region: Optional[str]
    delivery_status: Optional[str]
    status: Optional[str]


class OrderResponse(BaseModel):
    order: OrderCore
    customer: Optional[CustomerModel]
    products: List[ProductModel]


# response model for /products/{product_id}

class ProductDetailsResponse(BaseModel):
    product: ProductModel
    orders: List[OrderCore]
    customers: List[CustomerModel]

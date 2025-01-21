from pydantic import BaseModel
from enum import Enum
from typing import List
from datetime import datetime

class petStatus(str, Enum):
    available = "available"
    pending = "pending"
    sold = "sold"

class orderStatus(str, Enum):
    placed = "placed"
    approved = "approved"
    delivered = "delivered"

class ApiResponse(BaseModel):
    code: int
    type: str
    message: str

class Category(BaseModel):
    id: int
    name: str

class Tag(BaseModel):
    id: int
    name: str

class User(BaseModel):
    id: int
    username: str
    firstName: str
    lastName: str
    email: str
    password: str
    phone: str
    userStatus: int

class Pet(BaseModel):
    id: int
    category: Category
    name: str
    photoUrls: List[str] = []
    tags: List[Tag] = []
    status: petStatus

class Order(BaseModel):
    id: int
    petId: int
    quantity: int
    shipDate: datetime
    status: orderStatus
    complete: bool
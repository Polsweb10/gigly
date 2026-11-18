from typing import List, Optional
from pydantic import BaseModel, EmailStr

class UserRegister(BaseModel):
    email: EmailStr
    username: str
    full_name: str
    password: str

class UserLogin(BaseModel):
    username_or_email: str
    password: str

class SwitchModeRequest(BaseModel):
    mode: str  # "buyer" or "seller"

class PackageCreate(BaseModel):
    tier: str  # "basic", "standard", "premium"
    name: str
    description: str
    delivery_days: int
    revisions: int
    price: float
    features: List[str]

class GigCreate(BaseModel):
    title: str
    category: str
    sub_category: Optional[str] = "General"
    description: str
    tags: Optional[str] = ""
    image_url: str
    requires_nda: bool = False
    allows_retainer: bool = False
    retainer_monthly_price: Optional[float] = None
    packages: List[PackageCreate]

class OrderCreateRequest(BaseModel):
    gig_id: Optional[int] = None
    package_id: Optional[int] = None
    request_id: Optional[int] = None
    is_milestone_based: bool = False
    milestones: Optional[List[dict]] = None
    is_subscription: bool = False

class ProjectRequestCreate(BaseModel):
    title: str
    description: str
    category: str
    budget: float
    delivery_days: int
    requires_nda: bool = False
    allows_milestones: bool = True

class ProposalCreate(BaseModel):
    request_id: int
    cover_letter: str
    offered_price: float
    offered_days: int

class NDASignRequest(BaseModel):
    order_id: int
    full_legal_name: str
    agreed: bool

class ReviewCreate(BaseModel):
    order_id: int
    rating: int
    comment: str

class WalletDepositRequest(BaseModel):
    amount: float

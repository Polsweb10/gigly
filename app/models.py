import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey, Index
)
from sqlalchemy.orm import relationship
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=False)
    bio = Column(Text, default="Freelancer profesional en Gigly.")
    avatar_url = Column(String(500), default="https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80")
    
    # Mode switcher: "buyer" or "seller"
    current_mode = Column(String(20), default="buyer", nullable=False)
    
    # Financials (Gigly Escrow & Wallet)
    wallet_balance = Column(Float, default=150.0)  # Starting bonus / demo funds for seamless testing
    escrow_balance = Column(Float, default=0.0)    # Funds held in escrow as seller
    
    is_verified = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    rating_avg = Column(Float, default=5.0)
    reviews_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    gigs = relationship("Gig", back_populates="seller", cascade="all, delete-orphan")
    orders_as_buyer = relationship("Order", foreign_keys="Order.buyer_id", back_populates="buyer")
    orders_as_seller = relationship("Order", foreign_keys="Order.seller_id", back_populates="seller")
    project_requests = relationship("ProjectRequest", back_populates="buyer")
    proposals = relationship("Proposal", back_populates="seller")
    reviews_written = relationship("Review", foreign_keys="Review.buyer_id", back_populates="buyer")
    reviews_received = relationship("Review", foreign_keys="Review.seller_id", back_populates="seller")
    transactions = relationship("WalletTransaction", back_populates="user", cascade="all, delete-orphan")


class Gig(Base):
    __tablename__ = "gigs"

    id = Column(Integer, primary_key=True, index=True)
    seller_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), index=True, nullable=False)
    slug = Column(String(255), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(100), index=True, nullable=False)
    sub_category = Column(String(100), default="General")
    tags = Column(String(255), default="")  # comma separated
    image_url = Column(String(500), nullable=False)
    gallery = Column(Text, default="[]")     # JSON array string
    is_active = Column(Boolean, default=True)
    
    # Gigly Advanced Features
    requires_nda = Column(Boolean, default=False)
    allows_retainer = Column(Boolean, default=False)
    retainer_monthly_price = Column(Float, nullable=True)
    
    rating_avg = Column(Float, default=5.0)
    rating_count = Column(Integer, default=0)
    orders_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    seller = relationship("User", back_populates="gigs")
    packages = relationship("GigPackage", back_populates="gig", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="gig")
    reviews = relationship("Review", back_populates="gig")


class GigPackage(Base):
    __tablename__ = "gig_packages"

    id = Column(Integer, primary_key=True, index=True)
    gig_id = Column(Integer, ForeignKey("gigs.id"), nullable=False)
    tier = Column(String(20), nullable=False)  # "basic", "standard", "premium"
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    delivery_days = Column(Integer, default=3)
    revisions = Column(Integer, default=2)  # -1 for unlimited
    price = Column(Float, nullable=False)
    features = Column(Text, default="[]")   # JSON array of strings

    gig = relationship("Gig", back_populates="packages")


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String(50), unique=True, index=True, nullable=False)
    buyer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    seller_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    gig_id = Column(Integer, ForeignKey("gigs.id"), nullable=True)
    package_id = Column(Integer, ForeignKey("gig_packages.id"), nullable=True)
    request_id = Column(Integer, ForeignKey("project_requests.id"), nullable=True)
    
    title = Column(String(255), nullable=False)
    description = Column(Text, default="")
    
    # Financial Escrow Breakdown
    base_amount = Column(Float, nullable=False)
    buyer_fee = Column(Float, default=0.0)      # 3% Gigly Buyer Service Fee
    seller_fee = Column(Float, default=0.0)     # 10% Gigly Commission
    total_buyer_paid = Column(Float, nullable=False)
    seller_net_amount = Column(Float, nullable=False)
    
    # Order Status Flow:
    # pending -> in_progress -> delivered -> in_review -> completed | disputed | cancelled
    status = Column(String(50), default="in_progress", nullable=False)
    
    # Features
    is_milestone_based = Column(Boolean, default=False)
    is_subscription = Column(Boolean, default=False)
    
    # NDA integration
    nda_required = Column(Boolean, default=False)
    nda_signed = Column(Boolean, default=False)
    nda_signed_at = Column(DateTime, nullable=True)
    nda_signature_text = Column(String(255), nullable=True)

    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    delivery_deadline = Column(DateTime, nullable=True)

    # Relationships
    buyer = relationship("User", foreign_keys=[buyer_id], back_populates="orders_as_buyer")
    seller = relationship("User", foreign_keys=[seller_id], back_populates="orders_as_seller")
    gig = relationship("Gig", back_populates="orders")
    package = relationship("GigPackage")
    project_request = relationship("ProjectRequest", back_populates="order")
    milestones = relationship("Milestone", back_populates="order", cascade="all, delete-orphan")
    deliverables = relationship("Deliverable", back_populates="order", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="order", cascade="all, delete-orphan")
    review = relationship("Review", back_populates="order", uselist=False)
    nda_contract = relationship("NDAContract", back_populates="order", uselist=False)


class Milestone(Base):
    __tablename__ = "milestones"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    order_index = Column(Integer, default=1)
    title = Column(String(255), nullable=False)
    description = Column(Text, default="")
    amount = Column(Float, nullable=False)
    due_days = Column(Integer, default=5)
    
    # Milestone Status: pending -> in_progress -> delivered -> approved
    status = Column(String(50), default="pending", nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    approved_at = Column(DateTime, nullable=True)

    order = relationship("Order", back_populates="milestones")
    deliverables = relationship("Deliverable", back_populates="milestone")


class Deliverable(Base):
    __tablename__ = "deliverables"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    milestone_id = Column(Integer, ForeignKey("milestones.id"), nullable=True)
    uploader_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    file_title = Column(String(255), nullable=False)
    notes = Column(Text, default="")
    original_file_path = Column(String(500), nullable=False)
    watermarked_file_path = Column(String(500), nullable=True)  # Protected preview before approval
    is_image = Column(Boolean, default=False)
    file_size = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    order = relationship("Order", back_populates="deliverables")
    milestone = relationship("Milestone", back_populates="deliverables")


class ProjectRequest(Base):
    __tablename__ = "project_requests"

    id = Column(Integer, primary_key=True, index=True)
    buyer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(100), nullable=False)
    budget = Column(Float, nullable=False)
    delivery_days = Column(Integer, default=7)
    requires_nda = Column(Boolean, default=False)
    allows_milestones = Column(Boolean, default=True)
    
    # Status: open -> awarded -> closed
    status = Column(String(50), default="open", nullable=False)
    proposals_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    buyer = relationship("User", back_populates="project_requests")
    proposals = relationship("Proposal", back_populates="request", cascade="all, delete-orphan")
    order = relationship("Order", back_populates="project_request", uselist=False)


class Proposal(Base):
    __tablename__ = "proposals"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(Integer, ForeignKey("project_requests.id"), nullable=False)
    seller_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    cover_letter = Column(Text, nullable=False)
    offered_price = Column(Float, nullable=False)
    offered_days = Column(Integer, nullable=False)
    
    # Status: pending -> accepted -> rejected
    status = Column(String(50), default="pending", nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    request = relationship("ProjectRequest", back_populates="proposals")
    seller = relationship("User", back_populates="proposals")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    attachment_url = Column(String(500), nullable=True)
    is_system_message = Column(Boolean, default=False)
    jitsi_meeting_url = Column(String(500), nullable=True)  # Video call link
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    order = relationship("Order", back_populates="messages")
    sender = relationship("User")


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), unique=True, nullable=False)
    gig_id = Column(Integer, ForeignKey("gigs.id"), nullable=True)
    buyer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    seller_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    rating = Column(Integer, nullable=False)  # 1 to 5
    comment = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    order = relationship("Order", back_populates="review")
    gig = relationship("Gig", back_populates="reviews")
    buyer = relationship("User", foreign_keys=[buyer_id], back_populates="reviews_written")
    seller = relationship("User", foreign_keys=[seller_id], back_populates="reviews_received")


class WalletTransaction(Base):
    __tablename__ = "wallet_transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    
    # Types: deposit, escrow_hold, escrow_release, fee_deduction, withdrawal, refund
    type = Column(String(50), nullable=False)
    amount = Column(Float, nullable=False)
    description = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="transactions")


class NDAContract(Base):
    __tablename__ = "nda_contracts"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), unique=True, nullable=False)
    signer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    full_legal_name = Column(String(255), nullable=False)
    signature_hash = Column(String(255), nullable=False)
    ip_address = Column(String(100), default="127.0.0.1")
    signed_at = Column(DateTime, default=datetime.datetime.utcnow)

    order = relationship("Order", back_populates="nda_contract")
    signer = relationship("User")

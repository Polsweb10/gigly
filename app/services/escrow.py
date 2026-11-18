import datetime
from sqlalchemy.orm import Session
from app.config import settings
from app.models import Order, User, WalletTransaction, Milestone

def calculate_fees(base_amount: float):
    """
    Calculates platform fees and totals:
    - Buyer Fee: 3% service fee added to base price
    - Seller Fee: 10% platform commission retained from seller payout
    - Total Buyer Paid: base_amount + buyer_fee
    - Seller Net Amount: base_amount - seller_fee
    """
    buyer_fee = round(base_amount * (settings.PLATFORM_BUYER_FEE_PERCENT / 100.0), 2)
    seller_fee = round(base_amount * (settings.PLATFORM_SELLER_FEE_PERCENT / 100.0), 2)
    total_buyer_paid = round(base_amount + buyer_fee, 2)
    seller_net_amount = round(base_amount - seller_fee, 2)
    
    return {
        "base_amount": base_amount,
        "buyer_fee": buyer_fee,
        "seller_fee": seller_fee,
        "total_buyer_paid": total_buyer_paid,
        "seller_net_amount": seller_net_amount
    }

def hold_funds_in_escrow(db: Session, order: Order, buyer: User) -> bool:
    """
    Deducts total_buyer_paid from buyer's available wallet balance
    and reflects it in the seller's escrow_balance (held in Gigly Escrow).
    """
    if buyer.wallet_balance < order.total_buyer_paid:
        return False
    
    # Deduct from buyer
    buyer.wallet_balance = round(buyer.wallet_balance - order.total_buyer_paid, 2)
    
    # Add to seller's escrow pending balance
    seller = order.seller
    seller.escrow_balance = round(seller.escrow_balance + order.seller_net_amount, 2)
    
    # Register transaction for buyer
    tx = WalletTransaction(
        user_id=buyer.id,
        order_id=order.id,
        type="escrow_hold",
        amount=-order.total_buyer_paid,
        description=f"Pago retenido en Gigly Escrow por pedido #{order.order_number}"
    )
    db.add(tx)
    db.commit()
    return True

def release_order_escrow(db: Session, order: Order) -> bool:
    """
    Releases the held escrow funds directly into the seller's available wallet balance,
    recording the fee deduction transaction and net release.
    """
    seller = order.seller
    
    # Decrease escrow balance
    if seller.escrow_balance >= order.seller_net_amount:
        seller.escrow_balance = round(seller.escrow_balance - order.seller_net_amount, 2)
    else:
        seller.escrow_balance = 0.0
        
    # Increase seller available wallet balance with net earnings
    seller.wallet_balance = round(seller.wallet_balance + order.seller_net_amount, 2)
    
    # Register transactions for seller
    tx_release = WalletTransaction(
        user_id=seller.id,
        order_id=order.id,
        type="escrow_release",
        amount=order.seller_net_amount,
        description=f"Liberación de fondos Gigly Escrow por pedido #{order.order_number} (Comisión {settings.PLATFORM_SELLER_FEE_PERCENT}% deducida)"
    )
    db.add(tx_release)
    
    order.status = "completed"
    order.updated_at = datetime.datetime.utcnow()
    
    if order.gig:
        order.gig.orders_count += 1
        
    db.commit()
    return True

def release_milestone_escrow(db: Session, milestone: Milestone) -> bool:
    """
    Releases partial payment for a specific milestone approved by the buyer.
    """
    order = milestone.order
    seller = order.seller
    
    milestone_base = milestone.amount
    milestone_seller_fee = round(milestone_base * (settings.PLATFORM_SELLER_FEE_PERCENT / 100.0), 2)
    milestone_seller_net = round(milestone_base - milestone_seller_fee, 2)
    
    seller.escrow_balance = max(0.0, round(seller.escrow_balance - milestone_seller_net, 2))
    seller.wallet_balance = round(seller.wallet_balance + milestone_seller_net, 2)
    
    milestone.status = "approved"
    milestone.approved_at = datetime.datetime.utcnow()
    
    tx = WalletTransaction(
        user_id=seller.id,
        order_id=order.id,
        type="escrow_release",
        amount=milestone_seller_net,
        description=f"Liberación de Hito '{milestone.title}' del pedido #{order.order_number}"
    )
    db.add(tx)
    
    all_milestones = db.query(Milestone).filter(Milestone.order_id == order.id).all()
    if all(m.status == "approved" for m in all_milestones):
        order.status = "completed"
        order.updated_at = datetime.datetime.utcnow()
        if order.gig:
            order.gig.orders_count += 1
            
    db.commit()
    return True

def refund_order_escrow(db: Session, order: Order, reason: str = "") -> bool:
    """
    Refunds held escrow funds back to buyer and cancels order (Admin arbitration).
    """
    buyer = order.buyer
    seller = order.seller
    
    # Deduct held escrow balance from seller
    if seller.escrow_balance >= order.seller_net_amount:
        seller.escrow_balance = round(seller.escrow_balance - order.seller_net_amount, 2)
    else:
        seller.escrow_balance = 0.0
        
    # Re-credit buyer available balance
    buyer.wallet_balance = round(buyer.wallet_balance + order.total_buyer_paid, 2)
    
    # Record transaction
    tx = WalletTransaction(
        user_id=buyer.id,
        order_id=order.id,
        type="refund",
        amount=order.total_buyer_paid,
        description=f"Reembolso de Gigly Escrow por resolución de disputa en pedido #{order.order_number}"
    )
    db.add(tx)
    
    order.status = "cancelled"
    order.updated_at = datetime.datetime.utcnow()
    db.commit()
    return True

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, ForeignKey, LargeBinary, DateTime, Boolean
from sqlalchemy.orm import relationship
from src.database.base_class import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    # Storing digital signature as raw binary data (BYTEA in PostgreSQL)
    digital_signature = Column(LargeBinary, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    invoices = relationship("Invoice", back_populates="creator")


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(20), unique=True, index=True, nullable=False)
    email = Column(String(100), nullable=True)
    address = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    invoices = relationship("Invoice", back_populates="customer")


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    total_amount = Column(Float, nullable=False, default=0.0)  # Subtotal (sum of item subtotals)
    discount_amount = Column(Float, nullable=False, default=0.0)  # Flat discount applied before VAT
    tax_rate = Column(Float, nullable=False,
                      default=0.0)  # e.g., 0.05 for 5%, user-entered per invoice (labeled "VAT" in UI/PDF)
    less_adjustment = Column(Float, nullable=False,
                             default=0.0)  # Manual deduction applied after VAT, before grand total
    grand_total = Column(Float, nullable=False, default=0.0)
    paid_amount = Column(Float, nullable=False, default=0.0)       # How much the customer has actually paid
    payment_status = Column(String(20), nullable=False, default="Paid")  # Paid, Due, Partial Due
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Due-payment chain: for a due-payment record, this always points to the ORIGINAL
    # root sale invoice (never to an intermediate due-payment), so balance math is a
    # flat sum instead of tree recursion. NULL for normal sale invoices.
    parent_invoice_id = Column(Integer, ForeignKey("invoices.id", ondelete="SET NULL"), nullable=True)
    # True only for a record created to log a payment against a due balance — carries
    # no cart items, subtotal, tax, etc. False for a normal product-sale invoice.
    is_due_payment = Column(Boolean, nullable=False, default=False)

    # Relationships
    customer = relationship("Customer", back_populates="invoices")
    creator = relationship("User", back_populates="invoices")
    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan")
    root_invoice = relationship(
        "Invoice", remote_side=[id], foreign_keys=[parent_invoice_id], backref="due_payments"
    )

    @property
    def due_amount(self) -> float:
        """Outstanding balance on THIS record as originally issued — derived, not stored,
        never edited after issuing. Historical/as-sold figure."""
        return round(self.grand_total - self.paid_amount, 2)

    @property
    def effective_paid_amount(self) -> float:
        """Original paid_amount PLUS every linked due-payment made against this invoice.
        Only meaningful on a root (non due-payment) invoice."""
        total = self.paid_amount
        for dp in self.due_payments:
            total += dp.paid_amount
        return round(total, 2)

    @property
    def effective_due_amount(self) -> float:
        """Current true outstanding balance including all due-payments made so far."""
        return round(self.grand_total - self.effective_paid_amount, 2)

    @property
    def effective_status(self) -> str:
        """Current true status including all due-payments made so far."""
        if self.effective_due_amount <= 0.001:
            return "Paid"
        if self.effective_paid_amount > 0:
            return "Partial Payment"
        return self.payment_status

class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False)
    product_name = Column(String(100), nullable=False)         # "Vermi-compost" or "Earthworms"
    quantity = Column(Float, nullable=False)                   # weight/quantity
    unit_price = Column(Float, nullable=False)
    subtotal = Column(Float, nullable=False)                   # quantity * unit_price

    # Relationships
    invoice = relationship("Invoice", back_populates="items")
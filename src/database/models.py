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


class CustomerType(Base):
    """Admin-managed list (e.g. Retail / Wholesale / Distributor). Editable via Settings page."""
    __tablename__ = "customer_types"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)

    # Relationships
    customers = relationship("Customer", back_populates="customer_type")


class CustomerTier(Base):
    """Admin-managed purchase-based ranking (e.g. Silver/Golden/Platinum). Editable via Settings page.
    NOTE: internally named 'Tier' in code to avoid confusion with Invoice.payment_status /
    Invoice.effective_status, but every UI-facing label for this concept must say 'Status'
    (e.g. Customer Directory column header = 'Status', badge tooltip = 'Status: Golden')."""
    __tablename__ = "customer_tiers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)              # e.g. "Silver", "Golden", "Platinum"
    min_amount = Column(Float, nullable=False)              # qualifying Grand Total threshold
    period = Column(String(10), nullable=False, default="monthly")  # "monthly" or "yearly"
    rank = Column(Integer, nullable=False, unique=True)      # higher rank = evaluated first / higher tier


class AppSettings(Base):
    """Singleton settings row (always id=1). Currently holds the Status grace/decay/
    hold configuration; can grow to hold other app-wide admin settings later."""
    __tablename__ = "app_settings"

    id = Column(Integer, primary_key=True)
    grace_days = Column(Integer, nullable=False, default=30)
    decay_step_days = Column(Integer, nullable=False, default=30)
    rank_hold_months = Column(Integer, nullable=False, default=6)  # how long an earned

    # Status level is kept after last qualifying, before it re-evaluates to current-period volume

class Product(Base):
    """Admin-managed sellable product/catalog item (e.g. Vermi-Compost, Earthworms).
    Editable via Settings page. NOTE: InvoiceItem.product_name stores a plain string
    SNAPSHOT of the name at time of sale (per the app's invoice-immutability rule) --
    it does NOT foreign-key to this table. Renaming or deleting a Product here never
    touches historical invoices; it only changes what's offered going forward."""
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    unit = Column(String(20), nullable=False, default="kg")  # e.g. "kg", "pcs", "L"
    default_price = Column(Float, nullable=False,
                            default=0.0)  # pre-fills Unit Price on Invoice Terminal, still editable per sale

class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(20), unique=True, index=True, nullable=False)
    email = Column(String(100), nullable=True)
    address = Column(String(255), nullable=True)
    customer_type_id = Column(Integer, ForeignKey("customer_types.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    invoices = relationship("Invoice", back_populates="customer")
    customer_type = relationship("CustomerType", back_populates="customers")


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
    transport_charge = Column(Float, nullable=False,
                              default=0.0)  # Optional flat add-on, applied after VAT, before less_adjustment
    show_transport_charge = Column(Boolean, nullable=False,
                                   default=False)  # Whether the charge row appears on the invoice/PDF at all
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
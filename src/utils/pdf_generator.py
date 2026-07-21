import io
from datetime import datetime
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from src.config import company_config as cfg
from src.config import pdf_styles as pstyle
from src.database.connection import get_db_session
from src.database.models import Invoice, User, Customer
from src.utils.pdf_fonts import register_unicode_fonts
from src.utils.time_utils import to_local_str

class PDFGenerator:
    @staticmethod
    def generate_invoice_pdf(invoice_id: int, output_path: str) -> bool:
        try:
            with get_db_session() as session:
                invoice = session.query(Invoice).filter_by(id=invoice_id).first()
                if not invoice:
                    raise ValueError(f"Invoice #{invoice_id} not found.")

                if invoice.is_due_payment:
                    return PDFGenerator._build_due_payment_pdf(invoice, output_path)
                return PDFGenerator._build_sale_invoice_pdf(invoice, output_path)
        except Exception as e:
            print(f"[Critical PDF Generation Error]: {e}")
            return False

    @staticmethod
    def _build_sale_invoice_pdf(invoice: Invoice, output_path: str) -> bool:
        """Standard product-sale invoice. Amount Paid / Balance Due / Status shown here are
        the EFFECTIVE figures (they include any due-payments made after issuing), so a
        reprinted invoice always reflects the current true balance rather than a stale
        as-issued snapshot."""
        customer = invoice.customer
        creator = invoice.creator
        items = invoice.items
        effective_status = invoice.effective_status
        effective_paid = invoice.effective_paid_amount
        effective_due = invoice.effective_due_amount
        status_color = cfg.resolve_status_color(effective_status)
        paid_color = cfg.STATUS_COLORS["paid"]  # always green
        due_color = cfg.STATUS_COLORS["due"]  # always red

        doc = SimpleDocTemplate(output_path, pagesize=letter, rightMargin=36,
                                leftMargin=36, topMargin=36, bottomMargin=50)
        story = []
        font_regular, _ = register_unicode_fonts()
        sym = f'<font face="{font_regular}">{cfg.CURRENCY_SYMBOL}</font>'
        styles = getSampleStyleSheet()
        meta_style = ParagraphStyle('MetaStyle', parent=styles['Normal'], fontSize=9,
                                    leading=12, textColor=colors.HexColor("#7f8c8d"))
        body_bold = ParagraphStyle('BodyBold', parent=styles['Normal'], fontSize=10,
                                   leading=14, fontName='Helvetica-Bold')
        header_cell_style = ParagraphStyle('HeaderCell', parent=styles['Normal'], fontSize=10,
                                           leading=13, fontName='Helvetica-Bold',
                                           textColor=colors.HexColor("#ffffff"))

        # 1. Header (logo + company info vs invoice meta)
        company_info = f"""<b>{cfg.COMPANY_NAME}</b><br/>
            {cfg.COMPANY_ADDRESS}<br/>
            Email: {cfg.COMPANY_EMAIL}<br/>
            Phone: {cfg.COMPANY_PHONE}
            """
        company_para = Paragraph(company_info, styles['Normal'])

        logo_img = None
        if cfg.COMPANY_LOGO_PATH:
            try:
                logo_img = Image(cfg.COMPANY_LOGO_PATH, width=70, height=70)
                logo_img.hAlign = 'LEFT'
            except Exception:
                logo_img = None

        if logo_img:
            company_block = Table([[logo_img, company_para]], colWidths=[80, 280])
            company_block.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ]))
        else:
            company_block = company_para

        invoice_meta = f"""<br/>
            <b>INVOICE</b><br/>
            <b>Invoice ID:</b> #{invoice.id}<br/>
            <b>Date:</b> {to_local_str(invoice.created_at)}<br/><br/>
            <b>Status:</b> <font color="{status_color}"><b>{effective_status.upper()}</b></font>
            """

        # Allocated 380 to the left and 160 to the right to cleanly position the left-aligned text on the right side
        header_table = Table([[company_block, Paragraph(invoice_meta, styles['Normal'])]],
                             colWidths=[380, 160])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'LEFT'),
            ('BACKGROUND', (0, 0), (-1, -1), pstyle.hex_with_alpha(pstyle.COMPANY_INFO_BG)),
            ('PADDING', (0, 0), (-1, -1), 10),
        ]))
        story.append(header_table)
        story.append(Spacer(1, 20))

        # 2. Bill To
        bill_to_info = f"""<b>BILL TO:</b><br/>
            <b>Name:</b> {customer.name}<br/>
            <b>Phone:</b> {customer.phone}<br/>
            <b>Email:</b> {customer.email if customer.email else 'N/A'}<br/>
            <b>Address:</b> {customer.address if customer.address else 'N/A'}
            """
        bill_table = Table([[Paragraph(bill_to_info, styles['Normal'])]], colWidths=[540])
        bill_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), pstyle.hex_with_alpha(pstyle.CUSTOMER_INFO_BG)),
            ('PADDING', (0, 0), (-1, -1), 10),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ]))
        story.append(bill_table)
        story.append(Spacer(1, 20))

        # 3. Items grid
        grid_data = [[
            Paragraph("Product Description", header_cell_style),
            Paragraph("Quantity", header_cell_style),
            Paragraph("Unit Price", header_cell_style),
            Paragraph("Subtotal", header_cell_style)
        ]]
        for item in items:
            grid_data.append([
                Paragraph(item.product_name, styles['Normal']),
                Paragraph(f"{item.quantity:.2f} kg", styles['Normal']),
                Paragraph(f"{sym} {item.unit_price:,.2f}", styles['Normal']),
                Paragraph(f"{sym} {item.subtotal:,.2f}", styles['Normal'])
            ])

        taxable_amount = invoice.total_amount - invoice.discount_amount
        tax_amount = taxable_amount * invoice.tax_rate

        grid_data.append(["", "", Paragraph("<b>Subtotal:</b>", styles['Normal']),
                          Paragraph(f"{sym} {invoice.total_amount:,.2f}", styles['Normal'])])
        grid_data.append(["", "", Paragraph("<b>Discount:</b>", styles['Normal']),
                          Paragraph(f"- {sym} {invoice.discount_amount:,.2f}",
                                    styles['Normal'])])
        grid_data.append(["", "", Paragraph(f"<b>VAT ({invoice.tax_rate * 100:.1f}%):</b>", styles['Normal']),
                          Paragraph(f"{sym} {tax_amount:,.2f}", styles['Normal'])])
        grid_data.append(["", "", Paragraph("<b>Less Adjustment:</b>", styles['Normal']),
                          Paragraph(f"- {sym} {invoice.less_adjustment:,.2f}",
                                    styles['Normal'])])
        grid_data.append(["", "", Paragraph("<b>Grand Total:</b>", body_bold),
                          Paragraph(f"<b>{sym} {invoice.grand_total:,.2f}</b>", body_bold)])
        grid_data.append(["", "", Paragraph("<b>Amount Paid:</b>", styles['Normal']),
                          Paragraph(
                              f'<font color="{paid_color}"><b>{sym} {effective_paid:,.2f}</b></font>',
                              styles['Normal'])])
        grid_data.append(["", "", Paragraph("<b>Balance Due:</b>", body_bold),
                          Paragraph(
                              f'<font color="{due_color}"><b>{sym} {effective_due:,.2f}</b></font>',
                              body_bold)])

        grid_table = Table(grid_data, colWidths=[240, 100, 100, 100])
        grid_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1c2833")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#ffffff")),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('TOPPADDING', (0, 0), (-1, 0), 10),
            ('ROWBACKGROUNDS', (0, 1), (-1, -8),
             [colors.white, pstyle.hex_with_alpha(pstyle.ITEMS_ALT_ROW_BG)]),
            ('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            # Highlighted separators: before Subtotal, and before Grand Total
            ('LINEABOVE', (2, -7), (3, -7), 1.0, colors.HexColor("#1c2833")),
            ('LINEABOVE', (2, -3), (3, -3), 1.0, colors.HexColor("#1c2833")),
            ('LINEABOVE', (2, -2), (3, -2), 0.5, colors.HexColor("#cbd5e1")),
            ('BACKGROUND', (0, -2), (-1, -1), pstyle.hex_with_alpha(pstyle.PAYMENT_BLOCK_BG)),
        ]))
        story.append(grid_table)
        story.append(Spacer(1, 10))

        # 3b. Due-payment trail note (only if any linked due-payments exist)
        if invoice.due_payments:
            sorted_payments = sorted(invoice.due_payments, key=lambda x: x.created_at)
            trail_ids = ", ".join(f"#{dp.id}" for dp in sorted_payments)
            last_payment_date = to_local_str(sorted_payments[-1].created_at)
            trail_note = (
                f'<font size="8" color="#7f8c8d">Additional due payment(s) recorded against this '
                f'invoice: {trail_ids} (Date of last due payment: {last_payment_date}). '
                f'See individual receipts for details.</font>'
            )
            story.append(Paragraph(trail_note, styles['Normal']))

        story.append(Spacer(1, 20))

        # 4. Signature (right-aligned block)
        right_body_style = ParagraphStyle('RightBody', parent=styles['Normal'], alignment=TA_RIGHT)
        right_meta_style = ParagraphStyle('RightMeta', parent=meta_style, alignment=TA_RIGHT)

        sig_elements = [Paragraph(f"Prepared By: <b>{creator.name}</b>", right_body_style), Spacer(1, 5)]
        if creator.digital_signature:
            try:
                sig_image = Image(io.BytesIO(creator.digital_signature), width=120, height=45)
                sig_image.hAlign = 'RIGHT'
                sig_elements.append(sig_image)
            except Exception as e:
                print(f"[PDF Engine Warning]: Failed to paste digital signature object: {e}")
        else:
            sig_elements.append(Spacer(1, 20))
        sig_elements.append(
            Paragraph("____________________________<br/>Authorized Signature", right_meta_style))
        story.append(KeepTogether(sig_elements))

        doc.build(story, onFirstPage=PDFGenerator._draw_footer, onLaterPages=PDFGenerator._draw_footer)
        return True

    @staticmethod
    def _build_due_payment_pdf(invoice: Invoice, output_path: str) -> bool:
        """Short 'Payment Receipt' layout for a due-payment record — no product items,
        just a statement that this is a payment against a prior sale's due balance."""
        root = invoice.root_invoice
        if root is None:
            raise ValueError(f"Due-payment #{invoice.id} has no linked original invoice.")

        customer = invoice.customer
        creator = invoice.creator

        # Amount already paid on the root BEFORE this particular payment (root's own paid
        # amount, plus every other due-payment that isn't this one).
        previously_paid = root.paid_amount + sum(
            dp.paid_amount for dp in root.due_payments if dp.id != invoice.id
        )
        remaining_due = root.effective_due_amount
        remaining_due_after = round(root.grand_total - (previously_paid + invoice.paid_amount), 2)
        final_status = "FULLY PAID" if remaining_due_after <= 0.001 else "PARTIALLY PAID — DUE REMAINS"
        status_color = cfg.STATUS_COLORS["paid"] if remaining_due_after <= 0.001 else cfg.STATUS_COLORS["due"]

        doc = SimpleDocTemplate(output_path, pagesize=letter, rightMargin=36,
                                leftMargin=36, topMargin=36, bottomMargin=50)
        story = []
        font_regular, _ = register_unicode_fonts()
        sym = f'<font face="{font_regular}">{cfg.CURRENCY_SYMBOL}</font>'
        styles = getSampleStyleSheet()
        meta_style = ParagraphStyle('MetaStyle', parent=styles['Normal'], fontSize=9,
                                    leading=12, textColor=colors.HexColor("#7f8c8d"))
        body_bold = ParagraphStyle('BodyBold', parent=styles['Normal'], fontSize=10,
                                   leading=14, fontName='Helvetica-Bold')
        note_style = ParagraphStyle('NoteStyle', parent=styles['Normal'], fontSize=9,
                                    leading=13, textColor=colors.HexColor("#34495e"))

        # 1. Header
        company_info = f"""<b>{cfg.COMPANY_NAME}</b><br/>
            {cfg.COMPANY_ADDRESS}<br/>
            Email: {cfg.COMPANY_EMAIL}<br/>
            Phone: {cfg.COMPANY_PHONE}
            """
        company_para = Paragraph(company_info, styles['Normal'])

        logo_img = None
        if cfg.COMPANY_LOGO_PATH:
            try:
                logo_img = Image(cfg.COMPANY_LOGO_PATH, width=70, height=70)
                logo_img.hAlign = 'LEFT'
            except Exception:
                logo_img = None

        if logo_img:
            company_block = Table([[logo_img, company_para]], colWidths=[80, 280])
            company_block.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ]))
        else:
            company_block = company_para

        receipt_meta = f"""<br/>
            <b>PAYMENT RECEIPT</b><br/>
            <b>Receipt ID:</b> #{invoice.id}<br/>
            <b>Against Invoice:</b> #{root.id}<br/>
            <b>Date:</b> {to_local_str(invoice.created_at)}
            """
        header_table = Table([[company_block, Paragraph(receipt_meta, styles['Normal'])]],
                             colWidths=[380, 160])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'LEFT'),
            ('BACKGROUND', (0, 0), (-1, -1), pstyle.hex_with_alpha(pstyle.COMPANY_INFO_BG)),
            ('PADDING', (0, 0), (-1, -1), 10),
        ]))
        story.append(header_table)
        story.append(Spacer(1, 20))

        # 2. Explanatory note — the key requirement: make clear this is a due-payment,
        # a continuation of the original sale, not a new product transaction.
        note_text = (
            f"This receipt records a payment received against the outstanding due balance of "
            f"<b>Invoice #{root.id}</b>, originally issued on <b>{to_local_str(root.created_at)}</b>. "
            f"It is a continuation of that sale and does not represent a new product transaction."
        )
        note_table = Table([[Paragraph(note_text, note_style)]], colWidths=[540])
        note_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), pstyle.hex_with_alpha(pstyle.CUSTOMER_INFO_BG)),
            ('PADDING', (0, 0), (-1, -1), 10),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ]))
        story.append(note_table)
        story.append(Spacer(1, 20))

        # 3. Bill To
        bill_to_info = f"""<b>RECEIVED FROM:</b><br/>
            <b>Name:</b> {customer.name}<br/>
            <b>Phone:</b> {customer.phone}<br/>
            <b>Email:</b> {customer.email if customer.email else 'N/A'}<br/>
            <b>Address:</b> {customer.address if customer.address else 'N/A'}
            """
        story.append(Paragraph(bill_to_info, styles['Normal']))
        story.append(Spacer(1, 20))

        # 4. Payment breakdown
        grid_data = [
            [Paragraph("<b>Original Invoice Grand Total</b>", styles['Normal']),
             Paragraph(f"{sym} {root.grand_total:,.2f}", styles['Normal'])],
            [Paragraph("<b>Previously Paid</b>", styles['Normal']),
             Paragraph(f"{sym} {previously_paid:,.2f}", styles['Normal'])],
            [Paragraph("<b>Amount Paid Now (this receipt)</b>", body_bold),
             Paragraph(f'<font color="{cfg.STATUS_COLORS["paid"]}"><b>{sym} {invoice.paid_amount:,.2f}</b></font>', body_bold)],
            [Paragraph("<b>Remaining Due After This Payment</b>", body_bold),
             Paragraph(f'<font color="{status_color}"><b>{sym} {remaining_due_after:,.2f}</b></font>', body_bold)],
        ]
        grid_table = Table(grid_data, colWidths=[340, 200])
        grid_table.setStyle(TableStyle([
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, pstyle.hex_with_alpha(pstyle.ITEMS_ALT_ROW_BG)]),
            ('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ('LINEABOVE', (0, -1), (-1, -1), 1.0, colors.HexColor("#1c2833")),
            ('BACKGROUND', (0, -1), (-1, -1), pstyle.hex_with_alpha(pstyle.PAYMENT_BLOCK_BG)),
        ]))
        story.append(grid_table)
        story.append(Spacer(1, 15))

        status_para = Paragraph(
            f'<b>Status:</b> <font color="{status_color}"><b>{final_status}</b></font>', styles['Normal']
        )
        story.append(status_para)
        story.append(Spacer(1, 25))

        # 5. Signature
        right_body_style = ParagraphStyle('RightBody', parent=styles['Normal'], alignment=TA_RIGHT)
        right_meta_style = ParagraphStyle('RightMeta', parent=meta_style, alignment=TA_RIGHT)

        sig_elements = [Paragraph(f"Received By: <b>{creator.name}</b>", right_body_style), Spacer(1, 5)]
        if creator.digital_signature:
            try:
                sig_image = Image(io.BytesIO(creator.digital_signature), width=120, height=45)
                sig_image.hAlign = 'RIGHT'
                sig_elements.append(sig_image)
            except Exception as e:
                print(f"[PDF Engine Warning]: Failed to paste digital signature object: {e}")
        else:
            sig_elements.append(Spacer(1, 20))
        sig_elements.append(
            Paragraph("____________________________<br/>Authorized Signature", right_meta_style))
        story.append(KeepTogether(sig_elements))

        doc.build(story, onFirstPage=PDFGenerator._draw_footer, onLaterPages=PDFGenerator._draw_footer)
        return True

    @staticmethod
    def _draw_footer(canvas, doc):
        """Fixed footer pinned to the bottom of every page, with a divider line above it."""
        footer_parts = []
        if cfg.COMPANY_WHATSAPP:
            footer_parts.append(f"WhatsApp: {cfg.COMPANY_WHATSAPP}")
        if cfg.COMPANY_WEBSITE:
            footer_parts.append(f"Web: {cfg.COMPANY_WEBSITE}")
        if cfg.COMPANY_FACEBOOK:
            footer_parts.append(f"Facebook: {cfg.COMPANY_FACEBOOK}")
        if not footer_parts:
            return

        canvas.saveState()
        page_width, _ = letter
        y = 28
        canvas.setStrokeColor(colors.HexColor("#cbd5e1"))
        canvas.setLineWidth(0.6)
        canvas.line(36, y + 14, page_width - 36, y + 14)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#7f8c8d"))
        canvas.drawCentredString(page_width / 2, y, "   |   ".join(footer_parts))
        canvas.restoreState()

    @staticmethod
    def generate_summary_pdf(records: list, output_path: str) -> bool:
        try:
            doc = SimpleDocTemplate(output_path, pagesize=letter, rightMargin=36, leftMargin=36,
                                    topMargin=36, bottomMargin=36)
            story = []
            font_regular, _ = register_unicode_fonts()
            sym = f'<font face="{font_regular}">{cfg.CURRENCY_SYMBOL}</font>'
            styles = getSampleStyleSheet()
            story.append(Paragraph("<b>Sales History Summary Ledger</b>", styles['Heading1']))
            story.append(Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
            story.append(Spacer(1, 15))

            grid_data = [[
                Paragraph("<b>Invoice ID</b>", styles['Normal']),
                Paragraph("<b>Customer Name</b>", styles['Normal']),
                Paragraph("<b>Date Logged</b>", styles['Normal']),
                Paragraph("<b>Discount</b>", styles['Normal']),
                Paragraph("<b>Grand Total</b>", styles['Normal']),
                Paragraph("<b>Due</b>", styles['Normal'])
            ]]

            total_sum, total_due = 0.0, 0.0
            for row in records:
                total_sum += row['grand_total']
                total_due += row['due']
                status_color = cfg.resolve_status_color(row.get('status', ''))
                grid_data.append([
                    Paragraph(f"#{row['id']}", styles['Normal']),
                    Paragraph(row['customer_name'], styles['Normal']),
                    Paragraph(row['date'], styles['Normal']),
                    Paragraph(f"{sym} {row['discount']:,.2f}", styles['Normal']),
                    Paragraph(f"{sym} {row['grand_total']:,.2f}", styles['Normal']),
                    Paragraph(f'<font color="{status_color}">{sym} {row["due"]:,.2f}</font>', styles['Normal'])
                ])

            grid_data.append(["", "", Paragraph("<b>Sum Total:</b>", styles['Normal']), "",
                              Paragraph(f"<b>{sym} {total_sum:,.2f}</b>", styles['Normal']),
                              Paragraph(f"<b>{sym} {total_due:,.2f}</b>", styles['Normal'])])

            summary_table = Table(grid_data, colWidths=[60, 140, 110, 90, 100, 90])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (3, 0), (5, -1), 'RIGHT'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                ('TOPPADDING', (0, 0), (-1, 0), 6),
                ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor("#f8f9fa")]),
                ('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ]))
            story.append(summary_table)
            doc.build(story)
            return True
        except Exception as e:
            print(f"[Critical Summary PDF Generation Error]: {e}")
            return False
# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _inherit = "account.move"

    is_credit_note_issued = fields.Boolean(
        "Credit Note Issued", compute="_compute_associated_credit_note")
    associated_credit_note_id = fields.Many2one(
        comodel_name='account.move', string='Associated Reverse Move',
        compute='_compute_associated_credit_note', readonly=False,
        inverse='_inverse_associated_credit_note',
    )
    reverse_move_type = fields.Char(compute='_compute_reverse_move_type')

    @api.depends('move_type')
    def _compute_reverse_move_type(self):
        reverse_move_type = {
            'in_refund': 'in_invoice',
            'in_invoice': 'in_refund',
            'out_refund': 'out_invoice',
            'out_invoice': 'out_refund',
            'out_receipt': 'in_receipt',
            'in_receipt': 'out_receipt',
            'entry': 'entry',
        }
        for record in self:
            record.reverse_move_type = reverse_move_type.get(record.move_type, 'entry')

    @api.depends('reversal_move_id', 'reversal_move_id.state')
    def _compute_associated_credit_note(self):
        for move in self:
            reverse_move = move.reversal_move_id.filtered(lambda m: m.state == 'posted')
            move.is_credit_note_issued = reverse_move and True or False
            move.associated_credit_note_id = reverse_move and reverse_move[0] or False

    def _inverse_associated_credit_note(self):
        for move in self:
            move.reversal_move_id = False
            move.associated_credit_note_id.reversed_entry_id = move

    def _validate_credit_note_with_invoice(self, invoice, credit_note):
        if invoice.partner_id != credit_note.partner_id:
            partner_type = 'Customer' if invoice.move_type in ('out_invoice', 'out_refund') else 'Vendor'
            raise ValidationError(_("'%s' and '%s' should share the same %s.") % (invoice.name, credit_note.name, partner_type))
        invoice_products = invoice.invoice_line_ids.mapped('product_id')
        credit_note_products = credit_note.invoice_line_ids.mapped('product_id')
        if not any(product in invoice_products for product in credit_note_products):
            raise ValidationError(_("'%s' and '%s' should share the same products or at least one.") % (credit_note.name, invoice.name))
        invoice_product_data = dict.fromkeys(invoice_products.ids, 0)
        credit_note_product_data = dict.fromkeys(credit_note_products.ids, 0)
        for invoice_line in invoice.invoice_line_ids:
            invoice_product_data[invoice_line.product_id.id] += invoice_line.quantity
        for credit_note_line in credit_note.invoice_line_ids:
            credit_note_product_data[credit_note_line.product_id.id] += credit_note_line.quantity
        for credit_note_product in credit_note_products:
            credit_note_qty = credit_note_product_data[credit_note_product.id]
            invoice_qty = invoice_product_data.get(credit_note_product.id, 0)
            if credit_note_product in invoice_products and credit_note_qty > invoice_qty:
                raise ValidationError(_("'%s' cannot have more quantities of the same product, '%s', than '%s'." % (
                    credit_note.name, credit_note_product.display_name, invoice.name)))
        return True

    @api.constrains('associated_credit_note_id', 'reversed_entry_id', 'invoice_line_ids', 'amount_total')
    def _check_associated_credit_note_id(self):
        for move in self.filtered(lambda m: m.move_type != 'entry' and (m.associated_credit_note_id or m.reversed_entry_id)):
            if move.move_type in ('in_invoice', 'out_invoice'):
                invoice, credit_note = move, move.associated_credit_note_id
            elif move.move_type in ('in_refund', 'out_refund'):
                invoice, credit_note = move.reversed_entry_id, move
            self._validate_credit_note_with_invoice(invoice, credit_note)
        return True

    def button_draft(self):
        # empty original "Invoice" from the credit note
        self.filtered('reversed_entry_id').write({
            'reversed_entry_id': False,
        })
        # reset linked credit note to the invoice
        credit_notes = self.mapped('associated_credit_note_id')
        if credit_notes:
            credit_notes.button_draft()
        return super().button_draft()

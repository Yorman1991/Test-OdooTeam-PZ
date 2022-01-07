# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, _
from odoo.exceptions import UserError


class AccountBankStatementLine(models.AbstractModel):
    _inherit = "account.bank.statement.line"

    reconcile_move_id = fields.Many2one(
        comodel_name='account.move', string='Reconcile Journal Entry',)

    def _seek_for_lines(self):
        ''' Helper used to dispatch the journal items between:
        - The lines using the liquidity account.
        - The lines using the transfer account.
        - The lines being not in one of the two previous categories.
        :return: (liquidity_lines, suspense_lines, other_lines)
        '''
        liquidity_lines = self.env['account.move.line']
        suspense_lines = self.env['account.move.line']
        other_lines = self.env['account.move.line']

        # Custom code start 2022-01-06
        line_ids = self.move_id.line_ids
        if self.env.context.get('reconcile_move_id', False):
            line_ids = self.reconcile_move_id.line_ids
        # Custom code stop 2022-01-06

        for line in line_ids:
            if line.account_id == self.journal_id.default_account_id:
                liquidity_lines += line
            elif line.account_id == self.journal_id.suspense_account_id:
                suspense_lines += line
            else:
                other_lines += line
        return liquidity_lines, suspense_lines, other_lines

    def reconcile(self, lines_vals_list, to_check=False):
        ''' Perform a reconciliation on the current account.bank.statement.line with some
        counterpart account.move.line.
        If the statement line entry is not fully balanced after the reconciliation, an open balance will be created
        using the partner.

        :param lines_vals_list: A list of python dictionary containing:
            'id':               Optional id of an existing account.move.line.
                                For each line having an 'id', a new line will be created in the current statement line.
            'balance':          Optional amount to consider during the reconciliation. If a foreign currency is set on the
                                counterpart line in the same foreign currency as the statement line, then this amount is
                                considered as the amount in foreign currency. If not specified, the full balance is taken.
                                This value must be provided if 'id' is not.
            **kwargs:           Custom values to be set on the newly created account.move.line.
        :param to_check:        Mark the current statement line as "to_check" (see field for more details).
        '''
        self.ensure_one()
        # Custom code start 2022-01-06
        # Create reconcile move for do not change suspense account entry.
        self.reconcile_move_id = self.move_id.copy()
        self.reconcile_move_id.partner_id = self.move_id.partner_id
        self.reconcile_move_id.action_post()
        # Pass the reconcile move in context to get account move lines from
        # the reconcile move
        liquidity_lines, suspense_lines, other_lines = self.with_context(reconcile_move_id=True)._seek_for_lines()
        # Custom code stop 2022-01-06

        reconciliation_overview, open_balance_vals = self._prepare_reconciliation(lines_vals_list)

        # ==== Manage res.partner.bank ====

        if self.account_number and self.partner_id and not self.partner_bank_id:
            self.partner_bank_id = self._find_or_create_bank_account()

        # ==== Check open balance ====

        if open_balance_vals:
            if not open_balance_vals.get('partner_id'):
                raise UserError(_("Unable to create an open balance for a statement line without a partner set."))
            if not open_balance_vals.get('account_id'):
                raise UserError(_("Unable to create an open balance for a statement line because the receivable "
                                  "/ payable accounts are missing on the partner."))

        # ==== Create & reconcile payments ====
        # When reconciling to a receivable/payable account, create an payment on the fly.

        pay_reconciliation_overview = [reconciliation_vals
                                       for reconciliation_vals in reconciliation_overview
                                       if reconciliation_vals.get('payment_vals')]
        if pay_reconciliation_overview:
            payment_vals_list = [reconciliation_vals['payment_vals'] for reconciliation_vals in pay_reconciliation_overview]
            payments = self.env['account.payment'].create(payment_vals_list)

            payments.action_post()

            for reconciliation_vals, payment in zip(pay_reconciliation_overview, payments):
                reconciliation_vals['payment'] = payment

                # Reconcile the newly created payment with the counterpart line.
                (reconciliation_vals['counterpart_line'] + payment.line_ids)\
                    .filtered(lambda line: line.account_id == reconciliation_vals['counterpart_line'].account_id)\
                    .reconcile()

        # ==== Create & reconcile lines on the bank statement line ====

        to_create_commands = [(0, 0, open_balance_vals)] if open_balance_vals else []
        to_update_commands = [(1, line.id, {'credit': line.debit, 'debit': line.credit, 'amount_currency': line.amount_currency * -1 }) for line in suspense_lines]
        to_delete_commands = [(2, line.id) for line in liquidity_lines + other_lines]

        # Cleanup previous lines.
        # Custom code start 2022-01-06
        self.reconcile_move_id.with_context(check_move_validity=False, skip_account_move_synchronization=True, force_delete=True).write({
            'line_ids': to_delete_commands + to_update_commands + to_create_commands,
            'to_check': to_check,
        })
        # Custom code stop 2022-01-06

        line_vals_list = [reconciliation_vals['line_vals'] for reconciliation_vals in reconciliation_overview]
        # Custom code start 2022-01-06
        # Update the move id to reconcile move id.
        new_line_vals_list = line_vals_list.copy()
        for line in new_line_vals_list:
            line.update(move_id=self.reconcile_move_id.id)
        new_lines = self.env['account.move.line'].create(new_line_vals_list)
        # Custom code stop 2022-01-06
        new_lines = new_lines.with_context(skip_account_move_synchronization=True)
        for reconciliation_vals, line in zip(reconciliation_overview, new_lines):
            if reconciliation_vals.get('payment'):
                accounts = (self.journal_id.payment_debit_account_id, self.journal_id.payment_credit_account_id)
                counterpart_line = reconciliation_vals['payment'].line_ids.filtered(lambda line: line.account_id in accounts)
            elif reconciliation_vals.get('counterpart_line'):
                counterpart_line = reconciliation_vals['counterpart_line']
            else:
                continue

            (line + counterpart_line).reconcile()

        # Custom code start 2022-01-06
        # reconcile the suspense account line between bank statement's move id
        # and reconcile move id. to make the invoice paid.
        suspense_move_lines = self.move_id.line_ids.filtered(
            lambda line: line.account_id == self.journal_id.suspense_account_id)
        suspense_move_lines += self.reconcile_move_id.line_ids.filtered(
            lambda line: line.account_id == self.journal_id.suspense_account_id)
        # now reconcile each move lines
        suspense_move_lines.reconcile()
        # Custom code stop 2022-01-06

        # Assign partner if needed (for example, when reconciling a statement
        # line with no partner, with an invoice; assign the partner of this invoice)
        if not self.partner_id:
            rec_overview_partners = set(overview['counterpart_line'].partner_id.id
                                        for overview in reconciliation_overview
                                        if overview.get('counterpart_line') and overview['counterpart_line'].partner_id)
            if len(rec_overview_partners) == 1:
                self.line_ids.write({'partner_id': rec_overview_partners.pop()})

        # Refresh analytic lines.
        # Custom code start 2022-01-06
        self.reconcile_move_id.line_ids.analytic_line_ids.unlink()
        self.reconcile_move_id.line_ids.create_analytic_lines()
        # Custom code stop 2022-01-06

    def button_undo_reconciliation(self):
        super().button_undo_reconciliation()
        suspense_move_lines = self.move_id.line_ids.filtered(
            lambda line: line.account_id == self.journal_id.suspense_account_id)
        suspense_move_lines += self.reconcile_move_id.line_ids.filtered(
            lambda line: line.account_id == self.journal_id.suspense_account_id)
        suspense_move_lines.remove_move_reconcile()
        self.reconcile_move_id.button_draft()
        self.reconcile_move_id.button_cancel()

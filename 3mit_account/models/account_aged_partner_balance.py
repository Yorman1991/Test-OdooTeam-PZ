# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _



class MitReportAccountAgedPartner(models.AbstractModel):
    _name = 'mit.account.aged.partner'
    _inherit = "account.aged.partner"


class MitReportAccountAgedPayable(models.Model):
    _name = "mit.account.aged.payable"
    _description = "Aged Payable"
    _inherit = ["mit.account.aged.partner", "account.aged.payable"]

    @api.model
    def _get_options_domain(self, options):
        domain = super(MitReportAccountAgedPayable, self)._get_options_domain(options)
        user_type_id = self.env.ref('3mit_account.account_type_credit_note', raise_if_not_found=False)
        if user_type_id:
            domain += [
                ('account_id.user_type_id', '!=', user_type_id.id),
            ]
        return domain


class MitReportAccountPayableCreditNote(models.Model):
    _name = "mit.account.aged.payable.credit.note"
    _description = "Payable Credit Note"
    _inherit = "mit.account.aged.partner"
    _auto = False

    @api.model
    def _get_options(self, previous_options=None):
        # OVERRIDE
        options = super(MitReportAccountPayableCreditNote, self)._get_options(previous_options=previous_options)
        options['filter_account_type'] = 'payable'
        return options

    @api.model
    def _get_options_domain(self, options):
        domain = super()._get_options_domain(options)
        user_type_id = self.env.ref('3mit_account.account_type_credit_note', raise_if_not_found=False)
        if user_type_id:
            domain += [
                ('account_id.user_type_id', '=', user_type_id.id),
            ]
        return domain

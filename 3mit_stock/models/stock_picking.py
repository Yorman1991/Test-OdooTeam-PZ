# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class PickingType(models.Model):
    _inherit = "stock.picking.type"

    mit_movement_type_ids = fields.One2many(
        comodel_name='stock.picking', inverse_name='movement_type_id',
        string='Movement types')



class Picking(models.Model):
    _inherit = "stock.picking"

    movement_type_id = fields.Many2one(
        comodel_name='stock.picking.type', string="Movement Type", tracking=True)

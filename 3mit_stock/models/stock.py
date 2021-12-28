# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class StockPickingTags(models.Model):
    _name = 'mit.stock.picking.tag'
    _description = 'Movement Types'

    name = fields.Char(required=True, translate=True)
    picking_type_id = fields.Many2one(
        'stock.picking.type', string="Operation Types")
    picking_ids = fields.One2many(
        'stock.picking', 'mit_tag_id', string='Pickings')


class PickingType(models.Model):
    _inherit = "stock.picking.type"

    mit_tag_ids = fields.One2many(
        'mit.stock.picking.tag', 'picking_type_id',
        string='Movement Types')


class Picking(models.Model):
    _inherit = "stock.picking"

    mit_tag_id = fields.Many2one(
        'mit.stock.picking.tag', string="Movement Type", tracking=True)


class StockMove(models.Model):
    _inherit = 'stock.move.line'

    mit_tag_id = fields.Many2one(
        'mit.stock.picking.tag',
        related="picking_id.mit_tag_id",
        string="Movement Type")

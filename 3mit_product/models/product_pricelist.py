# -*- coding: utf-8 -*-

from odoo import api, models, fields, _
from odoo.tools.misc import format_date


class Pricelist(models.Model):
    _name = "product.pricelist"
    _inherit = ['product.pricelist', 'mail.thread', 'mail.activity.mixin']

    company_id = fields.Many2one(
        'res.company', tracking=True)
    country_group_ids = fields.Many2many(
        'res.country.group', 'res_country_group_pricelist_rel',
        'pricelist_id', 'res_country_group_id', string='Country Groups',
        tracking=True)
    discount_policy = fields.Selection(tracking=True)
    item_ids = fields.One2many(
        'product.pricelist.item', 'pricelist_id', string='Pricelist Items',
        tracking=True)

    @api.model
    def _field_will_change(self, record, vals, field_name):
        if field_name not in vals:
            return False
        field = record._fields[field_name]
        if field.type == 'many2one':
            return record[field_name].id != vals[field_name]
        if field.type == 'many2many':
            current_ids = set(record[field_name].ids)
            after_write_ids = set(record.new({field_name: vals[field_name]})[field_name].ids)
            return current_ids != after_write_ids
        if field.type == 'one2many':
            return True
        if field.type == 'monetary' and record[field.currency_field]:
            return not record[field.currency_field].is_zero(record[field_name] - vals[field_name])
        if field.type == 'float':
            record_value = field.convert_to_cache(record[field_name], record)
            to_write_value = field.convert_to_cache(vals[field_name], record)
            return record_value != to_write_value
        return record[field_name] != vals[field_name]

    @api.model
    def _cleanup_write_orm_values(self, record, vals):
        cleaned_vals = dict(vals)
        for field_name, value in vals.items():
            if not self._field_will_change(record, vals, field_name):
                del cleaned_vals[field_name]
        return cleaned_vals

    def _get_tracking_field_string(self, fields):
        msg = ''
        for field in fields:
            if field.get('error', False):
                msg += field['field_error'] + ': '
                if field['old_item_name']:
                    msg += "<div class='pl-4'>Deleted: %s</div>" % field['old_item_name']
                if field['new_item_name']:
                    msg += "<div class='pl-4'>Added: %s</div>" % field['new_item_name']
        return msg

    def write(self, vals):
        # Get all many2many tracked fields (without related fields because these fields must be manage on their own model)
        tracking_fields = []
        for value in vals:
            field = self._fields[value]
            if hasattr(field, 'related') and field.related:
                continue # We don't want to track related field.
            if hasattr(field, 'tracking') and field.tracking and field.type in ['many2many', 'one2many']:
                tracking_fields.append(value)

        if tracking_fields:
            ref_fields = self.fields_get(tracking_fields)
            item_initial_values = {}
            for pricelist in self:
                for field in tracking_fields:
                    # Group initial values by pricelist
                    if pricelist.id not in item_initial_values:
                        item_initial_values[pricelist.id] = {}
                    x2m_records = pricelist[field]
                    item_initial_values[pricelist.id].update({
                        field: x2m_records,
                        field + '_name': {record.id: record.display_name for record in x2m_records},
                    })

            result = True
            for record in self:
                cleaned_vals = record._cleanup_write_orm_values(record, vals)
                if not cleaned_vals:
                    continue
                # To saved changed fields value.
                result |= super(Pricelist, record).write(cleaned_vals)

            tracking_values = {}  # Tracking values to write in the message post
            for pricelist_id, modified_items in item_initial_values.items():
                tmp_pricelist = {pricelist_id: []}
                for pricelist in self.filtered(lambda pl: pl.id == pricelist_id):
                    changes, tracking_value_ids = pricelist._mail_track(ref_fields, modified_items)  # Return a tuple like (changed field, ORM command)
                    if changes:
                        for change in changes:
                            field_name = pricelist._fields[change].string  # Get the field name
                            old_item_ids = set(modified_items.get(change).ids)
                            items_added = [item.display_name for item in self[change] if item.id not in old_item_ids]
                            items_removed = [modified_items[change+'_name'].get(item_id) for item_id in old_item_ids if item_id not in self[change].ids]
                            tmp_pricelist[pricelist_id].append({
                                'item_id': pricelist.id,
                                'error': True,
                                'field_error': field_name,
                                'new_item_name': ', '.join(items_added) or '',
                                'old_item_name': ', '.join(items_removed) or '',
                            })
                    else:
                        continue
                if len(tmp_pricelist[pricelist_id]) > 0:
                    tracking_values.update(tmp_pricelist)
            # Write in the chatter for many2many.
            for record in self:
                tracking_fields = tracking_values.get(record.id, [])
                if len(tracking_fields) > 0:
                    msg = self._get_tracking_field_string(tracking_values.get(record.id))
                    pricelist_update_date = fields.Datetime.context_timestamp(record, record.write_date)
                    msg += '<div class="o_Message_date o_Message_headerDate">%s</div>' % fields.Datetime.to_string(pricelist_update_date)
                    record.message_post(body=msg)
        else:
            result = super(Pricelist, self).write(vals)

        return result


class PricelistItem(models.Model):
    _inherit = "product.pricelist.item"

    product_tmpl_id = fields.Many2one(
        'product.template', tracking=True)
    product_id = fields.Many2one(
        'product.product', tracking=True)
    applied_on = fields.Selection(tracking=True)
    base = fields.Selection(tracking=True)
    price_surcharge = fields.Float(tracking=True)
    price_discount = fields.Float(tracking=True)
    price_round = fields.Float(tracking=True)
    price_min_margin = fields.Float(tracking=True)
    price_max_margin = fields.Float(tracking=True)
    company_id = fields.Many2one(
        'res.company', tracking=True)
    date_start = fields.Datetime(tracking=True)
    date_end = fields.Datetime(tracking=True)
    compute_price = fields.Selection(tracking=True)
    fixed_price = fields.Float(tracking=True)
    percent_price = fields.Float(tracking=True)
    price = fields.Char(tracking=True)

    def _get_formated_values(self, tracked_field):
        if tracked_field.get('field_type') in ('date', 'datetime'):
            return {
                'old_value': format_date(self.env, fields.Datetime.from_string(tracked_field.get('old_value_datetime'))),
                'new_value': format_date(self.env, fields.Datetime.from_string(tracked_field.get('new_value_datetime'))),
            }
        elif tracked_field.get('field_type') == 'many2one':
            return {
                'old_value': tracked_field.get('old_value_char', ''),
                'new_value': tracked_field.get('new_value_char', '')
            }
        else:
            return {
                'old_value': [val for key, val in tracked_field.items() if 'old_value' in key][0], # Get the first element because we create a list like ['Elem']
                'new_value': [val for key, val in tracked_field.items() if 'new_value' in key][0], # Get the first element because we create a list like ['Elem']
            }

    def _get_tracking_field_string(self, fields):
        item_name = fields[0].get('item_name', '')
        item = fields[0]
        redirect_link = '<a href=# data-oe-model=product.pricelist.item data-oe-id=%d>#%d</a>' % (item['item_id'], item['item_id']) # Pricelist item link
        ARROW_RIGHT = '<div class="o_Message_trackingValueSeparator o_Message_trackingValueItem fa fa-long-arrow-right" title="Changed" role="img"/>'
        msg = '<div class="o_Message_prettyBody"><p>%s (%s)</p></div>' % (item['item_name'], redirect_link)
        msg += '<ul>'
        for field in fields:
            msg += '<li>%s: %s %s %s</li>' % (field['field_name'], field['old_value'], ARROW_RIGHT, field['new_value'])
        msg += '</ul>'
        return msg

    def _valid_field_parameter(self, field, name):
        # I can't even
        return name == 'tracking' or super()._valid_field_parameter(field, name)

    def write(self, vals):
        # Get all tracked fields (without related fields because these fields must be manage on their own model)
        tracking_fields = []
        for value in vals:
            field = self._fields[value]
            if hasattr(field, 'related') and field.related:
                continue # We don't want to track related field.
            if hasattr(field, 'tracking') and field.tracking and field.type not in ['many2many', 'one2many']:
                tracking_fields.append(value)
        ref_fields = self.fields_get(tracking_fields)
        # Get initial values for each pricelist item.
        item_initial_values = {}
        for item in self:
            for field in tracking_fields:
                # Group initial values by move_id
                if item.pricelist_id.id not in item_initial_values:
                    item_initial_values[item.pricelist_id.id] = {}
                item_initial_values[item.pricelist_id.id].update({field: item[field]})

        result = True
        for item in self:
            cleaned_vals = item.pricelist_id._cleanup_write_orm_values(item, vals)
            if not cleaned_vals:
                continue
            result |= super(PricelistItem, item).write(cleaned_vals)

        tracking_values = {}  # Tracking values to write in the message post
        for pricelist_id, modified_items in item_initial_values.items():
            tmp_pricelist = {pricelist_id: []}
            for item in self.filtered(lambda l: l.pricelist_id.id == pricelist_id):
                changes, tracking_value_ids = item._mail_track(ref_fields, modified_items)  # Return a tuple like (changed field, ORM command)
                if tracking_value_ids:
                    for value in tracking_value_ids:
                        selected_field = value[2]  # Get the last element of the tuple in the list of ORM command. (changed, [(0, 0, THIS)])
                        tmp_pricelist[pricelist_id].append({
                            'item_id': item.id,
                            'item_name': item.display_name,
                            **{'field_name': selected_field.get('field_desc')},
                            **self._get_formated_values(selected_field)
                        })
                else:
                    continue
            if len(tmp_pricelist[pricelist_id]) > 0:
                tracking_values.update(tmp_pricelist)

        # Write in the chatter.
        for pricelist in self.mapped('pricelist_id'):
            tracking_fields = tracking_values.get(pricelist.id, [])
            if len(tracking_fields) > 0:
                msg = self._get_tracking_field_string(tracking_values.get(pricelist.id))
                pricelist_update_date = fields.Datetime.context_timestamp(pricelist, pricelist.write_date)
                msg += '<div class="o_Message_date o_Message_headerDate">%s</div>' % fields.Datetime.to_string(pricelist_update_date)
                pricelist.message_post(body=msg)

        return result

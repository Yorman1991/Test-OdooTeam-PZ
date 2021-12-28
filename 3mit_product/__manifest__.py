# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    #  Information
    'name': '3MIT Pricelist Extension',
    'version': '14.0.1.0.0',
    'summary': 'Add chatter for Pricelist.',
    'description': """
""",
    'category': 'Customization/product',

    # Author
    'author': 'Odoo',
    'website': 'https://www.odoo.com/',

    # Dependency
    'depends': ['product'],
    'data': [
        'views/product_pricelist_views.xml',
    ],

    # Other
    'installable': True,

    'license': 'LGPL-3',
}



# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    #  Information
    'name': '3MIT Stock Extension',
    'version': '14.0.1.0.0',
    'summary': 'Add mapping between picking and its type.',
    'description': """
""",
    'category': 'Customization/stock',

    # Author
    'author': 'Odoo',
    'website': 'https://www.odoo.com/',

    # Dependency
    'depends': ['stock'],
    'data': [
        'views/stock_picking_views.xml',
    ],

    # Other
    'installable': True,

    'license': 'LGPL-3',
}



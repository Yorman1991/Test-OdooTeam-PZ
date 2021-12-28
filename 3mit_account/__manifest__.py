# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    #  Information
    'name': '3MIT Account Extension',
    'version': '14.0.1.1.0',
    'summary': '',
    'description': """
""",
    'category': 'Customization/account',

    # Author
    'author': 'Odoo',
    'website': 'https://www.odoo.com/',

    # Dependency
    'depends': ['account_reports'],
    'data': [
        'data/3mit_chart_data.xml',
        'data/account_financial_report_data.xml',
        'security/ir.model.access.csv',
        'views/account_move_views.xml',
    ],

    # Other
    'installable': True,

    'license': 'LGPL-3',
}

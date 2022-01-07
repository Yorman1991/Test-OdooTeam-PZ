# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    #  Information
    'name': '3MIT Accounting Extension',
    'version': '14.0.1.0.0',
    'summary': '',
    'description': """
""",
    'category': 'Customization/account',

    # Author
    'author': 'Odoo',
    'website': 'https://www.odoo.com/',

    # Dependency
    'depends': ['account_accountant'],
    'data': [
        'views/account_bank_statement_views.xml',
    ],

    # Other
    'installable': True,

    'license': 'LGPL-3',
}

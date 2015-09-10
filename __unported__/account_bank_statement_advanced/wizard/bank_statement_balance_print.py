# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#
#    Copyright (c) 2014-2015 Noviat nv/sa (www.noviat.com).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import time
from datetime import datetime

from openerp.osv import fields, orm
from openerp.tools.translate import _
from openerp.addons import decimal_precision as dp

class bank_statement_balance_print(orm.TransientModel):
    _name = 'bank.statement.balance.print'
    _description = 'Bank Statement Balances Report'

    def _get_journals(self, cr, uid, context=None):
        return self.pool.get('account.journal').search(cr, uid,
            [('type', '=', 'bank')]
        )

    _columns = {
        'journal_ids': fields.many2many(
        'account.journal', string='Financial Journal(s)',
        domain=[('type', '=', 'bank')],
        help="Select here the Financial Journal(s) you want to include "
             "in your Bank Statement Balances Report."),
        'date_balance': fields.date(
        string='Date', required=True, default=time.strftime('%Y-%m-%d')),
    }
    _defaults = {
        'journal_ids': _get_journals,
    }

    #V8 to V7
    # @api.multi
    # def balance_print(self):
    #     return self.env['report'].get_action(
    #         self, 'account_bank_statement_advanced.report_statement_balances')

    def balance_print(self, cr, uid, ids, data, context=None):
        return {'type': 'ir.actions.report.xml',
                'report_name': 'account_bank_statement_advanced.report_statement_balances',
                'datas': data}

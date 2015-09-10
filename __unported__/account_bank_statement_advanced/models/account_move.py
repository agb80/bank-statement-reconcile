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

import logging
_logger = logging.getLogger(__name__)

#V8 to V7
# from openerp import models, fields, api, _
# from openerp.exceptions import Warning

from openerp.osv import orm, fields
from openerp.tools.translate import _
from openerp.addons import decimal_precision as dp

# class AccountMove(models.Model):
#     _inherit = 'account.move'

#     @api.multi
#     def button_cancel(self):
#         for move in self:
#             for move_line in move.line_id:
#                 st = move_line.statement_id
#                 if st and st.state == 'confirm':
#                     raise Warning(
#                         _("Operation not allowed ! "
#                           "\nYou cannot unpost an Accounting Entry "
#                           "that is linked to a Confirmed Bank Statement."))
#         return super(AccountMove, self).button_cancel()


class AccountMove(orm.Model):
    _inherit = 'account.move'

    def button_cancel(self, cr, uid, ids, context=None):
        if context is None: context = {}
        for move in self.browse(cr, uid, ids, context=context):
            for move_line in move.line_id:
                st = move_line.statement_id
                if st and st.state == 'confirm':
                    raise orm.except_orm(
                        _("Operation not allowed ! "
                          "\nYou cannot unpost an Accounting Entry "
                          "that is linked to a Confirmed Bank Statement."))
        return super(AccountMove, self).button_cancel(cr, uid, ids, context=context)


# class AccountMoveLine(models.Model):
#     _inherit = 'account.move.line'

#     move_state = fields.Selection(
#         related='move_id.state', string='Move State',
#         readonly=True)

#     @api.onchange('tax_code_id')
#     def _onchange_tax_code(self):
#         if self.tax_code_id and self.debit or self.credit:
#                 self.tax_amount = self.debit or self.credit or False
#         else:
#             self.tax_amount = False

#     @api.model
#     def fields_view_get(self, view_id=None, view_type='form',
#                         toolbar=False, submenu=False):
#         ctx = self._context.copy()
#         if ctx.get('act_window_from_bank_statement'):
#             if view_type == 'tree':
#                 view_id = self.env.ref(
#                     'account_bank_statement_advanced.'
#                     'view_move_line_reconcile_tree').id
#                 ctx.update({'view_mode': 'tree'})
#             elif view_type == 'search':
#                 view_id = self.env.ref(
#                     'account_bank_statement_advanced.'
#                     'view_move_line_reconcile_search').id
#                 ctx.update({'view_mode': 'search'})
#         return super(
#             AccountMoveLine, self.with_context(ctx)).fields_view_get(
#                 view_id=view_id, view_type=view_type,
#                 toolbar=toolbar, submenu=submenu)

#     def unlink(self, cr, uid, ids, context=None, check=True):
#         for move_line in self.browse(cr, uid, ids, context):
#             st = move_line.statement_id
#             if st and st.state == 'confirm':
#                 raise Warning(
#                     _("Operation not allowed ! "
#                       "\nYou cannot delete an Accounting Entry "
#                       "that is linked to a Confirmed Bank Statement."))
#         return super(AccountMoveLine, self).unlink(
#             cr, uid, ids, context=context, check=check)

#     def write(self, cr, uid, ids, vals, context=None,
#               check=True, update_check=True):
#         for move_line in self.browse(cr, uid, ids, context):
#             st = move_line.statement_id
#             if st and st.state == 'confirm':
#                 if vals.keys() not in [
#                         ['reconcile_id'], ['reconcile_partial_id']]:
#                     raise Warning(
#                         _("Operation not allowed ! "
#                           "\nYou cannot modify an Accounting Entry "
#                           "that is linked to a Confirmed Bank Statement. "
#                           "\nStatement = %s"
#                           "\nMove = %s (id:%s)\nUpdate Values = %s")
#                         % (st.name, move_line.move_id.name,
#                            move_line.move_id.id, vals))
#         return super(AccountMoveLine, self).write(
#             cr, uid, ids, vals, context, check, update_check)

class AccountMoveLine(orm.Model):
    _inherit = 'account.move.line'

    move_state = fields.related('move_id','state', type='selection', 
        string='Move State', readonly=True)

    def _onchange_tax_code(self, cr, uid, ids, tax_code_id, 
        debit, credit, context=None):
        res = {"value":{}}
        tax_amount = 0.00
        if context is None: context = {}
        if tax_code_id and debit or credit:
            tax_amount = debit or credit or False
        else:
            tax_amount = 0.00
        res["value"]["tax_amount"] = tax_amount
        return res

    def fields_view_get(self, cr, uid, view_id=None, view_type='form',
                        toolbar=False, submenu=False, context=None):
        ctx = context.copy()
        if ctx.get('act_window_from_bank_statement'):
            if view_type == 'tree':
                view_id = self.env.ref(
                    'account_bank_statement_advanced.'
                    'view_move_line_reconcile_tree').id
                ctx.update({'view_mode': 'tree'})
            elif view_type == 'search':
                #FIXME
                view_id = self.env.ref(
                    'account_bank_statement_advanced.'
                    'view_move_line_reconcile_search').id
                ctx.update({'view_mode': 'search'})
        return super(
            AccountMoveLine, self.with_context(ctx)).fields_view_get(cr, uid,
                view_id=view_id, view_type=view_type,
                toolbar=toolbar, submenu=submenu, context=context)

    def unlink(self, cr, uid, ids, context=None, check=True):
        for move_line in self.browse(cr, uid, ids, context):
            st = move_line.statement_id
            if st and st.state == 'confirm':
                raise Warning(
                    _("Operation not allowed ! "
                      "\nYou cannot delete an Accounting Entry "
                      "that is linked to a Confirmed Bank Statement."))
        return super(AccountMoveLine, self).unlink(
            cr, uid, ids, context=context, check=check)

    def write(self, cr, uid, ids, vals, context=None,
              check=True, update_check=True):
        for move_line in self.browse(cr, uid, ids, context):
            st = move_line.statement_id
            if st and st.state == 'confirm':
                if vals.keys() not in [
                        ['reconcile_id'], ['reconcile_partial_id']]:
                    raise orm.except_orm(
                        _("Operation not allowed ! "
                          "\nYou cannot modify an Accounting Entry "
                          "that is linked to a Confirmed Bank Statement. "
                          "\nStatement = %s"
                          "\nMove = %s (id:%s)\nUpdate Values = %s")
                        % (st.name, move_line.move_id.name,
                           move_line.move_id.id, vals))
        return super(AccountMoveLine, self).write(
            cr, uid, ids, vals, context, check, update_check)
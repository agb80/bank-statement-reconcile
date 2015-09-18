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

import pickle
import logging
_logger = logging.getLogger(__name__)

#V8 to V7
# from openerp import models, fields, api, _
# import openerp.addons.decimal_precision as dp
# from openerp.exceptions import Warning

from openerp.osv import orm, fields
from openerp.tools.translate import _
from openerp.addons import decimal_precision as dp



# class AccountBankStatementLineGlobal(models.Model):
#     _name = 'account.bank.statement.line.global'
#     _description = 'Batch Payment Info'
#     _rec_name = 'code'

#     name = fields.Char(
#         string='OBI', required=True, default='/',
#         help="Originator to Beneficiary Information")
#     code = fields.Char(
#         string='Code', required=True,
#         default=lambda self: self.env['ir.sequence'].get(
#             'account.bank.statement.line.global'))
#     parent_id = fields.Many2one(
#         'account.bank.statement.line.global',
#         string='Parent Code', ondelete='cascade')
#     child_ids = fields.One2many(
#         'account.bank.statement.line.global', 'parent_id',
#         string='Child Codes')
#     type = fields.Selection([
#         ('iso20022', 'ISO 20022'),
#         ('coda', 'CODA'),
#         ('manual', 'Manual'),
#         ], string='Type', required=True)
#     amount = fields.Float(
#         string='Amount',
#         digits_compute=dp.get_precision('Account'))
#     payment_reference = fields.Char(
#         string='Payment Reference',
#         help="Payment Reference. For SEPA (SCT or SDD) transactions, "
#              "the PaymentInformationIdentification "
#              "is recorded in this field.")
#     bank_statement_line_ids = fields.One2many(
#         'account.bank.statement.line', 'globalisation_id',
#         string='Bank Statement Lines')

#     _sql_constraints = [
#         ('code_uniq', 'unique (code)', 'The code must be unique !'),
#     ]


class AccountBankStatementLineGlobal(orm.Model):
    _name = 'account.bank.statement.line.global'
    _description = 'Batch Payment Info'
    _rec_name = 'code'

    _columns = {

        'name': fields.char(
                    string='OBI', required=True, default='/',
                    help="Originator to Beneficiary Information"
                ),
        'code': fields.char(string='Code', required=True),
        'parent_id': fields.many2one(
            'account.bank.statement.line.global',
            string='Parent Code', ondelete='cascade'),
        'child_ids': fields.one2many(
            'account.bank.statement.line.global', 'parent_id',
            string='Child Codes'),
        'type': fields.selection([
            ('iso20022', 'ISO 20022'),
            ('coda', 'CODA'),
            ('manual', 'Manual'),
            ], string='Type', required=True),
        'amount': fields.float(
            string='Amount',
            digits_compute=dp.get_precision('Account')),
        'payment_reference': fields.char(
            string='Payment Reference',
            help="Payment Reference. For SEPA (SCT or SDD) transactions, "
                 "the PaymentInformationIdentification "
                 "is recorded in this field."),
        'bank_statement_line_ids': fields.one2many(
            'account.bank.statement.line', 'globalisation_id',
            string='Bank Statement Lines'),
    }

    _defaults = {
        'code': lambda self,cr,uid,context={}: self.pool.get('ir.sequence').get(
                    cr, uid, 'account.bank.statement.line.global'
                ),
    }

    # _sql_constraints = [
    #     ('code_uniq', 'unique (code)', 'The code must be unique !'),
    # ]

    # @api.model
    # def name_search(self, name, args=None, operator='ilike', limit=100):
    #     args = args or []
    #     if name:
    #         recs = self.search([('code', '=ilike', name)] + args, limit=limit)
    #         if not recs:
    #             recs = self.search(
    #                 [('name', operator, name)] + args, limit=limit)
    #         if not recs and len(name.split()) >= 2:
    #             # Separating code and name for searching
    #             # name can contain spaces
    #             operand1, operand2 = name.split(' ', 1)
    #             recs = self.search([
    #                 ('code', '=like', operand1), ('name', operator, operand2)
    #                 ] + args, limit=limit)
    #     else:
    #         recs = self.browse()
    #     return recs.name_get()

    def name_search(self, cr, user, name, args=None, operator='ilike',
        context=None, limit=100):
        args = args or []
        if name:
            recs = self.search(cr, uid, [('code', '=ilike', name)] + args, limit=limit)
            if not recs:
                recs = self.search(cr, uid,
                    [('name', operator, name)] + args, limit=limit)
            if not recs and len(name.split()) >= 2:
                # Separating code and name for searching
                # name can contain spaces
                operand1, operand2 = name.split(' ', 1)
                recs = self.search(cr, uid, [
                    ('code', '=like', operand1),
                    ('name', operator, operand2)
                ] + args, limit=limit)
        else:
            recs = self.browse(cr, uid, ids, context=context)


# class AccountBankStatement(models.Model):
#     _inherit = 'account.bank.statement'

#     fiscalyear_id = fields.Many2one(
#         string='Fiscal Year', related='period_id.fiscalyear_id',
#         store=True, readonly=True)
#     all_lines_reconciled = fields.Boolean(compute='_all_lines_reconciled')


class AccountBankStatement(orm.Model):
    _inherit = 'account.bank.statement'

    def _currency(self, cursor, user, ids, name, args, context=None):
            res = {}
            res_currency_obj = self.pool.get('res.currency')
            res_users_obj = self.pool.get('res.users')
            default_currency = res_users_obj.browse(cursor, user,
                    user, context=context).company_id.currency_id
            for statement in self.browse(cursor, user, ids, context=context):
                currency = statement.journal_id.currency
                if not currency:
                    currency = default_currency
                res[statement.id] = currency.id
            currency_names = {}
            for currency_id, currency_name in res_currency_obj.name_get(cursor,
                    user, [x for x in res.values()], context=context):
                currency_names[currency_id] = currency_name
            for statement_id in res.keys():
                currency_id = res[statement_id]
                res[statement_id] = (currency_id, currency_names[currency_id])
            return res

    def _all_lines_reconciled(self, cr, uid, ids, fields_name, args,
            context=None):
        """
        Replacement of this method without inherit.

        Standard account module logic:
        all([line.journal_entry_id.id or line.account_id.id
             for line in statement.line_ids])
        """
        res = {}
        all_lines_reconciled = True
        for rec in self.browse(cr, uid, ids, context=context):
            for line in rec.line_ids:
                if line.amount and not line.journal_entry_id:
                    self.all_lines_reconciled = False
                    break
        res[rec.id] = all_lines_reconciled
        return res

    _columns = {
    'fiscalyear_id': fields.related('period_id','fiscalyear_id',
        type='many2one', relation='account.fiscalyear', string='Fiscal Year',
        store=True, readonly=True),
    'all_lines_reconciled': fields.function(_all_lines_reconciled,
        string='All lines reconciled', type='boolean'),
    'currency': fields.function(_currency, string='Currency',
            type='many2one', relation='res.currency',store=True),
    }

    def init(self, cr):
        cr.execute("""
            ALTER TABLE account_bank_statement
            DROP CONSTRAINT IF EXISTS account_bank_statement_name_uniq;
            DROP INDEX IF EXISTS account_bank_statement_name_non_slash_uniq;
            CREATE UNIQUE INDEX account_bank_statement_name_non_slash_uniq ON
                account_bank_statement(name, journal_id, fiscalyear_id, company_id)
            WHERE name !='/';
        """)


    def button_cancel(self, cr, uid, ids, context=None):
        """
        Replace the account module button_cancel to allow
        cancel statements while preserving associated moves.
        """
        self.write(cr, uid, ids, {'state':'draft'}, context=context)
        return True


# class AccountBankStatementLine(models.Model):
#     _inherit = 'account.bank.statement.line'

class AccountBankStatementLine(orm.Model):
    _inherit = 'account.bank.statement.line'


    # old fields
    # state = fields.Selection(
    #     related='statement_id.state', string='Statement State',
    #     readonly=True, store=True)
    # val_date = fields.Date(
    #     string='Value Date',  # nl: valuta datum
    #     states={'confirm': [('readonly', True)]})
    # journal_code = fields.Char(
    #     related='statement_id.journal_id.code',
    #     string='Journal', store=True, readonly=True)
    # globalisation_id = fields.Many2one(
    #     'account.bank.statement.line.global',
    #     string='Globalisation ID',
    #     states={'confirm': [('readonly', True)]},
    #     help="Code to identify transactions belonging to the same "
    #     "globalisation level within a batch payment")
    # globalisation_amount = fields.Float(
    #     related='globalisation_id.amount',
    #     string='Glob. Amount', readonly=True)
    # counterparty_name = fields.Char(
    #     string='Counterparty Name',
    #     states={'confirm': [('readonly', True)]})
    # counterparty_bic = fields.Char(
    #     string='Counterparty BIC', size=11,
    #     states={'confirm': [('readonly', True)]})
    # counterparty_number = fields.Char(
    #     string='Counterparty Number',
    #     states={'confirm': [('readonly', True)]})
    # counterparty_currency = fields.Char(
    #     string='Counterparty Currency', size=3,
    #     states={'confirm': [('readonly', True)]})
    # payment_reference = fields.Char(
    #     string='Payment Reference', size=35,
    #     states={'confirm': [('readonly', True)]},
    #     help="Payment Reference. For SEPA (SCT or SDD) transactions, "
    #          "the EndToEndReference is recorded in this field.")
    # creditor_reference_type = fields.Char(
    #     # To DO : change field to selection list
    #     string='Creditor Reference Type', size=35,
    #     states={'confirm': [('readonly', True)]},
    #     help="Creditor Reference Type. For SEPA (SCT) transactions, "
    #          "the <CdtrRefInf> type is recorded in this field."
    #          "\nE.g. 'BBA' for belgian structured communication "
    #          "(Code 'SCOR', Issuer 'BBA'")
    # creditor_reference = fields.Char(
    #     'Creditor Reference',
    #     size=35,  # cf. pain.001.001.003 type="Max35Text"
    #     states={'confirm': [('readonly', True)]},
    #     help="Creditor Reference. For SEPA (SCT) transactions, "
    #          "the <CdtrRefInf> reference is recorded in this field.")
    # reconcile_get = fields.Char(
    #     string='Reconciled', compute='_compute_reconcile_get', readonly=True)
    # move_get = fields.Char(
    #     string='Move', compute='_compute_move_get', readonly=True)
    # move_state = fields.Selection(
    #     string='Move State', related='journal_entry_id.state', readonly=True)

    # # update existing fields
    # date = fields.Date(string='Entry Date')
    # partner_id = fields.Many2one(
    #     domain=['|', ('parent_id', '=', False), ('is_company', '=', True)])

    _columns = {

        'state': fields.related('statement_id','state', type='selection',
            string='Statement State', readonly=True, store=True),
        'val_date': fields.date(
            string='Value Date',  # nl: valuta datum
            states={'confirm': [('readonly', True)]}),
        'journal_code': fields.related('statement_id','journal_id','code',
            type='char', string='Journal', store=True, readonly=True),
        'globalisation_id': fields.many2one(
            'account.bank.statement.line.global',
            string='Globalisation ID',
            states={'confirm': [('readonly', True)]},
            help="Code to identify transactions belonging to the same "
            "globalisation level within a batch payment"),
        'globalisation_amount': fields.related(
            'globalisation_id','amount', type='float',
            string='Glob. Amount', readonly=True),
        'counterparty_name': fields.char(
            string='Counterparty Name',
            states={'confirm': [('readonly', True)]}),
        'counterparty_bic': fields.char(
            string='Counterparty BIC', size=11,
            states={'confirm': [('readonly', True)]}),
        'counterparty_number': fields.char(
            string='Counterparty Number',
            states={'confirm': [('readonly', True)]}),
        'counterparty_currency': fields.char(
            string='Counterparty Currency', size=3,
            states={'confirm': [('readonly', True)]}),
        'payment_reference': fields.char(
            string='Payment Reference', size=35,
            states={'confirm': [('readonly', True)]},
            help="Payment Reference. For SEPA (SCT or SDD) transactions, "
                 "the EndToEndReference is recorded in this field."),
        'creditor_reference_type': fields.char(
            # To DO : change field to selection list
            string='Creditor Reference Type', size=35,
            states={'confirm': [('readonly', True)]},
            help="Creditor Reference Type. For SEPA (SCT) transactions, "
                 "the <CdtrRefInf> type is recorded in this field."
                 "\nE.g. 'BBA' for belgian structured communication "
                 "(Code 'SCOR', Issuer 'BBA'"),
        'creditor_reference': fields.char(
            'Creditor Reference',
            size=35,  # cf. pain.001.001.003 type="Max35Text"
            states={'confirm': [('readonly', True)]},
            help="Creditor Reference. For SEPA (SCT) transactions, "
                 "the <CdtrRefInf> reference is recorded in this field."),
        'reconcile_get':fields.char(
            string='Reconciled', compute='_compute_reconcile_get', readonly=True),
        'move_get': fields.char(
            string='Move', compute='_compute_move_get', readonly=True),
        'move_state': fields.related('journal_entry_id','state',type='selection',
            string='Move State', readonly=True),
        # update existing fields
        'date': fields.date(string='Entry Date'),
        'partner_id': fields.many2one('res.partner',
            domain=['|', ('parent_id', '=', False), ('is_company', '=', True)]),
        'journal_entry_id': fields.many2one('account.move', 'Journal Entry', copy=False),

    }

    def _compute_reconcile_get(self, cr, uid, ids, field_name, args, context=None):
        if context is None: context = {}
        rec = self.browse(cr, uid, ids, context=context)[0]
        result = {}
        res = '-'
        move = rec.journal_entry_id
        if move:
            reconciles = filter(lambda x: x.reconcile_id, move.line_id)
            rec_partials = filter(
                lambda x: x.reconcile_partial_id, move.line_id)
            rec_total = reduce(
                lambda y, t: (t.credit or 0.0) - (t.debit or 0.0) + y,
                reconciles + rec_partials, 0.0)
            if rec_total:
                res = '%.2f' % rec_total
                if rec_total != self.amount or rec_partials:
                    res += ' (!)'
        result[rec.id] = res

    def _compute_move_get(self, cr, uid, ids, field_name, args, context=None):
        if context is None: context = {}
        rec = self.browse(cr, uid, ids, context=context)[0]
        result = {}
        res = '-'
        move = rec.journal_entry_id
        if move:
            field_dict = self.pool.get('account.move').fields_get(
                cr, uid, ['state'], context=context)
            result_list = field_dict['state']['selection']
            res = filter(lambda x: x[0] == move.state, result_list)[0][1]
        self.move_get = res

    def action_cancel(self):
        """
        remove the account_id from the line for manual reconciliation
        """
        for line in self.browse(cr, uid, ids, context=context):
            if line.account_id:
                line.account_id = False
        self.cancel()
        return True


    def action_process(self, cr, uid, ids, context=None):
        if context is None: context = {}
        st_line = self.browse(cr, uid, ids, context=context)[0]
        if not st_line.move_ids:
            st_number = st_name
            st_line_number = statement_obj.get_next_st_line_number(cr, uid, st_number, st_line, context)
            company_currency_id = journal.company_id.currency_id.id
            move_id = self.create_move(cr, uid, st_line.id, company_currency_id, st_line_number, context=context)
        else:
            if len(st_line.move_ids) > 1:
                raise orm.except_orm(_('Unsupported Function !'),
                        _('Multiple Account Moves linked to a single Bank Statement Line is currently not supported.' \
                          'Bank Statement "%s", Bank Statement Line "%s"') % (st_line.statement_id.name, st_line_number) )               
            move_id = st_line.move_ids[0].id
            mod_obj = self.pool.get('ir.model.data')
        move_view = mod_obj.get_object_reference(cr, uid, 'account_bank_statement_voucher', 'view_move_from_bank_form')
        act_move = {
            'name': _('Journal Entry'),
            'res_id': move_id,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.move',
            'view_id': [move_view[1]],
            'nodestroy': True,
            'target': 'new',
            'type': 'ir.actions.act_window',
        }
        act_move['context'] = dict(context, wizard_action=pickle.dumps(act_move))
        return act_move

    def unlink(self, cr, uid, ids, context=None):
        if context.get('block_statement_line_delete', False):
            raise orm.except_orm(
                _("Delete operation not allowed ! "
                  "Please go to the associated bank statement in order to "
                  "delete and/or modify this bank statement line"))
        return super(AccountBankStatementLine, self).unlink(cr, uid, ids, context=context)


    def create(self, cr, uid, vals, context=None):
        if context is None: context = {}
        """
        This method can be dropped after acceptance by Odoo of
        - PR 8397
        - PR 8396
        Until these Pull Requests have been merged you should install the
        account_bank_statement.diff patch shipped with this module
        (cf. doc directory)
        """
        # cf. https://github.com/odoo/odoo/pull/8397
        if not vals.get('sequence'):
            lines = self.search(cr, uid,
                [('statement_id', '=', vals.get('statement_id'))],
                order='sequence desc', limit=1)
            lines_brw = self.browse(cr, uid, lines, context=context)
            if lines:
                seq = lines_brw[0].sequence
            else:
                seq = 0
            vals['sequence'] = seq + 1
        # cf. https://github.com/odoo/odoo/pull/8396
        if not vals.get('name'):
            vals['name'] = '/'
        return super(AccountBankStatementLine, self).create(cr, uid, vals, context=context)

    def _needaction_domain_get(self, cr, uid, vals, context=None):
        if context is None: context = {}
        res = super(AccountBankStatementLine, self)._needaction_domain_get(cr, uid, vals, context=context)
        res.append(('amount', '=', True))
        return res

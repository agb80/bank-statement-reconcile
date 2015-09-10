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

    _sql_constraints = [
        ('code_uniq', 'unique (code)', 'The code must be unique !'),
    ]

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

    'fiscalyear_id' = fields.related('period_id','fiscalyear_id',
        type='many2one', relation='account.fiscalyear', string='Fiscal Year', 
        store=True, readonly=True)
    'all_lines_reconciled': fields.boolean(compute='_all_lines_reconciled')


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

    'state': fields.related('statement_id','state', type='relation',
        string='Statement State', readonly=True, store=True),
    'val_date': fields.date(
        string='Value Date',  # nl: valuta datum
        states={'confirm': [('readonly', True)]})
    'journal_code': fields.related('statement_id','journal_id','code',
        type='char', string='Journal', store=True, readonly=True)
    'globalisation_id': fields.many2one(
        'account.bank.statement.line.global',
        string='Globalisation ID',
        states={'confirm': [('readonly', True)]},
        help="Code to identify transactions belonging to the same "
        "globalisation level within a batch payment")
    'globalisation_amount': fields.related(
        'globalisation_id','amount', type='float'
        string='Glob. Amount', readonly=True)
    'counterparty_name': fields.char(
        string='Counterparty Name',
        states={'confirm': [('readonly', True)]})
    'counterparty_bic': fields.char(
        string='Counterparty BIC', size=11,
        states={'confirm': [('readonly', True)]})
    'counterparty_number': fields.char(
        string='Counterparty Number',
        states={'confirm': [('readonly', True)]})
    'counterparty_currency': fields.char(
        string='Counterparty Currency', size=3,
        states={'confirm': [('readonly', True)]})
    'payment_reference': fields.char(
        string='Payment Reference', size=35,
        states={'confirm': [('readonly', True)]},
        help="Payment Reference. For SEPA (SCT or SDD) transactions, "
             "the EndToEndReference is recorded in this field.")
    'creditor_reference_type' = fields.char(
        # To DO : change field to selection list
        string='Creditor Reference Type', size=35,
        states={'confirm': [('readonly', True)]},
        help="Creditor Reference Type. For SEPA (SCT) transactions, "
             "the <CdtrRefInf> type is recorded in this field."
             "\nE.g. 'BBA' for belgian structured communication "
             "(Code 'SCOR', Issuer 'BBA'")
    'creditor_reference' = fields.char(
        'Creditor Reference',
        size=35,  # cf. pain.001.001.003 type="Max35Text"
        states={'confirm': [('readonly', True)]},
        help="Creditor Reference. For SEPA (SCT) transactions, "
             "the <CdtrRefInf> reference is recorded in this field.")
    'reconcile_get' = fields.char(
        string='Reconciled', compute='_compute_reconcile_get', readonly=True)
    'move_get' = fields.char(
        string='Move', compute='_compute_move_get', readonly=True)
    'move_state' = fields.related('journal_entry_id','state', type='selection'
        string='Move State', , readonly=True)

    # update existing fields
    'date' = fields.date(string='Entry Date')
    'partner_id' = fields.many2one(
        domain=['|', ('parent_id', '=', False), ('is_company', '=', True)])

    @api.one
    @api.depends('journal_entry_id')
    def _compute_reconcile_get(self):
        res = '-'
        move = self.journal_entry_id
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
        self.reconcile_get = res

    @api.one
    @api.depends('journal_entry_id.state')
    def _compute_move_get(self):
        res = '-'
        move = self.journal_entry_id
        if move:
            field_dict = self.env['account.move'].fields_get(
                allfields=['state'])
            result_list = field_dict['state']['selection']
            res = filter(lambda x: x[0] == move.state, result_list)[0][1]
        self.move_get = res

    @api.multi
    def action_cancel(self):
        """
        remove the account_id from the line for manual reconciliation
        """
        for line in self:
            if line.account_id:
                line.account_id = False
        self.cancel()
        return True

    @api.multi
    def action_process(self):
        """
        TODO:
        add reconciliation/move logic for use in bank.statement.line list view
        """
        st_line = self[0]
        ctx = self._context.copy()
        ctx.update({
            'act_window_from_bank_statement': True,
            'active_id': st_line.id,
            'active_ids': [st_line.id],
            'statement_id': st_line.statement_id.id,
            })
        module = __name__.split('addons.')[1].split('.')[0]
        view = self.env.ref(
            '%s.view_move_from_bank_form' % module)
        act_move = {
            'name': _('Journal Entry'),
            'res_id': st_line.journal_entry_id.id,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.move',
            'view_id': [view.id],
            'type': 'ir.actions.act_window',
            }
        act_move['context'] = dict(ctx, wizard_action=pickle.dumps(act_move))
        return act_move

    @api.multi
    def unlink(self):
        if self._context.get('block_statement_line_delete', False):
            raise Warning(
                _("Delete operation not allowed ! "
                  "Please go to the associated bank statement in order to "
                  "delete and/or modify this bank statement line"))
        return super(AccountBankStatementLine, self).unlink()

    @api.model
    def create(self, vals):
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
            lines = self.search(
                [('statement_id', '=', vals.get('statement_id'))],
                order='sequence desc', limit=1)
            if lines:
                seq = lines[0].sequence
            else:
                seq = 0
            vals['sequence'] = seq + 1
        # cf. https://github.com/odoo/odoo/pull/8396
        if not vals.get('name'):
            vals['name'] = '/'
        return super(AccountBankStatementLine, self).create(vals)

    @api.model
    def _needaction_domain_get(self):
        res = super(AccountBankStatementLine, self)._needaction_domain_get()
        res.append(('amount', '=', True))
        return res

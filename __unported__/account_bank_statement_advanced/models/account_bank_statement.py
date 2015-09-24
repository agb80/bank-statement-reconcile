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
import time

# V8 to V7
# from openerp import models, fields, api, _
# import openerp.addons.decimal_precision as dp
# from openerp.exceptions import Warning
from openerp.report import report_sxw
from openerp.osv import osv, orm, fields
from openerp.tools import float_compare, float_round
from openerp.tools.translate import _
from openerp.addons import decimal_precision as dp


_logger = logging.getLogger(__name__)


class ir_model_data(osv.osv):
    _inherit = "ir.model.data"

    def xmlid_lookup(self, cr, uid, xmlid):
        """Low level xmlid lookup
        Return (id, res_model, res_id) or raise ValueError if not found
        """
        module, name = xmlid.split('.', 1)
        ids = self.search(cr, uid, [('module', '=', module), ('name', '=', name)])
        if not ids:
            raise ValueError('External ID not found in the system: %s' % (xmlid))
        # the sql constraints ensure us we have only one result
        res = self.read(cr, uid, ids[0], ['model', 'res_id'])
        if not res['res_id']:
            raise ValueError('External ID not found in the system: %s' % (xmlid))
        return ids[0], res['model'], res['res_id']

    def xmlid_to_res_model_res_id(self, cr, uid, xmlid, raise_if_not_found=False):
        """ Return (res_model, res_id)"""
        try:
            return self.xmlid_lookup(cr, uid, xmlid)[1:3]
        except ValueError:
            if raise_if_not_found:
                raise
            return (False, False)

    def xmlid_to_res_id(self, cr, uid, xmlid, raise_if_not_found=False):
        """ Returns res_id """
        return self.xmlid_to_res_model_res_id(cr, uid, xmlid, raise_if_not_found)[1]

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

class AccountTax(orm.Model):
    _inherit = 'account.tax'
    
    def compute_all(self, cr, uid, taxes, price_unit, quantity, product=None, partner=None, force_excluded=False):
        """
        :param force_excluded: boolean used to say that we don't want to consider the value of field price_include of
            tax. It's used in encoding by line where you don't matter if you encoded a tax with that boolean to True or
            False
        RETURN: {
                'total': 0.0,                # Total without taxes
                'total_included: 0.0,        # Total with taxes
                'taxes': []                  # List of taxes, see compute for the format
            }
        """

        # By default, for each tax, tax amount will first be computed
        # and rounded at the 'Account' decimal precision for each
        # PO/SO/invoice line and then these rounded amounts will be
        # summed, leading to the total amount for that tax. But, if the
        # company has tax_calculation_rounding_method = round_globally,
        # we still follow the same method, but we use a much larger
        # precision when we round the tax amount for each line (we use
        # the 'Account' decimal precision + 5), and that way it's like
        # rounding after the sum of the tax amounts of each line
        precision = self.pool.get('decimal.precision').precision_get(cr, uid, 'Account')
        tax_compute_precision = precision
        if taxes and taxes[0].company_id.tax_calculation_rounding_method == 'round_globally':
            tax_compute_precision += 5
        totalin = totalex = round(price_unit * quantity, precision)
        tin = []
        tex = []
        for tax in taxes:
            if not tax.price_include or force_excluded:
                tex.append(tax)
            else:
                tin.append(tax)
        tin = self.compute_inv(cr, uid, tin, price_unit, quantity, product=product, partner=partner, precision=tax_compute_precision)
        for r in tin:
            totalex -= r.get('amount', 0.0)
        totlex_qty = 0.0
        try:
            totlex_qty = totalex/quantity
        except:
            pass
        tex = self._compute(cr, uid, tex, totlex_qty, quantity, product=product, partner=partner, precision=tax_compute_precision)
        for r in tex:
            totalin += r.get('amount', 0.0)
        return {
            'total': totalex,
            'total_included': totalin,
            'taxes': tin + tex
        }


    def compute_for_bank_reconciliation(self, cr, uid, tax_id, amount, context=None):
        """ Called by RPC by the bank statement reconciliation widget """
        tax = self.browse(cr, uid, tax_id, context=context)
        return self.compute_all(cr, uid, [tax], amount, 1) # TOCHECK may use force_exclude parameter

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
            string='Parent Code', ondelete='cascade'
        ),
        'child_ids': fields.one2many(
            'account.bank.statement.line.global', 'parent_id',
            string='Child Codes'
        ),
        'type': fields.selection([
            ('iso20022', 'ISO 20022'),
            ('coda', 'CODA'),
            ('manual', 'Manual'),
            ], string='Type', required=True
        ),
        'amount': fields.float(
            string='Amount',
            digits_compute=dp.get_precision('Account')
        ),
        'payment_reference': fields.char(
            string='Payment Reference',
            help="Payment Reference. For SEPA (SCT or SDD) transactions, "
                 "the PaymentInformationIdentification "
                 "is recorded in this field."
        ),
        'bank_statement_line_ids': fields.one2many(
            'account.bank.statement.line', 'globalisation_id',
            string='Bank Statement Lines'
        ),
    }

    def _default_code(self, cr, uid, ids, context=None):
        return self.pool.get('ir.sequence').get(
            cr, uid, 'account.bank.statement.line.global'
        )

    _defaults = {
        'code': _default_code
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

    def name_search(
        self, cr, user, name, args=None, operator='ilike', context=None,
        limit=100
    ):
        args = args or []
        if name:
            recs = self.search(
                cr, user, [('code', '=ilike', name)] + args, limit=limit
            )
            if not recs:
                recs = self.search(
                    cr, user,
                    [('name', operator, name)] + args, limit=limit
                )
            if not recs and len(name.split()) >= 2:
                # Separating code and name for searching
                # name can contain spaces
                operand1, operand2 = name.split(' ', 1)
                recs = self.search(cr, user, [
                    ('code', '=like', operand1),
                    ('name', operator, operand2)
                ] + args, limit=limit)
        else:
            return {}


class AccountBankStatement(orm.Model):
    _inherit = 'account.bank.statement'

    def _currency(self, cursor, user, ids, name, args, context=None):
        res = {}
        res_currency_obj = self.pool.get('res.currency')
        res_users_obj = self.pool.get('res.users')
        default_currency = res_users_obj.browse(
            cursor, user, user, context=context
        ).company_id.currency_id
        for statement in self.browse(cursor, user, ids, context=context):
            currency = statement.journal_id.currency
            if not currency:
                currency = default_currency
            res[statement.id] = currency.id
        currency_names = {}
        for currency_id, currency_name in res_currency_obj.name_get(
            cursor, user, [x for x in res.values()], context=context
        ):
            currency_names[currency_id] = currency_name
        for statement_id in res.keys():
            currency_id = res[statement_id]
            res[statement_id] = (currency_id, currency_names[currency_id])
        return res

    def _all_lines_reconciled(self, cr, uid, ids, name, args, context=None):
        res = {}
        for statement in self.browse(cr, uid, ids, context=context):
            res[statement.id] = all([line.journal_entry_id.id or line.account_id.id for line in statement.line_ids])
        return res

    _columns = {
        'fiscalyear_id': fields.related(
            'period_id', 'fiscalyear_id',
            type='many2one', relation='account.fiscalyear',
            string='Fiscal Year', store=True, readonly=True
        ),
        'all_lines_reconciled': fields.function(
            _all_lines_reconciled, string='All lines reconciled',
            type='boolean'
        ),
        'currency': fields.function(
            _currency, string='Currency', type='many2one',
            relation='res.currency', store=True
        ),
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
        bnk_st_line_ids = []
        for st in self.browse(cr, uid, ids, context=context):
            bnk_st_line_ids += [line.id for line in st.line_ids]
        self.pool.get('account.bank.statement.line').cancel(cr, uid, bnk_st_line_ids, context=context)
        self.write(cr, uid, ids, {'state': 'draft'}, context=context)
        return True

    def get_format_currency_js_function(self, cr, uid, id, context=None):
        """ Returns a string that can be used to instanciate a javascript function.
            That function formats a number according to the statement line's currency or the statement currency"""
        company_currency = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.currency_id
        st = id and self.browse(cr, uid, id, context=context)
        if not st:
            return
        statement_currency = st.journal_id.currency or company_currency
        digits = 2  # TODO : from currency_obj
        function = ""
        done_currencies = []
        for st_line in st.line_ids:
            st_line_currency = st_line.currency_id or statement_currency
            if st_line_currency.id not in done_currencies:
                if st_line_currency.position == 'after':
                    return_str = "return amount.toFixed(" + str(digits) + ") + ' " + st_line_currency.symbol + "';"
                else:
                    return_str = "return '" + st_line_currency.symbol + " ' + amount.toFixed(" + str(digits) + ");"
                function += "if (currency_id === " + str(st_line_currency.id) + "){ " + return_str + " }"
                done_currencies.append(st_line_currency.id)
        return function

    def number_of_lines_reconciled(self, cr, uid, ids, context=None):
        print "=>ids",ids
        print "=>number_of_lines_reconciled"
        bsl_obj = self.pool.get('account.bank.statement.line')
        line_ids = bsl_obj.search_count(
            cr, uid,
            [('statement_id', 'in', ids),
             ('journal_entry_id', '!=', False)],
            context=context
        )
        print "=>line_ids", line_ids
        return line_ids

    def button_confirm_bank(self, cr, uid, ids, context=None):
        if context is None:
            context = {}

        for st in self.browse(cr, uid, ids, context=context):
            j_type = st.journal_id.type
            if not self.check_status_condition(cr, uid, st.state, journal_type=j_type):
                continue

            self.balance_check(cr, uid, st.id, journal_type=j_type, context=context)
            if (not st.journal_id.default_credit_account_id) \
                    or (not st.journal_id.default_debit_account_id):
                raise osv.except_osv(_('Configuration Error!'), _('Please verify that an account is defined in the journal.'))
            for line in st.move_line_ids:
                if line.state != 'valid':
                    raise osv.except_osv(_('Error!'), _('The account entries lines are not in valid state.'))
            move_ids = []
            for st_line in st.line_ids:
                if not st_line.amount:
                    continue
                if st_line.account_id and not st_line.journal_entry_id.id:
                    # make an account move as before
                    vals = {
                        'debit': st_line.amount < 0 and -st_line.amount or 0.0,
                        'credit': st_line.amount > 0 and st_line.amount or 0.0,
                        'account_id': st_line.account_id.id,
                        'name': st_line.name
                    }
                    print "=>vals", vals
                    self.pool.get('account.bank.statement.line').process_reconciliation(cr, uid, st_line.id, [vals], context=context)
                elif not st_line.journal_entry_id.id:
                    raise osv.except_osv(_('Error!'), _('All the account entries lines must be processed in order to close the statement.'))
                move_ids.append(st_line.journal_entry_id.id)
            if move_ids[0]:
                self.pool.get('account.move').post(cr, uid, move_ids, context=context)
            self.message_post(cr, uid, [st.id], body=_('Statement %s confirmed, journal items were created.') % (st.name,), context=context)
        self.link_bank_to_partner(cr, uid, ids, context=context)
        return self.write(cr, uid, ids, {'state': 'confirm', 'closing_date': time.strftime("%Y-%m-%d %H:%M:%S")}, context=context)

    def _compute_balance_end_real(self, cr, uid, journal_id, context=None):
        res = False
        if journal_id:
            journal = self.pool.get('account.journal').browse(cr, uid, journal_id, context=context)
            if journal.with_last_closing_balance:
                cr.execute('SELECT balance_end_real \
                      FROM account_bank_statement \
                      WHERE journal_id = %s AND NOT state = %s \
                      ORDER BY date DESC,id DESC LIMIT 1', (journal_id, 'draft'))
                res = cr.fetchone()
        return res and res[0] or 0.0

    def onchange_journal_id(self, cr, uid, statement_id, journal_id, context=None):
        if not journal_id:
            return {}
        balance_start = self._compute_balance_end_real(cr, uid, journal_id, context=context)
        journal = self.pool.get('account.journal').browse(cr, uid, journal_id, context=context)
        currency = journal.currency or journal.company_id.currency_id
        res = {'balance_start': balance_start, 'company_id': journal.company_id.id, 'currency': currency.id}
        if journal.type == 'cash':
            res['cash_control'] = journal.cash_control
        return {'value': res}

    def unlink(self, cr, uid, ids, context=None):
        statement_line_obj = self.pool['account.bank.statement.line']
        if context.get('block_statement_line_delete', False):
            raise orm.except_orm(
                _("Delete operation not allowed ! "
                  "Please go to the associated bank statement in order to "
                  "delete and/or modify this bank statement line"))
        for item in self.browse(cr, uid, ids, context=context):
            if item.state != 'draft':
                raise osv.except_osv(
                    _('Invalid Action!'),
                    _('In order to delete a bank statement, you must first cancel it to delete related journal items.')
                )
            # Explicitly unlink bank statement lines
            # so it will check that the related journal entries have
            # been deleted first
            statement_line_obj.unlink(
                cr, uid, [line.id for line in item.line_ids],
                context=context
            )
        return super(AccountBankStatement, self).unlink(
            cr, uid, ids, context=context
        )

    def button_journal_entries(self, cr, uid, ids, context=None):
        ctx = (context or {}).copy()
        ctx['journal_id'] = self.browse(
            cr, uid, ids[0], context=context
        ).journal_id.id
        return {
            'name': _('Journal Items'),
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'account.move.line',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('statement_id', 'in', ids)],
            'context': ctx,
        }

    def link_bank_to_partner(self, cr, uid, ids, context=None):
        for statement in self.browse(cr, uid, ids, context=context):
            for st_line in statement.line_ids:
                if st_line.bank_account_id and st_line.partner_id and st_line.bank_account_id.partner_id.id != st_line.partner_id.id:
                    # Update the partner informations of the bank account, possibly overriding existing ones
                    bank_obj = self.pool.get('res.partner.bank')
                    bank_vals = bank_obj.onchange_partner_id(cr, uid, [st_line.bank_account_id.id], st_line.partner_id.id, context=context)['value']
                    bank_vals.update({'partner_id': st_line.partner_id.id})
                    bank_obj.write(cr, uid, [st_line.bank_account_id.id], bank_vals, context=context)


class account_bank_statement_line(orm.Model):
    _inherit = 'account.bank.statement.line'

    def unlink(self, cr, uid, ids, context=None):
        for item in self.browse(cr, uid, ids, context=context):
            if item.journal_entry_id:
                raise osv.except_osv(
                    _('Invalid Action!'),
                    _('In order to delete a bank statement line, you must'
                      ' first cancel it to delete related journal items.')
                )
        return super(account_bank_statement_line, self).unlink(
            cr, uid, ids, context=context
        )

    def cancel(self, cr, uid, ids, context=None):
        account_move_obj = self.pool.get('account.move')
        move_ids = []
        for line in self.browse(cr, uid, ids, context=context):
            if line.journal_entry_id:
                move_ids.append(line.journal_entry_id.id)
                for aml in line.journal_entry_id.line_id:
                    if aml.reconcile_id:
                        move_lines = [l.id for l in aml.reconcile_id.line_id]
                        move_lines.remove(aml.id)
                        self.pool.get('account.move.reconcile').unlink(cr, uid, [aml.reconcile_id.id], context=context)
                        if len(move_lines) >= 2:
                            self.pool.get('account.move.line').reconcile_partial(cr, uid, move_lines, 'auto', context=context)
        if move_ids:
            account_move_obj.button_cancel(cr, uid, move_ids, context=context)
            account_move_obj.unlink(cr, uid, move_ids, context)

    def get_data_for_reconciliations(self, cr, uid, ids, excluded_ids=None,
        search_reconciliation_proposition=True, context=None):
        """
            Returns the data required to display a reconciliation,
            for each statement line id in ids
        """
        print "=>GET_DATA_FOR_RECONCILIATIONS"
        ret = []
        if excluded_ids is None:
            excluded_ids = []

        for st_line in self.browse(cr, uid, ids, context=context):
            print "=>ST_LINE", st_line
            reconciliation_data = {}
            if search_reconciliation_proposition:
                reconciliation_proposition = self.get_reconciliation_proposition(
                    cr, uid, st_line, excluded_ids=excluded_ids, context=context
                )
                print "=>RECONCILIATION_PROPOSITION", reconciliation_proposition
                for mv_line in reconciliation_proposition:
                    excluded_ids.append(mv_line['id'])
                reconciliation_data['reconciliation_proposition'] = reconciliation_proposition
            else:
                reconciliation_data['reconciliation_proposition'] = []
            st_line = self.get_statement_line_for_reconciliation(cr, uid, st_line, context=context)
            print "=>LINEAS A CONCILIAR", st_line
            reconciliation_data['st_line'] = st_line
            ret.append(reconciliation_data)

        print "=>ret", ret
        return ret

    def get_statement_line_for_reconciliation(self, cr, uid, st_line, context=None):
        """ Returns the data required by the bank statement reconciliation widget to display a statement line """
        if context is None:
            context = {}
        statement_currency = st_line.journal_id.currency or st_line.journal_id.company_id.currency_id
        rml_parser = report_sxw.rml_parse(cr, uid, 'reconciliation_widget_asl', context=context)

        if st_line.amount_currency and st_line.currency_id:
            amount = st_line.amount_currency
            amount_currency = st_line.amount
            amount_currency_str = amount_currency > 0 and amount_currency or -amount_currency
            amount_currency_str = rml_parser.formatLang(amount_currency_str, currency_obj=statement_currency)
        else:
            amount = st_line.amount
            amount_currency_str = ""
        amount_str = amount > 0 and amount or -amount
        amount_str = rml_parser.formatLang(amount_str, currency_obj=st_line.currency_id or statement_currency)

        data = {
            'id': st_line.id,
            'ref': st_line.ref,
            'note': st_line.note or "",
            'name': st_line.name,
            'date': st_line.date,
            'amount': amount,
            'amount_str': amount_str,  # Amount in the statement line currency
            'currency_id': st_line.currency_id.id or statement_currency.id,
            'partner_id': st_line.partner_id.id,
            'statement_id': st_line.statement_id.id,
            'account_code': st_line.journal_id.default_debit_account_id.code,
            'account_name': st_line.journal_id.default_debit_account_id.name,
            'partner_name': st_line.partner_id.name,
            'communication_partner_name': st_line.partner_name,
            'amount_currency_str': amount_currency_str,  # Amount in the statement currency
            'has_no_partner': not st_line.partner_id.id,
        }
        if st_line.partner_id.id:
            if amount > 0:
                data['open_balance_account_id'] = st_line.partner_id.property_account_receivable.id
            else:
                data['open_balance_account_id'] = st_line.partner_id.property_account_payable.id

        return data

    def _domain_reconciliation_proposition(self, cr, uid, st_line, excluded_ids=None, context=None):
        if excluded_ids is None:
            excluded_ids = []
        domain = [('ref', '=', st_line.name),
                  ('reconcile_id', '=', False),
                  ('state', '=', 'valid'),
                  ('account_id.reconcile', '=', True),
                  ('id', 'not in', excluded_ids),
                  ('partner_id', 'in', (False, st_line.partner_id.id))]
        return domain

    def get_reconciliation_proposition(self, cr, uid, st_line, excluded_ids=None, context=None):
        """ Returns move lines that constitute the best guess to reconcile a statement line. """
        mv_line_pool = self.pool.get('account.move.line')

        # Look for structured communication
        if st_line.name:
            domain = self._domain_reconciliation_proposition(cr, uid, st_line, excluded_ids=excluded_ids, context=context)
            match_id = mv_line_pool.search(cr, uid, domain, offset=0, limit=2, context=context)
            if match_id and len(match_id) == 1:
                mv_line_br = mv_line_pool.browse(cr, uid, match_id, context=context)
                target_currency = st_line.currency_id or st_line.journal_id.currency or st_line.journal_id.company_id.currency_id
                mv_line = mv_line_pool.prepare_move_lines_for_reconciliation_widget(cr, uid, mv_line_br, target_currency=target_currency, target_date=st_line.date, context=context)[0]
                mv_line['has_no_partner'] = not bool(st_line.partner_id.id)
                # If the structured communication matches a move line that is associated with a partner, we can safely associate the statement line with the partner
                if (mv_line['partner_id']):
                    self.write(cr, uid, st_line.id, {'partner_id': mv_line['partner_id']}, context=context)
                    mv_line['has_no_partner'] = False
                return [mv_line]

        # How to compare statement line amount and move lines amount
        precision_digits = self.pool.get('decimal.precision').precision_get(cr, uid, 'Account')
        currency_id = st_line.currency_id.id or st_line.journal_id.currency.id
        # NB : amount can't be == 0 ; so float precision is not an issue for amount > 0 or amount < 0
        amount = st_line.amount_currency or st_line.amount
        domain = [('reconcile_partial_id', '=', False)]
        if currency_id:
            domain += [('currency_id', '=', currency_id)]
        sign = 1  # correct the fact that st_line.amount is signed and debit/credit is not
        amount_field = 'debit'
        if currency_id is False:
            if amount < 0:
                amount_field = 'credit'
                sign = -1
        else:
            amount_field = 'amount_currency'

        # Look for a matching amount
        domain_exact_amount = domain + [(amount_field, '=', float_round(sign * amount, precision_digits=precision_digits))]
        domain_exact_amount_ref = domain_exact_amount + [('ref', '=', st_line.ref)]
        match_id = self.get_move_lines_for_reconciliation(cr, uid, st_line, excluded_ids=excluded_ids, offset=0, limit=2, additional_domain=domain_exact_amount_ref)
        if not match_id:
            match_id = self.get_move_lines_for_reconciliation(cr, uid, st_line, excluded_ids=excluded_ids, offset=0, limit=2, additional_domain=domain_exact_amount)

        if match_id and len(match_id) == 1:
            return match_id

        if not st_line.partner_id.id:
            return []

        # Look for a set of move line whose amount is <= to the line's amount
        if amount > 0:  # Make sure we can't mix receivable and payable
            domain += [('account_id.type', '=', 'receivable')]
        else:
            domain += [('account_id.type', '=', 'payable')]
        if amount_field == 'amount_currency' and amount < 0:
            domain += [(amount_field, '<', 0), (amount_field, '>', (sign * amount))]
        else:
            domain += [(amount_field, '>', 0), (amount_field, '<', (sign * amount))]
        mv_lines = self.get_move_lines_for_reconciliation(cr, uid, st_line, excluded_ids=excluded_ids, limit=5, additional_domain=domain, context=context)
        ret = []
        total = 0
        for line in mv_lines:
            total += abs(line['debit'] - line['credit'])
            if float_compare(total, abs(amount), precision_digits=precision_digits) != 1:
                ret.append(line)
            else:
                break
        return ret

    def get_move_lines_for_reconciliation_by_statement_line_id(self, cr, uid, st_line_id, excluded_ids=None, str=False, offset=0, limit=None, count=False, additional_domain=None, context=None):
        """ Bridge between the web client reconciliation widget and get_move_lines_for_reconciliation (which expects a browse record) """
        if excluded_ids is None:
            excluded_ids = []
        if additional_domain is None:
            additional_domain = []
        st_line = self.browse(cr, uid, st_line_id, context=context)
        return self.get_move_lines_for_reconciliation(cr, uid, st_line, excluded_ids, str, offset, limit, count, additional_domain, context=context)

    def _domain_move_lines_for_reconciliation(self, cr, uid, st_line, excluded_ids=None, str=False, additional_domain=None, context=None):
        if excluded_ids is None:
            excluded_ids = []
        if additional_domain is None:
            additional_domain = []
        # Make domain
        domain = additional_domain + [
            ('reconcile_id', '=', False),
            ('state', '=', 'valid'),
            ('account_id.reconcile', '=', True)
        ]
        if st_line.partner_id.id:
            domain += [('partner_id', '=', st_line.partner_id.id)]
        if excluded_ids:
            domain.append(('id', 'not in', excluded_ids))
        if str:
            domain += [
                '|', ('move_id.name', 'ilike', str),
                '|', ('move_id.ref', 'ilike', str),
                ('date_maturity', 'like', str),
            ]
            if not st_line.partner_id.id:
                domain.insert(-1, '|',)
                domain.append(('partner_id.name', 'ilike', str))
            if str != '/':
                domain.insert(-1, '|',)
                domain.append(('name', 'ilike', str))
        return domain

    def get_move_lines_for_reconciliation(self, cr, uid, st_line, excluded_ids=None, str=False, offset=0, limit=None, count=False, additional_domain=None, context=None):
        """ Find the move lines that could be used to reconcile a statement line. If count is true, only returns the count.
            :param st_line: the browse record of the statement line
            :param integers list excluded_ids: ids of move lines that should not be fetched
            :param boolean count: just return the number of records
            :param tuples list additional_domain: additional domain restrictions
        """
        mv_line_pool = self.pool.get('account.move.line')
        domain = self._domain_move_lines_for_reconciliation(cr, uid, st_line, excluded_ids=excluded_ids, str=str, additional_domain=additional_domain, context=context)

        # Get move lines ; in case of a partial reconciliation, only keep one line (the first whose amount is greater than
        # the residual amount because it is presumably the invoice, which is the relevant item in this situation)
        filtered_lines = []
        reconcile_partial_ids = []
        actual_offset = offset
        while True:
            line_ids = mv_line_pool.search(cr, uid, domain, offset=actual_offset, limit=limit, order="date_maturity asc, id asc", context=context)
            lines = mv_line_pool.browse(cr, uid, line_ids, context=context)
            make_one_more_loop = False
            for line in lines:
                if line.reconcile_partial_id and \
                        (line.reconcile_partial_id.id in reconcile_partial_ids or \
                        abs(line.debit - line.credit) < abs(line.amount_residual)):
                    # if we filtered a line because it is partially reconciled with an already selected line, we must do one more loop
                    # in order to get the right number of items in the pager
                    make_one_more_loop = True
                    continue
                filtered_lines.append(line)
                if line.reconcile_partial_id:
                    reconcile_partial_ids.append(line.reconcile_partial_id.id)

            if not limit or not make_one_more_loop or len(filtered_lines) >= limit:
                break
            actual_offset = actual_offset + limit
        lines = limit and filtered_lines[:limit] or filtered_lines

        # Either return number of lines
        if count:
            return len(lines)

        # Or return list of dicts representing the formatted move lines
        else:
            target_currency = st_line.currency_id or st_line.journal_id.currency or st_line.journal_id.company_id.currency_id
            mv_lines = mv_line_pool.prepare_move_lines_for_reconciliation_widget(cr, uid, lines, target_currency=target_currency, target_date=st_line.date, context=context)
            has_no_partner = not bool(st_line.partner_id.id)
            for line in mv_lines:
                line['has_no_partner'] = has_no_partner
            return mv_lines

    def get_currency_rate_line(self, cr, uid, st_line, currency_diff, move_id, context=None):
        if currency_diff < 0:
            account_id = st_line.company_id.expense_currency_exchange_account_id.id
            if not account_id:
                raise osv.except_osv(_('Insufficient Configuration!'), _("You should configure the 'Loss Exchange Rate Account' in the accounting settings, to manage automatically the booking of accounting entries related to differences between exchange rates."))
        else:
            account_id = st_line.company_id.income_currency_exchange_account_id.id
            if not account_id:
                raise osv.except_osv(_('Insufficient Configuration!'), _("You should configure the 'Gain Exchange Rate Account' in the accounting settings, to manage automatically the booking of accounting entries related to differences between exchange rates."))
        return {
            'move_id': move_id,
            'name': _('change') + ': ' + (st_line.name or '/'),
            'period_id': st_line.statement_id.period_id.id,
            'journal_id': st_line.journal_id.id,
            'partner_id': st_line.partner_id.id,
            'company_id': st_line.company_id.id,
            'statement_id': st_line.statement_id.id,
            'debit': currency_diff < 0 and -currency_diff or 0,
            'credit': currency_diff > 0 and currency_diff or 0,
            'amount_currency': 0.0,
            'date': st_line.date,
            'account_id': account_id
            }

    def _get_exchange_lines(self, cr, uid, st_line, mv_line, currency_diff, currency_id, move_id, context=None):
        '''
        Prepare the two lines in company currency due to currency rate difference.
        :param line: browse record of the voucher.line for which we want to create currency rate difference accounting
            entries
        :param move_id: Account move wher the move lines will be.
        :param currency_diff: Amount to be posted.
        :param company_currency: id of currency of the company to which the voucher belong
        :param current_currency: id of currency of the voucher
        :return: the account move line and its counterpart to create, depicted as mapping between fieldname and value
        :rtype: tuple of dict
        '''
        if currency_diff > 0:
            exchange_account_id = st_line.company_id.expense_currency_exchange_account_id.id
        else:
            exchange_account_id = st_line.company_id.income_currency_exchange_account_id.id
        # Even if the amount_currency is never filled, we need to pass the foreign currency because otherwise
        # the receivable/payable account may have a secondary currency, which render this field mandatory
        if mv_line.account_id.currency_id:
            account_currency_id = mv_line.account_id.currency_id.id
        else:
            account_currency_id = st_line.company_id.currency_id.id != currency_id and currency_id or False
        move_line = {
            'journal_id': st_line.journal_id.id,
            'period_id': st_line.statement_id.period_id.id,
            'name': _('change') + ': ' + (st_line.name or '/'),
            'account_id': mv_line.account_id.id,
            'move_id': move_id,
            'partner_id': st_line.partner_id.id,
            'currency_id': account_currency_id,
            'amount_currency': 0.0,
            'quantity': 1,
            'credit': currency_diff > 0 and currency_diff or 0.0,
            'debit': currency_diff < 0 and -currency_diff or 0.0,
            'date': st_line.date,
            'counterpart_move_line_id': mv_line.id,
        }
        move_line_counterpart = {
            'journal_id': st_line.journal_id.id,
            'period_id': st_line.statement_id.period_id.id,
            'name': _('change') + ': ' + (st_line.name or '/'),
            'account_id': exchange_account_id,
            'move_id': move_id,
            'amount_currency': 0.0,
            'partner_id': st_line.partner_id.id,
            'currency_id': account_currency_id,
            'quantity': 1,
            'debit': currency_diff > 0 and currency_diff or 0.0,
            'credit': currency_diff < 0 and -currency_diff or 0.0,
            'date': st_line.date,
        }
        return (move_line, move_line_counterpart)

    def process_reconciliations(self, cr, uid, data, context=None):
        for datum in data:
            self.process_reconciliation(cr, uid, datum[0], datum[1], context=context)

    def process_reconciliation(self, cr, uid, id, mv_line_dicts, context=None):
        """ Creates a move line for each item of mv_line_dicts and for the statement line. Reconcile a new move line with its counterpart_move_line_id if specified. Finally, mark the statement line as reconciled by putting the newly created move id in the column journal_entry_id.
            :param int id: id of the bank statement line
            :param list of dicts mv_line_dicts: move lines to create. If counterpart_move_line_id is specified, reconcile with it
        """
        if context is None:
            context = {}
        st_line = self.browse(cr, uid, id, context=context)
        company_currency = st_line.journal_id.company_id.currency_id
        statement_currency = st_line.journal_id.currency or company_currency
        bs_obj = self.pool.get('account.bank.statement')
        am_obj = self.pool.get('account.move')
        aml_obj = self.pool.get('account.move.line')
        currency_obj = self.pool.get('res.currency')

        # Checks
        if st_line.journal_entry_id.id:
            raise osv.except_osv(_('Error!'), _('The bank statement line was already reconciled.'))
        for mv_line_dict in mv_line_dicts:
            for field in ['debit', 'credit', 'amount_currency']:
                if field not in mv_line_dict:
                    mv_line_dict[field] = 0.0
            if mv_line_dict.get('counterpart_move_line_id'):
                mv_line = aml_obj.browse(cr, uid, mv_line_dict.get('counterpart_move_line_id'), context=context)
                if mv_line.reconcile_id:
                    raise osv.except_osv(_('Error!'), _('A selected move line was already reconciled.'))

        # Create the move
        move_name = (st_line.statement_id.name or st_line.name) + "/" + str(st_line.sequence)
        move_vals = bs_obj._prepare_move(cr, uid, st_line, move_name, context=context)
        move_id = am_obj.create(cr, uid, move_vals, context=context)

        # Create the move line for the statement line
        if st_line.statement_id.currency.id != company_currency.id:
            if st_line.currency_id == company_currency:
                amount = st_line.amount_currency
            else:
                ctx = context.copy()
                ctx['date'] = st_line.date
                amount = currency_obj.compute(cr, uid, st_line.statement_id.currency.id, company_currency.id, st_line.amount, context=ctx)
        else:
            amount = st_line.amount
        bank_st_move_vals = bs_obj._prepare_bank_move_line(cr, uid, st_line, move_id, amount, company_currency.id, context=context)
        aml_obj.create(cr, uid, bank_st_move_vals, context=context)
        # Complete the dicts
        st_line_currency = st_line.currency_id or statement_currency
        st_line_currency_rate = st_line.currency_id and (st_line.amount_currency / st_line.amount) or False
        to_create = []
        for mv_line_dict in mv_line_dicts:
            if mv_line_dict.get('is_tax_line'):
                continue
            mv_line_dict['ref'] = move_name
            mv_line_dict['move_id'] = move_id
            mv_line_dict['period_id'] = st_line.statement_id.period_id.id
            mv_line_dict['journal_id'] = st_line.journal_id.id
            mv_line_dict['company_id'] = st_line.company_id.id
            mv_line_dict['statement_id'] = st_line.statement_id.id
            if mv_line_dict.get('counterpart_move_line_id'):
                mv_line = aml_obj.browse(cr, uid, mv_line_dict['counterpart_move_line_id'], context=context)
                mv_line_dict['partner_id'] = mv_line.partner_id.id or st_line.partner_id.id
                mv_line_dict['account_id'] = mv_line.account_id.id
            if st_line_currency.id != company_currency.id:
                ctx = context.copy()
                ctx['date'] = st_line.date
                mv_line_dict['amount_currency'] = mv_line_dict['debit'] - mv_line_dict['credit']
                mv_line_dict['currency_id'] = st_line_currency.id
                if st_line.currency_id and statement_currency.id == company_currency.id and st_line_currency_rate:
                    debit_at_current_rate = self.pool.get('res.currency').round(cr, uid, company_currency, mv_line_dict['debit'] / st_line_currency_rate)
                    credit_at_current_rate = self.pool.get('res.currency').round(cr, uid, company_currency, mv_line_dict['credit'] / st_line_currency_rate)
                elif st_line.currency_id and st_line_currency_rate:
                    debit_at_current_rate = currency_obj.compute(cr, uid, statement_currency.id, company_currency.id, mv_line_dict['debit'] / st_line_currency_rate, context=ctx)
                    credit_at_current_rate = currency_obj.compute(cr, uid, statement_currency.id, company_currency.id, mv_line_dict['credit'] / st_line_currency_rate, context=ctx)
                else:
                    debit_at_current_rate = currency_obj.compute(cr, uid, st_line_currency.id, company_currency.id, mv_line_dict['debit'], context=ctx)
                    credit_at_current_rate = currency_obj.compute(cr, uid, st_line_currency.id, company_currency.id, mv_line_dict['credit'], context=ctx)
                if mv_line_dict.get('counterpart_move_line_id'):
                    # post an account line that use the same currency rate than the counterpart (to balance the account) and post the difference in another line
                    ctx['date'] = mv_line.date
                    if mv_line.currency_id.id == mv_line_dict['currency_id'] \
                            and float_is_zero(abs(mv_line.amount_currency) - abs(mv_line_dict['amount_currency']), precision_rounding=mv_line.currency_id.rounding):
                        debit_at_old_rate = mv_line.credit
                        credit_at_old_rate = mv_line.debit
                    else:
                        debit_at_old_rate = currency_obj.compute(cr, uid, st_line_currency.id, company_currency.id, mv_line_dict['debit'], context=ctx)
                        credit_at_old_rate = currency_obj.compute(cr, uid, st_line_currency.id, company_currency.id, mv_line_dict['credit'], context=ctx)
                    mv_line_dict['credit'] = credit_at_old_rate
                    mv_line_dict['debit'] = debit_at_old_rate
                    if debit_at_old_rate - debit_at_current_rate:
                        currency_diff = debit_at_current_rate - debit_at_old_rate
                        to_create.append(self.get_currency_rate_line(cr, uid, st_line, -currency_diff, move_id, context=context))
                    if credit_at_old_rate - credit_at_current_rate:
                        currency_diff = credit_at_current_rate - credit_at_old_rate
                        to_create.append(self.get_currency_rate_line(cr, uid, st_line, currency_diff, move_id, context=context))
                    if mv_line.currency_id and mv_line_dict['currency_id'] == mv_line.currency_id.id:
                        amount_unreconciled = mv_line.amount_residual_currency
                    else:
                        amount_unreconciled = currency_obj.compute(cr, uid, company_currency.id, mv_line_dict['currency_id'] , mv_line.amount_residual, context=ctx)
                    if float_is_zero(mv_line_dict['amount_currency'] + amount_unreconciled, precision_rounding=mv_line.currency_id.rounding):
                        amount = mv_line_dict['debit'] or mv_line_dict['credit']
                        sign = -1 if mv_line_dict['debit'] else 1
                        currency_rate_difference = sign * (mv_line.amount_residual - amount)
                        if not company_currency.is_zero(currency_rate_difference):
                            exchange_lines = self._get_exchange_lines(cr, uid, st_line, mv_line, currency_rate_difference, mv_line_dict['currency_id'], move_id, context=context)
                            for exchange_line in exchange_lines:
                                to_create.append(exchange_line)

                else:
                    mv_line_dict['debit'] = debit_at_current_rate
                    mv_line_dict['credit'] = credit_at_current_rate
            elif statement_currency.id != company_currency.id:
                # statement is in foreign currency but the transaction is in company currency
                prorata_factor = (mv_line_dict['debit'] - mv_line_dict['credit']) / st_line.amount_currency
                mv_line_dict['amount_currency'] = prorata_factor * st_line.amount
            to_create.append(mv_line_dict)
        # If the reconciliation is performed in another currency than the company currency, the amounts are converted to get the right debit/credit.
        # If there is more than 1 debit and 1 credit, this can induce a rounding error, which we put in the foreign exchane gain/loss account.
        if st_line_currency.id != company_currency.id:
            diff_amount = bank_st_move_vals['debit'] - bank_st_move_vals['credit'] \
                + sum(aml['debit'] for aml in to_create) - sum(aml['credit'] for aml in to_create)
            if not company_currency.is_zero(diff_amount):
                diff_aml = self.get_currency_rate_line(cr, uid, st_line, diff_amount, move_id, context=context)
                diff_aml['name'] = _('Rounding error from currency conversion')
                to_create.append(diff_aml)
        # Create move lines
        move_line_pairs_to_reconcile = []
        for mv_line_dict in to_create:
            counterpart_move_line_id = None  # NB : this attribute is irrelevant for aml_obj.create() and needs to be removed from the dict
            if mv_line_dict.get('counterpart_move_line_id'):
                counterpart_move_line_id = mv_line_dict['counterpart_move_line_id']
                del mv_line_dict['counterpart_move_line_id']
            new_aml_id = aml_obj.create(cr, uid, mv_line_dict, context=context)
            if counterpart_move_line_id != None:
                move_line_pairs_to_reconcile.append([new_aml_id, counterpart_move_line_id])
        # Reconcile
        for pair in move_line_pairs_to_reconcile:
            aml_obj.reconcile_partial(cr, uid, pair, context=context)
        # Mark the statement line as reconciled
        self.write(cr, uid, id, {'journal_entry_id': move_id}, context=context)

    # FIXME : if it wasn't for the multicompany security settings in
    # account_security.xml, the method would just
    # return [('journal_entry_id', '=', False)]
    # Unfortunately, that spawns a "no access rights" error;
    # it shouldn't.
    def _needaction_domain_get(self, cr, uid, vals, context=None):
        if context is None:
            context = {}
        user = self.pool.get("res.users").browse(cr, uid, uid)
        res = super(account_bank_statement_line, self)._needaction_domain_get(
            cr, uid, vals, context=context
        )
        res.append(
            '|', ('company_id', '=', False),
            ('company_id', 'child_of', [user.company_id.id]),
            ('amount', '=', True),
            ('journal_entry_id', '=', False),
            ('account_id', '=', False)
        )
        return res

    def _compute_reconcile_get(self, cr, uid, ids, field_name, args, context=None):
        if context is None:
            context = {}
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
        print "=>result", result
        return result

    def _compute_move_get(self, cr, uid, ids, field_name, args, context=None):
        if context is None:
            context = {}
        rec = self.browse(cr, uid, ids, context=context)[0]
        result = {}
        res = '-'
        move = rec.journal_entry_id
        if move:
            field_dict = self.pool.get('account.move').fields_get(
                cr, uid, ['state'], context=context)
            result_list = field_dict['state']['selection']
            res = filter(lambda x: x[0] == move.state, result_list)[0][1]
        result[rec.id] = res
        return result

    _columns = {
        'state': fields.related(
            'statement_id', 'state', type='selection',
            string='Statement State', readonly=True, store=True
        ),
        'val_date': fields.date(
            string='Value Date',  # nl: valuta datum
            states={'confirm': [('readonly', True)]}
        ),
        'journal_code': fields.related(
            'statement_id', 'journal_id', 'code',
            type='char', string='Journal', store=True, readonly=True
        ),
        'globalisation_id': fields.many2one(
            'account.bank.statement.line.global',
            string='Globalisation ID',
            states={'confirm': [('readonly', True)]},
            help="Code to identify transactions belonging to the same "
            "globalisation level within a batch payment"
        ),
        'globalisation_amount': fields.related(
            'globalisation_id', 'amount', type='float',
            string='Glob. Amount', readonly=True
        ),
        'counterparty_name': fields.char(
            string='Counterparty Name',
            states={'confirm': [('readonly', True)]}
        ),
        'counterparty_bic': fields.char(
            string='Counterparty BIC', size=11,
            states={'confirm': [('readonly', True)]}
        ),
        'counterparty_number': fields.char(
            string='Counterparty Number',
            states={'confirm': [('readonly', True)]}
        ),
        'counterparty_currency': fields.char(
            string='Counterparty Currency', size=3,
            states={'confirm': [('readonly', True)]}
        ),
        'payment_reference': fields.char(
            string='Payment Reference', size=35,
            states={'confirm': [('readonly', True)]},
            help="Payment Reference. For SEPA (SCT or SDD) transactions, "
                 "the EndToEndReference is recorded in this field."
        ),
        'creditor_reference_type': fields.char(
            # To DO : change field to selection list
            string='Creditor Reference Type', size=35,
            states={'confirm': [('readonly', True)]},
            help="Creditor Reference Type. For SEPA (SCT) transactions, "
                 "the <CdtrRefInf> type is recorded in this field."
                 "\nE.g. 'BBA' for belgian structured communication "
                 "(Code 'SCOR', Issuer 'BBA'"
        ),
        'creditor_reference': fields.char(
            'Creditor Reference',
            size=35,  # cf. pain.001.001.003 type="Max35Text"
            states={'confirm': [('readonly', True)]},
            help="Creditor Reference. For SEPA (SCT) transactions, "
                 "the <CdtrRefInf> reference is recorded in this field."
        ),
        'reconcile_get': fields.function(
            _compute_reconcile_get, type='char', string='Reconciled',
            store=True, readonly=True,
        ),
        'move_get': fields.function(
            _compute_move_get, type='char', string='Move', store=True,
            readonly=True,
        ),
        'move_state': fields.related(
            'journal_entry_id', 'state', type='selection',
            string='Move State', readonly=True
        ),
        # update existing fields
        'date': fields.date(string='Entry Date'),
        'partner_id': fields.many2one(
            'res.partner',
            domain=[
                '|', ('parent_id', '=', False),
                ('is_company', '=', True)
            ]
        ),
        'journal_entry_id': fields.many2one(
            'account.move', 'Journal Entry', copy=False
        ),
        'currency_id': fields.many2one(
            'res.currency', 'Currency',
            help="The optional other currency if it is a multi-currency "
            "entry."
        ),
        'amount_currency': fields.float(
            'Amount Currency', help="The amount expressed in an optional"
            " other currency if it is a multi-currency entry.",
            digits_compute=dp.get_precision('Account')
        ),
        'partner_name': fields.char(
            'Partner Name', help="This field is used to record the third"
            " party name when importing bank statement in electronic"
            " format, when the partner doesn't exist yet in the database"
            " (or cannot be found)."
        ),
        'bank_account_id': fields.many2one(
            'res.partner.bank', 'Bank Account'
        ),
    }

    def action_cancel(self, cr, uid, ids, context=None):
        """
        remove the account_id from the line for manual reconciliation
        """
        context = context or {}
        for line in self.browse(cr, uid, ids, context=context):
            if line.account_id:
                line.account_id = False
        self.cancel()
        return True

    def action_process(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        st_line = self.browse(cr, uid, ids, context=context)[0]
        ctx = dict(context)
        ctx.update({
            'act_window_from_bank_statement': True,
            'active_id': st_line.id,
            'active_ids': [st_line.id],
            'statement_id': st_line.statement_id.id,
            })

        move_id = st_line.journal_entry_id.id,
        mod_obj = self.pool.get('ir.model.data')
        move_view = mod_obj.get_object_reference(
            cr, uid, 'account_bank_statement_advanced',
            'view_move_from_bank_form'
        )
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
        act_move['context'] = dict(
            ctx, wizard_action=pickle.dumps(act_move)
        )
        return act_move

    def create(self, cr, uid, vals, context=None):
        """
        This method can be dropped after acceptance by Odoo of
        - PR 8397
        - PR 8396
        Until these Pull Requests have been merged you should install the
        account_bank_statement.diff patch shipped with this module
        (cf. doc directory)
        """
        if context is None:
            context = {}
        # cf. https://github.com/odoo/odoo/pull/8397
        if not vals.get('sequence'):
            lines = self.search(
                cr, uid,
                [('statement_id', '=', vals.get('statement_id'))],
                order='sequence desc', limit=1
            )
            lines_brw = self.browse(cr, uid, lines, context=context)
            if lines:
                seq = lines_brw[0].sequence
            else:
                seq = 0
            vals['sequence'] = seq + 1
        # cf. https://github.com/odoo/odoo/pull/8396
        if not vals.get('name'):
            vals['name'] = '/'
        return super(account_bank_statement_line, self).create(
            cr, uid, vals, context=context
        )


class account_statement_operation_template(orm.Model):
    _name = "account.statement.operation.template"
    _description = "Preset for the lines that can be created rec"
    _columns = {
        'name': fields.char(
            'Button Label', required=True
        ),
        'account_id': fields.many2one(
            'account.account', 'Account',
            ondelete='cascade',
            domain=[
                ('type', 'not in', ('view', 'closed', 'consolidation'))
            ]
        ),
        'label': fields.char('Label'),
        'amount_type': fields.selection(
            [('fixed', 'Fixed'),
             ('percentage_of_total', 'Percentage of total amount'),
             ('percentage_of_balance', 'Percentage of open balance')],
            'Amount type', required=True
        ),
        'amount': fields.float(
            'Amount', digits_compute=dp.get_precision('Account'),
            help="The amount will count as a debit if it is negative, as"
            " a credit if it is positive (except if amount type is "
            "'Percentage of open balance').",
            required=True
        ),
        'tax_id': fields.many2one(
            'account.tax', 'Tax',
            ondelete='restrict',
            domain=[
                ('type_tax_use', 'in', ['purchase', 'all']),
                ('parent_id', '=', False)
            ]
        ),
        'analytic_account_id': fields.many2one(
            'account.analytic.account', 'Analytic Account',
            ondelete='set null',
            domain=[
                ('type', '!=', 'view'),
                ('state', 'not in', ('close', 'cancelled'))
            ]
        ),
    }

    _defaults = {
        'amount_type': 'percentage_of_balance',
        'amount': 100.0
    }

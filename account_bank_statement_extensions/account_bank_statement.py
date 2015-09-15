# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#
#    Copyright (c) 2009-2015 Noviat nv/sa (www.noviat.com).
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
from openerp.osv import osv, orm, fields
from openerp.addons.decimal_precision import decimal_precision as dp
from openerp.tools.translate import _
import logging
_logger = logging.getLogger(__name__)


class account_bank_statement(orm.Model):
    _inherit = 'account.bank.statement'

    def write(self, cr, uid, ids, vals, context=None):
        if context is None:
            context = {}           
        for statement in self.browse(cr, uid, ids, context):
            st_type = statement.journal_id.type
            #if vals.get('line_ids', False) or context.get('ebanking_import', False):
            if st_type == 'bank':
                # bypass statement line resequencing (replaced by sequencing via statement line create method)
                super(osv.osv, self).write(cr, uid, [statement.id], vals, context=context)
            else:
                super(account_bank_statement, self).write(cr, uid, [statement.id], vals, context=context)
        return True


class account_bank_statement_line_global(orm.Model):
    _name = 'account.bank.statement.line.global'
    _description = 'Batch Payment Info'

    _columns = {
        'name': fields.char('OBI', size=128, required=True, help="Originator to Beneficiary Information"),
        'code': fields.char('Code', size=64, required=True),
        'parent_id': fields.many2one('account.bank.statement.line.global', 'Parent Code', ondelete='cascade'),
        'child_ids': fields.one2many('account.bank.statement.line.global', 'parent_id', 'Child Codes'),
        'type': fields.selection([
            ('iso20022', 'ISO 20022'),
            ('coda', 'CODA'),
            ('manual', 'Manual'),
            ], 'Type', required=True),
        'amount': fields.float('Amount', digits_compute=dp.get_precision('Account')),
        'payment_reference': fields.char('Payment Reference', size=35,
            help="Payment Reference. For SEPA (SCT or SDD) transactions, the PaymentInformationIdentification "\
                 "is recorded in this field."),
        'bank_statement_line_ids': fields.one2many('account.bank.statement.line', 'globalisation_id', 'Bank Statement Lines'),
    }
    _rec_name = 'code'
    _defaults = {
        'code': lambda s,c,u,ctx={}: s.pool.get('ir.sequence').get(c, u, 'account.bank.statement.line.global'),
        'name': '/',
    }
    # _sql_constraints = [
    #     ('code_uniq', 'unique (code)', 'The code must be unique !'),
    # ]

    def name_search(self, cr, user, name, args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
        ids = []
        if name:
            ids = self.search(cr, user, [('code', '=ilike', name)] + args, limit=limit)
            if not ids:
                ids = self.search(cr, user, [('name', operator, name)] + args, limit=limit)
            if not ids and len(name.split()) >= 2:
                #Separating code and name for searching
                operand1, operand2 = name.split(' ', 1) #name can contain spaces
                ids = self.search(cr, user, [('code', '=like', operand1), ('name', operator, operand2)] + args, limit=limit)
        else:
            ids = self.search(cr, user, args, context=context, limit=limit)
        return self.name_get(cr, user, ids, context=context)


class account_bank_statement_line(orm.Model):
    _inherit = 'account.bank.statement.line'
    _columns = {
        # new fields
        'state': fields.related('statement_id', 'state', type='char', relation='account.bank.statement',
            string='Statement State', readonly=True),
        'val_date': fields.date('Value Date',  # nl: valuta datum
            states={'confirm': [('readonly', True)]}),
        'journal_code': fields.related('statement_id', 'journal_id', 'code', type='char',
            relation='account.journal', string='Journal', store=True,
            states={'confirm': [('readonly', True)]}),
        'globalisation_id': fields.many2one('account.bank.statement.line.global', 'Globalisation ID',
            states={'confirm': [('readonly', True)]},
            help="Code to identify transactions belonging to the same globalisation level within a batch payment"),
        'globalisation_amount': fields.related('globalisation_id', 'amount', type='float',
            relation='account.bank.statement.line.global', string='Glob. Amount', readonly=True),
        'counterparty_name': fields.char('Counterparty Name', size=35,
            states={'confirm': [('readonly', True)]}),
        'counterparty_bic': fields.char('Counterparty BIC', size=11,
            states={'confirm': [('readonly', True)]}),
        'counterparty_number': fields.char('Counterparty Number', size=34,
            states={'confirm': [('readonly', True)]}),
        'counterparty_currency': fields.char('Counterparty Currency', size=3,
            states={'confirm': [('readonly', True)]}),
        'payment_reference': fields.char('Payment Reference', size=35,
            states={'confirm': [('readonly', True)]},
            help="Payment Reference. For SEPA (SCT or SDD) transactions, the EndToEndReference "\
                 "is recorded in this field."),
        'creditor_reference_type': fields.char('Creditor Reference Type', size=35,  # To DO : change field to selection list
            states={'confirm': [('readonly', True)]},
            help="Creditor Reference Type. For SEPA (SCT) transactions, "\
                 "the <CdtrRefInf> type is recorded in this field."\
                 "\nE.g. 'BBA' for belgian structured communication (Code 'SCOR', Issuer 'BBA'"),
        'creditor_reference': fields.char('Creditor Reference', size=35,  # cf. pain.001.001.003 type="Max35Text"
            states={'confirm': [('readonly', True)]},
            help="Creditor Reference. For SEPA (SCT) transactions, "\
                 "the <CdtrRefInf> reference is recorded in this field."),
        # update existing fields
        'date': fields.date('Entry Date', required=True),
        'partner_id': fields.many2one(
            'res.partner', 'Partner',
            domain=['|', ('parent_id', '=', False), ('is_company', '=', True)]),
    }

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if context.get('block_statement_line_delete', False):
            raise orm.except_orm(_('Warning'), _('Delete operation not allowed ! \
            Please go to the associated bank statement in order to delete and/or modify this bank statement line'))
        return super(account_bank_statement_line, self).unlink(cr, uid, ids, context=context)

    def create(self, cr, uid, vals, context=None):
        if not vals.get('statement_id'):
            raise orm.except_orm(_('Error !'),
                _("Please recalculate the statement balance first via the 'Compute' button"))
        if not vals.get('sequence'):
            l_ids = self.search(cr, uid, [('statement_id','=', vals['statement_id'])], order='sequence desc', limit=1)
            if l_ids:
                l_seq = self.read(cr, uid, l_ids[0], ['sequence'])['sequence']
            else:
                l_seq = 0
            vals['sequence'] = l_seq + 1
        return super(account_bank_statement_line, self).create(cr, uid, vals, context=context)


# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import math

from openerp.osv import orm


class res_currency(orm.Model):
    _inherit = 'res.currency'

    def get_format_currencies_js_function(self, cr, uid, context=None):
        """ Returns a string that can be used to instanciate a javascript function that formats numbers as currencies.
            That function expects the number as first parameter and the currency id as second parameter. In case of failure it returns undefined."""
        function = ""
        row_ids = self.search(cr, uid, [], context=context)
        for row in self.read(
            cr, uid, row_ids, fields=['id', 'name', 'symbol', 'rounding', 'position'],
            context=context
        ):
            digits = int(math.ceil(math.log10(1 / row['rounding'])))
            symbol = row['symbol'] or row['name']

            format_number_str = "openerp.web.format_value(arguments[0], {type: 'float', digits: [69," + str(digits) + "]}, 0.00)"
            if row['position'] == 'after':
                return_str = "return " + format_number_str + " + '\\xA0" + symbol + "';"
            else:
                return_str = "return '" + symbol + "\\xA0' + " + format_number_str + ";"
            function += "if (arguments[1] === " + str(row['id']) + ") { " + return_str + " }"
        return function

<!DOCTYPE>
<html>
<head>
    <style type="text/css">
        ${css}
    </style>
</head>

<!--margion_top : 20-->
<body>
    %for o in objects :
          <div class="page">
            <h2>
              <span>Bank Statement Balances Report</span>
              <span>${o.date_balance or ''}</span>
            </h2>

            <table class="table table-condensed">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Date</th>
                  <th>Journal</th>
                  <th class="text-right">Closing Balance</th>
                </tr>
              </thead>
              <tbody>
                %for l in o.lines:
                <tr>
                  <td>
                    <span>${ l['s_name'] or ''}</span>
                  </td>
                  <td>
                    <span>${ l['s_date'] or ''}</span>
                  </td>
                  <td>
                    <span>${ l['j_code'] or ''} </span>
                  </td>
                  <td class="text-right">
                    <span> ${ formatLang( l['s_balance']) l['currency'] or ''}</span>
                  </td>
                </tr>
              </tbody>
              %endfor
              <tfoot>
                %for t in o.totals:
                <tr>
                  <td>
                    &amp;nbsp;
                  </td>
                  <td>
                    &amp;nbsp;
                  </td>
                  <td>
                    <strong>
                      <span>Total</span>
                      <span> ${str(len(totals)&gt;1 and + ' ' + t['currency'].symbol) or ''}</span>
                    </strong>
                  </td>
                  <td class="text-right">
                    <strong>
                      <span>$ ${formatLang(t['total_amount']) currency_obj=t['currency'] or '' }</span>
                    </strong>
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>
        </t>
      </t>
    </template>

  </data>
</openerp>

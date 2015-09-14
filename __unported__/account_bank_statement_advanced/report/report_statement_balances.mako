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
    ${set_global_data(o)}
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
                <span>${ l.s_name or ''}</span>
              </td>
              <td>
                <span>${ l.s_date or ''}</span>
              </td>
              <td>
                <span>${ l.j_code or ''} </span>
              </td>
              <td class="text-right">
                <span>$ ${ formatLang(l.s_balance) or ''}</span>
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
                  <span> ${len(o.totals) or ''}</span>
                </strong>
              </td>
              <td class="text-right">
                <strong>
                  <span>$ ${formatLang(t.total_amount) or '' }</span>
                </strong>
              </td>
            </tr>
            %endfor
          </tfoot>
        </table>
      </div>
  %endfor
</body>

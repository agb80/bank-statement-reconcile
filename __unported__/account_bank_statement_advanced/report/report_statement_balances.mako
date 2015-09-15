<!DOCTYPE>
<html>
<head>
    <style type="text/css">
        ${css}
    </style>
</head>
<body>
    %for o in objects :
      <div class="page">
        <h2>
          <span>Bank Statement Balances Report</span>

          <span>${o.date_balance or ''}</span>
        </h2>
        <hr/>

        <table class="basic_table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Date</th>
              <th>Journal</th>
              <th class="text-right">Closing Balance</th>
            </tr>
          </thead>
          <tbody>
            %for l in lines:
            <tr>
              <td class="basic_td">
                <span>${ l['s_name'] or ''}</span>
              </td>
              <td class="basic_td">
                <span>${ l['s_date'] or ''}</span>
              </td>
              <td class="basic_td">
                <span>${ l['j_code'] or ''} </span>
              </td>
              <td class="text-right">
                <span>$ ${ formatLang(l['s_balance']) or ''}</span>
              </td>
            </tr>
          </tbody>
          %endfor
          <tfoot>
            %for t in totals:
            <tr class="basic_tr">
              <td class="basic_td">
                &nbsp;
              </td>
              <td class="basic_td">
                &nbsp;
              </td>
              <td class="basic_td">
                <strong>
                  <span>Total</span>
                  <span> ${ len(totals) or ''}</span>
                </strong>
              </td>
              <td class="basic_td text-right">
                <strong>
                  <span>$ ${formatLang(t['total_amount']) or '' }</span>
                </strong>
              </td>
            </tr>
            %endfor
          </tfoot>
        </table>
      </div>
  %endfor
</body>

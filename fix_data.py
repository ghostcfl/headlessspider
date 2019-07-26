from flask import Flask, render_template, request
from sql import Sql
from settings import SQL_SETTINGS

app = Flask(__name__)


@app.route('/')
def result():
    sql_ele = Sql(**SQL_SETTINGS)
    res = sql_ele.select_data('tb_order_spider', 0, "*", orderNo='553392578891239204')
    res2 = sql_ele.select_data('tb_order_detail_spider', 0, "*", orderNo='553392578891239204')
    print(res)
    # dict = {'phy': 50, 'che': 60, 'maths': 70}
    return render_template('fix_data.html', result=res[0], item=res2)


@app.route('/fix', methods=['POST', 'GET'])
def fix():
    if request.method == 'POST':
        # result = request.form
        result = request.form
        item = result.to_dict()
        print(item)
        couponPrice = item['couponPrice']
        unitPrice = item['unitPrice']
        print(couponPrice)
        print(unitPrice)
    return "Success"


if __name__ == '__main__':
    app.run()

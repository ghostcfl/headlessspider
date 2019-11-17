from flask import Flask, render_template, request
from mysql import Sql
from settings import SQL_SETTINGS

app = Flask(__name__)


@app.route('/<id>')
def result(id):
    sql_ele = Sql(**SQL_SETTINGS)
    res = sql_ele.select_data('tb_order_spider', 0, "*", orderNo=id)
    res2 = sql_ele.select_data('tb_order_detail_spider', 0, "*", orderNo=id)
    print(res)
    # dict = {'phy': 50, 'che': 60, 'maths': 70}
    return render_template('fix_data.html', result=res[0], item=res2)


@app.route('/fix', methods=['POST', 'GET'])
def fix():
    sql_ele = Sql(**SQL_SETTINGS)
    if request.method == 'POST':
        # result = request.form
        result = request.form
        item = result.to_dict()
        sql_ele.update_old_data('tb_order_spider', {'couponPrice': item['couponPrice']}, {'orderNo': item['orderNo']})
        sql_ele.update_old_data('tb_order_detail_spider', {'unitPrice': item['unitPrice']},
                                {'orderNo': item['orderNo'], 'itemNo': item['itemNo']})
    return "Success"


@app.route('/test')
def test():
    return render_template('1.html')


if __name__ == '__main__':
    app.run()

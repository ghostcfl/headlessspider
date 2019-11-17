import requests, re, mysql
from pyquery import PyQuery as pq
from flask import Flask, render_template, request
from Format import concat, time_now
from settings import SQL_SETTINGS

app = Flask(__name__)


@app.route('/')
def form():
    return render_template('form.html')


@app.route('/result', methods=['POST', 'GET'])
def result():
    if request.method == 'POST':
        result = request.form
        item = result.to_dict()
        itemID = item['itemID'].strip()
        res = requests.get("https://item.taobao.com/item.htm?id=%s" % (str(itemID)))
        content = res.text
        a = re.findall('";(.*?);".*?e":"(\d+\.\d+)', content)
        if a:
            j = []
            for i in range(len(a)):
                item = get_detail(content)
                item['price_tb'] = a[i][1]
                y = {"data-value": a[i][0], "price": a[i][1]}
                d = y['data-value'].split(";")
                attr = []
                for l in d:
                    pattern = 'data-value="' + l + '".*?\s+.*?\s+<span>(.*?)</span>'
                    g = re.search(pattern, content).group(1)
                    attr.append(g)
                # y['attribute'] = attr
                item['attribute'] = "-".join(attr)
                j.append(item)
            #     t = concat(item, ',')
            #     j.append(t)
            # return "<br>".join(j)
            return render_template('competitor_data.html', result=j)
        else:
            j = []
            item = get_detail(content)
            k = "".join(re.findall('<input.*?name="current.*?"(\d+\.\d+)', content))
            item['price_tb'] = k
            item['attribute'] = ""
            j.append(item)
            return render_template('competitor_data.html', result=j)


def get_detail(content):
    item = {}
    # print(content)
    doc = pq(content)
    item['link_id'] = doc.find("#J_Pine").attr("data-itemid")
    item['shop_id'] = doc.find("#J_Pine").attr("data-shopid")
    item['typeabbrev'] = ""
    item['price_erp'] = 0
    item['currabrev'] = "CNY"
    item['operator'] = ""
    item['last_time'] = time_now()
    item['flag'] = "add"
    item['freight'] = doc("#J_WlServiceTitle").text()
    item['ratio'] = 1
    item['promotionprice'] = 0
    item['package_number'] = 1
    item['SpiderDate'] = time_now()
    item['Checker'] = ""
    item['CheckDate'] = time_now()
    item["description"] = doc.find(".tb-main-title").text()
    item["rates"] = doc.find("#J_RateCounter").text()
    if item['rates'] == "-":
        item['rates'] = 0
    item["sales"] = doc.find("#J_SellCounter").text()
    if item['sales'] == "-":
        item['sales'] = 0
    # print(item)
    return item


@app.route('/competitor', methods=['POST', 'GET'])
def competitor_data():
    if request.method == 'POST':
        # print("adlsfjlsdjf")
        result = request.form
        res = result.to_dict()
        stk_list = result.getlist("stockid[]")
        res.pop("stockid[]")
        attr_list = result.getlist("attribute[]")
        res.pop("attribute[]")
        price_list = result.getlist("price_tb[]")
        res.pop("price_tb[]")
        pgn_list = result.getlist("package_number[]")
        res.pop("package_number[]")
        for i in range(len(stk_list)):
            item = res.copy()
            item['stockid'] = stk_list[i]
            if not item['stockid']:
                continue
            item['attribute'] = attr_list[i]
            item['price_tb'] = price_list[i]
            pgn = item.pop("package_number_t")
            if int(pgn_list[i]) > 1:
                item['package_number'] = pgn_list[i]
            elif int(pgn) > 1:
                item['package_number'] = pgn
            else:
                item['package_number'] = 1
            c = {"stockid": item["stockid"], "link_id": item["link_id"]}
            res_sql = mysql.get_data(c=c, t="prices_tb")
            if res_sql:
                mysql.update_data(set=item, c=c, t="prices_tb")
            else:
                mysql.insert_data(d=item, t="prices_tb")
            # print(res)
            # print(item)
    return "添加成功!"


if __name__ == '__main__':
    app.run()

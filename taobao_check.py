from sql import Sql
from settings import SQL_SETTINGS
from Format import time_zone


def taobao_check():
    sql_element = Sql(**SQL_SETTINGS)
    today = time_zone("0:00")
    res = sql_element.select_dict(
        """
        select OrderNo as orderNo,StocksCatTotal,Total
        from taobaoorders 
        where importdate>'%s' and spiderFlag='0'
        """ % (today)
    )
    # print(today)
    # print(res)
    for r in res:
        out_list = []
        # print(r)
        itemNum = sql_element.select_dict(
            "select count(itemNo) from tb_order_detail_spider where orderNo='%s'" % (r['orderNo']))
        if itemNum:
            actualFee = sql_element.select_dict(
                "select actualFee from tb_order_spider where orderNo='%s'" % (r['orderNo']))
            if r['StocksCatTotal'] != itemNum[0]['count(itemNo)']:
                out_list.append("宝贝种类数量不一致！导入了%d个宝贝种类，爬取了%d个宝贝种类"
                                % (r['StocksCatTotal'], itemNum[0]['count(itemNo)']))
            elif actualFee:
                if r['Total'] - actualFee[0]['actualFee'] != 0:
                    out_list.append("订单总价不一致，爬虫修正（%f ==> %f)" % (r['Total'], actualFee[0]['actualFee']))
                    # print("and".join(out_list))
            else:
                out_list.append("1")
            sql_element.update_old_data("taobaoorders",
                                        {'Total': actualFee[0]['actualFee'],
                                         'spiderFlag': "and".join(out_list)},
                                        {'OrderNo': r['orderNo']})

        res_detail = sql_element.select_dict("select *  from taobaoordersdetail where OrderNo='%s'" % (r['orderNo']))

        for rd in res_detail:
            spider_detail = sql_element.select_dict(
                "select * from tb_order_detail_spider where OrderNo='%s' and goodsCode='%s'" % (
                    r['orderNo'], rd['ShopCode']))
            if spider_detail:

                for sd in spider_detail:
                    price = (sd['unitPrice'] * sd['sellNum'] - sd['unitBenefits']) / sd['sellNum']
                    if price - rd['Price'] != 0:
                        out_str = "爬虫修正宝贝平均成交单价(%f ==> %f)" % (rd['Price'], price)
                        print(round(price, 2))
                        print(out_str)
                        sql_element.update_old_data('taobaoordersdetail',
                                                    {'Price': round(price, 2), 'spiderFlag': out_str},
                                                    {'orderNo': r['orderNo'], 'ShopCode': rd['ShopCode']})


if __name__ == '__main__':
    taobao_check()

import mysql, re
from settings import test_server as ts
from Format import time_zone, time_now, sleep
from logger import get_logger

logger = get_logger()


def taobao_check():
    test_server = ts.copy()
    test_server['db'] = 'test'
    today = time_zone(["00:00"])[0]
    # 查询表erp导入脚本标记为8并且已被爬虫爬取到的数据
    sql = """
    SELECT t.OrderNo as orderNo,t.StocksCatTotal,t.RealPay,t.StoreName,t.CreatDate
    FROM taobaoorders AS t JOIN tb_order_spider AS s
    ON t.OrderNo = s.orderNo
    WHERE t.Flag=8 AND s.isVerify=1;
    """
    res = mysql.get_data(sql=sql, dict_result=True)

    if res:
        pass
    else:
        logger.info("没有数据")
        return

    for r in res:
        # 获取今日报告的数据，如果没有就初始一个0的数据

        sql = """
        select * from spider_reports
        where reports_date='%s'
        and reports_type = '优惠差额报告' and store_name='%s'
        """ % (today, r['StoreName'])

        report = mysql.get_data(db=test_server, dict_result=True, sql=sql)

        if report:
            fix_total = report[0]['price']
            count = report[0]['count']
            flag = 'update'
        else:
            fix_total = 0
            count = 0
            flag = 'create'

        out_list = []
        itemNum = mysql.get_data(t="tb_order_detail_spider", cn=["count(itemNo)"], c={"orderNo": r["orderNo"]},
                                 dict_result=True)
        if itemNum:
            actualFee = mysql.get_data(t="tb_order_spider", cn=["actualFee"], c={"orderNo": r["orderNo"]},
                                       dict_result=True)
            if r['StocksCatTotal'] != itemNum[0]['count(itemNo)']:
                out_list.append("宝贝种类数量不一致！导入了%d个宝贝种类，爬取了%d个宝贝种类"
                                % (r['StocksCatTotal'], itemNum[0]['count(itemNo)']))
            elif actualFee:
                if r['RealPay'] - actualFee[0]['actualFee'] != 0:
                    out_list.append("订单总价不一致，爬虫修正（%.2f ==> %.2f)" % (r['RealPay'], actualFee[0]['actualFee']))
                    mysql.update_data(t="taobaoorders",
                                      set={'RealPay': actualFee[0]['actualFee']},
                                      c={'OrderNo': r['orderNo']})
                else:
                    out_list.append("1")
            mysql.update_data(t="taobaoorders",
                              set={'RealPay': actualFee[0]['actualFee'], 'Flag': 0,
                                   'spiderFlag': "and".join(out_list)},
                              c={'OrderNo': r['orderNo']})
        res_detail = mysql.get_data(t="taobaoordersdetail", c={"OrderNo": r["orderNo"]}, dict_result=True)
        if res_detail:
            pass
        else:
            continue
        for rd in res_detail:
            spider_detail = mysql.get_data(t="tb_order_detail_spider",
                                           c={"orderNo": r["orderNo"], "goodsCode": rd["ShopCode"],
                                              "itemNo": rd["LineNo"]},
                                           dict_result=True)
            if len(spider_detail) == 1:

                for sd in spider_detail:
                    price = (sd['unitPrice'] * sd['sellNum'] - sd['unitBenefits']) / sd['sellNum']
                    fix_total += rd['Price'] - price
                    count += 1
                    if price - rd['Price'] != 0:
                        out_str = "%.2f ==> %.2f" % (rd['Price'], price)
                    else:
                        out_str = '1'
                    mysql.update_data(t="taobaoordersdetail",
                                      set={'Price': round(price, 2), 'spiderFlag': out_str,
                                           'YouHui': sd['unitBenefits']},
                                      c={'Id': rd['Id']})
            else:
                logger.error("订单报错：" + r["orderNo"])
        if flag == 'create':
            mysql.insert_data(t="spider_reports",
                              d={'reports_type': '优惠差额报告',
                                 'reports_date': today,
                                 'count': count,
                                 'price': round(fix_total, 2),
                                 'store_name': r['StoreName'], },
                              db=test_server)
        elif flag == 'update':
            mysql.update_data(t="spider_reports",
                              set={'count': count, 'price': round(fix_total, 2), },
                              c={'reports_type': '优惠差额报告', 'reports_date': today, 'store_name': r['StoreName'], },
                              db=test_server
                              )


if __name__ == '__main__':
    while True:
        taobao_check()
        sleep(1)

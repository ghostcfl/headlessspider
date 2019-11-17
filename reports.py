import datetime, time
from smtp import mail
from mysql import Sql
from Format import store_trans, time_zone
from maintain_price import MaintainPrice


class Reports():
    def __init__(self):
        db_test = {'host': 'www.veatao.com', 'port': 3306, 'user': 'test', 'password': 'sz123456', 'db': 'test'}
        self.sql_element = Sql(**db_test)

    def reports_in(self, fromStore, price):
        reports = {}
        reports['reports_type'] = '订单爬虫报告'
        reports['store_name'] = store_trans(fromStore)
        reports['reports_date'] = datetime.date.today()
        temp = reports.copy()
        res = self.sql_element.select_data("spider_reports", 1, *['count', 'price'], **reports)
        if res:
            reports['count'] = res[0][0] + 1
            reports['price'] = res[0][1] + price
            self.sql_element.update_old_data("spider_reports", reports, temp)
        else:
            reports['count'] = 1
            reports['price'] = price
            self.sql_element.insert_new_data("spider_reports", **reports)

    def reports_mail(self):
        # results = self.sql_element.select_dict("""select * from spider_reports
        # where reports_date='%s'
        # """ % (str(datetime.date.today())))
        # string = ""
        # for result in results:
        #     if result['reports_type'] == '订单爬虫报告':
        #         string += str(result['reports_date']) + " "
        #         string += result['store_name'] + " " + result['reports_type'] + ":\n"
        #         string += "今日共爬取新订单数：" + str(result['count']) + " 条\n"
        #         string += "订单总金额：" + str(result['price']) + " 元\n"
        #     elif result['reports_type'] == '优惠差额报告':
        #         string += str(result['reports_date']) + " "
        #         string += result['store_name'] + " " + result['reports_type'] + ":\n"
        #         string += "今日导入修正订单优惠价格数量：" + str(result['count']) + " 条\n"
        #         string += "总优惠金额：" + str(result['price']) + " 元\n"
        # print(result)
        # print(string)

        # mail('订单爬虫报告', string, ['946930866@qq.com', 'szjavali@qq.com'])
        mail('订单爬虫报告', "abc", ['946930866@qq.com'])


def run():
    t = time_zone(["23:00", "23:10"])
    t1, t2 = t[0], t[1]
    while True:
        now = datetime.datetime.now()
        if t1 < now < t2:
            r = Reports()
            m = MaintainPrice()
            m.report_mail()
            r.reports_mail()
            break
        print(">", end="", flush=True)
        time.sleep(1)
    while True:
        now = datetime.datetime.now()
        if now > t2:
            break
        print(">", end="", flush=True)
        time.sleep(1)
    run()


if __name__ == '__main__':
    run()

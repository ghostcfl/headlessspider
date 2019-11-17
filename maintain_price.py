import datetime, mysql
from Format import time_now, date_now_str, time_zone
from smtp import mail_reports
import pandas as pd


class MaintainPrice():
    report_item = {}
    db_test = {'host': 'www.veatao.com', 'port': 3306, 'user': 'test', 'password': 'sz123456', 'db': 'test'}

    def get_link_id(self, **kwargs):
        shop_id = self.shop_id(fromStore=kwargs['fromStore'])
        result = mysql.get_data(t="prices_tb",
                                cn=["link_id"],
                                c={"stockid": kwargs['goodsCode'], "shop_id": shop_id,
                                   "attribute": kwargs['goodsAttribute']})
        # result = self.sql_temp.select_data('prices_tb', 0, 'linkId', **kwargs_temp)
        if len(result) == 1:
            return result[0][0]
        else:
            return None

    def shop_id(self, fromStore):
        res = mysql.get_data(t="shop_info", l=1, c={"typeabbrev": fromStore, "shopindex": 0})
        if res:
            return res[0][0]

    def data_compare(self, **kwargs):
        res = mysql.get_data(t="prices_tb", cn=["price_tb", "SpiderDate"],
                             c={"stockid": kwargs["goodsCode"], "link_id": kwargs["link_id"],
                                "shop_id": self.shop_id(kwargs["fromStore"])})

        if res:
            # d = datetime.datetime.strptime(res[0][1], "%Y-%m-%d %H:%M:%S")
            # print(type(res[0][1]))
            update_condition = float(kwargs['unitPrice']) - float(res[0][0])
            ratio = float(kwargs['unitPrice']) / float(res[0][0])
            if res[0][1] == '0000-00-00 00:00:00':
                return "更新", ratio
            days = (datetime.datetime.now() - res[0][1]).days
            if abs(update_condition) >= 0.01 or days > 7:
                self.report_item['price_before'] = res[0][0]
                return "更新", ratio
            else:
                return None, None

        else:
            return "创建", None

    def maintain(self, operation, **kwargs):
        item = {'stockid': kwargs['goodsCode'],
                'link_id': kwargs['link_id'],
                'shop_id': self.shop_id(kwargs['fromStore']),
                'price_tb': kwargs['unitPrice'],
                # 'first_discount': kwargs['unitBenefits'],
                'currabrev': 'CNY',
                'operator': '爬虫维护',
                'SpiderDate': time_now(),
                'attribute': kwargs['goodsAttribute'],
                'flag': None,
                'description': kwargs['tbName'],
                'typeabbrev': "",
                'price_erp': 0,
                'last_time': time_now(),
                'freight': "",
                'ratio': 1,
                'promotionprice': 0,
                'sales': 0,
                'rates': 0,
                'Checker': "",
                'package_number': 1,
                'CheckDate': time_now(),
                }
        if operation == "更新":
            item['flag'] = 'update'
            item_set = {
                'SpiderDate': time_now(),
                'flag': 'update',
                'price_tb': kwargs['unitPrice'],
                'description': kwargs['tbName'],
                'ratio': kwargs['ratio'],
                'attribute': kwargs['goodsAttribute'],
                # 'first_discount': kwargs['unitBenefits']
            }
            item_where = {
                'stockid': kwargs['goodsCode'],
                'link_id': kwargs['link_id'],
                'shop_id': self.shop_id(kwargs['fromStore'])
            }
            mysql.update_data(t="prices_tb", set=item_set, c=item_where)
        elif operation == "创建":
            item['flag'] = 'create'
            mysql.insert_data(t="prices_tb", d=item)
        else:
            item['flag'] = 'lookup'
        self.report_in(**item)

    def fix_data(self, **kwargs):
        e = self.sql_temp.insert_new_data('fix_data', **kwargs)
        if e:
            print(e)

    def report_in(self, **kwargs):

        if kwargs['flag'] == 'lookup':
            res = mysql.get_data("update_reports", l=1, cn=["lookup"], c={"link_id": "count"}, db=self.db_test)
            mysql.update_data(t="update_reports",
                              set={'lookup': res[0][0] + 1, 'last_time': kwargs['SpiderDate']},
                              c={'link_id': 'count', 'shop_id': kwargs['shop_id']})
        else:
            self.report_item['stockid'] = kwargs['stockid']
            self.report_item['link_id'] = kwargs['link_id']
            self.report_item['shop_id'] = kwargs['shop_id']
            self.report_item['price_tb'] = kwargs['price_tb']
            # self.report_item['first_discount'] = kwargs['first_discount']
            self.report_item['last_time'] = kwargs['SpiderDate']
            self.report_item['attribute'] = kwargs['attribute']
            self.report_item['flag'] = kwargs['flag']
            self.report_item['description'] = kwargs['description']
            mysql.insert_data(t="update_reports", d=self.report_item, db=self.db_test)

    def report_mail(self):
        d = time_zone(["18:05", "18:05"])
        d1, d2 = d[0], d[1]
        d = (d1 - datetime.timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
        sql = "SELECT shop_id,flag,COUNT(flag),lookup FROM update_reports " \
              "WHERE last_time < '%s' AND last_time > '%s' " \
              "GROUP BY Flag,shop_id" % (d1, d)
        sql2 = "SELECT * FROM update_reports WHERE last_time < '%s' AND last_time > '%s' " % (d1, d)
        res = mysql.get_data(sql=sql, db=self.db_test)
        con, c, cd = mysql.connection(self.db_test)
        df = pd.read_sql(sql2, con)
        con.close()
        date = date_now_str()
        df.to_csv("./reports/reports" + date + ".csv")
        out_list = []
        out_list.append("今日爬虫维护 开源店 价格  ：<br>")
        for r in res:
            # print(r)
            if r[0] == '115443253':
                if r[1] == 'create':
                    string = '创建了 ' + str(r[2]) + ' 条数据。<br>'
                    out_list.append(string)
                elif r[1] == 'update':
                    string = '更新了 ' + str(r[2]) + ' 条数据。<br>'
                    out_list.append(string)
                elif r[1] == 'lookup':
                    string = '查看了 ' + str(r[3]) + ' 条数据。<br>'
                    out_list.append(string)
        out_list.append("今日爬虫维护 玉佳企业店 价格：<br>")
        for r in res:
            # print(r)
            if r[0] == '197444037':
                if r[1] == 'create':
                    string = '创建了 ' + str(r[2]) + ' 条数据。<br>'
                    out_list.append(string)
                elif r[1] == 'update':
                    string = '更新了 ' + str(r[2]) + ' 条数据。<br>'
                    out_list.append(string)
                elif r[1] == 'lookup':
                    string = '查看了 ' + str(r[3]) + ' 条数据。<br>'
                    out_list.append(string)
        out_list.append("今日爬虫维护 赛宝电子店 价格：<br>")
        for r in res:
            # print(r)
            if r[0] == '34933991':
                if r[1] == 'create':
                    string = '创建了 ' + str(r[2]) + ' 条数据。<br>'
                    out_list.append(string)
                elif r[1] == 'update':
                    string = '更新了 ' + str(r[2]) + ' 条数据。<br>'
                    out_list.append(string)
                elif r[1] == 'lookup':
                    string = '查看了 ' + str(r[3]) + ' 条数据。<br>'
                    out_list.append(string)
        out_list.append("今日爬虫维护 玉佳电子店 价格：<br>")
        for r in res:
            # print(r)
            if r[0] == '68559944':
                if r[1] == 'create':
                    string = '创建了 ' + str(r[2]) + ' 条数据。<br>'
                    out_list.append(string)
                elif r[1] == 'update':
                    string = '更新了 ' + str(r[2]) + ' 条数据。<br>'
                    out_list.append(string)
                elif r[1] == 'lookup':
                    string = '查看了 ' + str(r[3]) + ' 条数据。<br>'
                    out_list.append(string)
        # print("".join(out_list))
        mail_reports("爬虫更新erp价格报告", "".join(out_list), date, *["946930866@qq.com", 'szjavali@qq.com'])  #
        dt = (d1 - datetime.timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S")
        print(dt)
        sql = "delete from update_reports where last_time<'%s'" % (dt)
        mysql.delete_data(sql=sql, db=self.db_test)
        mysql.update_data(t="update_reports", set={"loopup": 0}, c={"link_id": "count"})


if __name__ == '__main__':
    # a = m.data_compare(**{'goodsCode': "000001", 'tbName': 'abc', 'fromStore': "YK"})
    m = MaintainPrice()
    a = m.report_mail()
    # print(a)

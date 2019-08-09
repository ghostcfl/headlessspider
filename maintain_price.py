import datetime
from settings import SQL_SETTINGS
from Format import time_now, date_now_str, time_zone
from sql import Sql
from smtp import mail_reports
import pandas as pd


class MaintainPrice():
    report_item = {}

    def __init__(self):
        self.sql_element = Sql(**SQL_SETTINGS)
        db_test = SQL_SETTINGS.copy()
        db_test['db'] = 'test'
        self.sql_temp = Sql(**db_test)

    def shop_id(self, fromStore):
        res = self.sql_element.select_data('salestypes', 0, 'shop_id', typeabbrev=fromStore)
        return res[0][0]

    def data_compare(self, **kwargs):
        res = self.sql_element.select("""
            SELECT price_tb FROM prices_tb 
            WHERE stockid='%s' AND link_id='%s' AND shop_id='%s' 
            ORDER BY last_time DESC LIMIT 1 
            """ % (kwargs['goodsCode'], kwargs['link_id'], self.shop_id(fromStore=kwargs['fromStore'])))
        if res:
            if float(kwargs['unitPrice']) - float(res[0][0]) != 0:
                self.report_item['price_before'] = res[0][0]
                return "更新"
            else:
                return None

        else:
            return "创建"

    def maintain(self, operation, **kwargs):
        item = {'stockid': kwargs['goodsCode'],
                'link_id': kwargs['link_id'],
                'shop_id': self.shop_id(kwargs['fromStore']),
                'price_tb': kwargs['unitPrice'],
                'currabrev': 'CNY',
                'operator': '爬虫维护',
                'last_time': time_now(),
                'attribute': kwargs['goodsAttribute'],
                'flag': None,
                'description': kwargs['tbName'],
                }
        if operation == "更新":
            item['flag'] = 'update'
            self.sql_element.insert_new_data('prices_tb', **item)
        elif operation == "创建":
            item['flag'] = 'create'
            self.sql_element.insert_new_data('prices_tb', **item)
            # print(self.sql_element.insert_new_data_sql('prices_tb', **item))
        else:
            item['flag'] = 'lookup'
        self.report_in(**item)

    def get_link_id(self, **kwargs):
        kwargs_temp = {'goodsCode': kwargs['goodsCode'],
                       'fromStore': kwargs['fromStore'],
                       'tbName': kwargs['tbName'],
                       }
        result = self.sql_temp.select_data('prices_tb', 0, 'linkId', **kwargs_temp)
        if result:
            return result[0][0]
        else:
            return None

    def fix_data(self, **kwargs):
        e = self.sql_temp.insert_new_data('fix_data', **kwargs)
        if e:
            print(e)

    def report_in(self, **kwargs):
        if kwargs['flag'] == 'lookup':
            res = self.sql_temp.select_data('update_reports', 1, "lookup", link_id='count')
            self.sql_temp.update_old_data("update_reports",
                                          {'lookup': res[0][0] + 1, 'last_time': kwargs['last_time']},
                                          {'link_id': 'count', 'shop_id': kwargs['shop_id']})
        else:
            self.report_item['stockid'] = kwargs['stockid']
            self.report_item['link_id'] = kwargs['link_id']
            self.report_item['shop_id'] = kwargs['shop_id']
            self.report_item['price_tb'] = kwargs['price_tb']
            self.report_item['last_time'] = kwargs['last_time']
            self.report_item['attribute'] = kwargs['attribute']
            self.report_item['flag'] = kwargs['flag']
            self.report_item['description'] = kwargs['description']
            self.sql_temp.insert_new_data('update_reports', **self.report_item)

    def report_mail(self):
        d1, d2 = time_zone("18:00", "18:00")
        d = (d1 - datetime.timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
        sql = "SELECT shop_id,flag,COUNT(flag),lookup FROM update_reports " \
              "WHERE last_time < '%s' AND last_time > '%s' " \
              "GROUP BY Flag,shop_id" % (d1, d)
        sql2 = "SELECT * FROM update_reports WHERE last_time < '%s' AND last_time > '%s' " % (d1, d)
        res = self.sql_temp.select(sql)
        df = pd.read_sql(sql2, self.sql_temp.con)
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
        # print("".join(out_list))
        mail_reports("爬虫更新erp价格报告", "".join(out_list), date, *["946930866@qq.com", 'szjavali@qq.com'])  #
        try:
            dt = (d1 - datetime.timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S")
            print(dt)
            self.sql_temp.cursor.execute("delete from update_reports where last_time<%s", dt)
            self.sql_temp.cursor.execute("update update_reports set lookup=0 where link_id='count'")
        except Exception as e:
            self.sql_temp.con.rollback()
        else:
            self.sql_temp.con.commit()


if __name__ == '__main__':
    # a = m.data_compare(**{'goodsCode': "000001", 'tbName': 'abc', 'fromStore': "YK"})
    m = MaintainPrice()
    m.report_mail()
    # print(a)

import pymysql
from settings import WEBERP_SQL_SETTINGS
from Format import time_now


class MaintainPrice():
    def __init__(self, **kwargs):
        self.item = kwargs
        self.item['operator'] = "爬虫维护"
        self.item['last_time'] = time_now()

    def sql_connect(self):
        self.con = pymysql.connect(**WEBERP_SQL_SETTINGS)
        self.cursor = self.con.cursor()

    def sql_close(self):
        self.con.close()

    def shop_id(self):
        sql = "select shop_id from salestypes where typeabbrev = '%s'" % (self.item['fromStore'])
        self.cursor.execute(sql)
        result = self.cursor.fetchall()
        # print(result)
        self.item['shop_id'] = result[0][0]

    def data_compare(self):
        sql = "select price_tb from prices_tb where stockid='s%' and description='s%' and shop_id='%s'" % (
            self.item['goodsCode'], self['tbName'], self.item['shop_id'])
        self.cursor.execute(sql)
        res = self.cursor.fetchall()
        if res is None:
            return "创建"
        elif self.item['unitPrice'] != res[0][0]:
            return "更新"
        else:
            return None

    def maintain(self):
        self.sql_connect()
        self.shop_id()
        print(self.item)


if __name__ == '__main__':
    m = MaintainPrice(**{'fromStore': "YK"})
    m.maintain()

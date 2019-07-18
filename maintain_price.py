from settings import WEBERP_SQL_SETTINGS
from Format import time_now
from sql import Sql


class MaintainPrice():
    sql_element = Sql(**WEBERP_SQL_SETTINGS)

    def __init__(self, **kwargs):
        self.item = kwargs
        self.item['operator'] = "爬虫维护"
        self.item['last_time'] = time_now()

    def shop_id(self):
        res = self.sql_element.select_data('salestypes', 0, 'shop_id', typeabbrev=self.item['fromStore'])
        self.item['shop_id'] = res[0][0]

    def data_compare(self):
        kwargs = {'stockid': self.item['goodsCode'],
                  'description': self.item['tbName'],
                  'shop_id': self.item['shop_id'],
                  }
        res = self.sql_element.select_data_sql('prices_tb', 0, 'price_tb', **kwargs)
        print(res)
        # if res is None:
        #     return "创建"
        # elif self.item['unitPrice'] != res[0][0]:
        #     return "更新"
        # else:
        #     return None

    def maintain(self):
        self.shop_id()
        # print(self.item)
        self.data_compare()


if __name__ == '__main__':
    m = MaintainPrice(**{'fromStore': "YK", 'goodsCode': "000001", 'tbName': "abc"})
    m.maintain()

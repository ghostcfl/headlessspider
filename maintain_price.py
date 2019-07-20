from settings import SQL_SETTINGS_ERP
from Format import time_now
from sql import Sql


class MaintainPrice():
    sql_element = Sql(**SQL_SETTINGS_ERP)

    def __init__(self):
        pass

    def shop_id(self, fromStore):
        res = self.sql_element.select_data('salestypes', 0, 'shop_id', typeabbrev=fromStore)
        return res[0][0]

    def data_compare(self, **kwargs):
        kwargs_temp = {'stockid': kwargs['goodsCode'],
                       'description': kwargs['tbName'],
                       'shop_id': self.shop_id(fromStore=kwargs['fromStore']),
                       }
        res = self.sql_element.select_data('prices_tb', 0, 'price_tb', **kwargs_temp)
        if res:
            pass
            if self.item['unitPrice'] != res[0][0]:
                return "更新"
            else:
                return None
        else:
            return "创建"

    def maintain(self, operation, **kwargs):
        if operation == "更新":
            item1 = {'price_tb': kwargs['unitPrice'],
                     'operator': '爬虫维护',
                     'last_time': time_now(),
                     'attribute': kwargs['goodsAttribute'],
                     'flag': 'update'}
            item2 = {'stockid': kwargs['goodsCode'],
                     'shop_id': self.shop_id(kwargs['fromStore']),
                     'link_id': kwargs['link_id']}
            # self.sql_element.update_old_data("prices_tb", item1, item2)
            print(self.sql_element.update_old_data_sql("prices_tb", item1, item2))
        elif operation == "创建":
            item = {'stockid': kwargs['goodsCode'],
                    'link_id': kwargs['link_id'],
                    'shop_id': self.shop_id(kwargs['fromStore']),
                    'price_tb': kwargs['unitPrice'],
                    'currabrev': 'CNY',
                    'operator': '爬虫维护',
                    'last_time': time_now(),
                    'attribute': kwargs['goodsAttribute'],
                    'flag': 'create',
                    'description': kwargs['tbName'],
                    }
            # self.sql_element.insert_new_data('prices_tb', **item)
            print(self.sql_element.insert_new_data_sql('prices_tb', **item))


if __name__ == '__main__':
    m = MaintainPrice()
    # a = m.data_compare(**{'goodsCode': "000001", 'tbName': 'abc', 'fromStore': "YK"})
    print(m.shop_id(fromStore="YK"))
    # print(a)

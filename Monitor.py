import datetime, pymysql
import re
from settings import SQL_SETTINGS, my_user
from smtp import mail
from Format import time_zone, time_stamp, store_trans
from sql import Sql


class Monitor():
    sql_element = Sql(**SQL_SETTINGS)
    total_list = []
    title_list = ['15分钟未付款订单', '24小时末发货订单', '退货退款未完成订单']

    def orderMonitor(self):
        result = self.sql_element.select_data("tb_order_spider", 0,
                                              *['createTime', 'payTime', 'orderStatus', 'orderNo', 'fromStore'])
        pay_timeout_list = []
        delivery_timeout_list = []
        for i in result:
            item = {}
            item['createTime'] = i[0]
            item['payTime'] = i[1]
            item['orderStatus'] = i[2]
            item['orderNo'] = i[3]
            item['fromStore'] = i[4]
            d1 = datetime.datetime.now()
            if item['payTime']:
                hours = (d1 - item['payTime']).days * 24 + (d1 - item['payTime']).seconds / 3600
                if item['orderStatus'] == "买家已付款" and hours > 24:
                    item['hours'] = hours
                    delivery_timeout_list.append(item)
            else:
                minutes = (d1 - item['createTime']).seconds / 60
                if item['orderStatus'] == "等待买家付款" and minutes > 15:
                    item['minutes'] = round(minutes)
                    pay_timeout_list.append(item)
        refund_list = self.refund_monitor()
        print(pay_timeout_list)
        print(delivery_timeout_list)
        self.total_list = [pay_timeout_list, delivery_timeout_list, refund_list]

    def split_store(self, item):
        if item['fromStore'] == 'YK':
            string = store_trans('YK') + "\n"
            for i in range(3):
                string += self.title_list[i] + ':\n'
                for j in range(len(self.total_list[i])):
                    pass
            print(string)
        elif item['fromStore'] == 'KY':
            pass
        elif item['fromStore'] == 'SC':
            pass
        elif item['fromStore'] == 'VP':
            pass
        elif item['fromStore'] == 'YJ':
            pass
        elif item['fromStore'] == 'TB':
            pass

    def refund_monitor(self):
        content = []
        result = self.sql_element.select_data("tb_order_detail_spider", 0,
                                              *['orderNo', 'orderStatus', 'refundStatus'],
                                              isRefund='1')
        a = 1
        for i in result:
            if i[2]:
                if i[2] == '退款成功' or i[2] == '退运保险':
                    pass
                else:
                    content.append(str(a) + ".监测到退款订单：" + str(i[0]) + "订单状态：" + i[1] + "退款处理状态：" + i[2])
                    a += 1
        return content

    def send_mail(self):
        content1 = self.refund_monitor()
        content2, content3 = [], []
        result = self.sql_element.select_data("tb_order_monitor", 0, *['monitorStatus'])
        x, y = 1, 1
        for i in result:
            if re.search(".*?未发货", i[0]):
                content2.append(str(x) + "." + i[0])
                x += 1
            elif re.search(".*?末付款", i[0]):
                content3.append(str(y) + "." + i[0])
                y += 1
        a = "退款订单:\n" + "\n".join(content1)
        b = "\n未发货订单:\n" + "\n".join(content2)
        c = "\n末付款订单:\n" + "\n".join(content3)
        d = a + b + c
        print(d)
        # mail("订单状态监测报告", d, my_user)

    def mail_control(self):
        d_time1, d_time2 = time_zone("9:00", "9:30")
        d_time3, d_time4 = time_zone("17:30", "18:00")
        n_time = datetime.datetime.now()
        # 判断当前时间是否在范围时间内
        if d_time1 < n_time < d_time2:
            # print("a")
            self.send_mail()
        elif d_time3 < n_time < d_time4:
            # print("b")
            self.send_mail()
        else:
            pass


if __name__ == '__main__':
    m = Monitor()
    # m.orderMonitor()
    m.split_store({'fromStore': 'YK',
                   'status': [{'createTime': datetime.datetime(2019, 7, 20, 10, 50, 40), 'payTime': None,
                               'orderStatus': '等待买家付款', 'orderNo': '545440642016868264', 'minutes': 403}, 1, 2],
                   })

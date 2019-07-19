import datetime, pymysql
import re
from settings import SQL_SETTINGS_SPIDER
from smtp import mail
from Format import time_zone


def orderMonitor():
    item = {}
    con = pymysql.connect(**SQL_SETTINGS_SPIDER)
    cursor = con.cursor()
    result = select_order(cursor, con)
    for i in result:
        creatTime = i[0]
        payTime = i[1]
        monitorStatus = i[2]
        orderNo = i[3]
        d1 = datetime.datetime.now()
        if select(cursor, orderNo):
            # print("1")
            if payTime:
                # print("2")
                d3 = datetime.datetime.strptime(payTime, '%Y-%m-%d %H:%M:%S')
                hours = (d1 - d3).days * 24 + (d1 - d3).seconds / 3600
                if monitorStatus == "买家已付款" and hours > 24:
                    # print("3")
                    item['orderNo'] = orderNo
                    item['monitorStatus'] = "订单超时未发货：" + orderNo + "，超出时长为：" + str(round(hours)) + "小时"
                    item['updateTime'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    update(cursor, con, item, orderNo)
                else:
                    # print("4")
                    remove_warring(cursor, con, orderNo)
            else:
                # print("5")
                minutes = (d1 - creatTime).seconds / 60
                if monitorStatus == "等待买家付款" and minutes > 15:
                    # print("6")
                    item['orderNo'] = orderNo
                    item['monitorStatus'] = "订单超时末付款：" + orderNo + "，超出时长为：" + str(round(minutes)) + "分钟"
                    item['updateTime'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    update(cursor, con, item, orderNo)
                else:
                    # print("7")
                    remove_warring(cursor, con, orderNo)
        else:
            # print("8")
            if payTime:
                # print("9")
                d3 = datetime.datetime.strptime(payTime, '%Y-%m-%d %H:%M:%S')
                hours = (d1 - d3).days * 24 + (d1 - d3).seconds / 3600
                if monitorStatus == "买家已付款" and hours > 24:
                    # print("10")
                    item['orderNo'] = orderNo
                    item['monitorStatus'] = "订单超时未发货：" + orderNo + "，超出时长为：" + str(round(hours)) + "小时"
                    item['updateTime'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    insert(cursor, con, item)
            else:
                # print("11")
                # d2 = datetime.datetime.strptime(creatTime, '%Y-%m-%d %H:%M:%S')
                minutes = (d1 - creatTime).seconds / 60
                if monitorStatus == "等待买家付款" and minutes > 15:
                    # print("12")
                    item['orderNo'] = orderNo
                    item['monitorStatus'] = "订单超时末付款：" + orderNo + "，超出时长为：" + str(round(minutes)) + "分钟"
                    item['updateTime'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    insert(cursor, con, item)
    con.close()


def refund_monitor(cursor):
    content = []
    sql = "select orderNo,orderStatus,refundStatus from tb_order_detail_spider where isRefund = '1'"
    cursor.execute(sql)
    result = cursor.fetchall()
    a = 1
    for i in result:
        # if i[2] == "退款申请等待卖家确认中":
        if i[2]:
            content.append(str(a) + ".监测到退款订单：" + str(i[0]) + "订单状态：" + i[1] + "退款处理状态：" + i[2])
            a += 1
    return content


def insert(cursor, con, item):
    keys = ','.join(item.keys())
    values = ','.join(['%s'] * len(item))
    sql = "INSERT INTO tb_order_monitor (%s) VALUES (%s)" % (keys, values)
    try:
        cursor.execute(sql, tuple(item.values()))
        con.commit()
    except Exception as e:
        con.rollback()
        print(e)


def update(cursor, con, item, orderNo):
    list_key_value = []
    for k, v in item.items():
        list_key_value.append(k + "=" + '\'' + v + '\'')
    conditions = ",".join(list_key_value)
    sql = "UPDATE tb_order_monitor SET %s WHERE orderNo='%s'" % (conditions, orderNo)
    try:
        cursor.execute(sql)
        con.commit()
    except Exception as e:
        print(e)
        con.rollback()


def select(cursor, orderNo):
    sql = "select orderNo from tb_order_monitor where orderNo = '%s'" % (orderNo)
    cursor.execute(sql)
    result = cursor.fetchall()
    return result


def concat(dictionary, string):
    """
    拼装字典
    :param dictionary: 需要拼装的字典
    :param string: 拼装时所使用的连接的字符
    :return: key='value' string key='value' string key='value'...
    """
    list_key_value = []
    for k, v in dictionary.items():
        list_key_value.append(k + "=" + '\'' + v + '\'')
    conditions = string.join(list_key_value)
    return conditions


def select_order(cursor, con):
    sql = "select orderCreatTime,payTime,orderStatus,orderNo from tb_order_spider"
    cursor.execute(sql)
    result = cursor.fetchall()
    return result


def remove_warring(cursor, con, orderNo):
    sql = "DELETE FROM tb_order_monitor WHERE orderNo='%s'" % (orderNo)
    try:
        cursor.execute(sql)
        con.commit()
    except Exception as e:
        print(e)
        con.rollback()


def send_mail():
    con = pymysql.connect(**spider_settings.SQL_SETTINGS)
    cursor = con.cursor()
    content1 = refund_monitor(cursor)
    content2, content3 = [], []
    sql = "select monitorStatus from tb_order_monitor"
    cursor.execute(sql)
    result = cursor.fetchall()
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
    # print(d)
    mail("订单状态监测报告", d, spider_settings.my_user)


def mail_control():
    d_time1, d_time2 = time_zone("9:00", "9:30")
    d_time3, d_time4 = time_zone("17:30", "18:00")
    n_time = datetime.datetime.now()
    # 判断当前时间是否在范围时间内
    if d_time1 < n_time < d_time2:
        # print("a")
        send_mail()
    elif d_time3 < n_time < d_time4:
        # print("b")
        send_mail()
    else:
        pass


if __name__ == '__main__':
    # orderMonitor()
    mail_control()

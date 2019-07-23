import re
import datetime
import time


def time_now_str():
    return datetime.datetime.now().strftime('%Y%m%d%H%M%S')


def time_now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def time_stamp():
    return str(int(time.time()))


def time_zone(time1, time2):
    d_time1 = datetime.datetime.strptime(str(datetime.datetime.now().date()) + time1, '%Y-%m-%d%H:%M')
    d_time2 = datetime.datetime.strptime(str(datetime.datetime.now().date()) + time2, '%Y-%m-%d%H:%M')
    return d_time1, d_time2


def status_format(string):
    list = ["等待买家付款", "已付款", "交易关闭", "已发货", "交易成功"]
    for i in list:
        a = re.search(i, string)
        if a:
            if a.group() == "等待买家付款":
                temp = "未付款"
            else:
                temp = a.group()
            return temp


def delivery_company_translate(company_name):
    if company_name == "韵达快递":
        ship_via = "2"
    elif company_name == "圆通快递":
        ship_via = "3"
    elif company_name == "申通快递":
        ship_via = "4"
    elif company_name == "顺丰快递":
        ship_via = "5"
    elif company_name == "优速快递":
        ship_via = "6"
    elif company_name == "中通快递":
        ship_via = "7"
    else:
        ship_via = "1"
    return ship_via


if __name__ == '__main__':
    string = "当前订单状态：商品已拍下，等待买家付款"
    # string = "当前订单状态：买家已付款，等待商家发货"
    # string = "当前订单状态：交易关闭"
    # string = "当前订单状态：商家已发货，等待买家确认"
    # string = "当前订单状态：交易成功"
    print(status_format(string))


def store_trans(string):
    if string == "YK":
        return '玉佳企业店'
    elif string == "KY":
        return "开源电子"
    elif string == "SC":
        return '微信商城'
    elif string == "VP":
        return '批发'
    elif string == "YJ":
        return "玉佳电子"
    elif string == "TB":
        return "赛宝电子"


def concat(dictionary, string):
    """
    拼装字典
    :param dictionary: 需要拼装的字典
    :param string: 拼装时所使用的连接的字符
    :return: key='value' string key='value' string key='value'...
    """
    for k, v in dictionary.items():
        dictionary[k] = str(v)
    list_key_value = []
    for k, v in dictionary.items():
        list_key_value.append(k + "=" + '\'' + v + '\'')
    conditions = string.join(list_key_value)
    return conditions
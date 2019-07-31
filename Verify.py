from settings import SQL_SETTINGS
from smtp import mail
from Format import store_trans
from sql import Sql


def Verify():
    l_orderNo = []
    sql_element = Sql(**SQL_SETTINGS)
    args = ['orderNo', 'deliverFee', 'actualFee', 'couponPrice', 'fromStore']
    kwargs = {'isVerify': '0', 'isDetaildown': '1'}
    # kwargs = {'isVerify': '2', 'isDetaildown': '1'}
    result = sql_element.select_data("tb_order_spider", 0, *args, **kwargs)
    for i in result:
        total = 0
        orderNo = i[0]
        deliverFee = i[1]
        actualFee = i[2]
        couponPrice = i[3]
        fromStore = i[4]
        args = ['unitPrice', 'sellNum', 'unitBenefits']
        kwargs = {'orderNo': orderNo}
        result2 = sql_element.select_data('tb_order_detail_spider', 0, *args, **kwargs)
        for j in result2:
            unitPrice = j[0]
            sellNum = j[1]
            unitBenefits = j[2]
            total = total + unitPrice * sellNum - unitBenefits
        a = round(total, 3) + deliverFee - actualFee - couponPrice
        if int(a) != 0:
            list_tmp = []
            list_tmp.append(str(round(total, 2)))
            list_tmp.append(str(deliverFee))
            list_tmp.append(str(actualFee))
            list_tmp.append(str(couponPrice))
            list_tmp.append(str(round(a, 2)))
            list_tmp.append(store_trans(fromStore))
            list_tmp.append(orderNo)
            l_orderNo.append("|".join(list_tmp))
            dict1 = {'isVerify': '2'}
            dict2 = {'orderNo': orderNo}
            sql_element.update_old_data('tb_order_spider', dict1, dict2)
        else:
            dict1 = {'isVerify': '1'}
            dict2 = {'orderNo': orderNo}
            sql_element.update_old_data('tb_order_spider', dict1, dict2)
            # print('没有异常数据，验证完成！')
    if l_orderNo:
        s = "\n".join(l_orderNo)
        mail("数据异常报告", s, ["946930866@qq.com"])


if __name__ == '__main__':
    Verify()

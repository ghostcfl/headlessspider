from settings import SQL_SETTINGS
import mysql
from smtp import mail
from Format import store_trans
from taobao_check import taobao_check


def Verify():
    l_orderNo = []
    column_name = ['orderNo', 'deliverFee', 'actualFee', 'couponPrice', 'fromStore', 'orderStatus']
    condition = {'isVerify': '0', 'isDetaildown': '1'}
    # kwargs = {'isVerify': '2', 'isDetaildown': '1'}
    result = mysql.get_data(t="tb_order_spider", cn=column_name, c=condition)
    if result:
        for i in result:
            total = 0
            orderNo = i[0]
            deliverFee = i[1]
            actualFee = i[2]
            couponPrice = i[3]
            fromStore = i[4]
            column_name = ['unitPrice', 'sellNum', 'unitBenefits']
            condition = {'orderNo': orderNo}
            result2 = mysql.get_data(t="tb_order_detail_spider", cn=column_name, c=condition)
            for j in result2:
                unitPrice = j[0]
                sellNum = j[1]
                unitBenefits = j[2]
                total = total + unitPrice * sellNum - unitBenefits
            a = round(total, 3) + deliverFee - actualFee - couponPrice
            if int(a) != 0 and i[5] != '交易关闭':
                list_tmp = []
                list_tmp.append(str(round(total, 2)))
                list_tmp.append(str(deliverFee))
                list_tmp.append(str(actualFee))
                list_tmp.append(str(couponPrice))
                list_tmp.append(str(round(a, 2)))
                list_tmp.append(store_trans(fromStore))
                list_tmp.append(orderNo)
                l_orderNo.append("|".join(list_tmp))
                mysql.update_data(t="tb_order_spider", set={'isVerify': 2}, c={'orderNo': orderNo})
            else:
                mysql.update_data(t="tb_order_spider", set={'isVerify': 1}, c={'orderNo': orderNo})
                # print('没有异常数据，验证完成！')
    if l_orderNo:
        s = "\n".join(l_orderNo)
        # print(s)
        mail("数据异常报告", s, ["946930866@qq.com"])
    taobao_check()


if __name__ == '__main__':
    Verify()

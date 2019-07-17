import pymysql
from settings import SQL_SETTINGS
from smtp import mail
from Format import store_trans


def Verify():
    l_orderNo = []
    con = pymysql.connect(**SQL_SETTINGS)
    # self.con = pymysql.connect(host='localhost', port=3306, user='root', password='', db='test')
    cursor = con.cursor()

    # sql1 = "SELECT orderNo,unitPrice,sellNum,unitBenefits FROM tb_order_detail_spider"
    sql1 = "SELECT orderNo,deliverFee,actualFee,couponPrice,fromStore FROM tb_order_spider where isDetaildown = '1'"
    # sql2 = "SELECT orderNo,deliverPrice,totalPrice FROM tb_order_spider where orderNo='%s'" % orderNo
    cursor.execute(sql1)
    result = cursor.fetchall()
    for i in result:
        total = 0
        orderNo = i[0]
        deliverFee = i[1]
        actualFee = i[2]
        couponPrice = i[3]
        fromStore = i[4]
        sql2 = "SELECT unitPrice,sellNum,unitBenefits FROM tb_order_detail_spider where orderNo='%s'" % orderNo
        cursor.execute(sql2)
        result2 = cursor.fetchall()
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
            sql4 = "update tb_order_spider set isDetaildown = '1' where orderNo = '%s'" % (orderNo)
            cursor.execute(sql4)
            con.commit()
        else:
            sql3 = "update tb_order_spider set isVerify='1' where orderNo = '%s'"%(orderNo)
            cursor.execute(sql3)
            con.commit()
            # print('没有异常数据，验证完成！')
    if l_orderNo:
        s = "\n".join(l_orderNo)
        mail("数据异常报告", s, ["946930866@qq.com"])


if __name__ == '__main__':
    Verify()

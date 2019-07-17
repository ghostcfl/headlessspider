import pandas as pd
import pymysql
from settings import SQL_SETTINGS
from sqlalchemy import create_engine
from Format import time_now


def to_weberp():
    """
    DataFrame.to_sql()参数解释
    if_exists: 'fail', 'replace', 'append',默认为fail
        fail: 如果表存在，则不进行操作
        replace: 如果表存在就删除表，重新生成，插入数据
        append: 如果表存在就插入数据，不存在就直接生成表
    index: DataFrame的index列是否要插入，默认True
    :return:
    """
    con_spider = pymysql.connect(**SQL_SETTINGS)
    sql1 = "SELECT * FROM tb_order_spider WHERE isVerify = '1'"
    sql2 = """SELECT p.* FROM tb_order_detail_spider AS p,tb_order_spider AS l
           WHERE p.`orderNo` = l.`orderNo` AND l.`isVerify` = '1' """
    df1 = pd.read_sql(sql1, con_spider)
    # print(df1)
    df2 = pd.read_sql(sql2, con_spider)
    # print(df2)
    con_spider.close()
    df1["importDate"] = time_now()
    df2["importDate"] = time_now()
    df3 = df1.drop("id", axis=1)
    df4 = df2.drop("id", axis=1)
    print(df3)
    con_weberp = create_engine("mysql+pymysql://root:root@localhost/weberp", encoding="utf-8")
    # try:
    df3.to_sql("tb_order_spider", con_weberp, if_exists="append", index=False)
    df4.to_sql("tb_order_detail_spider", con_weberp, if_exists="append", index=False)
    df3.to_csv("./tb_order_spider.csv")
    df4.to_csv("./tb_order_detail_spider.csv")
    # except Exception:
    #     pass


if __name__ == '__main__':
    to_weberp()

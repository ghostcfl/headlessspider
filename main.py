import asyncio, datetime
from login import Login
from spider import Spider
from Format import time_zone, time_now
from maintain_price import MaintainPrice
from sql import Sql
from settings import SQL_SETTINGS


async def loop_get_page(s):
    while True:
        # print("a")
        d_time1, d_time2 = time_zone("08:00", "18:00")
        d_time3, d_time4 = time_zone("18:00", "23:59")
        d_time5, d_time6 = time_zone("00:00", "08:00")
        start_time = datetime.datetime.now()
        if d_time1 < start_time < d_time2:
            t = 300
        elif d_time3 < start_time < d_time4:
            t = 900
        elif d_time5 < start_time < d_time6:
            t = 900
        await s.get_page()
        end_time = datetime.datetime.now()
        spending_time = end_time - start_time
        print(time_now() + str(round(spending_time.seconds / 60, 2)) + "分钟完成一轮爬取")
        print("休息" + str(t / 60) + "分钟")
        await asyncio.sleep(t)


async def loop_order_page(s):
    while True:
        await s.order_page()
        await asyncio.sleep(10)


async def loop_reports(f):
    if f == 'KY':
        while True:
            d1, d2 = time_zone("18:00", "18:05")
            if d1 < datetime.datetime.now() < d2:
                print("*"*70)
                m = MaintainPrice()
                m.report_mail()
                print("+" * 70)
                await asyncio.sleep(300)
            else:
                print("=" * 70)
                await asyncio.sleep(10)
    else:
        return


async def loop_deliver(s):
    # sql_element = Sql(**SQL_SETTINGS)
    # while True:
    #     print("#" * 70)
    #     res = sql_element.select_data("tb_spider", 1, ["orderNO", "shipNo_erp", "fromStore"], isPrint=2)
    #     if res:
    #         await s.deliver(res[0][0], res[0][1], res[0][2])
    #     else:
    #         await asyncio.sleep(10)
    #         continue
    pass


def run():
    loop = asyncio.get_event_loop()
    l = Login()
    b, p, f = loop.run_until_complete(l.login())
    s = Spider(l, b, p, f)
    tasks = [loop_get_page(s), loop_order_page(s), loop_reports(f), loop_deliver(s)]
    loop.run_until_complete(asyncio.wait(tasks))


if __name__ == '__main__':
    run()

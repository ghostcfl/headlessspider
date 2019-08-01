import asyncio, datetime
from login import Login
from spider import Spider
from Format import time_zone, time_now


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
            t = 28000
        await s.get_page()
        end_time = datetime.datetime.now()
        spending_time = end_time - start_time
        print(time_now() + str(round(spending_time.seconds / 60, 2)) + "分钟完成一轮爬取")
        print("休息" + str(t / 60) + "分钟")
        await asyncio.sleep(t)


async def loop_order_page(s):
    while True:
        # start_time = datetime.datetime.now()
        await s.order_page()
        # end_time = datetime.datetime.now()
        # spending_time = end_time - start_time
        # print(str(round(spending_time.seconds / 60, 2)) + "分钟完成一轮爬取")


def run():
    loop = asyncio.get_event_loop()
    l = Login()
    b, p, f = loop.run_until_complete(l.login())
    s = Spider(l, b, p, f)
    tasks = [loop_get_page(s), loop_order_page(s)]
    loop.run_until_complete(asyncio.wait(tasks))


if __name__ == '__main__':
    run()

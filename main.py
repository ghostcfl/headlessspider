import asyncio, datetime
from login import Login
from spider import Spider
from Verify import Verify
from spider_to_weberp import to_weberp


async def loop_get_page(s):
    while True:
        print("a")
        start_time = datetime.datetime.now()
        await s.get_page()
        end_time = datetime.datetime.now()
        spending_time = end_time - start_time
        print(str(round(spending_time.seconds / 60, 2)) + "分钟完成一轮爬取")


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

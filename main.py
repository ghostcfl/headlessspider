import asyncio, datetime
from login import Login
from spider import Spider
from Verify import Verify
from spider_to_weberp import to_weberp


def run():
    loop = asyncio.get_event_loop()
    l = Login()
    b, p, f = loop.run_until_complete(l.login())
    s = Spider(l, b, p, f)
    while True:
        print(f)
        print("starting spider")
        start_time = datetime.datetime.now()
        # tasks = [s.get_page(), s.order_page()]
        loop.run_until_complete(s.get_page())
        loop.run_until_complete(s.order_page())
        Verify()
        to_weberp()
        end_time = datetime.datetime.now()
        spending_time = end_time - start_time
        print(str(round(spending_time.seconds / 60, 2)) + "分钟完成一轮爬取")
        loop.run_until_complete(asyncio.sleep(900))


if __name__ == '__main__':
    run()

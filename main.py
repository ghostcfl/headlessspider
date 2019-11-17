import asyncio
from login import Login
from spider import Spider
from settings import ORDER_NUMBER, STORE_INFO
from slaver_spider import SlaverSpider


def run():
    loop = asyncio.get_event_loop()
    l = Login()
    b, p, f = loop.run_until_complete(l.login())
    s = Spider(l, b, p, f)
    tasks = [
        asyncio.ensure_future(s.get_page(orderno=ORDER_NUMBER)),
    ]
    loop.run_until_complete(asyncio.wait(tasks))


def run_by_head():
    loop = asyncio.get_event_loop()
    ss = SlaverSpider()
    b, p, f = loop.run_until_complete(ss.login(**STORE_INFO['YK']))
    s = Spider(ss, b, p, f)
    loop.run_until_complete(s.get_page())


if __name__ == '__main__':
    run()
    # run_by_head()

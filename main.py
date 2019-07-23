import asyncio
from login import Login
from spider import Spider
import Verify
import spider_to_weberp


def main():
    loop = asyncio.get_event_loop()
    login = Login()
    browser, page, fromStore = loop.run_until_complete(login.login())
    spider = Spider(login, browser, page, fromStore)
    while True:
        spider.connect_sql()
        tasks = [spider.get_page(), spider.order_page()]
        loop.run_until_complete(tasks)
        spider.sql_close()
        Verify.Verify()
        spider_to_weberp.to_weberp()


if __name__ == '__main__':
    main()
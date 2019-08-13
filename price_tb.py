import asyncio, re, sys
from login import Login
from urllib.parse import unquote
from Format import time_now
from sql import Sql
from settings import SQL_SETTINGS


class PriceTaoBao():
    url = "https://item.publish.taobao.com/taobao/manager/" \
          "render.htm?pagination.current=2&pagination.pageSize" \
          "=20&tab=all&table.sort.upShelfDate_m=desc"
    DB_TEST = SQL_SETTINGS.copy()
    DB_TEST['db'] = 'test'
    sql_element = Sql(**DB_TEST)

    def __init__(self, login, browser, page, fromStore):
        self.login = login
        self.browser = browser
        self.page = page
        self.fromStore = fromStore
        # pass

    async def get_page(self):
        # 跳转至订单页面
        await self.page.goto(self.url)  # 跳转到订单页面
        await self.next_page(self.page)

    async def intercept_request(self, req):
        """截取request请求"""
        if req.url == 'https://item.publish.taobao.com/taobao/manager/table.htm':
            # print(unquote(req.postData,encoding='utf-8'))
            a = re.search("\"current\":(\d+)", unquote(req.postData, encoding='utf-8'))
            if a:
                print("爬取第" + str(a.group(1) + "页成功！"))
        await req.continue_()

    async def intercept_response(self, res):
        """截取response响应"""
        req = res.request
        # print(req.method)
        if req.method == "POST":
            a = await res.json()
            # print(a)
            try:
                if a['data']['table']['dataSource']:
                    await self.parse(a['data']['table']['dataSource'])
                else:
                    await self.parse("q")
            except KeyError:
                try:
                    if a['data']['value']['skuOuterIdTable']['dataSource']:
                        await self.parse_2(a['data']['value'])
                except KeyError:
                    pass

        # if res.url == 'https://item.publish.taobao.com/taobao/manager/table.htm':
        #     a = await res.json()
        #     # print(a)
        #     if a['data']['table']['dataSource']:
        #         await self.parse(a['data']['table']['dataSource'])
        #     else:
        #         await self.parse("q")

    async def next_page(self, page):
        """执行翻页"""
        await self.page.waitForSelector("#pagination-toolbar", timeout=0)
        await asyncio.sleep(3)
        p = 1
        while True:
            await page.setRequestInterception(True)
            page.on('request', self.intercept_request)
            page.on('response', self.intercept_response)
            if p == 1:
                await self.page.click("#pagination-toolbar > div:last-child button:first-child")  # 跳到第一页
            else:
                await self.page.click("#pagination-toolbar > div:last-child button:last-child")  # 翻页
            print("正面爬取第" + str(p) + "页" + time_now())
            p += 1
            await asyncio.sleep(3)

    async def get_attr(self):
        # await self.page.goto(self.url)
        await self.page.waitForSelector("input[name='queryOuterId']", timeout=0)
        sql = "SELECT linkId,url,goodsCode FROM prices_tb WHERE flag=0 and fromStore='%s' and goodsCode regexp '^MUT'" % (
            self.fromStore)
        result = self.sql_element.select(sql)
        for data in result:
            item = {}
            item['linkId'] = data[0]
            item['url'] = data[1]
            await self.page.focus("input[name='queryOuterId']")
            await self.page.keyboard.down("ShiftLeft")
            await self.page.keyboard.press("Home")
            await self.page.keyboard.down("ShiftLeft")
            await self.page.keyboard.press("Delete")
            await self.page.focus("input[name='queryItemId']")
            await self.page.keyboard.down("ShiftLeft")
            await self.page.keyboard.press("Home")
            await self.page.keyboard.down("ShiftLeft")
            await self.page.keyboard.press("Delete")
            await self.page.type("input[name='queryItemId']", data[0])
            await self.page.type("input[name='queryOuterId']", data[2])
            await asyncio.sleep(1)
            await self.page.click(".filter-footer button:first-child")
            await self.page.setRequestInterception(True)
            self.page.on('request', self.intercept_request)
            self.page.on('response', self.intercept_response)
            self.sql_element.update_old_data('prices_tb', {'flag': 1}, {'linkId': data[0]})
            await asyncio.sleep(1)
            await self.page.click(".next-table-row td:nth-child(2) div.product-desc-hasImg span:nth-child(2) i")
            await asyncio.sleep(1)
            await page.keyboard.press('Escape')
            await asyncio.sleep(1)

    async def parse(self, data):
        if data != "q":
            for i in range(len(data)):
                item = {}
                item['linkId'] = data[i]['itemId']
                item['url'] = data[i]['itemDesc']['desc'][0]['href']
                item['tbName'] = data[i]['itemDesc']['desc'][0]['text']
                item['price'] = re.search("(\d+\.\d)+", data[i]['managerPrice']['currentPrice']).group(1)
                item['goodsCode'] = re.search("编码:(.*)", data[i]['itemDesc']['desc'][1]['text']).group(1).upper()
                item['outerId'] = item['goodsCode']
                item['fromStore'] = self.fromStore
                item['updateTime'] = time_now()
                print(item['goodsCode'])
                result = self.sql_element.select_data(
                    'prices_tb', 0, "*",
                    **{'linkId': item['linkId'],
                       'goodsCode': item['goodsCode'],
                       'tbName': item['tbName'],
                       'fromStore': self.fromStore}
                )
                if result:
                    print("Exist")
                else:
                    e = self.sql_element.insert_new_data('prices_tb', **item)
                    if e:
                        print(e)
                    else:
                        print("new data")
        else:
            pass
            # sys.exit(2)

    async def parse_2(self, data):
        print(data)
        outerId = data['outerId']
        result = self.sql_element.select_data(
            'prices_tb', 0,
            *['linkId', 'url'],
            **{'outerId': outerId, 'fromStore': self.fromStore}
        )
        for i in data['skuOuterIdTable']['dataSource']:
            item = {}
            item['skuId'] = i['skuId']
            item['linkId'] = result[0][0]
            item['goodsCode'] = i['skuOuterId']
            item['outerId'] = outerId
            item['tbName'] = data['textTitle']
            item['goodsAttribute'] = i['prop']
            item['price'] = None
            item['url'] = result[0][1]
            item['fromStore'] = self.fromStore
            item['updateTime'] = time_now()
            res = self.sql_element.select_data(
                'prices_tb', 0, "*",
                **{'linkId': item['linkId'],
                   'goodsCode': item['goodsCode'],
                   'tbName': item['tbName'],
                   }
            )
            if res:
                print("Ex")
            else:
                insert = self.sql_element.insert_new_data('prices_tb', **item)
                print(insert)
                print("new data")

    async def fix_data(self):
        # page = await self.browser.newPage()
        await self.page.goto(self.url)
        await self.page.waitForSelector("input[name='queryOuterId']", timeout=0)
        await self.page.waitForSelector("input[name='queryTitle']", timeout=0)
        sql = "select tbName,goodsCode from fix_data where flag=1 and fromStore='%s'" % (self.fromStore)
        result = self.sql_element.select(sql)
        # await self.page.click(".filter-footer button:first-child")
        for i in result:
            # await self.page.type("input[name='queryOuterId']", i[1])
            await self.page.type("input[name='queryTitle']", i[0][0:])
            await self.page.setRequestInterception(True)
            self.page.on('request', self.intercept_request)
            self.page.on('response', self.intercept_response)
            await asyncio.sleep(1)
            await self.page.click(".filter-footer button:first-child")
            await asyncio.sleep(1)
            # await self.page.focus("input[name='queryOuterId']")
            await self.page.focus("input[name='queryTitle']")
            await self.page.keyboard.down("ShiftLeft")
            await self.page.keyboard.press("Home")
            await self.page.keyboard.down("ShiftLeft")
            await self.page.keyboard.press("Delete")
            delete = self.sql_element.delete_data('fix_data', goodsCode=i[1], fromStore=self.fromStore)
            if delete:
                print(delete)
            await asyncio.sleep(1)
            # await self.page.click(".next-table-row td:nth-child(2) div.product-desc-hasImg span:nth-child(2) i")
            await asyncio.sleep(1)
            await page.keyboard.press('Escape')
            await asyncio.sleep(1)

    async def fix_data2(self):
        # page = await self.browser.newPage()
        await self.page.goto(self.url)
        while True:
            input("回车：")
            # await self.page.type("input[name='queryOuterId']", i[1])
            # await self.page.type("input[name='queryTitle']", i[0][0:])
            await self.page.setRequestInterception(True)
            self.page.on('request', self.intercept_request)
            self.page.on('response', self.intercept_response)
            await asyncio.sleep(1)
            await self.page.click(".filter-footer button:first-child")
            await asyncio.sleep(1)
            await page.keyboard.press('Escape')
            await asyncio.sleep(1)


if __name__ == '__main__':
    login = Login()
    loop = asyncio.get_event_loop()
    browser, page, fromStore = loop.run_until_complete(login.login())
    p = PriceTaoBao(login, browser, page, fromStore)
    # loop.run_until_complete(p.get_page())
    # loop.run_until_complete(p.fix_data())
    # loop.run_until_complete(p.get_attr())
    loop.run_until_complete(p.fix_data2())

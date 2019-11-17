import asyncio, mysql, random, datetime, re, json, subprocess
from pyquery.pyquery import PyQuery as pq
from login import Login
from settings import EARLIEST_ORDER_CREATETIME, \
    NEXT_PAGE_TIME, NEXT_ORDER_TIME as n_o_time, LINUX, test_server as ts, SQL_SETTINGS
from Format import time_now, store_trans, net_check, sleep, status_format, time_zone
from Verify import Verify
from logger import get_logger
from pyppeteer import errors

logger = get_logger("spider_log")


class Spider():
    url = 'https://trade.taobao.com/trade/itemlist/list_sold_items.htm'
    base_url = 'https://trade.taobao.com'
    page = None
    fromStore = None
    browser = None
    rep = None
    _loop_start_time = None
    _loop_end_time = None
    orderno = None
    complete = 0
    _page_seller_flag = None
    _page_link_id = None
    _page_order_detail = None

    # m = MaintainPrice()

    def __init__(self, login, browser, page, fromStore):
        # self.login = Login()
        # loop = asyncio.get_event_loop()
        # self.browser, self.page, self.fromStore = loop.run_until_complete(self.login.login())
        self.login = login
        self.browser = browser
        self.page = page
        self.fromStore = fromStore

    async def get_page(self, orderno=None):
        # 跳转至订单页面
        # await self.page.goto(self.url)  # 跳转到订单页面
        self._page_link_id = await self.browser.newPage()
        self._page_seller_flag = await self.browser.newPage()
        self._page_order_detail = await self.browser.newPage()
        self.orderno = orderno
        await self.next_page(page_num=1)

    async def intercept_request(self, req):
        """截取request请求"""
        await req.continue_()

    async def intercept_response(self, res):
        """截取response响应"""

        if res.url == 'https://trade.taobao.com/trade/itemlist/asyncSold.htm?event_submit_do_query=1&_input_charset=utf8':
            a = await res.json()
            try:
                await self.parse(a['mainOrders'], a['page']['currentPage'])
            except KeyError:
                logger.error("KeyError")
                await asyncio.sleep(5)
                await self.login.slider(self.page)
                await self.page.bringToFront()
                await self.page.screenshot({'path': './headless-test-result.png'})

    async def next_page(self, page_num=1):
        """执行翻页"""
        temp = 0
        while 1:
            t = time_zone(["08:00", "18:00", "23:00"])
            a = datetime.datetime.now()
            if a < t[0]:
                if not temp:
                    temp = 0
                n_p_time = 600
            elif t[0] < a < t[1]:
                temp += 1
                if temp == 1:
                    page_num = 1
                n_p_time = NEXT_PAGE_TIME
            elif a > t[2]:
                n_p_time = 60
                if not LINUX:
                    subprocess.call("shutdown /s")
                    exit("到点关机")
            else:
                n_p_time = 60

            await self.page.bringToFront()
            if self.orderno:
                await self.page.focus("#bizOrderId")
                await asyncio.sleep(1)
                await self.page.keyboard.down("ShiftLeft")
                await asyncio.sleep(1)
                await self.page.keyboard.press("Home")
                await asyncio.sleep(1)
                await self.page.keyboard.down("ShiftLeft")
                await asyncio.sleep(1)
                await self.page.keyboard.press("Delete")
                await asyncio.sleep(1)

                orderno = input(time_now() + " | 输入订单号:")

                await self.page.type("#bizOrderId", orderno)
                await self.page.setRequestInterception(True)
                self.page.on('request', self.intercept_request)
                self.page.on('response', self.intercept_response)
                net_check()
                await self.page.click(".button-mod__primary___17-Uv")
                await asyncio.sleep(10)
            else:
                while 1:
                    try:
                        await self.page.waitForSelector(".pagination-options-go")
                        await self.page.focus(".pagination-options input")
                        # await self.page.click(".pagination-options input", clickCount=2)
                        await self.page.keyboard.press("Delete")
                        await self.page.keyboard.press("Delete")
                        await self.page.keyboard.press("Delete")
                        await self.page.keyboard.press("Backspace")
                        await self.page.keyboard.press("Backspace")
                        await self.page.keyboard.press("Backspace")
                        await self.page.setRequestInterception(True)
                        self.page.on('request', self.intercept_request)
                        self.page.on('response', self.intercept_response)
                        net_check()
                        await self.page.type(".pagination-options input", str(page_num))
                        await self.page.keyboard.press("Enter")
                        self.page.waitForSelector(
                            ".pagination-item.pagination-item-" + str(page_num) + ".pagination-item-active",
                            timeout=10000)
                    except errors.TimeoutError:
                        logger.info('翻页超时，5秒后重新翻页')
                        sleep(5)
                    else:
                        break
                # await self.page.waitForSelector(".pagination-item-" + str(page_num) + " a", timeout=30000)
                # await self.page.click(".pagination-item-" + str(page_num) + " a")
                while 1:
                    if self.complete == 1:
                        s = random.random()
                        if s > 0.5:
                            await self.link_spider()
                            await self.order_page()
                            logger.info(str(int(s * n_p_time)) + " 秒后开始下一页爬取")
                            sleep(int(s * n_p_time))
                            break
                    elif self.complete == 2:
                        page_num = 0
                        s = random.random()
                        if s > 0.9:
                            mysql.update_data(t="tb_order_spider", set={"isDetaildown": 0},
                                              c={"isDetaildown": 2, "fromStore": self.fromStore})
                            sleep(int(s * n_p_time))
                            break
                    else:
                        # if i == 59:
                        #     logger.info("超时")
                        #     await self.page.screenshot({'path': './headless-test-result.png'})
                        await asyncio.sleep(3)
                self.complete = 0
                page_num += 1

    async def parse(self, mainOrders, pageNum):
        """解析爬取内容信息"""
        t = time_zone(["08:00", "18:00", "23:59"])
        a = datetime.datetime.now()
        if a < t[0]:
            eoc = EARLIEST_ORDER_CREATETIME
        elif t[0] < a < t[1]:
            eoc = 2
        else:
            eoc = 20

        start_time = datetime.datetime.now()
        logger.info("开始第 " + str(pageNum) + " 页订单爬取")
        logger.info(store_trans(self.fromStore))
        if pageNum == 1:
            self._loop_start_time = datetime.datetime.now()
        loop_control = 0
        for i in range(len(mainOrders)):
            order = {}  # 用于存储订单详细信息
            order['orderNo'] = mainOrders[i]["id"]
            order['createTime'] = mainOrders[i]['orderInfo']['createTime']
            order['buyerName'] = mainOrders[i]['buyer']['nick']
            flag = mainOrders[i]['extra']['sellerFlag']
            order['actualFee'] = mainOrders[i]['payInfo']['actualFee']
            order['deliverFee'] = re.search("\(含快递:￥(\d+\.\d+)\)", mainOrders[i]['payInfo']['postType']).group(1)
            order['datailURL'] = "https:" + mainOrders[i]['statusInfo']['operations'][0]['url']
            order['orderStatus'] = mainOrders[i]['statusInfo']['text']
            order['fromStore'] = self.fromStore
            order['updateTime'] = time_now()
            if flag == 1:
                data_url = self.base_url + mainOrders[i]['operations'][0]['dataUrl']
                order['sellerFlag'] = await self.get_flag_text(data_url)
            try:
                order['isPhoneOrder'] = mainOrders[i]['payInfo']['icons'][0]['linkTitle']
            except KeyError:
                pass
            items = mainOrders[i]['subOrders']
            line_no = 0
            for j in range(len(items)):
                continue_code = 0
                item = {}  # 用于存储售出商品详细信息
                item['orderNo'] = mainOrders[i]["id"]
                item['itemNo'] = line_no
                try:
                    item['goodsCode'] = items[j]['itemInfo']['extra'][0]['value']
                except KeyError:
                    item['goodsCode'] = 'error'
                    logger.error(time_now() + " 订单：" + item['orderNo'])
                item['tbName'] = items[j]['itemInfo']['title'].strip() \
                    .replace("&plusmn;", "±").replace("&Phi;", "Φ").replace("&Omega;", "Ω") \
                    .replace("&mdash;", "—").replace("&deg;", "°").replace("&times;", "×") \
                    .replace("&mu;", "μ").replace("&nbsp;", "").replace("（", "(").replace("）", ")")
                item['unitPrice'] = items[j]['priceInfo']['realTotal']
                item['sellNum'] = items[j]['quantity']
                item['orderStatus'] = order['orderStatus']
                if self.orderno:
                    logger.info(item['orderStatus'])
                item['refundStatus'] = None
                item['isRefund'] = 0
                item['goodsAttribute'] = ""
                item['url'] = "https:" + items[j]['itemInfo']['itemUrl']
                try:
                    goodsAttributes = items[j]['itemInfo']['skuText']
                except KeyError:
                    pass
                else:
                    temp = []
                    for k in range(len(goodsAttributes)):
                        try:
                            goodsAttributes[k]['name']
                        except KeyError:
                            n = len(temp)
                            temp[n - 1] += goodsAttributes[k]['value'].replace("&Omega", "Ω").replace("&middot", "·")
                        else:
                            temp.append(
                                goodsAttributes[k]['value'].replace("&Omega", "Ω").replace("&middot", "·")
                            )
                    temp_ga = "-".join(temp)
                    item['goodsAttribute'] = temp_ga.replace("（", "(").replace("）", ")")
                try:
                    operations = items[j]['operations']
                except KeyError:
                    pass
                else:
                    for x in range(len(operations)):
                        t = operations[x]['style']
                        if t in ['t12', 't16'] and operations[x]['text'] != "退运保险":
                            item['refundStatus'] = operations[x]['text']
                            item['isRefund'] = "1"
                        elif t == 't0' and operations[x]['text'] == '已取消':
                            continue_code = 1
                            delete_item = {'orderNo': item['orderNo'],
                                           'itemNo': item['itemNo'],
                                           'goodsCode': item['goodsCode']}
                            is_exist = mysql.get_data(t="tb_order_detail_spider", l=1, c=delete_item)
                            if is_exist:
                                mysql.delete_data(t="tb_order_detail_spider", c=delete_item)
                            sql = """
                            UPDATE tb_order_detail_spider
                            SET itemNo=itemNo-1
                            WHERE OrderNo='%s' and itemNo>'%s'
                            """ % (item['orderNo'], item['itemNo'])
                            mysql.update_data(sql=sql)
                            pass
                if continue_code:
                    continue
                else:
                    line_no += 1
                self.save_in_sql(item=item, tableName='tb_order_detail_spider')
            self.save_in_sql(item=order, tableName='tb_order_spider')
            if self.orderno:
                logger.info("定向爬取订单完成")
                return
            date = datetime.date.today()
            date_limit = (date - datetime.timedelta(eoc)).strftime("%Y-%m-%d %H:%M:%S")
            if order['createTime'] < date_limit:
                logger.info("完成本轮爬取，共翻 " + str(pageNum) + " 页。")
                loop_control = 1
                break
        end_time = datetime.datetime.now()
        spend_time = end_time - start_time
        logger.info(str(spend_time.seconds) + " 秒完成第 " + str(pageNum) + " 页订单爬取")
        if loop_control:
            self._loop_end_time = datetime.datetime.now()
            loop_spend_time = round((self._loop_end_time - self._loop_start_time).seconds / 60, 0)
            logger.info(str(loop_spend_time) + " 分钟完成本轮订单爬取")
            self.complete = 2
        else:
            self.complete = 1

    async def get_flag_text(self, data_url):
        page = self._page_seller_flag
        net_check()
        while 1:
            try:
                await page.bringToFront()
                await page.goto(data_url)
            except errors.TimeoutError:
                sleep(5)
            except errors.PageError:
                sleep(5)
            else:
                break
        await asyncio.sleep(1)
        content = await page.content()
        await asyncio.sleep(2)
        # await page.close()
        await self.page.bringToFront()
        doc = pq(content)
        res = re.search('"tip":"(.*?)"}', doc("pre").text())
        if res:
            return res.group(1)
        else:
            logger.info(doc("pre").text())
            return None

    async def order_page(self, browser_in=None, page_in=None):
        """爬取订单详情"""
        while 1:
            result = mysql.get_data(t="tb_order_spider",
                                    cn=["datailURL", "orderNo"],
                                    c={"isDetaildown": 0, "fromStore": self.fromStore},
                                    o=["createTime"], om="d")
            if result:
                logger.info("订单详情爬取")
                for url in result:
                    start_time = datetime.datetime.now()
                    logger.info(store_trans(self.fromStore))
                    logger.info("开始订单 " + url[1] + " 详情爬取")
                    order = {}
                    await self._page_order_detail.bringToFront()
                    # if browser_in:
                    #     page = await browser_in.newPage()
                    # else:
                    #     page = page_in
                    page = self._page_order_detail
                    while 1:
                        try:
                            await page.goto(url[0])
                        except errors.PageError:
                            sleep(5)
                        except errors.TimeoutError:
                            sleep(5)
                        else:
                            break
                    try:
                        await page.waitForSelector('#detail-panel', timeout=30000)
                    except errors.TimeoutError:
                        continue

                    content = await page.content()
                    a = re.search("var data = JSON.parse\('(.*)'\);", content).group(1)
                    b = a.replace('\\\\\\"', '')
                    data = b.replace('\\"', '"')
                    m = json.loads(data)
                    order['actualFee'] = m['mainOrder']['payInfo']['actualFee']['value']
                    order['orderStatus'] = status_format(m['mainOrder']['statusInfo']['text'])
                    if order['orderStatus'] == '等待买家付款':
                        order['isDetaildown'] = 2
                    else:
                        order['isDetaildown'] = 1
                    coupon = 0
                    for k, v in m['mainOrder']['payInfo'].items():
                        if k == 'promotions':
                            promotions = m['mainOrder']['payInfo']['promotions']
                            for i in range(len(promotions)):
                                if 'prefix' and 'suffix' in promotions[i]:
                                    coupon_temp = re.search("(\d+\.\d+)", promotions[i]['value'])
                                    if coupon_temp:
                                        coupon += float(coupon_temp.group(1))
                    order['couponPrice'] = round(coupon, 2)
                    for k, v in m.items():
                        if k == 'buyMessage':
                            order['buyerComments'] = v
                    orderNo = m['mainOrder']['id']
                    order_info = m['mainOrder']['orderInfo']['lines'][1]['content']
                    for i in range(len(order_info)):
                        if order_info[i]['value']['name'] == '支付宝交易号:':
                            try:
                                order['tradeNo'] = order_info[i]['value']['value']
                            except KeyError:
                                order['tradeNo'] = None
                        # elif order_info[i]['value']['name'] == '创建时间:':
                        #     order['createTime'] = order_info[i]['value']['value']
                        # elif order_info[i]['value']['name'] == '发货时间:':
                        #     order['shipTime'] = order_info[i]['value']['value']
                        elif order_info[i]['value']['name'] == '付款时间:':
                            order['payTime'] = order_info[i]['value']['value']
                    ship_info = m['tabs']
                    for i in range(len(ship_info)):
                        if ship_info[i]['id'] == 'logistics':
                            temp = ship_info[i]['content']
                            for k, v in temp.items():
                                if k == 'logisticsName':
                                    order['shippingCompany'] = v
                                elif k == 'shipType':
                                    order['shippingMethod'] = v
                                elif k == 'logisticsNum':
                                    order['shippingNo'] = v
                                # elif k == 'logisticsUrl':
                                #     order['shipUrl'] = "https" + v
                                elif k == 'address':
                                    rec_info = v
                                    order['receiverName'] = rec_info.split("，")[0].replace(" ", "")
                                    order['receiverPhone'] = rec_info.split("，")[1]
                                    order['receiverAddress'] = "".join(rec_info.split("，")[2:])
                    sub_orders = m['mainOrder']['subOrders']
                    # print(len(sub_orders))
                    for i in range(len(sub_orders)):
                        item = {}
                        temp = 0
                        itemNo = i
                        if sub_orders[i]['promotionInfo']:
                            for j in sub_orders[i]['promotionInfo']:
                                for x in j['content']:
                                    for k, v in x.items():
                                        if k == 'value':
                                            p_list = re.findall("-?\d+\.\d+", v)
                                            if p_list:
                                                temp += float(p_list.pop())
                        item['unitBenefits'] = temp
                        mysql.update_data(t="tb_order_detail_spider", set=item,
                                          c={'orderNo': orderNo, 'itemNo': itemNo})
                        logger.info("详细订单状态更新成功")
                        # print(item)
                    # print(order)
                    mysql.update_data(t="tb_order_spider", set=order, c={'orderNo': orderNo})
                    logger.info("订单状态更新成功")

                    # if browser_in:
                    #     await page.close()
                    await self.page.bringToFront()
                    Verify()
                    end_time = datetime.datetime.now()
                    spend_time = end_time - start_time
                    logger.info(str(spend_time.seconds) + " 秒完成订单 " + url[1] + " 详情爬取")
                    while True:
                        s = random.random()
                        if s > 0.3:
                            logger.info("休息 " + str(int(s * n_o_time)) + " 秒完开始下一单详情爬取")
                            for i in range(int(s * n_o_time)):
                                await asyncio.sleep(1)
                            break
            else:
                logger.info("没有可以爬取的详情")
                break

    def save_in_sql(self, item, tableName):
        if 'goodsCode' in item:
            """判断是否orderdetail"""
            dict_select_condition = {'orderNo': item['orderNo'], 'itemNo': item['itemNo']}
            result = mysql.get_data(t=tableName, c=dict_select_condition)
            if result:
                item.pop("goodsCode")
                mysql.update_data(t=tableName, set=item, c=dict_select_condition)
                # logger.info(time_now() + " " + concat(dict_select_condition, "|") + "|订单详情更新成功|")
            else:
                mysql.insert_data(t=tableName, d=item)
                # logger.info(time_now() + " " + concat(dict_select_condition, "|") + "|新订单详情写入成功")
        else:
            dict_select_condition = {'orderNo': item['orderNo']}
            result = mysql.get_data(t=tableName, c=dict_select_condition)
            if result:
                mysql.update_data(t=tableName, set=item, c=dict_select_condition)
                # logger.info(time_now() + " " + concat(dict_select_condition, "|") + "|订单详情更新成功|")
            else:
                mysql.insert_data(t=tableName, d=item)
                # if SQL_SETTINGS['host'] == 'shai3c.com':
                #   self.rep.reports_in(item['fromStore'], float(item['actualFee']))
                # logger.info(time_now() + " " + concat(dict_select_condition, "|") + "|新订单详情写入成功")

    async def deliver(self, orderNo, shipNo, fromStore, shipCompany):
        if fromStore == self.fromStore:
            url = 'https://wuliu.taobao.com/user/consign.htm?trade_id=' + orderNo
            page = await self.browser.newPage()
            net_check()
            await page.goto(url)
            await page.waitForSelector(".ks-combobox-placeholder", timeout=30000)
            net_check()
            await page.click("#offlineTab a")
            await asyncio.sleep(1)
            net_check()
            await page.click(".font-blue.J_ChangeVision")
            await asyncio.sleep(1)
            print("offlineMailNo" + shipCompany)
            await page.type("#offlineMailNo" + shipCompany, shipNo)
            # await page.click("#" + shipCompany)
            # sql_element = Sql()
            # sql_element.update_old_data("tb_order_spider", {"isPrint": 3}, {"orderNo": orderNo, "fromStore": fromStore})

    async def link_spider(self):
        await self._page_link_id.bringToFront()
        p = self._page_link_id
        f = self.fromStore
        test_server = ts.copy()
        test_server["db"] = "test"
        while 1:
            sql = """
                SELECT a.id,url,goodsCode,a.orderNo FROM tb_order_detail_spider a
                JOIN tb_order_spider b ON a.`orderNo`=b.`orderNo`
                WHERE link_id="1" AND b.`fromStore`='%s' AND a.url IS NOT NULL
                ORDER BY b.createTime DESC
                LIMIT 1
                    """ % (f)
            url = "https://smf.taobao.com/promotionmonitor/orderPromotionQuery.htm?orderNo="
            results = mysql.get_data(sql=sql, dict_result=True)
            if not results:
                break
            orderno = results[0]['orderNo']
            url += orderno
            while 1:
                try:
                    await p.goto(url)
                except errors.PageError:
                    sleep(5)
                except errors.TimeoutError:
                    sleep(5)
                else:
                    break
            content = await p.content()
            data = re.findall(">(\{.*?\})<", content)
            try:
                order = json.loads(data[0])
                sub_orders = order["data"]["subOrderViewDTOs"]
            except IndexError:
                content
            except KeyError:
                continue
            for so in sub_orders:
                order_no = so["orderNoStr"]
                link_id = so["itemId"]
                logger.info(link_id)
                sql = "select goodsCode from tb_order_detail_spider where url like '%%%s%%'" % (order_no)
                goodsCode = mysql.get_data(sql=sql, return_one=True)
                del sql
                sql = "update tb_order_detail_spider set link_id='%s' where url like '%%%s%%'" % (link_id, order_no)
                mysql.update_data(sql=sql)
                del sql
                sql = """
                SELECT SpiderDate
                FROM prices_tb
                WHERE link_id='%s'
                AND stockid='%s'
                AND flag NOT IN ('del','XiaJia')
                """ % (link_id, goodsCode)

                if SQL_SETTINGS['host'] == "shai3c.com":
                    s = "production_server"
                elif SQL_SETTINGS['host'] == "www.veatao.com":
                    s = "test_server"

                res = mysql.get_data(sql=sql)
                res_fix = mysql.get_data(db=test_server,
                                         dict_result=True,
                                         t='prices_tb_fix',
                                         c={"link_id": link_id,
                                            "server": s})
                if res:
                    spider_date = res[0][0]
                    days = 1
                    if spider_date != '0000-00-00 00:00:00':
                        days = (datetime.datetime.now() - spider_date).days
                    if spider_date == '0000-00-00 00:00:00' or days > 14:
                        if not res_fix:
                            mysql.insert_data(db=test_server,
                                              t="prices_tb_fix",
                                              d={"link_id": link_id, "fromStore": f, "flag": 1, "server": s})
                        elif res_fix[0]["isComplete"] != 0:
                            mysql.update_data(db=test_server,
                                              t="prices_tb_fix",
                                              set={"isComplete": 0, "flag": 1},
                                              c={"link_id": link_id, "server": s})
                else:
                    if not res_fix:
                        mysql.insert_data(db=test_server,
                                          t="prices_tb_fix",
                                          d={"link_id": link_id, "fromStore": f, "flag": 0, "server": s})
                    elif res_fix[0]["isComplete"] != 0:
                        mysql.update_data(db=test_server,
                                          t="prices_tb_fix",
                                          set={"flag": 0, "isComplete": 0},
                                          c={"link_id": link_id, "server": s})
            sleep(5)
        # await p.close()
        await self.page.bringToFront()


if __name__ == '__main__':
    login = Login()
    loop = asyncio.get_event_loop()
    browser, page, fromStore = loop.run_until_complete(login.login())
    spider = Spider(login, browser, page, fromStore)
    # loop.run_until_complete(spider.deliver("570774880852899160", "12345678", "YK"))

    print(spider.fromStore)
    print("starting spider")
    # start_time = datetime.datetime.now()
    # tasks = [spider.get_page(), spider.order_page()]
    # loop.run_until_complete(asyncio.wait(tasks))
    # loop.run_until_complete(spider.get_page())
    while True:
        loop.run_until_complete(spider.order_page(page_in=page))
    # loop.run_until_complete(spider.deliver(" 551640557017888805", "12345678", fromStore, "SF"))
    # end_time = datetime.datetime.now()
    # spending_time = end_time - start_time
    # print(str(round(spending_time.seconds / 60, 2)) + "分钟完成一轮爬取")
    # loop.run_until_complete(asyncio.sleep(900))
    pass

import asyncio, logging, random, datetime, re, json
from pyquery.pyquery import PyQuery as pq
from login import Login
from settings import SQL_SETTINGS
from Format import time_now, concat
from smtp import mail
from sql import Sql
from Verify import Verify
from maintain_price import MaintainPrice
from price_tb import PriceTaoBao

logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)
handler = logging.FileHandler("log.txt")
handler.setLevel(logging.WARNING)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
logger.addHandler(console)
logger.addHandler(handler)


class Spider():
    url = 'https://trade.taobao.com/trade/itemlist/list_sold_items.htm'
    base_url = 'https://trade.taobao.com'
    page = None
    fromStore = None
    browser = None

    # m = MaintainPrice()

    def __init__(self, login, browser, page, fromStore):
        # self.login = Login()
        # loop = asyncio.get_event_loop()
        # self.browser, self.page, self.fromStore = loop.run_until_complete(self.login.login())
        self.login = login
        self.browser = browser
        self.page = page
        self.fromStore = fromStore

    async def get_page(self):
        # 跳转至订单页面
        await self.page.goto(self.url)  # 跳转到订单页面
        await self.next_page(self.page)

    async def intercept_request(self, req):
        """截取request请求"""
        if req.url == 'https://trade.taobao.com/trade/itemlist/asyncSold.htm?event_submit_do_query=1&_input_charset=utf8':
            a = re.search("pageNum=(\d+)", req.postData)
            if a:
                print("爬取第" + str(a.group(1) + "页成功！"))
        await req.continue_()

    async def intercept_response(self, res):
        """截取response响应"""
        if res.url == 'https://trade.taobao.com/trade/itemlist/asyncSold.htm?event_submit_do_query=1&_input_charset=utf8':
            a = await res.json()
            await self.parse(a['mainOrders'])

    async def next_page(self, page):
        """执行翻页"""
        await self.page.waitForSelector(".pagination-mod__show-more-page-button___txdoB", timeout=0)
        await self.page.click(".pagination-mod__show-more-page-button___txdoB")  # 显示全部页码
        await asyncio.sleep(3)
        for i in range(1, 21, 1):
            # 翻页并载数据包
            await page.setRequestInterception(True)
            page.on('request', self.intercept_request)
            page.on('response', self.intercept_response)
            await page.waitForSelector(".pagination-item-" + str(i) + " a", timeout=0)
            print("正面爬取第" + str(i) + "页" + time_now())
            await page.click(".pagination-item-" + str(i) + " a")
            while True:
                s = random.random()
                if s > 0.3:
                    # await asyncio.sleep(s * 30)
                    await asyncio.sleep(s * 30)
                    break
            # await asyncio.sleep(150)

    async def parse(self, mainOrders):
        """解析爬取内容信息"""
        sql_element = Sql(**SQL_SETTINGS)
        m = MaintainPrice()
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
            for j in range(len(items)):
                item = {}  # 用于存储售出商品详细信息
                item['orderNo'] = mainOrders[i]["id"]
                item['itemNo'] = j
                item['goodsCode'] = items[j]['itemInfo']['extra'][0]['value']
                item['tbName'] = items[j]['itemInfo']['title'].strip().replace("&plusmn;", "±").replace("&Phi;", "Φ")
                item['unitPrice'] = items[j]['priceInfo']['realTotal']
                item['sellNum'] = items[j]['quantity']
                item['orderStatus'] = order['orderStatus']
                item['refundStatus'] = None
                item['isRefund'] = 0
                url = "https:" + items[j]['itemInfo']['itemUrl']
                try:
                    goodsAttributes = items[j]['itemInfo']['skuText']
                except KeyError:
                    pass
                else:
                    temp = []
                    for k in range(len(goodsAttributes)):
                        temp.append(goodsAttributes[k]['value'])
                    item['goodsAttribute'] = "-".join(temp)
                try:
                    refund = items[j]['operations']
                except KeyError:
                    pass
                else:
                    for x in range(len(refund)):
                        if refund[x]['style'] == 't12':
                            item['refundStatus'] = refund[x]['text']
                            item['isRefund'] = "1"
                temp_dict = item.copy()
                temp_dict['fromStore'] = self.fromStore
                link_id = m.get_link_id(**temp_dict)
                if link_id:
                    temp_dict['link_id'] = link_id
                    x = m.data_compare(**temp_dict)
                    # print(x)
                    m.maintain(x, **temp_dict)
                else:
                    logger.warning(
                        time_now() + concat(
                            {'goodsCode': temp_dict['goodsCode'], 'fromStore': temp_dict['fromStore']}, '|')
                        + '没有这个条码！')
                    m.fix_data(**{
                        'goodsCode': temp_dict['goodsCode'],
                        'tbName': temp_dict['tbName'],
                        'fromStore': temp_dict['fromStore'],
                        'flag': 1,
                    })
                self.save_in_sql(sql_element, item=item, tableName='tb_order_detail_spider')
            self.save_in_sql(sql_element, item=order, tableName='tb_order_spider')

    async def get_flag_text(self, data_url):
        page = await self.browser.newPage()
        await self.login.page_evaluate(page)  # 载入新的页面时，重新使用JS写入浏览器属性，用于反爬
        await page.goto(data_url)
        await asyncio.sleep(1)
        content = await page.content()
        await page.close()
        doc = pq(content)
        return re.search('"tip":"(.*?)"', doc("pre").text()).group(1)

    async def order_page(self):
        """爬取订单详情"""
        sql_element = Sql(**SQL_SETTINGS)
        result = sql_element.select_data('tb_order_spider', 0, *['datailURL'],
                                         **{'isDetaildown': 0, 'fromStore': self.fromStore})

        if result:
            # print("订单详情爬取")
            for url in result:
                # print(url)
                order = {}
                page = await self.browser.newPage()
                await self.login.page_evaluate(page)
                await page.goto(url[0])
                await page.waitForSelector('title')
                content = await page.content()
                # print(content)
                a = re.search("var data = JSON.parse\('(.*)'\);", content).group(1)
                b = a.replace('\\\\\\"', '')
                data = b.replace('\\"', '"')
                m = json.loads(data)
                if m['mainOrder']['statusInfo']['text'] == '当前订单状态：商品已拍下，等待买家付款':
                    order['isDetaildown'] = 0
                else:
                    order['isDetaildown'] = 1
                for k, v in m['mainOrder']['payInfo'].items():
                    if k == 'promotions':
                        promotions = m['mainOrder']['payInfo']['promotions']
                        for i in range(len(promotions)):
                            if 'prefix' and 'suffix' in promotions[i]:
                                order['couponPrice'] = promotions[i]['value']
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
                for i in range(len(sub_orders)):
                    item = {}
                    temp = 0
                    itemNo = i
                    if sub_orders[i]['promotionInfo']:
                        for j in sub_orders[i]['promotionInfo']:
                            for x in j['content']:
                                for k, v in x.items():
                                    if k == 'value':
                                        temp += float(re.findall("-?\d+\.\d+", v).pop())
                    item['unitBenefits'] = temp
                    update = sql_element.update_old_data('tb_order_detail_spider', item,
                                                         {'orderNo': orderNo, 'itemNo': itemNo})
                    if update is None:
                        logger.info(time_now() + " " + sql_element.concat({'orderNo': orderNo, 'itemNo': itemNo}, "|") +
                                    "|详细订单状态更新成功|" +
                                    sql_element.concat(item, "|"))
                    else:
                        logger.warning(time_now() + " " + update)
                #     print(item)
                # print(order)
                update = sql_element.update_old_data('tb_order_spider', order, {'orderNo': orderNo})
                if update is None:
                    logger.info(time_now() + " " + sql_element.concat({'orderNo': orderNo}, "|") +
                                "|订单状态更新成功|" +
                                sql_element.concat(order, "|"))
                else:
                    logger.warning(time_now() + " " + update)
                await page.close()
                Verify()
                while True:
                    s = random.random()
                    if s > 0.3:
                        print("$" * 70)
                        await asyncio.sleep(s * 40)
                        break
        else:
            print("@" * 70)
            logger.info(time_now() + " " + "没有可以爬取的详情")

    def save_in_sql(self, sql_element, item, tableName):
        if 'goodsCode' in item:
            """判断是否orderdetail"""
            dict_select_condition = {'goodsCode': item['goodsCode'], 'orderNo': item['orderNo'],
                                     'itemNo': item['itemNo']}
            result = sql_element.select_data(
                tableName, 0, *["*"], **dict_select_condition
            )
            if result:
                update = sql_element.update_old_data(tableName, item, dict_select_condition)
                if update is None:
                    logger.info(time_now() + " " + sql_element.concat(dict_select_condition, "|") +
                                "|订单详情更新成功|")
                else:
                    logger.warning(time_now() + " " + update)
            else:
                insert = sql_element.insert_new_data(tableName, **item)
                if insert is None:
                    logger.info(time_now() + " " + sql_element.concat(dict_select_condition, "|") + "|新订单详情写入成功")
                else:
                    logger.warning(time_now() + " " + insert)
        else:
            dict_select_condition = {'orderNo': item['orderNo']}
            result = sql_element.select_data(
                tableName, 0, *["*"], **dict_select_condition
            )
            if result:
                update = sql_element.update_old_data(tableName, item, dict_select_condition)
                if update is None:
                    logger.info(time_now() + " " + sql_element.concat(dict_select_condition, "|") +
                                "|订单详情更新成功|")
                else:
                    logger.warning(time_now() + " " + update)
            else:
                insert = sql_element.insert_new_data(tableName, **item)
                if insert is None:
                    logger.info(time_now() + " " + sql_element.concat(dict_select_condition, "|") + "|新订单详情写入成功")
                else:
                    logger.warning(time_now() + " " + insert)

    async def deliver(self, orderNo, shipNo, fromStore, shipCompany):
        if fromStore == self.fromStore:
            url = 'https://wuliu.taobao.com/user/consign.htm?trade_id=' + orderNo
            page = await self.browser.newPage()
            await login.page_evaluate(page)
            await page.goto(url)
            await page.waitForSelector(".ks-combobox-placeholder", timeout=0)
            await page.click("#offlineTab a")
            await asyncio.sleep(1)
            await page.type("#offlineMailNo" + shipCompany, shipNo)
            # await page.click("#" + shipCompany)
            sql_element = Sql()
            sql_element.update_old_data("tb_order_spider", {"isPrint": 3}, {"orderNo": orderNo, "fromStore": fromStore})


if __name__ == '__main__':
    login = Login()
    loop = asyncio.get_event_loop()
    browser, page, fromStore = loop.run_until_complete(login.login())
    spider = Spider(login, browser, page, fromStore)
    # loop.run_until_complete(spider.deliver("570774880852899160", "12345678", "YK"))
    while True:
        print(spider.fromStore)
        print("starting spider")
        start_time = datetime.datetime.now()
        # tasks = [spider.get_page(), spider.order_page()]
        # loop.run_until_complete(asyncio.wait(tasks))
        # loop.run_until_complete(spider.get_page())
        loop.run_until_complete(spider.order_page())
        end_time = datetime.datetime.now()
        spending_time = end_time - start_time
        print(str(round(spending_time.seconds / 60, 2)) + "分钟完成一轮爬取")
        loop.run_until_complete(asyncio.sleep(900))
    pass

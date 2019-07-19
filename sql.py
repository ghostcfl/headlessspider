import pymysql
from settings import SQL_SETTINGS_ERP


class Sql():
    def __init__(self, **kwargs):
        # print("数据库连接")
        self.con = pymysql.connect(**kwargs)
        self.cursor = self.con.cursor()

    def __del__(self):
        # print("关闭数据库")
        self.con.close()

    def insert_new_data(self, table_name, **kwargs):
        sql = self.insert_new_data_sql(table_name, **kwargs)
        try:
            self.cursor.execute(sql, tuple(kwargs.values()))
        except Exception as e:
            print(e)
        else:
            self.con.commit()

    def update_old_data(self, table_name, dict1, dict2):
        sql = self.update_old_data_sql(table_name, dict1, dict2)
        try:
            self.cursor.execute(sql)
        except Exception as e:
            print(e)
        else:
            self.con.commit()

    def select_data(self, table_name, limit_num, *args, **kwargs):
        sql = self.select_data_sql(table_name, limit_num, *args, **kwargs)
        self.cursor.execute(sql)
        res = self.cursor.fetchall()
        return res

    def delete_data(self, table_name, **kwargs):
        sql = self.delete_data_sql(table_name, **kwargs)
        try:
            self.cursor.execute(sql)
        except Exception as e:
            print(e)
        else:
            self.con.commit()

    def concat(self, dictionary, string):
        """
        拼装字典
        :param dictionary: 需要拼装的字典
        :param string: 拼装时所使用的连接的字符
        :return: key='value' string key='value' string key='value'...
        """
        for k, v in dictionary.items():
            dictionary[k] = str(v)
        list_key_value = []
        for k, v in dictionary.items():
            list_key_value.append(k + "=" + '\'' + v + '\'')
        conditions = string.join(list_key_value)
        return conditions

    def insert_new_data_sql(self, table_name, **kwargs):
        keys = ','.join(kwargs.keys())
        values = ','.join(['%s'] * len(kwargs))
        sql = "INSERT INTO %s (%s) VALUES (%s)" % (table_name, keys, values)
        return sql

    def select_data_sql(self, table_name, limit_num, *args, **kwargs):
        """
        :param table_name: 操作的表名
        :param limit_num:查询结果输出的条数
        :param args: 需要查询的表头数组
        :param kwargs: 查询条件的字典
        :return: 查询结果
        """
        table_head = ",".join(args)
        if kwargs:
            a = self.concat(kwargs, " AND ")
            where_string = " where %s" % (a)
        else:
            where_string = ""
        if limit_num != 0:
            limit = " limit %d" % limit_num
        else:
            limit = ""
        sql = "select %s from %s%s%s" % (table_head, table_name, where_string, limit)
        return sql

    def update_old_data_sql(self, table_name, dict1, dict2):
        set_string = self.concat(dict1, ",")
        where_string = self.concat(dict2, " AND ")
        sql = "UPDATE %s SET %s WHERE %s" % (table_name, set_string, where_string)
        return sql

    def delete_data_sql(self, table_name, **kwargs):
        where_string = self.concat(kwargs, ' AND ')
        sql = "delete from %s where %s" % (table_name, where_string)
        return sql


if __name__ == '__main__':
    SQL_SETTINGS_ERP['db'] = "weberp"
    sql_element = Sql(**SQL_SETTINGS_ERP)
    res = sql_element.select_data('tb_order_spider', 0, "*", fromStore="YK")
    print(res)
    if res:
        print("a")
    else:
        print("b")

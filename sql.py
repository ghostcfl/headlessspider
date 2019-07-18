import pymysql
from settings import LOCAL_SQL_SETTINGS
import datetime


class Sql():
    def __init__(self, **kwargs):
        print("数据库连接")
        self.con = pymysql.connect(**kwargs)
        self.cursor = self.con.cursor()

    def __del__(self):
        print("关闭数据库")
        self.con.close()

    def insert_new_data(self, table_name, **kwargs):
        keys = ','.join(kwargs.keys())
        values = ','.join(['%s'] * len(kwargs))
        sql = "INSERT INTO %s (%s) VALUES (%s)" % (table_name, keys, values)
        try:
            self.cursor.execute(sql, tuple(kwargs.values()))
        except Exception as e:
            print(e)
        else:
            self.con.commit()

    def update_old_data(self, table_name, dict1, dict2):
        set = self.concat(dict1, ",")
        where = self.concat(dict2, " AND ")
        sql = "UPDATE %s SET %s WHERE %s" % (table_name, set, where)
        try:
            self.cursor.execute(sql)
        except Exception as e:
            print(e)
        else:
            self.con.commit()

    def select_data(self, table_name, limit_num, *args, **kwargs):
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
            where = " where %s" % (a)
        else:
            where = ""
        if limit_num != 0:
            limit = " limit %d" % (limit_num)
        else:
            limit = ""
        sql = "select %s from %s%s%s" % (table_head, table_name, where, limit)
        self.cursor.execute(sql)
        res = self.cursor.fetchall()
        return res

    def delete_data(self, table_name, **kwargs):
        where = self.concat(kwargs, ' AND ')
        sql = "delete from %s where %s" % (table_name, where)
        print(sql)
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


if __name__ == '__main__':
    LOCAL_SQL_SETTINGS['db'] = "weberp"
    sql = Sql(**LOCAL_SQL_SETTINGS)
    a = sql.delete_data('table',fromStore="YK", orderNO=datetime.datetime.now())

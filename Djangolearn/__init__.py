import pymysql
pymysql.version_info = (2, 2, 1)  # 强制伪装高版本
pymysql.install_as_MySQLdb()
import pymysql

from typing import Optional

import server_info

class IdGen:
    count: int = 0
    @staticmethod
    def get() -> str:
        result = "{:04}".format(IdGen.count)
        IdGen.count += 1
        return result

class Node:
    def __init__(self, id: str, parent: 'Node', children: list['Node']):
        self.parent: Node = parent
        self.children: list[Node] = children
        self.id = id

    # make list of (id, prev_id, next_id) from node connections
    def list_recursive(self) -> list[tuple[str, Optional[str], Optional[str]]]:
        result: list[tuple[str, Optional[str], Optional[str]]] = []
        if self.children == []:
            result.append((self.id, self.parent.id if self.parent is not None else None, None))
        else:
            for child in self.children:
                result.append(
                    (self.id, self.parent.id if self.parent is not None else None, child.id))
                result.extend(child.list_recursive())
        return result
    
    def __repr__(self):
        return str(self.__dict__)


def main():
   recreate_test_data()

def recreate_test_data():
    connection = pymysql.connect(
        host=server_info.host, user=server_info.user, password=server_info.passwd,
        database=server_info.database
    )
    with connection:
        # drop table
        try:
            sql = "DROP TABLE relations;"
            connection.query(sql)
        except Exception as e:
            print(e)
        # create table
        try:
            sql = (
                "CREATE TABLE relations ("
                "   id VARCHAR(10),"
                "   name VARCHAR(20),"
                "   prev_id VARCHAR(10),"
                "   next_id VARCHAR(10)"
                ");"
            )
            connection.query(sql)
        except Exception as e:
            print(e)
        #insert data
        root = Node("0000", None, [])
        root.children = [Node("{:04}".format(id), root, []) for id in [1,2,3]]
        for child in root.children:
            child.children = []
        node_list = root.list_recursive()
        try:
            with connection.cursor() as cursor:
                for node in node_list:
                    sql = (
                        f"INSERT INTO relations (id, prev_id, next_id) VALUES"
                        f"({','.join([ n if n is not None else 'NULL' for n in node])});"
                    )
                    cursor.execute(sql)
            connection.commit()
        except Exception as e:
            print(e)
        

if __name__ == "__main__":
    main()
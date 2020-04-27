import json
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.types import TypeDecorator, VARCHAR, INTEGER
from werewolf.utils.enums import GameEnum
from werewolf.utils.json_utils import ExtendedJSONEncoder, json_hook


class MySQLBase(object):
    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

    __table_args__ = {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8', 'mysql_collate': 'utf8_general_ci'}


Base = declarative_base(cls=MySQLBase)


class JSONEncodedType(TypeDecorator):
    impl = VARCHAR

    def process_bind_param(self, value, dialect):
        if value is not None:
            value = json.dumps(value, cls=ExtendedJSONEncoder)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = json.loads(value, object_hook=json_hook)
        return value


class EnumType(TypeDecorator):
    impl = INTEGER

    def process_bind_param(self, value, dialect):
        if value is not None:
            value = value.value
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = GameEnum(int(value))
        return value

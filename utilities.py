from datetime import datetime


timestamp_format = '%Y%m%d %H:%M:%S'


def timestamp():
    return datetime.now().strftime(timestamp_format)

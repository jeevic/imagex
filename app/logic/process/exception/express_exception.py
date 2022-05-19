
class ExpressParseException(BaseException):
    """
     表达式异常类
    """




'''
页
'''
if __name__ == '__main__':
    try:
        raise ExpressParseException("parse error")
    except ExpressParseException as e:
        print(str(e))

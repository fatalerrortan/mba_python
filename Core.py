import asyncio

class Core():

    def __init__(self, redis: object):
        self.redis = redis

    async def bricks_checking(self):
        # compare the records of selected platforms 
        while True:
            await asyncio.sleep(1)
            huobi_record = self.redis.get('huobi')    
            print(huobi_record)
            
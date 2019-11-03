from redis import StrictRedis


class DefaultQueue:
    def __init__(self):
        self.seen = set()
        self.queue = []
        self.depth = {}

    def __len__(self):
        return len(self.queue)

    def push(self, element):
        if not self.already_seen(element):
            self.queue.append(element)
            self.seen.add(element)

    def pop(self):
        return self.queue.pop()

    def already_seen(self, element):
        return element in self.seen

    def set_depth(self, element, depth):
        self.depth[element] = depth

    def get_depth(self, element):
        return self.depth.get(element, 0)


class RedisQueue:
    def __init__(self, client=None, db=0, queue_name="emmhaha"):
        self.client = StrictRedis(host="localhost", port=6379, db=db) if client is None else client
        self.queue_name = "queue:%s" % queue_name
        self.seen_set = "seen:%s" % queue_name
        self.depth = "depth:%s" % queue_name
        self.delete()

    def __len__(self):
        return self.client.llen(self.queue_name)

    def push(self, element):
        if isinstance(element, list):
            element = [e for e in element if not self.already_seen(e)]
            self.client.lpush(self.queue_name, *element)
            self.client.sadd(self.seen_set, *element)
        elif not self.already_seen(element):
            self.client.lpush(self.queue_name, element)
            self.client.sadd(self.seen_set, element)

    def pop(self):
        return self.client.rpop(self.queue_name).decode()

    def already_seen(self, element):
        return self.client.sismember(self.seen_set, element)

    def set_depth(self, element, depth):
        self.client.hset(self.depth, element, depth)

    def get_depth(self, elememt):
        depth = self.client.hget(self.depth, elememt)
        if depth:
            return int(depth.decode())

    def delete(self):
        self.client.delete(self.depth)
        self.client.delete(self.queue_name)
        self.client.delete(self.seen_set)

    def show(self):
        print("seen: ", self.client.scard(self.seen_set))
        print("queue: ", self.client.llen(self.queue_name))
        print("depthDict: ", self.client.hlen(self.depth))

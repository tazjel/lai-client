# -*- coding: utf-8 -*-

## tid = transaction_id

import tornado.ioloop
import tornado.web
import tornado.options
from tornado.options import options

import json
import pymongo
import logging


class Application(tornado.web.Application):
    def __init__(self):
        handlers = [(r'/(\d+)?', MainHandler)]
        self.conn = pymongo.Connection(options.db_host, options.db_port)
        self.db = self.conn[options.db_name]
        super(Application, self).__init__(handlers, debug=True)

class MainHandler(tornado.web.RequestHandler):
    def __init__(self, *args, **kwargs):
        super(MainHandler, self).__init__(*args, **kwargs)
        self.coll = self.application.db[options.db_collection]

    def get(self, tid=None):
        tid = self._check_tid(tid)
        docs = []
        for doc in self.coll.find({'tid': {'$gt': tid}}):
            doc['_id'] = str(doc['_id'])
            docs.append(doc)
        self.set_header('Content-Type', 'application/json')
        self.write(json.dumps(docs))

    def post(self, tid=None):
        tid = self._check_tid(tid)
        docs = json.loads(self.get_argument('docs'))
        #tid = self._get_max_tid(docs)
        if self._check_db_tid(tid):
            tid += 1
            docs_ = []
            for doc in docs:
                docs_.append(self._process(doc, tid))
            self.set_header('Content-Type', 'application/json')
            self.write(json.dumps(docs_))
        else:
            self.write('you must update first')

    def _process(self, doc, tid):
        doc['tid'] = tid
        doc['_id'] = str(self.coll.insert(doc))
        del doc['data']
        return doc

    def _get_max_tid(self, docs):
        return max(docs, key=lambda doc:doc['tid'])['tid']

    def _check_db_tid(self, tid):
        return not self.coll.find({'tid': {'$gt': tid}}).count()

    def _check_tid(self, tid):
        return 0 if tid is None else int(tid)


if __name__ == '__main__':
    tornado.options.parse_config_file('config.py')
    tornado.options.parse_command_line()

    application = Application()
    application.listen(options.port)

    logging.info('lai server started')
    tornado.ioloop.IOLoop.instance().start()


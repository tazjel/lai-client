# -*- coding: utf-8 -*-

# This file is part of lai-client.
#
# lai-client is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 3
# as published by the Free Software Foundation.
#
# lai-client is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with lai-client. If not, see <http://www.gnu.org/licenses/>.

import os.path
import urllib
import urllib2
import json
import base64

from lai import config
from lai.document import Document
from lai.database import DatabaseException, UPDATE_PROCESS, COMMIT_PROCESS
from lai.lib import crypto
#from lai.lib import gist


PUB_KEY_FILE = os.path.join(os.path.expanduser('~'), ".ssh/id_rsa.pub")
PUB_KEY = open(PUB_KEY_FILE).read()
PRV_KEY_FILE = os.path.join(os.path.expanduser('~'), ".ssh/id_rsa")
PRV_KEY = open(PRV_KEY_FILE).read()


class ClientException(Exception):
    pass


class Client:

    def __init__(self, database):
        try:
            self.db = database
            self.db.connect()
        except DatabaseException as e:
            raise ClientException(e)

    def sync(self):
        # Update
        request = self._get_request_base_doc()
        request['process'] = UPDATE_PROCESS
        response = self._send(request)
        ids = self._update(response)
        self.db.save_last_sync(UPDATE_PROCESS, ids)
        # Commit
        request = self._get_request_base_doc()
        request['session_id'] = response['session_id']
        request['process'] = COMMIT_PROCESS
        request['docs'] = self.db.get_docs_to_commit()
        ids = []
        if len(request['docs']):
            response = self._send(request)
            ids = self._update(response)
        self.db.save_last_sync(COMMIT_PROCESS, ids)

    def _update(self, response):
        ids = []
        if len(response['docs']):
            for doc_ in response['docs']:
                try: 
                    doc = Document(**doc_)
                    doc = self.db.update(doc, type=response['process'])
                    ids.append(doc.id)
                except DatabaseException as e:
                    raise ClientException(e)
        return ids

    def _get_request_base_doc(self):
        return {'user'      : config.USER,
                'key_name'  : config.KEY_NAME,
                'session_id': None,
                'process'   : None,
                'last_tid'  : self.db.get_last_tid(),
                'docs'      : []}

    def get(self, id):
        try:
            return self.db.get(id)
        except DatabaseException as e:
            raise ClientException(e)

    def getall(self):
        try:
            return self.db.getall()
        except DatabaseException as e:
            raise ClientException(e)

    def save(self, doc):
        try:
            return self.db.save(doc)
        except DatabaseException as e:
            raise ClientException(e)

    def delete(self, doc):
        try:
            return self.db.delete(doc)
        except DatabaseException as e:
            raise ClientException(e)

    def search(self, regex):
        try:
            return self.db.search(regex)
        except DatabaseException as e:
            raise ClientException(e)

    def status(self):
        try:
            return self.db.status()
        except DatabaseException as e:
            raise ClientException(e)

    def _send(self, request):
        msg  = json.dumps(request)
        enc  = crypto.encrypt(msg, PUB_KEY)
        data = base64.b64encode(enc)
        try:
            url = self._get_url(request)
            data = self.fetch(url, data)
        except urllib2.URLError as e:
            raise ClientException(e)
        enc = base64.b64decode(data)
        msg = crypto.decrypt(enc, PRV_KEY)
        response = json.loads(msg)
        return response

    def _get_url(self, request):
        args = (config.SERVER, request['user'], request['process'])
        url = '%s/sync?user=%s&process=%s' % args
        return url

    def fetch(self, url, data=None):
        if data is not None:
            data = urllib.urlencode({'data': data})
            req = urllib2.Request(url, data)
        else:
            req = url
        res = urllib2.urlopen(req)
        return res.read()

#   def send_to_gist(self, doc):
#       try:
#           g = gist.Gist(config.GITHUB_USER, config.GITHUB_PASSWORD)
#           return g.create(True, doc)
#       except gist.GistException as e:
#           raise ClientException(e)

if __name__ == '__main__':
    from lai.database import Database
    database = Database()
    client = Client(database)
    docs = client.search('awk')
    for doc in docs:
        print doc

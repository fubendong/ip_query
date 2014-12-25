#!/usr/bin/env python

import os
import sys
import socket
import codecs
import mmap
from struct import pack, unpack

import markdown
import os.path
import re
import torndb
import tornado.auth
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import unicodedata

from tornado.options import define, options

from tornado.options import define, options

define("port", default=8888, help="run on the given port", type=int)

def decode_str(old):
    try:
        return unicode(old,'gbk').encode('utf-8')
    except:
        if old[-1] == '\x96':
            try:
                return unicode(old[:-1],'gbk').encode('utf-8') + '?'
            except:
                pass

        return 'Invalid'

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        ip = self.get_argument("ip")
        dbpath = "/root/run/ip/ip-location-zh/ylinux/tools/IP/QQWry/qqwry.dat"
        qqwry = QQWry(dbpath)
        
        c, a = qqwry.query(ip)
#         print
#         print '%15s %s%s' % (ip, c, a)
        str = c + a
        
        self.write(str)





class QQWry(object):

    def __init__(self, path):
        self.path = path
        self.db = None
        self.open_db()
        self.idx_start, self.idx_end = self._read_idx()
       
        self.total = (self.idx_end - self.idx_start) / 7 + 1

    def open_db(self):
        if not self.db:
            self.db = open(self.path, 'rb')
            self.db = mmap.mmap(self.db.fileno(), 0, access = 1)
        return self.db

    def _read_idx(self):


        self.db.seek(0)
        start = unpack('I', self.db.read(4))[0]
        end = unpack('I', self.db.read(4))[0]

        return start, end

    def version(self):


        ip_end_offset = self.read_offset(self.idx_end + 4)
        a_raw, b_raw = self.read_record(ip_end_offset+4)

        return decode_str(a_raw + b_raw)

    def read_ip(self, off, seek=True):


        if seek:
            self.db.seek(off)

        buf = self.db.read(4)
        return unpack('I', buf)[0]

    def read_offset(self, off, seek=True):

        if seek:
            self.db.seek(off)

        buf = self.db.read(3)
        return unpack('I', buf+'\0')[0]

    def read_string(self, offset):


        if offset == 0:
            return 'N/A1'

        flag = self.get_flag(offset)

        if flag == 0:

            return 'N/A2'

        elif flag == 2:

            offset = self.read_offset(offset+1)
            return self.read_string(offset)

        self.db.seek(offset)

        raw_string  = ''
        while True:
            x = self.db.read(1)
            if x == '\0':
                break
            raw_string += x

        return raw_string

    def get_flag(self, offset):

        self.db.seek(offset)
        c = self.db.read(1)
        if not c:
            return 0
        return ord(c)

    def read_record(self, offset):

        self.db.seek(offset)


        flag = ord(self.db.read(1))

        if flag == 1:

            buf = self.db.read(3)
            a_offset = unpack('I', buf+'\0')[0]

            a_raw = self.read_string(a_offset)


            a_flag = self.get_flag(a_offset)
            if a_flag == 2:
                b_raw = self.read_string(a_offset+4)
            else:
                b_raw = self.read_string(a_offset+len(a_raw)+1)

        elif flag == 2:


            buf = self.db.read(3)
            a_offset = unpack('I', buf+'\0')[0]

            a_raw = self.read_string(a_offset)
            b_raw = self.read_string(offset+4)

        else:

            a_raw = self.read_string(offset)
            b_raw = self.read_string(offset+len(a_raw)+1)

        return a_raw, b_raw

    def output(self, output_file='ip.txt'):


        fp = codecs.open(output_file, 'w', 'utf8')

        idx = self.idx_start
        while idx <= self.idx_end:

            ip_int = self.read_ip(idx)
            ip_start = socket.inet_ntoa(pack('!I', ip_int))

            ip_end_offset = self.read_offset(idx + 4)

            ip_int = self.read_ip(ip_end_offset)
            ip_end = socket.inet_ntoa(pack('!I', ip_int))

            a_raw, b_raw = self.read_record(ip_end_offset+4)

            a_info = decode_str(a_raw)
            b_info = decode_str(b_raw)

            fp.write(u'%15s\t%15s\t%s,%s\n' %(
                ip_start, ip_end,
                a_info.decode('utf8'), b_info.decode('utf8')))

            idx += 7

        fp.close()

    def find(self, ip, l, r):


        if r - l <= 1:
            return l

        m = (l + r) / 2
        offset = self.idx_start + m * 7

        new_ip = self.read_ip(offset)

        if ip < new_ip:
            return self.find(ip, l, m)
        else:
            return self.find(ip, m, r)

    def query(self, ip):



        ip = unpack('!I', socket.inet_aton(ip))[0]

        i = self.find(ip, 0, self.total - 1)

        o = self.idx_start + i * 7

        o2 = self.read_offset(o + 4)

        (c, a) = self.read_record(o2 + 4)
        return (decode_str(c), decode_str(a))

    def __del__(self):
        if self.db:
            self.db.close()

def main():
    tornado.options.parse_command_line()
    application = tornado.web.Application([
        (r"/", MainHandler),
    ])
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()



if __name__ == "__main__":
    main()

#! /usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'esemi'

import logging
import urllib2
import lxml.html as l


SANDBOX_URL = 'http://russianaicup.ru/contest/1/standings/page/%d'
ROUND_FIRST_URL = 'http://russianaicup.ru/contest/2/standings/page/%d'


def get_top(pages, url):
    players = []
    page = 1
    while page <= pages:
        try:
            res = urllib2.urlopen(url % page, timeout=20)
        except Exception, e:
            logging.error('http error %d %s' % (page, e.message))
        else:
            tree = l.fromstring(res.read())
            players += tree.xpath('//table[@class="table table-bordered table-max margBottom table-striped"]/tbody/tr/td[2]/a[1]/img/@title')
        page += 1
    return players

if __name__ == '__main__':

    logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s', level=logging.INFO)

    topRound = get_top(3, ROUND_FIRST_URL)
    logging.info('find %d top players by first round' % len(topRound))

    topSandbox = get_top(5, SANDBOX_URL)
    logging.info('find %d top players by sandbox' % len(topSandbox))

    top60 = []
    for n, p in enumerate(topSandbox):
        if p not in topRound:
            top60.append(p)

    if 'esemi' in top60:
        logging.info('esemi found into TOP60')
    else:
        logging.info('esemi NOT found into TOP60')
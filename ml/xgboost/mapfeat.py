#!/user/bin/env python
# -*- coding: utf-8 -*-
# @File  : mapfeat.py
# @Author: sl
# @Date  : 2021/6/26 -  下午10:28
import os

from util.constant import ML_DATA_DIR


def loadfmap(fname):
    fmap = {}
    nmap = {}

    for l in open(fname):
        arr = l.split()
        if arr[0].find('.') != -1:
            idx = int(arr[0].strip('.'))
            assert idx not in fmap
            fmap[idx] = {}
            ftype = arr[1].strip(":")
            content = arr[2]
        else:
            content = arr[0]

        for it in content.split(","):
            if it.strip() == "":
                continue
            k, v = it.split("=")
            fmap[idx][v] = len(nmap) + 1
            nmap[len(nmap)] = ftype + '=' + k
    return fmap, nmap


def write_nmap(fo, nmap):
    for i in range(len(nmap)):
        fo.write('%d\t%s\ti\n' % (i, nmap[i]))



if __name__ == '__main__':

    fmap, nmap = loadfmap(os.path.join(ML_DATA_DIR, 'agaricus-lepiota.fmap'))
    fo = open('featmap.txt', 'w')
    write_nmap(fo, nmap)
    fo.close()

    fo = open('agaricus.txt', 'w')
    for l in open(os.path.join(ML_DATA_DIR, 'agaricus-lepiota.data')):
        arr = l.split(',')
        if arr[0] == 'p':
            fo.write('1')
        else:
            assert arr[0] == 'e'
            fo.write('0')
        for i in range(1, len(arr)):
            fo.write(' %d:1' % fmap[i][arr[i].strip()])
        fo.write('\n')

    fo.close()

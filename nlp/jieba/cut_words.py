#!/user/bin/env python
# -*- coding: utf-8 -*-
# @File  : cut_words.py
# @Author: sl
# @Date  : 2021/4/10 -  下午12:25

"""
分词学习
- 正向最大匹配
- 逆向最大匹配
- 双向最大匹配
- 统计分词 HMM

"""

import glob
import os
import random
import re
from datetime import datetime, timedelta

import jieba
from dateutil.parser import parse

from util.common_utils import get_TF
from util.file_utils import get_news_path, get_content
from util.logger_utils import get_log
import os

from util.nlp_utils import stop_words
import os
log = get_log("{}.log".format(str(os.path.split(__file__)[1]).replace(".py", '')))


# 正向最大匹配
class MM(object):

    def __init__(self, window_size=3, word_dict=None):
        self.window_size = window_size
        self.word_dict = word_dict
        self.init()

    def init(self):
        if self.word_dict is None:
            self.word_dict = ['研究', '研究生', '生命', '命', '的', '起源']

    def cut(self, text):
        result = []
        index = 0
        text_length = len(text)
        while text_length > index:
            for size in range(self.window_size + index, index, -1):
                piece = text[index:size]
                if piece in self.word_dict:
                    index = size - 1
                    break
            index = index + 1
            result.append(piece)
        return result


# 逆向最大匹配
class IMM(object):

    def __init__(self, dic_path):
        self.word_dict = set()
        self.window_size = 0

        self.init(dic_path)

    def init(self, path):
        with open(path, 'r', encoding='utf8') as f:
            for line in f:
                line = line.rstrip()
                if not line:
                    continue
                self.word_dict.add(line)
                if len(line) > self.window_size:
                    self.window_size = len(line)

    def cut(self, text):
        result = []
        index = len(text)
        while index > 0:
            word = None
            for size in range(self.window_size, 0, -1):
                if index - size < 0:
                    continue

                piece = text[(index - size):index]
                if piece in self.word_dict:
                    word = piece
                    result.append(word)
                    index -= size
                    break
            if word is None:
                index -= 1

        return result[::-1]


# 统计分词 HMM
class HMM(object):
    def __init__(self,trained = False):
        import os

        # 主要是用于存取算法中间结果，不用每次都训练模型
        self.model_file = '../../data/nlp/hmm_model.pkl'

        # 状态值集合
        self.state_list = ['B', 'M', 'E', 'S']
        # 参数加载,用于判断是否需要重新加载model_file
        self.load_para = False

    # 用于加载已计算的中间结果，当需要重新训练时，需初始化清空结果
    def try_load_model(self, trained):
        if trained:
            import pickle
            with open(self.model_file, 'rb') as f:
                self.A_dic = pickle.load(f)
                self.B_dic = pickle.load(f)
                self.Pi_dic = pickle.load(f)
                self.load_para = True
        else:
            # 状态转移概率（状态->状态的条件概率）
            self.A_dic = {}
            # 发射概率（状态->词语的条件概率）
            self.B_dic = {}
            # 状态的初始概率
            self.Pi_dic = {}
            self.load_para = False
        pass

    # 计算转移概率、发射概率以及初始概率
    def train(self, path):
        # 重置几个概率矩阵
        self.try_load_model(False)

        # 统计状态出现次数，求p(o)
        Count_dic = {}

        # 初始化参数
        def init_parameters():
            for state in self.state_list:
                self.A_dic[state] = {s: 0.0 for s in self.state_list}
                self.Pi_dic[state] = 0.0
                self.B_dic[state] = {}
                Count_dic[state] = 0

        def make_label(text):
            out_text = []
            if len(text) == 1:
                out_text.append('S')
            else:
                out_text += ['B'] + ['M'] * (len(text) - 2) + ['E']
            return out_text

        init_parameters()
        line_num = -1
        # 观察者集合，主要是字以及标点等
        words = set()
        with open(path, encoding='utf8') as f:
            for line in f:
                line_num += 1

                line = line.strip()
                if not line:
                    continue

                word_list = [i for i in line if i != ' ']
                words |= set(word_list)  # 更新字的集合

                line_list = line.split()
                line_state = []
                for w in line_list:
                    line_state.extend(make_label(w))
                assert len(word_list) == len(line_state)

                for k, v in enumerate(line_state):
                    Count_dic[v] += 1
                    if k == 0:
                        self.Pi_dic[v] += 1  # 每个句子的第一个字的状态，用于计算初始状态概率
                    else:
                        self.A_dic[line_state[k - 1]][v] += 1  # 计算转移概率
                        self.B_dic[line_state[k]][word_list[k]] = \
                            self.B_dic[line_state[k]].get(word_list[k], 0) + 1.0  # 计算发射概率

        self.Pi_dic = {k: v * 1.0 / line_num for k, v in self.Pi_dic.items()}
        self.A_dic = {k: {k1: v1 / Count_dic[k] for k1, v1 in v.items()} for k, v in self.A_dic.items()}
        # 加1平滑
        self.B_dic = {k: {k1: (v1 + 1) / Count_dic[k] for k1, v1 in v.items()} for k, v in self.B_dic.items()}

        # 序列化
        import pickle
        with open(self.model_file, 'wb') as f:
            pickle.dump(self.A_dic, f)
            pickle.dump(self.B_dic, f)
            pickle.dump(self.Pi_dic, f)

        return self

    # viterbi 算法 求最大概率的路径
    # 关于该算法的数学推导，可以查阅一下李航统计学习方法10.4.2，或者是Speech and Language Processing8.4.5
    def viterbi(self, text, states, start_p, trans_p, emit_p):
        V = [{}]
        path = {}
        for y in states:
            V[0][y] = start_p[y] * emit_p[y].get(text[0], 0)
            path[y] = [y]
        for t in range(1, len(text)):
            V.append({})
            new_path = {}

            # 检验训练的发射概率矩阵中是否有该字
            never_seen = text[t] not in emit_p['S'].keys() and \
                         text[t] not in emit_p['M'].keys() and \
                         text[t] not in emit_p['E'].keys() and \
                         text[t] not in emit_p['B'].keys()

            for y in states:
                emitP = emit_p[y].get(text[t], 0) if never_seen else 1.0  # 设置未知字单独成词
                (prob, state) = max(
                    [(V[t - 1][y0] * trans_p[y0].get(y, 0) * emitP, y0)
                     for y0 in states if V[t - 1][y0] > 0])
                V[t][y] = prob
                new_path[y] = path[state] + [y]
            path = new_path

        if emit_p['M'].get(text[-1], 0) > emit_p['S'].get(text[-1], 0):
            (prob, state) = max([(V[len(text) - 1][y], y) for y in ('E', 'M')])
        else:
            (prob, state) = max([(V[len(text) - 1][y], y) for y in states])
        return (prob, path[state])

    # 分词
    def cut(self, text):
        import os
        if not self.load_para:
            self.try_load_model(os.path.exists(self.model_file))
        prob, pos_list = self.viterbi(text, self.state_list, self.Pi_dic, self.A_dic, self.B_dic)
        begin, next = 0, 0
        for i, char in enumerate(text):
            pos = pos_list[i]
            if pos == 'B':
                begin = i
            elif pos == 'E':
                yield text[begin:i + 1]
                next = i + 1
            elif pos == 'S':
                yield char
                next = i + 1
        if next < len(text):
            yield text[next:]


if __name__ == '__main__':
    # text = '研究生命的起源'
    # tokenizer = MM()

    # text = '南京市长江大桥'
    # tokenizer = IMM("../../data/nlp/imm_dic.utf8")

    text = '这是一个非常棒的方案!'
    tokenizer = HMM()
    # tokenizer.train('/home/sl/workspace/python/github/learning-nlp-master/chapter-3/data/trainCorpus.txt_utf8')
    result = tokenizer.cut(text)
    print(text)
    print('/ '.join(result))
    pass

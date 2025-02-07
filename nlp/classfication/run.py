#!/user/bin/env python
# -*- coding: utf-8 -*-
# @File  : run.py
# @Author: sl
# @Date  : 2021/5/9 -  下午9:29

import time
import torch
import numpy as np
from train_eval import train, init_network,train_bert
from importlib import import_module
import argparse

parser = argparse.ArgumentParser(description='Chinese Text Classification')
parser.add_argument('--model', type=str, required=True,
                    help='choose a model: TextCNN, TextRNN, FastText, TextRCNN, TextRNN_Att, DPCNN, Transformer')
parser.add_argument('--embedding', default='pre_trained', type=str, help='random or pre_trained')
parser.add_argument('--word', default=False, type=bool, help='True for word, False for char')
args = parser.parse_args()


def run_general(args):
    # 搜狗新闻:embedding_SougouNews.npz, 腾讯:embedding_Tencent.npz, 随机初始化:random
    embedding = 'embedding_SougouNews.npz'
    if args.embedding == 'random':
        embedding = 'random'
    model_name = args.model  # 'TextRCNN'  # TextCNN, TextRNN, FastText, TextRCNN, TextRNN_Att, DPCNN, Transformer
    if model_name == 'FastText':
        from utils_fasttext import build_dataset, build_iterator, get_time_dif
        embedding = 'random'
    else:
        from utils import build_dataset, build_iterator, get_time_dif

    # dataset = 'THUCNews'  # 数据集
    DATA_THUCNEWS_DIR = '/home/sl/workspace/python/a2020/ml-learn/data/nlp/THUCNews'
    dataset = DATA_THUCNEWS_DIR  # 数据集

    x = import_module('models.' + model_name)
    config = x.Config(dataset, embedding)
    np.random.seed(1)
    torch.manual_seed(1)
    torch.cuda.manual_seed_all(1)
    torch.backends.cudnn.deterministic = True  # 保证每次结果一样

    start_time = time.time()
    print("Loading data...")
    vocab, train_data, dev_data, test_data = build_dataset(config, args.word)
    train_iter = build_iterator(train_data, config)
    dev_iter = build_iterator(dev_data, config)
    test_iter = build_iterator(test_data, config)
    time_dif = get_time_dif(start_time)
    print("Time usage:", time_dif)

    # train
    config.n_vocab = len(vocab)
    model = x.Model(config).to(config.device)
    if model_name != 'Transformer':
        init_network(model)
    print(model.parameters)
    train(config, model, train_iter, dev_iter, test_iter)


def run_bert(args):
    # dataset = 'THUCNews'  # 数据集
    DATA_THUCNEWS_DIR = '/home/sl/workspace/python/a2020/ml-learn/data/nlp/THUCNews'
    dataset = DATA_THUCNEWS_DIR  # 数据集
    model_name = args.model

    x = import_module('models.' + model_name)
    config = x.Config(dataset)
    np.random.seed(1)
    torch.manual_seed(1)
    torch.cuda.manual_seed_all(1)
    torch.backends.cudnn.deterministic = True  # 保证每次结果一样

    from utils_bert import build_dataset, build_iterator, get_time_dif

    start_time = time.time()
    print("Loading data...")
    train_data, dev_data, test_data = build_dataset(config)
    train_iter = build_iterator(train_data, config)
    dev_iter = build_iterator(dev_data, config)
    test_iter = build_iterator(test_data, config)
    time_dif = get_time_dif(start_time)
    print("Time usage:", time_dif)

    # train
    model = x.Model(config).to(config.device)
    if model_name != 'Transformer':
        init_network(model)
    print(model.parameters)
    train_bert(config, model, train_iter, dev_iter, test_iter)


if __name__ == '__main__':

    general_model = ['TextRCNN', 'TextCNN', 'TextRNN', 'FastText', 'TextRCNN', 'TextRNN_Att', 'DPCNN', 'Transformer']
    model_name = args.model
    if model_name in set(general_model):
        run_general(args)
    else:
        run_bert(args)

    pass

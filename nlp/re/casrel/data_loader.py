#!/user/bin/env python
# -*- coding: utf-8 -*-
# @File  : data_loader.py
# @Author: sl
# @Date  : 2021/8/27 - 下午4:27
import json
import os
from collections import defaultdict
from dataclasses import dataclass
from random import choice
from typing import List, Dict

import torch
from torch import Tensor
from torch.nn.utils.rnn import pad_sequence
from torch.utils.data import Dataset, DataLoader
from transformers import BertTokenizer, BertConfig

from nlp.re.casrel.config import BERT_MODEL_NAME, DATA_DIR, ModelArguments
from nlp.re.casrel.model import CasRel
from nlp.re.casrel.utils import load_tag, load_tokenizer
from nlp.re.casrel.utils import logger


@dataclass
class Example:
    guid: str = None
    text: str = None
    spo_list: List = None


@dataclass
class ReEntity:
    predicate: str = None
    object_type: str = None
    subject_type: str = None
    object: str = None
    subject: str = None


# 读取数据集:json 格式
def read_dataset_txt(input_file, set_type="train"):
    """read dataset """
    examples = []
    with open(input_file, "r", encoding="utf-8") as file:
        data = file.readlines()
    res = [json.loads(i) for i in data]
    for (i, line) in enumerate(res):
        guid = "%s-%s" % (set_type, i)
        text = line["text"]
        spo_list = line["spo_list"] if "spo_list" in line else []
        re_entitys = []
        if len(spo_list) > 0:
            for spo in spo_list:
                re_entitys.append(ReEntity(spo["predicate"], spo["object_type"],
                                           spo["subject_type"], spo["object"], spo["subject"]))
        if i % 1000 == 0:
            logger.info(line)
        examples.append(Example(guid=guid, text=text, spo_list=re_entitys))
    return examples


def read_data(path, set_type="train"):
    examples = read_dataset_txt(path, set_type)
    return examples


def find_head_idx(source, target):
    target_len = len(target)
    for i in range(len(source)):
        if source[i: i + target_len] == target:
            return i
    return -1


class Re18BaiduDataset(Dataset):
    def __init__(self, examples: List[Example], max_length=384,
                 tokenizer=BertTokenizer.from_pretrained(BERT_MODEL_NAME)):
        self.max_length = 512 if max_length > 512 else max_length
        self.tags, self.tag2id, self.id2tag = load_tag()
        self.tokenizer = tokenizer
        self.texts = []
        self.input_ids = []

        self.sub_heads = []
        self.sub_tails = []
        self.sub_head = []
        self.sub_tail = []
        self.obj_heads = []
        self.obj_tails = []
        self.spo_list = []

        self.masks = []

        for (ex_index, example) in enumerate(examples):
            if ex_index % 5000 == 0:
                logger.info("Writing example %d of %d" % (ex_index, len(examples)))

            tokenized = tokenizer(example.text, max_length=self.max_length, truncation=True)

            tokens = tokenized['input_ids']
            masks = tokenized['attention_mask']
            text_len = len(tokens)

            sub_heads, sub_tails = torch.zeros(text_len), torch.zeros(text_len)
            sub_head, sub_tail = torch.zeros(text_len), torch.zeros(text_len)
            obj_heads = torch.zeros((text_len, len(self.tags)))
            obj_tails = torch.zeros((text_len, len(self.tags)))

            s2ro_map = defaultdict(list)
            for spo in example.spo_list:
                triple = (self.tokenizer(spo.subject, add_special_tokens=False)['input_ids'],
                          self.tag2id[spo.predicate],
                          self.tokenizer(spo.object, add_special_tokens=False)['input_ids'])
                sub_head_idx = find_head_idx(tokens, triple[0])
                obj_head_idx = find_head_idx(tokens, triple[2])
                if sub_head_idx != -1 and obj_head_idx != -1:
                    sub = (sub_head_idx, sub_head_idx + len(triple[0]) - 1)
                    s2ro_map[sub].append(
                        (obj_head_idx, obj_head_idx + len(triple[2]) - 1, triple[1]))

            if s2ro_map:
                for s in s2ro_map:
                    sub_heads[s[0]] = 1
                    sub_tails[s[1]] = 1
                sub_head_idx, sub_tail_idx = choice(list(s2ro_map.keys()))
                sub_head[sub_head_idx] = 1
                sub_tail[sub_tail_idx] = 1
                for ro in s2ro_map.get((sub_head_idx, sub_tail_idx), []):
                    obj_heads[ro[0]][ro[2]] = 1
                    obj_tails[ro[1]][ro[2]] = 1

            self.texts.append(example.text)
            self.input_ids.append(torch.LongTensor(tokens))
            self.masks.append(torch.LongTensor(masks))

            self.sub_heads.append(sub_heads)
            self.sub_tails.append(sub_tails)
            self.sub_head.append(sub_head)
            self.sub_tail.append(sub_tail)

            self.obj_heads.append(obj_heads)
            self.obj_tails.append(obj_tails)

            self.spo_list.append(example.spo_list)

            if ex_index < 5:
                logger.info("*** Example ***")
                logger.info("guid: %s" % example.guid)
                logger.info("tokens: %s" % " ".join([str(x) for x in tokens]))
                logger.info("masks: %s" % " ".join([str(x) for x in masks]))

                logger.info("sub_heads: %s" % " ".join([str(x) for x in sub_heads]))
                logger.info("sub_tails: %s" % " ".join([str(x) for x in sub_tails]))

                logger.info("sub_head: %s" % " ".join([str(x) for x in sub_head]))
                logger.info("sub_tail: %s" % " ".join([str(x) for x in sub_tail]))
                logger.info("obj_heads: %s" % " ".join([str(x) for x in obj_heads]))
                logger.info("obj_tails: %s" % " ".join([str(x) for x in obj_tails]))
                logger.info("spo_list: %s" % " ".join([str(x) for x in example.spo_list]))

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, item):
        return {
            "texts": self.texts[item],
            "input_ids": self.input_ids[item],
            "masks": self.masks[item],
            "sub_heads": self.sub_heads[item],
            "sub_tails": self.sub_tails[item],
            "sub_head": self.sub_head[item],
            "sub_tail": self.sub_tail[item],
            "obj_heads": self.obj_heads[item],
            "obj_tails": self.obj_tails[item],
            "spo_list": self.spo_list[item],
        }


def collate_fn(features) -> Dict[str, Tensor]:
    batch_input_ids = [feature["input_ids"] for feature in features]
    batch_masks = [feature["masks"] for feature in features]

    batch_sub_heads = [feature["sub_heads"] for feature in features]
    batch_sub_tails = [feature["sub_tails"] for feature in features]
    batch_sub_head = [feature["sub_head"] for feature in features]
    batch_sub_tail = [feature["sub_tail"] for feature in features]
    batch_obj_heads = [feature["obj_heads"] for feature in features]
    batch_obj_tails = [feature["obj_tails"] for feature in features]

    batch_spo_list = [feature["spo_list"] for feature in features]

    batch_attention_mask = [torch.ones_like(feature["input_ids"]) for feature in features]

    # padding
    batch_input_ids = pad_sequence(batch_input_ids, batch_first=True, padding_value=0)
    batch_masks = pad_sequence(batch_masks, batch_first=True, padding_value=0)
    batch_sub_heads = pad_sequence(batch_sub_heads, batch_first=True, padding_value=0)
    batch_sub_tails = pad_sequence(batch_sub_tails, batch_first=True, padding_value=0)
    batch_sub_head = pad_sequence(batch_sub_head, batch_first=True, padding_value=0)
    batch_sub_tail = pad_sequence(batch_sub_tail, batch_first=True, padding_value=0)

    batch_obj_heads = pad_sequence(batch_obj_heads, batch_first=True, padding_value=0)
    batch_obj_tails = pad_sequence(batch_obj_tails, batch_first=True, padding_value=0)

    batch_attention_mask = pad_sequence(batch_attention_mask, batch_first=True, padding_value=0)

    assert batch_input_ids.shape == batch_sub_heads.shape
    assert batch_input_ids.shape == batch_sub_tails.shape

    return {
        "input_ids": batch_input_ids,
        "attention_mask": batch_attention_mask,
        "mask": batch_masks,
        "sub_head": batch_sub_head,
        "sub_tail": batch_sub_tail,
        "sub_heads": batch_sub_heads,
        "sub_tails": batch_sub_tails,
        "obj_heads": batch_obj_heads,
        "obj_tails": batch_obj_tails,
        "triples": batch_spo_list
    }


def load_dataset(args, tokenizer, data_type="train"):
    max_length = args.train_max_seq_length if data_type == 'train' else args.eval_max_seq_length
    cached_features_file = 'cached_{}-{}_{}_{}_{}'.format(args.model_name, data_type,
                                                          list(filter(None, args.model_name_or_path.split('/'))).pop(),
                                                          str(max_length), args.task_name)

    if os.path.exists(cached_features_file) and not args.overwrite_cache:
        logger.info("Loading dataset from cached file %s", cached_features_file)
        dataset = torch.load(cached_features_file)
        logger.info("Loading dataset success,length: %s", len(dataset))
    else:
        if data_type == "train":
            file_name = args.train_file
        elif data_type == "dev":
            file_name = args.dev_file
        elif data_type == "test":
            file_name = args.test_file
        else:
            file_name = args.dev_file

        logger.info("Creating dataset file at %s", file_name)
        dataset = Re18BaiduDataset(read_data(file_name), max_length=max_length, tokenizer=tokenizer)
        torch.save(dataset, cached_features_file)
        logger.info("Catching dataset file at %s,length: %s", cached_features_file, len(dataset))

    return dataset


if __name__ == '__main__':
    # 构建分词器
    tokenizer = load_tokenizer()

    train_filename = "{}/test.json".format(DATA_DIR)

    # 构建dataset
    # train_dataset = Re18BaiduDataset(read_data(train_filename), tokenizer=tokenizer)

    args = ModelArguments(save_steps=100)
    train_dataset = load_dataset(args, tokenizer=tokenizer, data_type="train")
    print(train_dataset[0])

    train_dataloader = DataLoader(train_dataset, shuffle=False, batch_size=32,
                                  collate_fn=collate_fn)

    batch = next(iter(train_dataloader))
    print(batch.keys())
    print(type(batch["input_ids"]))
    print(batch["input_ids"].shape)
    print(type(batch["sub_head"]))
    print(batch["sub_head"].shape)
    print(type(batch["attention_mask"]))
    print(batch["attention_mask"].shape)

    tags, tag2id, id2tag = load_tag()
    args = ModelArguments(num_relations=len(tags))
    config = BertConfig.from_pretrained(
        args.model_name_or_path,
        num_labels=args.num_labels,
        finetuning_task=args.task_name,
        id2label=id2tag,
        label2id=tag2id,
    )
    model = CasRel.from_pretrained(args.model_name_or_path, config=config, args=args)

    inputs = {"input_ids": batch["input_ids"], "attention_mask": batch["attention_mask"],
              "sub_head": batch["sub_head"], "sub_tail": batch["sub_tail"],
              "sub_heads": batch["sub_heads"], "sub_tails": batch["sub_tails"],
              "obj_heads": batch["obj_heads"], "obj_tails": batch["obj_tails"]}

    output = model(**inputs)
    print(type(output))
    print(output[0])
    print(type(output[0]))
    print(output[1])
    print(output[1].shape())

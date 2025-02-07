from collections import Counter

from nlp.bertner.utils_ner import get_entities


class SeqEntityScore(object):
    def __init__(self, id2label, markup='bios'):
        self.id2label = id2label
        self.markup = markup
        self.reset()

    def reset(self):
        self.origins = []
        self.founds = []
        self.rights = []

    def compute(self, origin, found, right):
        recall = 0 if origin == 0 else (right / origin)
        precision = 0 if found == 0 else (right / found)
        f1 = 0. if recall + precision == 0 else (2 * precision * recall) / (precision + recall)
        return recall, precision, f1

    def result(self):
        class_info = {}
        origin_counter = Counter([x[0] for x in self.origins])
        found_counter = Counter([x[0] for x in self.founds])
        right_counter = Counter([x[0] for x in self.rights])
        for type_, count in origin_counter.items():
            origin = count
            found = found_counter.get(type_, 0)
            right = right_counter.get(type_, 0)
            recall, precision, f1 = self.compute(origin, found, right)
            class_info[type_] = {"acc": round(precision, 4), 'recall': round(recall, 4), 'f1': round(f1, 4)}
        origin = len(self.origins)
        found = len(self.founds)
        right = len(self.rights)
        recall, precision, f1 = self.compute(origin, found, right)
        return {'acc': precision, 'recall': recall, 'f1': f1}, class_info

    def update(self, label_paths, pred_paths):
        '''
        labels_paths: [[],[],[],....]
        pred_paths: [[],[],[],.....]

        :param label_paths:
        :param pred_paths:
        :return:
        Example:
            >>> labels_paths = [['O', 'O', 'O', 'B-MISC', 'I-MISC', 'I-MISC', 'O'], ['B-PER', 'I-PER', 'O']]
            >>> pred_paths = [['O', 'O', 'B-MISC', 'I-MISC', 'I-MISC', 'I-MISC', 'O'], ['B-PER', 'I-PER', 'O']]
        '''
        for label_path, pre_path in zip(label_paths, pred_paths):
            label_entities = get_entities(label_path, self.id2label, self.markup)
            pre_entities = get_entities(pre_path, self.id2label, self.markup)
            self.origins.extend(label_entities)
            self.founds.extend(pre_entities)
            self.rights.extend([pre_entity for pre_entity in pre_entities if pre_entity in label_entities])


def compute_metric(metric: SeqEntityScore, preds, labels, tag2id, id2tag):
    """计算NER 的指标"""
    for i, label in enumerate(labels):
        temp_1 = []
        temp_2 = []
        for j, m in enumerate(label):
            if j == 0:
                continue
            elif labels[i][j] == tag2id['<eos>']:
                metric.update(pred_paths=[temp_2], label_paths=[temp_1])
                break
            else:
                temp_1.append(id2tag[labels[i][j]])
                temp_2.append(preds[i][j])


class SpanEntityScore(object):
    def __init__(self, id2label):
        self.id2label = id2label
        self.reset()

    def reset(self):
        self.origins = []
        self.founds = []
        self.rights = []

    def compute(self, origin, found, right):
        recall = 0 if origin == 0 else (right / origin)
        precision = 0 if found == 0 else (right / found)
        f1 = 0. if recall + precision == 0 else (2 * precision * recall) / (precision + recall)
        return recall, precision, f1

    def result(self):
        class_info = {}
        origin_counter = Counter([self.id2label[x[0]] for x in self.origins])
        found_counter = Counter([self.id2label[x[0]] for x in self.founds])
        right_counter = Counter([self.id2label[x[0]] for x in self.rights])
        for type_, count in origin_counter.items():
            origin = count
            found = found_counter.get(type_, 0)
            right = right_counter.get(type_, 0)
            recall, precision, f1 = self.compute(origin, found, right)
            class_info[type_] = {"acc": round(precision, 4), 'recall': round(recall, 4), 'f1': round(f1, 4)}
        origin = len(self.origins)
        found = len(self.founds)
        right = len(self.rights)
        recall, precision, f1 = self.compute(origin, found, right)
        return {'acc': precision, 'recall': recall, 'f1': f1}, class_info

    def update(self, true_subject, pred_subject):
        self.origins.extend(true_subject)
        self.founds.extend(pred_subject)
        self.rights.extend([pre_entity for pre_entity in pred_subject if pre_entity in true_subject])


if __name__ == '__main__':
    class_list = ["X", "B-address", "B-book", "B-company", 'B-game', 'B-government', 'B-movie', 'B-name',
                  'B-organization', 'B-position', 'B-scene', "I-address",
                  "I-book", "I-company", 'I-game', 'I-government', 'I-movie', 'I-name',
                  'I-organization', 'I-position', 'I-scene',
                  "S-address", "S-book", "S-company", 'S-game', 'S-government', 'S-movie',
                  'S-name', 'S-organization', 'S-position',
                  'S-scene', 'O', "[CLS]", "[SEP]"]

    id2label = {i: label for i, label in enumerate(class_list)}
    label2id = {label: i for i, label in enumerate(class_list)}

    metric = SeqEntityScore(id2label, markup='bios')
    labels_paths = [['O', 'O', 'B-address', 'I-address', 'I-address', 'I-address', 'O'], ['B-name', 'I-name', 'O']]
    pred_paths = [['O', 'O', 'B-address', 'I-address', 'I-address', 'I-address', 'O'], ['B-name', 'I-name', 'O']]

    labels_paths = [
        ['O', 'O', 'O', 'O', 'B-game', 'I-game', 'I-game', 'I-game', 'O', 'O', 'O', 'O', 'O', 'O', 'O', 'O', 'O', 'O'],
        ['B-organization', 'I-organization', 'I-organization', 'I-organization', 'O', 'O', 'B-organization',
         'I-organization', 'I-organization', 'O', 'O', 'B-organization', 'I-organization', 'O', 'O', 'B-organization',
         'I-organization', 'I-organization', 'O', 'O', 'O', 'O'],
        ['B-movie', 'I-movie', 'I-movie', 'I-movie', 'I-movie', 'I-movie', 'I-movie', 'I-movie', 'I-movie', 'I-movie',
         'I-movie', 'I-movie', 'O', 'O', 'O', 'O', 'O', 'O', 'O', 'O', 'O', 'O', 'O', 'O', 'O', 'O', 'O', 'O', 'O', 'O',
         'O', 'O', 'O', 'B-movie', 'I-movie', 'I-movie', 'I-movie', 'I-movie', 'I-movie', 'O'],
        ['B-organization', 'I-organization', 'I-organization', 'I-organization', 'I-organization', 'I-organization',
         'I-organization', 'I-organization', 'I-organization', 'I-organization', 'I-organization', 'I-organization',
         'I-organization', 'B-position', 'I-position', 'I-position', 'I-position', 'I-position', 'B-name', 'I-name',
         'O', 'O', 'O', 'O', 'O', 'O', 'O', 'O', 'O', 'O', 'O', 'O', 'B-address', 'I-address', 'O', 'O', 'O', 'O', 'O',
         'O', 'O', 'O', 'O', 'O'],
        ['O', 'O', 'O', 'O', 'O', 'O', 'O', 'O', 'O', 'O', 'O', 'O', 'O', 'O', 'O', 'O', 'O', 'O', 'O', 'O', 'O',
         'B-organization', 'I-organization', 'I-organization', 'I-organization', 'I-organization', 'I-organization',
         'O', 'O', 'B-organization', 'I-organization', 'I-organization', 'I-organization', 'I-organization',
         'I-organization', 'I-organization', 'I-organization', 'O', 'O', 'O', 'O', 'O', 'O', 'O', 'O', 'O', 'O', 'O'],
        ['O', 'O', 'O', 'O', 'O', 'O', 'O', 'O', 'O', 'B-organization', 'I-organization', 'O', 'O', 'O', 'O', 'O', 'O',
         'O', 'O', 'O'],
        ['O', 'O', 'O', 'O', 'O', 'O', 'O', 'O', 'B-game', 'I-game', 'I-game', 'I-game', 'O', 'O', 'O', 'O', 'O', 'O',
         'O', 'O', 'O', 'O', 'O', 'O', 'O', 'O', 'O'],
        ['O', 'O', 'B-name', 'I-name', 'I-name', 'O', 'O', 'O', 'O', 'O', 'B-name', 'I-name', 'I-name', 'O', 'B-name',
         'I-name', 'I-name', 'O', 'B-name', 'I-name', 'I-name', 'O', 'O', 'O', 'O', 'O', 'O', 'O', 'O', 'O'],
        ['O', 'O', 'O', 'O', 'O', 'O', 'O', 'O', 'O', 'O', 'O', 'O', 'O', 'O', 'O', 'O', 'O', 'O', 'O', 'O', 'O', 'O',
         'O', 'O', 'O', 'O', 'O', 'O', 'O', 'O', 'O', 'O', 'O', 'O', 'O', 'O', 'O', 'O', 'O', 'B-organization',
         'I-organization', 'O', 'O', 'O', 'O', 'O', 'O']]
    pred_paths = labels_paths

    metric.update(pred_paths=labels_paths, label_paths=pred_paths)

    print(' ')
    eval_info, entity_info = metric.result()
    results = {f'{key}': value for key, value in eval_info.items()}
    results['loss'] = 0.0
    info = "-".join([f' {key}: {value:.4f} ' for key, value in results.items()])
    print(info)

    for key in sorted(entity_info.keys()):
        print("******* %s results ********" % key)
        info = "-".join([f' {key}: {value:.4f} ' for key, value in entity_info[key].items()])
        print(info)
    pass

#!/user/bin/env python
# -*- coding: utf-8 -*-
# @File  : model.py
# @Author: sl
# @Date  : 2021/8/26 - 上午9:34
import torch
import torch.nn as nn
from transformers import BertPreTrainedModel, BertModel
from transformers.modeling_outputs import TokenClassifierOutput


class FCLayer(nn.Module):
    def __init__(self, input_dim, output_dim, dropout_rate=0.0, use_activation=True):
        super(FCLayer, self).__init__()
        self.use_activation = use_activation
        self.dropout = nn.Dropout(dropout_rate)
        self.linear = nn.Linear(input_dim, output_dim)
        self.tanh = nn.Tanh()

    def forward(self, x):
        x = self.dropout(x)
        if self.use_activation:
            x = self.tanh(x)
        x = self.linear(x)
        return x


class RBERT(BertPreTrainedModel):
    def __init__(self, config, args):
        super(RBERT, self).__init__(config)
        self.bert = BertModel(config)
        self.num_labels = config.num_labels
        self.cls_fc_layer = FCLayer(config.hidden_size, config.hidden_size, args.dropout_rate)
        self.entity_fc_layer = FCLayer(config.hidden_size, config.hidden_size, args.dropout_rate)
        self.label_classifier = FCLayer(config.hidden_size * 3, config.num_labels,
                                        args.dropout_rate, use_activation=False)

    @staticmethod
    def entity_average(hidden_output, e_mask):
        """
        Average the entity hidden state vectors (H_i ~ H_j)
        :param hidden_output: [batch_size, j-i+1, dim]
        :param e_mask: [batch_size, max_seq_len]
                e.g. e_mask[0] == [0, 0, 0, 1, 1, 1, 0, 0, ... 0]
        :return: [batch_size, dim]
        """
        e_mask_unsqueeze = e_mask.unsqueeze(1)  # [b, 1, j-i+1]
        length_tensor = (e_mask != 0).sum(dim=1).unsqueeze(1)  # [batch_size, 1]

        # [b, 1, j-i+1] * [b, j-i+1, dim] = [b, 1, dim] -> [b, dim]
        sum_vector = torch.bmm(e_mask_unsqueeze.float(), hidden_output).squeeze(1)
        avg_vector = sum_vector.float() / length_tensor.float()  # broadcasting
        return avg_vector

    def forward(self, input_ids=None, attention_mask=None, token_type_ids=None, labels=None,
                e1_mask=None, e2_mask=None, output_attentions=None, output_hidden_states=None, return_dict=False,
                ):
        return_dict = return_dict if return_dict is not None else self.config.use_return_dict

        outputs = self.bert(
            input_ids,
            attention_mask=attention_mask,
            token_type_ids=token_type_ids,
            output_attentions=output_attentions,
            output_hidden_states=output_hidden_states,
            return_dict=return_dict,
        )  # sequence_output, pooled_output, (hidden_states), (attentions)

        sequence_output = outputs[0]
        pooled_output = outputs[1]  # CLS

        # Average
        e1_h = self.entity_average(sequence_output, e1_mask)
        e2_h = self.entity_average(sequence_output, e2_mask)

        # Dropout -> tanh -> fc_layer (Share FC layer for e1 and e2)
        pooled_output = self.cls_fc_layer(pooled_output)
        e1_h = self.entity_fc_layer(e1_h)
        e2_h = self.entity_fc_layer(e2_h)

        # Concat -> fc_layer
        concat_h = torch.cat([pooled_output, e1_h, e2_h], dim=1)
        logits = self.label_classifier(concat_h)

        outputs = (logits,) + outputs[2:]  # add hidden states and attention if they are here

        # 　Softmax
        loss = None
        if labels is not None:
            if self.num_labels == 1:
                loss_fct = nn.MSELoss()
                loss = loss_fct(logits.reshape(-1), labels.reshape(-1))
            else:
                loss_fct = nn.CrossEntropyLoss()
                loss = loss_fct(logits.reshape(-1, self.num_labels), labels.reshape(-1))
            outputs = (loss,) + outputs

        if not return_dict:
            return outputs

        return TokenClassifierOutput(
            loss=loss,
            logits=logits,
            hidden_states=outputs.hidden_states,
            attentions=outputs.attentions,
        )

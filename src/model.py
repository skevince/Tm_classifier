import torch
import torch.nn as nn
import torch.nn.functional as F


class Model(nn.Module):
    def __init__(self, vocabulary_size, embedding_dim, hidden_dim, num_classes,
                 pretrain_char_embedding=None, if_glove=False,
                 freeze=False, dropout=0.5, if_biLSTM=False, device=None, bowandlstm=False):
        super(Model, self).__init__()
        self.device = device
        self.vocabulary_size = vocabulary_size
        self.hidden_dim = hidden_dim
        self.embedding_dim = embedding_dim
        self.num_classes = num_classes
        self.dropout = dropout
        self.if_biLSTM = if_biLSTM
        self.bowandlstm = bowandlstm
        if self.bowandlstm:
            self.hidden_dim = 150
        if if_glove == True:
            self.word_embeddings = nn.Embedding.from_pretrained(pretrain_char_embedding, freeze=freeze)
        else:
            self.word_embeddings = nn.Embedding(self.vocabulary_size, self.embedding_dim,
                                                padding_idx=vocabulary_size - 1)
        if if_biLSTM == True:
            self.lstm = nn.LSTM(self.embedding_dim, self.hidden_dim, bidirectional=True)
            self.fc1 = nn.Linear(self.hidden_dim * 2, hidden_dim * 4)
        else:
            self.fc1 = nn.Linear(self.embedding_dim, hidden_dim * 4)
        self.relu_1 = nn.ReLU(inplace=True)
        self.dropout1 = nn.Dropout(p=self.dropout)
        self.fc2 = nn.Linear(hidden_dim * 4, hidden_dim * 2)
        self.relu_2 = nn.ReLU(inplace=True)
        self.dropout2 = nn.Dropout(p=self.dropout)
        self.fc3 = nn.Linear(hidden_dim * 2, self.num_classes)
        self.softmax = nn.Softmax(dim=1)

    def forward(self, x, seq_len):
        out = self.word_embeddings(x)
        # sort and remove padding
        _, idx_sort = torch.sort(seq_len, dim=0, descending=True)
        _, idx_unsort = torch.sort(idx_sort)
        out = torch.index_select(out, 0, idx_sort)
        if self.bowandlstm:
            out1 = out.clone()
        seq_len = list(seq_len[idx_sort])
        if self.if_biLSTM == True:
            out = nn.utils.rnn.pack_padded_sequence(out, seq_len, batch_first=True)
            out, (hn, _) = self.lstm(out)
            out, _ = nn.utils.rnn.pad_packed_sequence(out, batch_first=True)
        out = torch.sum(out, dim=1)
        seq_len = torch.FloatTensor(seq_len)
        seq_len = seq_len.reshape([x.shape[0], 1])
        if self.if_biLSTM == True:
            seq_len = seq_len.expand([x.shape[0], self.hidden_dim * 2])
        else:
            seq_len = seq_len.expand([x.shape[0], self.embedding_dim])
        # if self.device != None:
        #      seq_len = seq_len.to(self.device)
        if self.bowandlstm:
            out1 = torch.sum(out1, dim=1)
            out1 = torch.div(out1, seq_len)
            out = (out * 1.5 + out1 * 0.5) / 2
        out = torch.div(out, seq_len)
        out = self.fc1(out)
        out = self.relu_1(out)
        out = self.dropout1(out)
        out = self.fc2(out)
        out = self.relu_2(out)
        out = self.dropout1(out)
        out = self.fc3(out)
        out = F.log_softmax(out, dim=1)
        return out, idx_sort

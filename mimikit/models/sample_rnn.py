import numpy as np
from numpy.lib.stride_tricks import as_strided as np_as_strided
from pytorch_lightning import LightningModule
import torch
import torch.nn as nn
from torchaudio.transforms import MuLawDecoding
import matplotlib.pyplot as plt

from ..kit import DBDataset
from ..audios import transforms as A
from ..kit.ds_utils import ShiftedSequences
from ..kit import SuperAdam, SequenceModel, DataSubModule
from ..kit.networks.sample_rnn import SampleRNNNetwork
from ..kit.sub_models.utils import tqdm
from ..utils import audio
from torch.utils.data import Sampler, RandomSampler, BatchSampler
import math


class TBPTTSampler(Sampler):
    """
    yields batches of indices for performing Truncated Back Propagation Through Time
    """
    def __init__(self,
                 n_samples,
                 batch_size=64,  # nbr of "tracks" per batch
                 chunk_length=8*16000,  # total length of a track
                 seq_len=512  # nbr of samples per backward pass
                 ):
        super().__init__(None)
        self.n_samples = n_samples
        self.chunk_length = chunk_length
        self.seq_len = seq_len
        self.n_chunks = self.n_samples // self.chunk_length
        self.n_per_chunk = self.chunk_length // self.seq_len
        self.batch_size = min(batch_size, self.n_chunks)

    def __iter__(self):
        smp = RandomSampler(torch.arange(self.n_chunks))
        for top in BatchSampler(smp, self.batch_size, True):  # drop last!
            for start in range(self.n_per_chunk):
                # start indices of the batch
                yield tuple((t * self.chunk_length) + (start * self.seq_len) for t in top)

    def __len__(self):
        return int(max(1, math.floor(self.n_chunks / self.batch_size)) * self.n_per_chunk)


class FramesDB(DBDataset):
    qx = None

    @staticmethod
    def extract(path, sr=16000, mu=255):
        signal = A.FileTo.mu_law_compress(path, sr=sr, mu=mu)
        return dict(qx=(dict(sr=sr, mu=mu), signal.reshape(-1, 1), None))

    def prepare_dataset(self, model, datamodule):
        batch_size, chunk_len, batch_seq_len, frame_sizes = model.batch_info()
        shifts = [frame_sizes[0] - size for size in frame_sizes + (0,)]  # (0,) for the target
        lengths = [batch_seq_len for _ in frame_sizes[:-1]]
        lengths += [frame_sizes[0] + batch_seq_len]
        lengths += [batch_seq_len]

        self.slicer = ShiftedSequences(len(self.qx), list(zip(shifts, lengths)))
        self.frame_sizes = frame_sizes
        self.seq_len = batch_seq_len

        # round the size of the dataset to a multiple of the chunk size :
        batch_sampler = TBPTTSampler(chunk_len * (len(self.qx) // chunk_len),
                                     batch_size,
                                     chunk_len,
                                     batch_seq_len)
        datamodule.loader_kwargs.update(dict(batch_sampler=batch_sampler))
        for k in ["batch_size", "shuffle", "drop_last"]:
            if k in datamodule.loader_kwargs:
                datamodule.loader_kwargs.pop(k)
        datamodule.loader_kwargs["sampler"] = None

    def __getitem__(self, item):
        if type(self.qx) is not torch.Tensor:
            itemsize = self.qx.dtype.itemsize
            as_strided = lambda slc, fs: np_as_strided(self.qx[slc],
                                                       shape=(self.seq_len, fs),
                                                       strides=(itemsize, itemsize))
        else:
            as_strided = lambda slc, fs: torch.as_strided(self.qx[slc],
                                                          size=(self.seq_len, fs),
                                                          stride=(1, 1))

        slices = self.slicer(item)
        tiers_slc, bottom_slc, target_slc = slices[:-2], slices[-2], slices[-1]
        inputs = [self.qx[slc].reshape(-1, fs) for slc, fs in zip(tiers_slc, self.frame_sizes[:-1])]
        # ugly but necessary if self.qx became a tensor...
        with torch.no_grad():
            inputs += [as_strided(bottom_slc, self.frame_sizes[-1])]

        target = self.qx[target_slc]

        return tuple(inputs), target

    def __len__(self):
        return len(self.qx)


class SampleRNN(SequenceModel,
                DataSubModule,
                SuperAdam,
                SampleRNNNetwork,
                LightningModule):

    @staticmethod
    def loss_fn(output, target):
        criterion = nn.CrossEntropyLoss(reduction="mean")
        return criterion(output.view(-1, output.size(-1)), target.view(-1))

    db_class = FramesDB

    def __init__(self,
                 frame_sizes=(4, 4),
                 net_dim=128,
                 emb_dim=128,
                 mlp_dim=256,
                 n_rnn=1,
                 q_levels=256,  # == mu + 1
                 max_lr=1e-3,
                 betas=(.9, .9),
                 div_factor=3.,
                 final_div_factor=1.,
                 pct_start=.25,
                 cycle_momentum=True,
                 db=None,
                 batch_size=64,
                 batch_seq_len=512,
                 chunk_len=8*16000,
                 n_test_warmups=10,
                 n_test_prompts=2,
                 n_test_steps=16000,
                 test_temp=0.5,
                 test_every_n_epochs=3,
                 in_mem_data=True,
                 splits=None,  # tbptt should implement the splits...
                 **loaders_kwargs
                 ):
        super(LightningModule, self).__init__()
        SequenceModel.__init__(self)
        DataSubModule.__init__(self, db, in_mem_data, splits, batch_size=batch_size, **loaders_kwargs)
        SuperAdam.__init__(self, max_lr, betas, div_factor, final_div_factor, pct_start, cycle_momentum)
        SampleRNNNetwork.__init__(self, frame_sizes, net_dim, n_rnn, q_levels, emb_dim, mlp_dim)
        self.save_hyperparameters()
        self.stored_grad_norms = []

    def batch_info(self, *args, **kwargs):
        return tuple(self.hparams[key] for key in ["batch_size", "chunk_len", "batch_seq_len", "frame_sizes"])

    def setup(self, stage: str):
        SuperAdam.setup(self, stage)

    def on_train_batch_start(self, batch, batch_idx, dataloader_idx):
        if (batch_idx * self.hparams.batch_seq_len) % self.hparams.chunk_len == 0:
            self.reset_h0()

    def on_epoch_end(self):
        super().on_epoch_end()
        if (1 + self.current_epoch) % self.hparams.test_every_n_epochs != 0:
            return
        new = self.warm_up(self.hparams.n_test_warmups, self.hparams.n_test_prompts)
        new = self.generate(new,
                            self.hparams.n_test_steps,
                            decode_outputs=True,
                            temperature=self.hparams.test_temp)
        self.train()
        for i in range(new.size(0)):
            y = new[i].squeeze().cpu().numpy()
            print("prompt number", i)
            plt.figure(figsize=(20, 2))
            plt.plot(y)
            plt.show()

            audio(y, sr=16000)

    def warm_up(self, n_warmups=10, n_prompts=4):
        self.eval()
        self.to("cuda")
        self.reset_h0()

        dl = iter(self.datamodule.train_dataloader())

        for _ in range(n_warmups):
            inpt, trgt = next(dl)
            inpt = tuple(x[:n_prompts].to("cuda") for x in inpt)
            with torch.no_grad():
                new = nn.Softmax(dim=-1)(self(inpt)).argmax(dim=-1)

        return new

    def decode_outputs(self, outputs):
        decoder = MuLawDecoding(self.hparams.q_levels)
        return decoder(outputs)

    def generate(self, prompt, n_steps=16000, decode_outputs=False, temperature=.5):
        # prepare model
        was_training = self.training
        initial_device = self.device
        self.eval()
        self.to("cuda" if torch.cuda.is_available() else "cpu")

        # prepare prompt
        if not isinstance(prompt, torch.Tensor):
            prompt = torch.from_numpy(prompt)
        if len(prompt.shape) == 1:
            prompt = prompt.unsqueeze(0)
        new = prompt.to(self.device)

        # init variables
        fs = [*self.frame_sizes]
        outputs = [None] * (len(fs) - 1)
        hiddens = self.hidden
        tiers = self.tiers

        for t in tqdm(range(new.size(1), n_steps + new.size(1)),
                      desc="Generate", dynamic_ncols=True, leave=False, unit="step"):
            for i in range(len(tiers) - 1):
                if t % fs[i] == 0:
                    inpt = new[:, t - fs[i]:t].unsqueeze(1)

                    if i == 0:
                        prev_out = None
                    else:
                        prev_out = outputs[i - 1][:, (t // fs[i]) % (fs[i - 1] // fs[i])].unsqueeze(1)

                    with torch.no_grad():
                        out, h = tiers[i](inpt, prev_out, hiddens[i])
                    hiddens[i] = h
                    outputs[i] = out

            prev_out = outputs[-1]
            inpt = new[:, t - fs[-1]:t].reshape(-1, 1, fs[-1])

            with torch.no_grad():
                out, _ = tiers[-1](inpt, prev_out[:, (t % fs[-1]) - fs[-1]].unsqueeze(1))
                if temperature is None:
                    pred = (nn.Softmax(dim=-1)(out)).argmax(dim=-1)
                else:
                    # great place to implement dynamic cooling/heating !
                    pred = torch.multinomial(nn.Softmax(dim=-1)(out / temperature).reshape(-1, out.size(-1)), 1)
                new = torch.cat((new, pred), dim=-1)

        # reset model
        self.to(initial_device)
        self.train() if was_training else None

        if decode_outputs:
            new = self.decode_outputs(new)

        return new

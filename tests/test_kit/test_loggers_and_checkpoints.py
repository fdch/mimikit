import os
import shutil
import pytorch_lightning as pl
import torch
import torch.nn as nn

from mimikit.kit import MMKHooks, LoggingHooks, get_trainer


class TestModel(MMKHooks,
                LoggingHooks,
                pl.LightningModule):

    def __init__(self, model_dim=10):
        super(pl.LightningModule, self).__init__()
        MMKHooks.__init__(self)
        LoggingHooks.__init__(self)
        self.fc = nn.Linear(model_dim, model_dim)
        self.save_hyperparameters()

    def forward(self, x):
        return self.fc(x)

    def training_step(self, batch, batch_idx):
        inpt, target = batch
        pred = self.forward(inpt)
        L = nn.MSELoss()(pred, target)
        self.log("recon", L, on_step=False, on_epoch=True)
        return {"loss": L, "recon_loss": L}

    def validation_step(self, batch, batch_idx):
        inpt, target = batch
        pred = self.forward(inpt)
        L = nn.MSELoss()(pred, target)
        self.log("recon", L, on_step=False, on_epoch=True)
        return {"loss": L, "recon_loss": L}

    def configure_optimizers(self):
        return torch.optim.Adam(self.parameters())

    def train_dataloader(self):
        ds = torch.utils.data.TensorDataset(torch.randn(32, 10), torch.randn(32, 10))
        return torch.utils.data.DataLoader(ds, batch_size=16)

    def val_dataloader(self):
        ds = torch.utils.data.TensorDataset(torch.randn(32, 10), torch.randn(32, 10))
        return torch.utils.data.DataLoader(ds, batch_size=16)


def test_model(tmp_path):
    root = tmp_path / "model_test"
    root.mkdir()
    print("FIRST RUN")
    mdl = TestModel(model_dim=10)
    trainer = get_trainer(root_dir=str(root), version=None, epochs=1, max_epochs=2)
    trainer.fit(mdl)
    assert trainer.current_epoch == 1

    created = os.listdir(str(root))
    assert "states" in created, created
    assert "logs" in created, created

    states = os.listdir(os.path.join(root, "states"))
    assert 'last_optim_state.ckpt' in states, states
    assert 'epoch=1.ckpt' in states, states

    ckpt_path = str(root / "states" / 'epoch=1.ckpt')
    ckpt = torch.load(ckpt_path)
    assert "hyper_parameters" in ckpt, list(ckpt.keys())
    assert "state_dict" in ckpt, list(ckpt.keys())
    assert "mmk_version" in ckpt, list(ckpt.keys())
    assert "epoch" in ckpt, list(ckpt.keys())
    assert "global_step" in ckpt, list(ckpt.keys())
    assert "optimizer_states" not in ckpt
    assert "lr_schedulers" not in ckpt

    from_ckpt = TestModel.load_from_checkpoint(ckpt_path)
    assert isinstance(from_ckpt, TestModel)
    new_trainer = get_trainer(resume_from_checkpoint=ckpt_path, max_epochs=4)
    print("SECOND RUN")
    new_trainer.fit(from_ckpt)
    assert new_trainer.current_epoch == 3

    from_ckpt = TestModel.load_from_checkpoint(ckpt_path)
    new_trainer = get_trainer(resume_from_checkpoint=ckpt_path, epochs=None, max_epochs=4)
    print("THIRD RUN")
    new_trainer.fit(from_ckpt)
    assert new_trainer.current_epoch == 3

    assert new_trainer.current_epoch > trainer.current_epoch
    assert new_trainer.global_step > trainer.global_step, (new_trainer.global_step, trainer.global_step)

    shutil.rmtree(root)

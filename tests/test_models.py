import pytest
from inspect import getsource
import re
import torch
import numpy as np
import matplotlib.pyplot as plt
import soundfile


from mimikit.models.freqnet import demo as fnet
from mimikit.models.sample_rnn import demo as srnn
from mimikit.models.s2s_lstm import demo as s2s
from mimikit.models.wavenet import demo as wnet


@pytest.fixture
def example_root(tmp_path):
    root = (tmp_path / "models")
    root.mkdir()
    data = (root / "data")
    data.mkdir()
    # we need at least 8 sec of audio...
    audio = np.random.rand(22050 * 10) - .5
    soundfile.write(str(data / "example.wav"), audio, 22050, 'PCM_24', format="WAV")
    return str(root)

@pytest.mark.parametrize("model", [fnet, srnn, s2s, wnet])
def test_models(example_root, monkeypatch, model):
    with_gpu = torch.cuda.is_available()
    src = getsource(model)

    src = re.sub(r"db_path = '.*.h5'\n", f"db_path = '{example_root}/data.h5'\n", src)
    src = re.sub(r"sources =.*\n", f"sources = ['{example_root}']\n", src)
    src = re.sub(r"every_n_epochs =.*\n", "every_n_epochs=1\n", src)
    src = re.sub(r"n_steps =.*\n", "n_steps = 10\n", src)
    src = re.sub(r"limit_train_batches=.*\n", "", src)
    src = re.sub(r"max_epochs=.*,\n", "max_epochs=1,limit_train_batches=10,\n", src)
    src = re.sub(r"root_dir=.*\n", f"root_dir ='{example_root}',\n", src)
    src += """\n\n\ndemo()\n"""
    print("----- RUNNING DEMO for", model, "-----------")
    # run the demo
    if with_gpu:
        exec(src)
        monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
        exec(src)
    else:
        monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
        exec (src)
    plt.close('all')
    # we only need that the demo runs without raising exceptions
    assert True
    return

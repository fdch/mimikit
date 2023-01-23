import ipywidgets as W
from .. import ui as UI
from ..networks.sample_rnn_v2 import SampleRNN

__all__ = [
    "sample_rnn_view"
]


def sample_rnn_view(cfg: SampleRNN.Config):

    view = UI.ConfigView(
        cfg,
        UI.Param(
            name='frame_sizes',
            widget=UI.Labeled(
                "Frame Sizes",
                W.Text(value=str(cfg.frame_sizes)[1:-1]),
                ),
            setter=lambda c, v: tuple(map(int, (s for s in v.split(",") if s not in ("", " "))))
        ),
        UI.Param(
            name='hidden_dim',
            widget=UI.Labeled(
                "Hidden Dim: ",
                UI.pw2_widget(value=str(cfg.hidden_dim))
            ),
            setter=lambda c, v: int(v)
        ),
        UI.Param(
            name="rnn_class",
            widget=UI.EnumWidget(
                W.Label(value="Type of RNN: "),
                [W.ToggleButton(description="LSTM"),
                 W.ToggleButton(description="RNN"),
                 W.ToggleButton(description="GRU")
                 ],
                W.HBox()
            ),
            setter=lambda c, v: v.lower()
        ),
        UI.Param(
            name="n_rnn",
            widget=UI.Labeled(
                "Num of RNN: ",
                W.IntText(value=cfg.n_rnn),
            )
        ),
        UI.Param(
            name="rnn_dropout",
            widget=UI.Labeled(
                "RNN dropout: ",
                W.FloatText(value=cfg.rnn_dropout, min=0., max=.999, step=.01,),
            )
        ),
        UI.Param(name="rnn_bias",
                 widget=UI.Labeled(
                     "use bias by RNNs",
                     UI.yesno_widget(initial_value=cfg.rnn_bias),
                 ),),
        UI.Param(
            name="h0_init",
            widget=UI.EnumWidget(
                W.Label(value="Hidden initialization: "),
                [W.ToggleButton(description="zeros"),
                 W.ToggleButton(description="randn"),
                 W.ToggleButton(description="ones")
                 ],
                W.HBox()
            ),
            setter=lambda c, v: v.lower()
        ),
        UI.Param(name="weight_norm",
                 widget=UI.Labeled(
                     "use weights normalization: ",
                     UI.yesno_widget(initial_value=cfg.weight_norm),
                 ), ),

    ).as_widget(lambda children, **kwargs: W.Accordion([W.VBox(children=children)], **kwargs),
                selected_index=0, layout=W.Layout(margin="0 auto 0 0", width="500px"))
    view.set_title(0, "SampleRNN Config")
    return view

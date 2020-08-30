from distutils.version import LooseVersion

import pytest
import torch

from tests.base import EvalModelTemplate
from tests.base.datamodules import TrialMNISTDataModule
from tests.base.models import ParityModuleRNN, BasicGAN


@pytest.mark.parametrize("modelclass", [
    EvalModelTemplate,
    ParityModuleRNN,
    BasicGAN,
])
def test_torchscript_input_output(modelclass):
    """ Test that scripted LightningModule forward works. """
    model = modelclass()
    script = model.to_torchscript()
    assert isinstance(script, torch.jit.ScriptModule)
    model.eval()
    model_output = model(model.example_input_array)
    script_output = script(model.example_input_array)
    assert torch.allclose(script_output, model_output)


def test_torchscript_retain_training_state():
    """ Test that torchscript export does not alter the training mode of original model. """
    model = EvalModelTemplate()
    model.train(True)
    script = model.to_torchscript()
    assert model.training
    assert not script.training
    model.train(False)
    _ = model.to_torchscript()
    assert not model.training
    assert not script.training


@pytest.mark.parametrize("modelclass", [
    EvalModelTemplate,
    ParityModuleRNN,
    BasicGAN,
])
def test_torchscript_properties(modelclass):
    """ Test that scripted LightningModule has unnecessary methods removed. """
    model = modelclass()
    model.datamodule = TrialMNISTDataModule()
    script = model.to_torchscript()
    assert not hasattr(script, "datamodule")
    assert not hasattr(model, "batch_size") or hasattr(script, "batch_size")
    assert not hasattr(model, "learning_rate") or hasattr(script, "learning_rate")

    if LooseVersion(torch.__version__) >= LooseVersion("1.4.0"):
        # only on torch >= 1.4 do these unused methods get removed
        assert not callable(getattr(script, "training_step", None))


@pytest.mark.parametrize("modelclass", [
    EvalModelTemplate,
    ParityModuleRNN,
    BasicGAN,
])
@pytest.mark.skipif(
    LooseVersion(torch.__version__) < LooseVersion("1.5.0"),
    reason="torch.save/load has bug loading script modules on torch <= 1.4",
)
def test_torchscript_save_load(tmpdir, modelclass):
    """ Test that scripted LightningModules can be saved and loaded. """
    model = modelclass()
    script = model.to_torchscript()
    assert isinstance(script, torch.jit.ScriptModule)
    output_file = str(tmpdir / "model.pt")
    torch.jit.save(script, output_file)
    torch.jit.load(output_file)

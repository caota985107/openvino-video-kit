# ===== CELL 2 =====
%pip install -q "torch>=2.1" "diffusers>=0.25" accelerate "peft>=0.15.0" "transformers<5" Pillow opencv-python tqdm "gradio>=4.19" safetensors --extra-index-url https://download.pytorch.org/whl/cpu
%pip install -q "datasets<4.0.0" "nncf>=2.16.0"
%pip install -qU --pre "openvino>=2025.1.0" --extra-index-url https://storage.openvinotoolkit.org/simple/wheels/nightly

# ===== CELL 3 =====
from pathlib import Path
import requests

if not Path("lcm_scheduler.py").exists():
    lcm_scheduler_url = "https://huggingface.co/spaces/wangfuyun/AnimateLCM-SVD/raw/main/lcm_scheduler.py"

    r = requests.get(lcm_scheduler_url)

    with open("lcm_scheduler.py", "w") as f:
        f.write(r.text)

if not Path("skip_kernel_extension.py").exists():
    r = requests.get(
        url="https://raw.githubusercontent.com/openvinotoolkit/openvino_notebooks/latest/utils/skip_kernel_extension.py",
    )
    open("skip_kernel_extension.py", "w").write(r.text)

if not Path("notebook_utils.py").exists():

    r = requests.get(
        url="https://raw.githubusercontent.com/openvinotoolkit/openvino_notebooks/latest/utils/notebook_utils.py",
    )
    open("notebook_utils.py", "w").write(r.text)

if not Path("ov_stable_video_diffusion_helper.py").exists():

    r = requests.get(
        url="https://raw.githubusercontent.com/openvinotoolkit/openvino_notebooks/latest/notebooks/stable-video-diffusion/ov_stable_video_diffusion_helper.py",
    )
    open("ov_stable_video_diffusion_helper.py", "w").write(r.text)

# ===== CELL 5 =====
# Read more about telemetry collection at https://github.com/openvinotoolkit/openvino_notebooks?tab=readme-ov-file#-telemetry
from notebook_utils import collect_telemetry

collect_telemetry("stable-video-diffusion.ipynb")

from ov_stable_video_diffusion_helper import convert_stable_video_diffusion

# Uncomment the line to see model conversion code
# ??convert_stable_video_diffusion

# ===== CELL 6 =====
convert_stable_video_diffusion()

# ===== CELL 8 =====
from ov_stable_video_diffusion_helper import OVStableVideoDiffusionPipeline

# Uncomment the line to see pipeline code
# ??OVStableVideoDiffusionPipeline

# ===== CELL 10 =====
from notebook_utils import device_widget

device = device_widget(exclude=["NPU"])

device

# ===== CELL 11 =====
from transformers import CLIPImageProcessor
from pathlib import Path
from diffusers.utils import load_image, export_to_video
from ov_stable_video_diffusion_helper import VAE_ENCODER_PATH, VAE_DECODER_PATH, MODEL_DIR, UNET_PATH, IMAGE_ENCODER_PATH
from lcm_scheduler import AnimateLCMSVDStochasticIterativeScheduler
import openvino as ov

# Load the conditioning image

image_path = Path("rocket.png")
if not image_path.exists():
    image = load_image("https://huggingface.co/datasets/huggingface/documentation-images/resolve/main/diffusers/svd/rocket.png?download=true")
    image = image.resize((512, 256))
    image.save(image_path)
else:
    image = load_image(str(image_path))

core = ov.Core()

vae_encoder = core.compile_model(VAE_ENCODER_PATH, device.value)
image_encoder = core.compile_model(IMAGE_ENCODER_PATH, device.value)
unet = core.compile_model(UNET_PATH, device.value)
vae_decoder = core.compile_model(VAE_DECODER_PATH, device.value)
scheduler = AnimateLCMSVDStochasticIterativeScheduler.from_pretrained(MODEL_DIR / "scheduler")
feature_extractor = CLIPImageProcessor.from_pretrained(MODEL_DIR / "feature_extractor")

# ===== CELL 13 =====
ov_pipe = OVStableVideoDiffusionPipeline(vae_encoder, image_encoder, unet, vae_decoder, scheduler, feature_extractor)

# ===== CELL 14 =====
import torch

frames = ov_pipe(
    image,
    num_inference_steps=4,
    motion_bucket_id=60,
    num_frames=8,
    height=320,
    width=512,
    generator=torch.manual_seed(12342),
).frames[0]

# ===== CELL 15 =====
out_path = Path("generated.mp4")

export_to_video(frames, str(out_path), fps=7)
frames[0].save(
    "generated.gif",
    save_all=True,
    append_images=frames[1:],
    optimize=False,
    duration=120,
    loop=0,
)

# ===== CELL 16 =====
from IPython.display import HTML

HTML('<img src="generated.gif">')

# ===== CELL 18 =====
from notebook_utils import quantization_widget

to_quantize = quantization_widget()

to_quantize

# ===== CELL 19 =====
# Fetch `skip_kernel_extension` module

ov_int8_pipeline = None
OV_INT8_UNET_PATH = MODEL_DIR / "unet_int8.xml"
OV_INT8_VAE_ENCODER_PATH = MODEL_DIR / "vae_encoder_int8.xml"
OV_INT8_VAE_DECODER_PATH = MODEL_DIR / "vae_decoder_int8.xml"

%load_ext skip_kernel_extension

# ===== CELL 21 =====
%%skip not $to_quantize.value

from typing import Any

import datasets
import numpy as np
from tqdm.notebook import tqdm
from IPython.utils import io


class CompiledModelDecorator(ov.CompiledModel):
    def __init__(self, compiled_model: ov.CompiledModel, data_cache = None, keep_prob: float = 0.5):
        super().__init__(compiled_model)
        self.data_cache = data_cache if data_cache is not None else []
        self.keep_prob = keep_prob

    def __call__(self, *args, **kwargs):
        if np.random.rand() <= self.keep_prob:
            self.data_cache.append(*args)
        return super().__call__(*args, **kwargs)


def collect_calibration_data(ov_pipe, calibration_dataset_size: int, num_inference_steps: int = 50):
    original_unet = ov_pipe.unet
    calibration_data = []
    ov_pipe.unet = CompiledModelDecorator(original_unet, calibration_data, keep_prob=1)

    dataset = datasets.load_dataset("fusing/instructpix2pix-1000-samples", split="train", streaming=False).shuffle(seed=42)
    # Run inference for data collection
    pbar = tqdm(total=calibration_dataset_size)
    for batch in dataset:
        image = batch["input_image"]

        with io.capture_output() as captured:
            ov_pipe(
                image,
                num_inference_steps=4,
                motion_bucket_id=60,
                num_frames=8,
                height=256,
                width=256,
                generator=torch.manual_seed(12342),
            )
        pbar.update(len(calibration_data) - pbar.n)
        if len(calibration_data) >= calibration_dataset_size:
            break

    ov_pipe.unet = original_unet
    return calibration_data[:calibration_dataset_size]

# ===== CELL 22 =====
%%skip not $to_quantize.value

if not OV_INT8_UNET_PATH.exists():
    subset_size = 200
    calibration_data = collect_calibration_data(ov_pipe, calibration_dataset_size=subset_size)

# ===== CELL 24 =====
%%skip not $to_quantize.value

from collections import deque

def get_operation_const_op(operation, const_port_id: int):
    node = operation.input_value(const_port_id).get_node()
    queue = deque([node])
    constant_node = None
    allowed_propagation_types_list = ["Convert", "FakeQuantize", "Reshape"]

    while len(queue) != 0:
        curr_node = queue.popleft()
        if curr_node.get_type_name() == "Constant":
            constant_node = curr_node
            break
        if len(curr_node.inputs()) == 0:
            break
        if curr_node.get_type_name() in allowed_propagation_types_list:
            queue.append(curr_node.input_value(0).get_node())

    return constant_node


def is_embedding(node) -> bool:
    allowed_types_list = ["f16", "f32", "f64"]
    const_port_id = 0
    input_tensor = node.input_value(const_port_id)
    if input_tensor.get_element_type().get_type_name() in allowed_types_list:
        const_node = get_operation_const_op(node, const_port_id)
        if const_node is not None:
            return True

    return False


def collect_ops_with_weights(model):
    ops_with_weights = []
    for op in model.get_ops():
        if op.get_type_name() == "MatMul":
            constant_node_0 = get_operation_const_op(op, const_port_id=0)
            constant_node_1 = get_operation_const_op(op, const_port_id=1)
            if constant_node_0 or constant_node_1:
                ops_with_weights.append(op.get_friendly_name())
        if op.get_type_name() == "Gather" and is_embedding(op):
            ops_with_weights.append(op.get_friendly_name())

    return ops_with_weights

# ===== CELL 25 =====
%%skip not $to_quantize.value

import nncf
import logging
from nncf.quantization.advanced_parameters import AdvancedSmoothQuantParameters

nncf.set_log_level(logging.ERROR)

if not OV_INT8_UNET_PATH.exists():
    diffusion_model = core.read_model(UNET_PATH)
    unet_ignored_scope = collect_ops_with_weights(diffusion_model)
    compressed_diffusion_model = nncf.compress_weights(diffusion_model, ignored_scope=nncf.IgnoredScope(types=['Convolution']))
    quantized_diffusion_model = nncf.quantize(
        model=compressed_diffusion_model,
        calibration_dataset=nncf.Dataset(calibration_data),
        subset_size=subset_size,
        model_type=nncf.ModelType.TRANSFORMER,
        # We additionally ignore the first convolution to improve the quality of generations
        ignored_scope=nncf.IgnoredScope(names=unet_ignored_scope + ["__module.conv_in/aten::_convolution/Convolution"]),
        advanced_parameters=nncf.AdvancedQuantizationParameters(smooth_quant_alphas=AdvancedSmoothQuantParameters(matmul=-1))
    )
    ov.save_model(quantized_diffusion_model, OV_INT8_UNET_PATH)

# ===== CELL 27 =====
%%skip not $to_quantize.value

nncf.set_log_level(logging.INFO)

if not OV_INT8_VAE_ENCODER_PATH.exists():
    text_encoder_model = core.read_model(VAE_ENCODER_PATH)
    compressed_text_encoder_model = nncf.compress_weights(text_encoder_model, mode=nncf.CompressWeightsMode.INT4_SYM, group_size=64)
    ov.save_model(compressed_text_encoder_model, OV_INT8_VAE_ENCODER_PATH)

if not OV_INT8_VAE_DECODER_PATH.exists():
    decoder_model = core.read_model(VAE_DECODER_PATH)
    compressed_decoder_model = nncf.compress_weights(decoder_model, mode=nncf.CompressWeightsMode.INT4_SYM, group_size=64)
    ov.save_model(compressed_decoder_model, OV_INT8_VAE_DECODER_PATH)

# ===== CELL 29 =====
%%skip not $to_quantize.value

ov_int8_vae_encoder = core.compile_model(OV_INT8_VAE_ENCODER_PATH, device.value)
ov_int8_unet = core.compile_model(OV_INT8_UNET_PATH, device.value, config={"DYNAMIC_QUANTIZATION_GROUP_SIZE":"0"})
ov_int8_decoder = core.compile_model(OV_INT8_VAE_DECODER_PATH, device.value)

ov_int8_pipeline = OVStableVideoDiffusionPipeline(
    ov_int8_vae_encoder, image_encoder, ov_int8_unet, ov_int8_decoder, scheduler, feature_extractor
)

int8_frames = ov_int8_pipeline(
    image,
    num_inference_steps=4,
    motion_bucket_id=60,
    num_frames=8,
    height=320,
    width=512,
    generator=torch.manual_seed(12342),
).frames[0]

# ===== CELL 30 =====
%%skip not $to_quantize.value

from IPython.display import display

int8_out_path = Path("generated_int8.mp4")

export_to_video(int8_frames, str(int8_out_path), fps=7)
int8_frames[0].save(
    "generated_int8.gif",
    save_all=True,
    append_images=int8_frames[1:],
    optimize=False,
    duration=120,
    loop=0,
)
display(HTML('<img src="generated_int8.gif">'))

# ===== CELL 32 =====
%%skip not $to_quantize.value

fp16_model_paths = [VAE_ENCODER_PATH, UNET_PATH, VAE_DECODER_PATH]
int8_model_paths = [OV_INT8_VAE_ENCODER_PATH, OV_INT8_UNET_PATH, OV_INT8_VAE_DECODER_PATH]

for fp16_path, int8_path in zip(fp16_model_paths, int8_model_paths):
    fp16_ir_model_size = fp16_path.with_suffix(".bin").stat().st_size
    int8_model_size = int8_path.with_suffix(".bin").stat().st_size
    print(f"{fp16_path.stem} compression rate: {fp16_ir_model_size / int8_model_size:.3f}")

# ===== CELL 34 =====
%%skip not $to_quantize.value

import time

def calculate_inference_time(pipeline, validation_data):
    inference_time = []
    for prompt in validation_data:
        start = time.perf_counter()
        with io.capture_output() as captured:
            _ = pipeline(
                image,
                num_inference_steps=4,
                motion_bucket_id=60,
                num_frames=8,
                height=320,
                width=512,
                generator=torch.manual_seed(12342),
            )
        end = time.perf_counter()
        delta = end - start
        inference_time.append(delta)
    return np.median(inference_time)

# ===== CELL 35 =====
%%skip not $to_quantize.value

validation_size = 3
validation_dataset = datasets.load_dataset("fusing/instructpix2pix-1000-samples", split="train", streaming=True).shuffle(seed=42).take(validation_size)
validation_data = [data["input_image"] for data in validation_dataset]

fp_latency = calculate_inference_time(ov_pipe, validation_data)
int8_latency = calculate_inference_time(ov_int8_pipeline, validation_data)
print(f"Performance speed-up: {fp_latency / int8_latency:.3f}")

# ===== CELL 37 =====
import ipywidgets as widgets

quantized_model_present = ov_int8_pipeline is not None

use_quantized_model = widgets.Checkbox(
    value=quantized_model_present,
    description="Use quantized model",
    disabled=not quantized_model_present,
)

use_quantized_model

# ===== CELL 38 =====
if not Path("gradio_helper.py").exists():
    r = requests.get(url="https://raw.githubusercontent.com/openvinotoolkit/openvino_notebooks/latest/notebooks/stable-video-diffusion/gradio_helper.py")
    open("gradio_helper.py", "w").write(r.text)

from gradio_helper import make_demo

pipeline = ov_int8_pipeline if use_quantized_model.value else ov_pipe

demo = make_demo(pipeline)

try:
    demo.queue().launch(debug=True)
except Exception:
    demo.queue().launch(debug=True, share=True)
# if you are launching remotely, specify server_name and server_port
# demo.launch(server_name='your server name', server_port='server port in int')
# Read more in the docs: https://gradio.app/docs/

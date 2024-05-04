import torch
import time
import time

import torch


def enable_GPU(model):
    if torch.cuda.is_available():
        torch.backends.cudnn.enabled = False
        model.cuda()
        print("CUDA available. Running on GPU")
    else:
        print("CUDA not available. Running on CPU")


def test_model_performance(stream, model):
    times = {}

    if torch.cuda.is_available():
        model.cuda()
        start_time = time.time()
        model.classify(stream)
        times['GPU'] = time.time() - start_time
        print("GPU time:", times['GPU'])
        torch.cuda.empty_cache()
    else:
        print("CUDA is not available. Cannot run on GPU.")

    model.cpu()  #
    start_time = time.time()
    model.classify(stream)
    times['CPU'] = time.time() - start_time
    print("CPU time:", times['CPU'])

    return times

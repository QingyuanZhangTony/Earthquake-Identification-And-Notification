import torch
import time
import time
import os
import torch
from obspy import UTCDateTime


def enable_GPU(model):
    if torch.cuda.is_available():
        torch.backends.cudnn.enabled = False
        model.cuda()
        print("CUDA available. Running on GPU")
    else:
        print("CUDA not available. Running on CPU")


def save_df_to_csv(df, date, path, identifier):
    date_str = date.strftime('%Y-%m-%d')

    # Ensure the target directory exists
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)

    # Construct file path
    filename = f"{date_str}.{identifier}.csv"
    path = os.path.join(path, filename)

    # Save DataFrame to CSV
    df.to_csv(path, index=False)  # index=False means do not write row index into the CSV file

    print(f"DataFrame saved to {path}")


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


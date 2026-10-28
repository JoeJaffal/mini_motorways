"""Persist model weights before attempting simulator recovery on Ctrl+C."""
from pathlib import Path
import signal


def save_checkpoint(model,path):
    path=Path(path).with_suffix('.zip')
    temporary=path.with_name(path.stem+'.saving.zip')
    model.save(temporary)
    temporary.replace(path)
    return path


def stop_and_save(model,env,callback,output):
    # Main process only; stop repeated Ctrl+C from interrupting serialization.
    signal.signal(signal.SIGINT,signal.SIG_IGN)
    path=save_checkpoint(model,Path(output)/'final.zip')
    print(f'CHECKPOINT SAVED | {path} | finishing worker shutdown',flush=True)
    try:
        if hasattr(env,'wait_pending'):env.wait_pending()
    except Exception as error:
        print(f'SHUTDOWN WARNING | {error} | model checkpoint is already safe',flush=True)
    try:callback.on_training_end()
    except Exception as error:
        print(f'REPLAY SAVE WARNING | {error} | existing best replay and final checkpoint retained',flush=True)

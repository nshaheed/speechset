import json
import multiprocessing as mp
import os
from typing import Callable, Dict, List, Optional, Tuple

import librosa
import numpy as np
from tqdm import tqdm

from .. import datasets


class DumpReader(datasets.DataReader):
    """Dumped loader
    """
    def __init__(self, data_dir: str, sr: Optional[int] = None):
        """Initializer.
        Args:
            data_dir: path to the mother directory.
            sr: target sampling rate.
        """
        prev_sr, self.speakers_, self.transcript = self.load_data(data_dir)
        assert not (sr is None and prev_sr is None), \
            'sampling rate not found, pass `sr` to the DumpReader'

        if prev_sr is None:
            # by assertion, `sr` is not None if `prev_sr` is None
            import warnings
            warnings.warn(
                'sampling rate of the `DumpReader` is not found on metadata'
                f', assume `sr`(={sr}) as native sampling rate of `DumpReader`')
            prev_sr = sr
        elif sr is None:
            # prev_sr is not None and sr is None
            sr = prev_sr
        # alias
        self.prev_sr, self.sr = prev_sr, sr

    def dataset(self) -> Dict[str, Tuple[int, str]]:
        """Return file reader.
        Returns:
            file-format datum read.er
        """
        return self.transcript
    
    def speakers(self) -> List[str]:
        """List of speakers.
        Returns:
            list of the speakers.
        """
        return self.speakers_

    def preproc(self) -> Callable:
        """Return data preprocessor.
        Returns:
            preprocessor.
        """
        return self.preprocessor

    def load_data(self, data_dir: str) -> Tuple[int, List[str], Dict[str, Tuple[int, str]]]:
        """Load the file lists.
        Args:
            data_dir: path to the mother directory.
        Returns:
            sampling rate, list of speakers and transcripts.
        """
        INTER = 'dumped'
        with open(os.path.join(data_dir, 'meta.json')) as f:
            meta = json.load(f)

        #speakers = [info['name'] for info in meta.values()]
        speakers = []

        for key, info in meta.items():
          if type(info) == Dict:
            speakers.append(info['name'])

        # transpose
        transcripts = {}
        for sid, info in meta.items():
            if not sid.isnumeric():
                continue

            sid = int(sid)
            for (i, text, _) in info['lists']:
                path = os.path.join(data_dir, INTER, f'{i}.npy')
                transcripts[path] = (sid, text)

        return meta.get('sr', None), speakers, transcripts

    def preprocessor(self, path: str) -> Tuple[int, str, np.ndarray]:
        """Load dumped.
        Args:
            path: str, path.
        Returns:
            tuple,
                sid: int, speaker id.
                text: str, text.
                audio: [np.float32; [T]], raw speech signal in range(-1, 1).
        """
        sid, text, audio = tuple(np.load(path, allow_pickle=True))
        if self.prev_sr != self.sr:
            # resampling
            audio = librosa.resample(audio, self.prev_sr, self.sr)
        return sid, text, audio

    @staticmethod
    def dumper(args) -> Tuple[int, int, str, str]:
        """Dumper, multiprocessing purpose.
        Args:
            i: int, index of the datasets.
            path: str, path to the original datum.
            preproc: Callable, preprocessor.
            out_dir: path to the output directory.
        Returns:
            i: index of the datasets.
            sid: speaker id.
            text: transcript.
            path: path to the original datum.
        """
        i, path, preproc, out_dir = args
        outputs = preproc(path)
        np.save(os.path.join(out_dir, f'{i}.npy'), outputs)

        sid, text, _ = outputs
        return i, sid, text, path

    @staticmethod
    def lookupDataReader(type: str) -> datasets.DataReader:
        match type:
            case 'LibriSpeech':
                return datasets.LibriSpeech
            case 'LibriTTS':
                return datasets.LibriTTS
            case 'LJSpeech':
                return datasets.LJSpeech
            case 'VCTK':
                return datasets.VCTK
            case _:
                print(f'Dataset type \"{type}\" was not found')
                return None

    @classmethod
    def dump(cls,
             reader: datasets.DataReader,
             out_dir: str,
             sr: Optional[int] = None,
             num_proc: Optional[int] = None,
             chunksize: int = 1):
        """Dump the reader.
        Args:
            reader: dataset reader.
            out_dir: path to the output directory.
            sr: sampling rate of input dataset reader.
            num_proc: the number of the process for multiprocessing.
            chunksize: size of the imap_unordered chunk.
        """
        INTER = 'dumped'
        os.makedirs(os.path.join(out_dir, INTER), exist_ok=True)

        speakers = reader.speakers()
        dataset, preproc = reader.dataset(), reader.preproc()

        meta = {
            sid: {'name': speaker, 'lists': []}
            for sid, speaker in enumerate(speakers)}
        meta['sr'] = sr

        if num_proc is None:
            for i, path in enumerate(tqdm(dataset)):
                outputs = preproc(path)
                np.save(os.path.join(out_dir, INTER, f'{i}.npy'), outputs)

                sid, text, _ = outputs
                meta[sid]['lists'].append((i, text, path))
        else:
            with mp.Pool(num_proc) as pool:
                worker = pool.imap_unordered(
                    DumpReader.dumper,
                    [
                        (i, path, preproc, os.path.join(out_dir, INTER))
                        for i, path in enumerate(dataset)],
                    chunksize=chunksize)
                for i, sid, text, path in tqdm(worker, total=len(dataset)):
                    meta[sid]['lists'].append((i, text, path))

        with open(os.path.join(out_dir, 'meta.json'), 'w') as f:
            json.dump(meta, f)


if __name__ == '__main__':
    def main():
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument('--out-dir', required=True)
        parser.add_argument('--num-proc', default=None, type=int)
        parser.add_argument('--chunksize', default=1, type=int)
        parser.add_argument('--default-sid', default=-1, type=int)
        parser.add_argument('--sr', default=22050, type=int)
        parser.add_argument('--config', required=True, type=str)
        args = parser.parse_args()

        # read json config file
        with open(args.config, 'r') as f:
            config = json.load(f)

        train_list = []
        test_list = []

        for name, dataset_info in config['train_data'].items():
            dataset = None
            data_path = dataset_info['data_path']
            sr = dataset_info.get('sr')

            dataset_type = DumpReader.lookupDataReader(dataset_info['type'])
            train_list.append(dataset_type(data_path, sr))

        for name, dataset_info in config['test_data'].items():
            dataset = None
            data_path = dataset_info['data_path']
            sr = dataset_info.get('sr')

            dataset_type = DumpReader.lookupDataReader(dataset_info['type'])
            test_list.append(dataset_type(data_path, sr))

        train_reader = datasets.ConcatReader(train_list)
        test_reader = datasets.ConcatReader(test_list)


        train_out_dir = config['train_dump_path']
        test_out_dir = config['test_dump_path']

        # Dump out training and test data
        DumpReader.dump(
            train_reader,
            train_out_dir,
            args.sr,
            args.num_proc,
            args.chunksize)

        DumpReader.dump(
            test_reader,
            test_out_dir,
            args.sr,
            args.num_proc,
            args.chunksize)
        
    main()

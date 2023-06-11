import os
from typing import List, Optional

import numpy as np

from .reader import DataReader


class Opencpop(DataReader):
    """ Opencpop dataset loader. """

    SR = 44100

    def __init__(self, data_dir: str, sr: Optional[int] = None, output_sr: Optional[int] = None):
        """Initializer.
        Args:
            data_dir: dataset directory.
            sr: sampling rate.
        """

        self.sr = sr or Opencpop.SR
        self.output_sr = output_sr or self.sr
        self.speakers_, self.transcript = self.load_data(data_dir)

    def speakers(self) -> List[str]:
        return self.speakers_

    def dataset(self) -> List[str]:
        return self.transcript

    def load_data(self, data_dir: str) -> List[str]:
        """Load audio. This is sort of backward because atm
        because VocalSet doesn't have any transcriptions.
        Args:
            data_dir: dataset directory.
        Returns:
            loaded data, speaker list, transcripts.
        """

        trans = {}
        # singers = os.listdir(data_dir)
        singers = ['opencpop']

        print(data_dir, singers)
        for root, dirs, files in os.walk(data_dir):
            for file in files:
                if not file.endswith('.wav'):
                    continue

                fullpath = os.path.join(root, file)
                # print(f'{fullpath}')
                # don't need any text where we're going
                trans[fullpath] = (0, '')

        return singers, trans
                                       
            

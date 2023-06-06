import os
from typing import List, Optional

import numpy as np

from .reader import DataReader


class VocalSet(DataReader):
    """ VocalSet dataset loader. """

    SR = 44100

    def __init__(self, data_dir: str, sr: Optional[int] = None):
        """Initializer.
        Args:
            data_dir: dataset directory.
            sr: sampling rate.
        """

        self.sr = sr or VocalSet.SR
        self.singers_, self.transcript = self.load_data(data_dir)

    def speakers(self) -> List[str]:
        return self.singers_

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
        data_dir = os.path.join(data_dir, 'FULL')
        singers = os.listdir(data_dir)
        for sid, singer in enumerate(singers):
            # print(f'{singer=}')

            for root, dirs, files in os.walk(os.path.join(data_dir, singer)):
                for file in files:
                    if not file.endswith('.wav'):
                        continue

                    fullpath = os.path.join(root, file)
                    # print(f'{fullpath}')
                    # don't need any text where we're going
                    trans[fullpath] = (sid, '')

        return singers, trans
                                       
            

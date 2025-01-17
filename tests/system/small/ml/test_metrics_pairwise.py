# Copyright 2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import numpy as np
import pandas as pd

from bigframes.ml import metrics
import bigframes.pandas as bpd


def test_cosine_similarity():
    x_col = [np.array([4.1, 0.5, 1.0])]
    y_col = [np.array([3.0, 0.0, 2.5])]
    X = bpd.read_pandas(pd.DataFrame({"X": x_col}))
    Y = bpd.read_pandas(pd.DataFrame({"Y": y_col}))

    result = metrics.pairwise.cosine_similarity(X, Y)
    expected_pd_df = pd.DataFrame(
        {"X": x_col, "Y": y_col, "cosine_similarity": [0.108199]}
    )

    pd.testing.assert_frame_equal(
        result.to_pandas(), expected_pd_df, check_dtype=False, check_index_type=False
    )

#!/bin/bash

set -eo pipefail
pushd "$(dirname "${BASH_SOURCE[0]}")" > /dev/null

source ../../common/load_env.sh

pushd "$PROJECT_ROOT" > /dev/null

python -m scripts.local.paper.helper.generate_vote_for_discontinuities_data
python -m scripts.local.paper.helper.generate_scanline_counts_table
python -m scripts.local.paper.helper.generate_resolutions_table
python -m scripts.local.paper.helper.generate_per_beam_metrics_table
python -m scripts.local.paper.helper.generate_ablation_table
python -m scripts.local.paper.helper.generate_range_image_metrics_table
python -m scripts.local.paper.helper.generate_range_image_qualitative
python -m scripts.local.paper.helper.generate_alice_times_table
python -m scripts.local.paper.helper.generate_rtst_metrics_table_and_figure
python -m scripts.local.paper.helper.generate_rtst_times_table

popd > /dev/null
popd > /dev/null

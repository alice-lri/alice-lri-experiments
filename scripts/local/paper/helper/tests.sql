SELECT name AS dataset,
       dfe.dataset_frame_id NOT IN (
           SELECT DISTINCT dataset_frame_id
           FROM dataset_frame_scanline_info_empirical
           WHERE points_count < 64
       ) AS robust,
       dfe.scanlines_count AS truth, ifr.scanlines_count AS pred, COUNT(*) AS count
FROM dataset d
         INNER JOIN main.dataset_frame df ON d.id = df.dataset_id
         INNER JOIN main.intrinsics_frame_result ifr ON df.id = ifr.dataset_frame_id
         INNER JOIN main.dataset_frame_empirical dfe ON df.id = dfe.dataset_frame_id
WHERE experiment_id == 38
GROUP BY name, robust, dfe.scanlines_count, ifr.scanlines_count


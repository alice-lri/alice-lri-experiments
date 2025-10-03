SELECT name AS dataset,
       dfe.dataset_frame_id NOT IN (SELECT DISTINCT dataset_frame_id
                                    FROM dataset_frame_scanline_info_empirical
                                    WHERE points_count < 64) AS robust,
       dfe.scanlines_count AS truth,
       ifr.scanlines_count AS pred,
       COUNT(*) AS count
FROM dataset d
         INNER JOIN main.dataset_frame df ON d.id = df.dataset_id
         INNER JOIN main.intrinsics_frame_result ifr ON df.id = ifr.dataset_frame_id
         INNER JOIN main.dataset_frame_empirical dfe ON df.id = dfe.dataset_frame_id
WHERE experiment_id == 38
GROUP BY name, robust, dfe.scanlines_count, ifr.scanlines_count;

SELECT e.id AS exp_id,
       e.use_hough_continuity,
       e.use_scanline_conflict_solver,
       e.use_vertical_heuristics,
       e.use_horizontal_heuristics,
       d.name AS dataset,
       dfe.dataset_frame_id NOT IN (SELECT DISTINCT dataset_frame_id
                                    FROM dataset_frame_scanline_info_empirical
                                    WHERE points_count < ?) AS robust,
       COUNT(CASE WHEN dfe.scanlines_count != ifr.scanlines_count THEN 1 END) AS incorrect_count
FROM dataset d
         INNER JOIN main.dataset_frame df ON d.id = df.dataset_id
         INNER JOIN main.intrinsics_frame_result ifr ON df.id = ifr.dataset_frame_id
         INNER JOIN main.experiment e ON e.id = ifr.experiment_id
         INNER JOIN main.dataset_frame_empirical dfe ON df.id = dfe.dataset_frame_id
GROUP BY exp_id, dataset, robust;



SELECT e.id AS exp_id,
       e.use_hough_continuity,
       e.use_scanline_conflict_solver,
       e.use_vertical_heuristics,
       e.use_horizontal_heuristics,
       d.name AS dataset,
       COALESCE(dfsie.dataset_frame_id NOT IN (SELECT DISTINCT dataset_frame_id
                                               FROM dataset_frame_scanline_info_empirical
                                               WHERE points_count < ?), 0) AS robust,
       COUNT(CASE
                 WHEN COALESCE(dfsie.horizontal_resolution, -1) != COALESCE(irsi.horizontal_resolution, -1)
                     THEN 1 END) AS incorrect_count
FROM dataset d
         INNER JOIN dataset_frame df ON df.dataset_id = d.id
         INNER JOIN intrinsics_frame_result ifr ON ifr.dataset_frame_id = df.id
         INNER JOIN experiment e ON e.id = ifr.experiment_id
         INNER JOIN dataset_frame_scanline_info_empirical dfsie ON dfsie.dataset_frame_id = df.id
         LEFT JOIN intrinsics_result_scanline_info irsi ON irsi.intrinsics_result_id = ifr.id
    AND irsi.scanline_idx = dfsie.scanline_idx
GROUP BY exp_id, dataset, robust;


WITH ri_data AS (
    SELECT dataset, method, ri_width, ri_height, chamfer, max_range,
           10 * log(max_range * max_range / original_to_reconstructed_mse) / log(10) as psnr,
           sampling_error, experiment_id
    FROM (
             SELECT experiment_id, d.name AS dataset, rfs.method AS method, ri_width, ri_height, original_to_reconstructed_mse,
                    (original_to_reconstructed_rmse + reconstructed_to_original_rmse) / 2 AS chamfer,
                    (original_points_count - reconstructed_points_count) / original_points_count * 100 as sampling_error,
                    (CASE
                         WHEN d.name = 'kitti'  THEN 120
                         WHEN d.name = 'durlar' THEN 200
                    END) AS max_range
             FROM ri_frame_result AS rfs
                  JOIN dataset_frame df ON rfs.dataset_frame_id = df.id
                  JOIN dataset d ON df.dataset_id = d.id
         )
)
SELECT dataset, method, ri_width, ri_height,
       AVG(chamfer) AS avg_cd, MAX(chamfer) AS max_cd,
       AVG(psnr) AS avg_psnr, MIN(psnr) AS min_psnr,
       AVG(sampling_error) AS avg_se, MAX(sampling_error) AS max_se
FROM ri_data
WHERE experiment_id = 2
GROUP BY dataset, method, ri_width, ri_height
ORDER BY dataset DESC, method DESC, ri_width, ri_height;

